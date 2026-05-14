# Deployment Guide

This guide covers going from "compose up" to a hardened production install.

---

## 1. Environment hardening

| Setting              | Dev default                       | Production                                  |
|----------------------|-----------------------------------|---------------------------------------------|
| `JWT_SECRET`         | `change-me-...` (demo bypass on)  | **MUST set** to `openssl rand -hex 32`     |
| `ALLOW_DEMO_BYPASS`  | `true`                            | Auto-disables once JWT_SECRET is non-default |
| `DEBUG`              | `true`                            | `false`                                     |
| `LOG_JSON`           | `false`                           | `true` for ELK / Loki ingestion             |
| `DATABASE_DRIVER`    | `sqlite`                          | `postgresql`                                |
| `CORS_ORIGINS`       | `["http://localhost:5173", ...]`  | Only your real frontend URL(s)              |
| `SEED_ADMIN_PASSWORD`| `admin123`                        | Strong, or rotate immediately after seed    |

> The demo bypass that accepts `Bearer demo` is **automatically disabled** the moment `JWT_SECRET` is changed away from the default. This is enforced in `config.Settings.demo_bypass_active`. You can't accidentally ship demo auth to prod.

---

## 2. PostgreSQL migration

### 2a. Spin up Postgres
Uncomment the `postgres:` service in `docker-compose.yml`, then:
```bash
docker compose up -d postgres
```

### 2b. Switch backend to PostgreSQL
In `.env`:
```env
DATABASE_DRIVER=postgresql
DATABASE_URL_PROD=postgresql+asyncpg://erp:erp@postgres:5432/erp
```

### 2c. Apply schema
```bash
# Generate the first migration (only the very first time)
docker compose exec backend alembic revision --autogenerate -m "init"

# Apply migrations
docker compose exec backend alembic upgrade head

# Re-run seed
docker compose exec backend python -m scripts.seed
```

> Note: SQLAlchemy `Boolean.is_(True)` syntax was used in services for portability — works on both SQLite and Postgres.

---

## 3. Reverse proxy + HTTPS

Example nginx in front of the stack (TLS-terminating):

```nginx
server {
    listen 443 ssl http2;
    server_name erp.example.com;
    ssl_certificate     /etc/letsencrypt/live/erp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erp.example.com/privkey.pem;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_buffering off;          # SSE
        proxy_read_timeout 1d;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    location / { proxy_pass http://localhost:5173; }
    location /war-room/ { proxy_pass http://localhost:8080/; }
}
```

Then redirect 80 → 443 and run `certbot --nginx`.

---

## 4. MESH factory rollout

For each remote factory:

1. Provision a small VM with Docker + persistent VPN to HQ.
2. Set environment:
   ```env
   FACTORY_ID=factory-c
   FACTORY_NAME=Factory C
   PORT=8003
   HQ_URL=https://erp.example.com
   ```
3. `docker run` only the `backend` image with `command: python factory_node.py`.
4. Node auto-registers with HQ on startup.

**Data sovereignty**: the factory node serves only `/api/factory/*` endpoints which return aggregated results. The local DB and any local LLM (Ollama / Qwen) stay on-premise — raw rows never traverse the WAN.

---

## 5. Observability

- **Logs**: stdout JSON (`LOG_JSON=true`) → ship to Loki / ELK.
- **Health**: `/api/health` (used by Compose & K8s liveness probes).
- **Metrics**: drop in `prometheus-fastapi-instrumentator` and add a `/metrics` route.
- **Audit trail**: every write goes into `audit_logs` (background, non-blocking).
- **Decision log**: AI-triggered actions go into `decision_logs` for after-action review.

---

## 6. Smoke test checklist

Run these after `docker compose up -d --build && docker compose exec backend python -m scripts.seed`:

```bash
# 1. Health
curl -s http://localhost:8000/api/health | jq

# 2. Login (real user)
curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token

# 3. List parts (use Bearer demo if bypass is on)
curl -s http://localhost:8000/api/inventory/parts \
  -H 'Authorization: Bearer demo' | jq length

# 4. Below-safety
curl -s http://localhost:8000/api/inventory/below-safety \
  -H 'Authorization: Bearer demo' | jq

# 5. Create + receive PO (round-trip)
# (omitted — see /docs interactive UI)

# 6. SSE stream
curl -N http://localhost:8000/api/events/stream | head -50

# 7. Chat (requires LLM_API_KEY)
curl -s -X POST http://localhost:8000/api/chat-v2 \
  -H 'Authorization: Bearer demo' \
  -H 'Content-Type: application/json' \
  -d '{"message":"列出庫存低於安全庫存的零件","session_id":"smoke-1"}' | jq
```

All seven should return 200 and meaningful payloads.

---

## 7. Upgrade path

Schema changes:
```bash
alembic revision --autogenerate -m "your change"
# review the generated migration file in alembic/versions/
alembic upgrade head
```

Code changes: rebuild backend image only:
```bash
docker compose up -d --build backend
```

---

## 8. Backup & DR

- **DB**: nightly `pg_dump` for PostgreSQL; `cp erp.db erp-$(date +%F).db` for SQLite.
- **Audit**: rotated weekly into cold storage.
- **MESH nodes**: each maintains its own backup; HQ doesn't need to restore them.

---

## 9. Known limitations / next steps

- WO completion does NOT yet auto-create a finished-goods inventory entry — that requires mapping `Product` ↔ `Part`, which is intentionally deferred.
- MRP is one-level explosion. For multi-level recursive explosion, traverse `BOMItem.parent_bom_id` in `services/mps_mrp.py:run_mrp`.
- Approval workflow tables exist (`approval_flows`, `approval_requests`, `approval_records`) but no UI yet — only schema and the `check_approval_step_valid` rule.
- The `factory_node.py` mesh-query endpoint is a stub; wire it to your local DB queries when deploying per-site.

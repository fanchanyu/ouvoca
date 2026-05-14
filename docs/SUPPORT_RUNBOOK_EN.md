# LLM-ERP Support Runbook (English)

> **What to do when things break — for customer IT or our support staff**
> Designed so you can self-resolve 90% by following this; only the last 10% needs us.

---

## 📑 Contents

1. [Severity Tiers](#1-severity-tiers)
2. [Quick Symptom Lookup](#2-quick-symptom-lookup)
3. [System Won't Start](#3-system-wont-start)
4. [API Slow / Timeout](#4-api-slow--timeout)
5. [LLM Unreachable](#5-llm-unreachable)
6. [SSE Push Not Received](#6-sse-push-not-received)
7. [Database Locked](#7-database-locked)
8. [Under Attack](#8-under-attack)
9. [Daily Monitoring SOP](#9-daily-monitoring-sop)
10. [Emergency Upgrade vs Rollback](#10-emergency-upgrade-vs-rollback)

---

## 1. Severity Tiers

| Level | Description | Response | Handler |
|---|---|---|---|
| **🔴 P0** | System fully down / data corruption | Immediate | Vendor + Customer IT both |
| **🟠 P1** | Core functions broken (cannot login / order) | Within 1 hour | Vendor |
| **🟡 P2** | Some function abnormal but workaround exists | Within 8 hours | Vendor |
| **🟢 P3** | UI bug / typo | Within 1 week | Vendor |

---

## 2. Quick Symptom Lookup

| Symptom | Try First | Details |
|---|---|---|
| Browser shows nothing | `docker compose ps`, see which container is down | §3 |
| Login then blank page | F12 → Console errors; likely JWT_SECRET changed | §3.4 |
| Inventory query hangs | Check backend log for N+1 query | §4 |
| AI chat "Connection error" | Check `/api/health` `llm_provider` status | §5 |
| Owner LINE Bot silent | Check Cloudflare Tunnel + LINE Channel webhook URL | §6 |
| "Database is locked" | SQLite write contention | §7 |
| Sudden 429 Too Many Requests | Rate limit triggered, possible attack | §8 |

---

## 3. System Won't Start

### 3.1 Check container status

```bash
docker compose ps
```

`Exit X` → that service crashed.

### 3.2 Backend startup failure

```bash
docker compose logs backend | tail -50
```

Common errors:

| Log Message | Cause | Fix |
|---|---|---|
| `JWT_SECRET still default` | No secret set | Edit `.env` → `JWT_SECRET=$(openssl rand -hex 32)` |
| `OperationalError: no such table` | Migration not run | `docker compose exec backend alembic upgrade head` |
| `Connection refused: postgres` | DB not running | `docker compose up -d db` |
| `ImportError` | Incomplete upgrade | `git status` to find missing files |

### 3.3 Frontend won't start

```bash
docker compose logs frontend | tail -30
```

Common: nginx config typo → check `nginx.conf`.

### 3.4 Login then blank page

90% it's "JWT_SECRET changed, old tokens invalid but browser still caches".

Fix:
1. Browser DevTools → Application → Clear site data
2. Re-login

---

## 4. API Slow / Timeout

### 4.1 Find slow endpoint

```bash
docker compose logs backend | grep "took" | sort -k 9 -nr | head -10
```

### 4.2 Common Causes

| Cause | Evidence | Fix |
|---|---|---|
| N+1 query | Log shows many sequential SELECTs | Add `selectinload` in service |
| LLM slow | Only chat endpoint slow | §5 |
| Disk full | "disk full" warning | Clean old data / add storage |
| Missing index | Big table + slow query | `EXPLAIN` + add index |

### 4.3 Emergency throttle

If some endpoint is being hammered:

```bash
# Rate limit built-in; tighten via .env
RATE_LIMIT_ENABLED=true
docker compose restart backend
```

---

## 5. LLM Unreachable

### 5.1 Confirm health

```bash
curl http://localhost:8000/api/health | jq .llm_provider
# Should return "deepseek" / "claude" etc., not null
```

### 5.2 Test API Key

```bash
docker compose exec backend python -c "
from app.config import settings
print('Provider:', settings.LLM_PROVIDER)
print('API key set:', bool(settings.LLM_API_KEY))
print('Model:', settings.LLM_MODEL)
"
```

### 5.3 Provider-Specific Outages

| Provider | 503 Workaround |
|---|---|
| Claude | Wait 5 min / switch to DeepSeek temporarily |
| OpenAI | Same |
| DeepSeek | China DC sometimes unstable; switch to local Ollama |
| Ollama | Confirm Ollama service alive: `curl http://ollama:11434/api/tags` |

### 5.4 Emergency Degrade to Demo Mode

```bash
# .env
LLM_PROVIDER=disabled
docker compose restart backend
# All chat endpoints return demo message (no error); other functions normal
```

---

## 6. SSE Push Not Received

### 6.1 Check nginx config

```bash
docker compose exec frontend cat /etc/nginx/conf.d/default.conf | grep -A 5 "/api/events"
```

Must include:
```
proxy_buffering off;
proxy_cache off;
chunked_transfer_encoding off;
```

### 6.2 Test SSE channel

```bash
curl -N http://localhost:8000/api/events/stream
# Should see heartbeat every 10 seconds
```

If silent → nginx buffering not disabled.

### 6.3 LINE Bot Webhook not receiving

- Cloudflare Tunnel up? `cloudflared tunnel list`
- LINE Channel webhook URL set correctly?
- Signature validation passing? Check backend log.

---

## 7. Database Locked

"Database is locked" almost always = SQLite write contention.

### 7.1 Immediate Fix

```bash
docker compose restart backend
```

### 7.2 Long-term Fix

Upgrade to PostgreSQL:

```bash
# .env
DATABASE_URL=postgresql+asyncpg://erp:password@db:5432/erp
# Also edit docker-compose.yml to add PostgreSQL service
```

See `docs/ADMIN_GUIDE.md` "Upgrade to PostgreSQL" section.

---

## 8. Under Attack

### 8.1 Detection

Run daily:

```bash
docker compose logs backend | grep -E "429|risk_flagged|injection" | wc -l
```

Sudden spike → possible attack.

### 8.2 Immediate Actions

1. **Tighten rate limit** (edit `.env`):
   ```
   RATE_LIMIT_LLM_CHAT=5/minute  # drop from 30 to 5
   ```
2. **Disable LLM temporarily** (if it's an LLM cost attack): `LLM_PROVIDER=disabled`
3. **Add firewall rules**: `deny` blacklist IP in nginx
4. **Check audit log** to identify source:
   ```bash
   docker compose exec backend python -m scripts.audit_query \
       --period 1h --filter "status_code=429"
   ```

### 8.3 Report + Add Whitelist

Once attack source identified:
- Whitelist in nginx (only allow customer's office IP)
- Notify customer IT to rotate VPN

---

## 9. Daily Monitoring SOP

### 9.1 Daily (Automated)

Add to crontab:

```cron
# Daily 09:00 health check + LINE notify
0 9 * * * /opt/llm-erp/scripts/daily_health_check.sh
```

`daily_health_check.sh`:

```bash
#!/bin/bash
cd /opt/llm-erp
HEALTH=$(curl -s http://localhost:8000/api/health)
LINE_TOKEN=$YOUR_LINE_NOTIFY_TOKEN

if [ "$(echo $HEALTH | jq -r .status)" != "ok" ]; then
    curl -X POST https://notify-api.line.me/api/notify \
         -H "Authorization: Bearer $LINE_TOKEN" \
         -d "message=⚠️ LLM-ERP health check failed: $HEALTH"
fi
```

### 9.2 Weekly

- Check `GET /api/analytics/ai-cost` — no overspend
- `docker compose logs backend | grep ERROR | wc -l` should be < 10
- Run `bash scripts/run_gates.sh` — 8 gates all green

### 9.3 Monthly

- Run backup script
- Run `scripts/data_quality_check`
- Monthly review with customer

---

## 10. Emergency Upgrade vs Rollback

### 10.1 Standard Upgrade

```bash
cd /opt/llm-erp
git fetch && git checkout v2.5  # specify version, not `main`
docker compose pull
docker compose up -d --build
# Run migrations
docker compose exec backend alembic upgrade head
# Verify
bash scripts/run_gates.sh
```

### 10.2 Rollback After Bad Upgrade

```bash
cd /opt/llm-erp
docker compose down
# Restore data
cp /opt/backup/erp-pre-upgrade.db erp.db
# Revert version
git checkout v2.4
docker compose up -d --build
```

**Pre-requisite**: Always backup before upgrade:
`docker compose exec backend cp /app/erp.db /tmp/erp-$(date +%F).db`

---

## 📞 If You're Stuck

| Severity | Contact |
|---|---|
| P0 system down | 24/7 phone (Pro+) / LINE @llmerp |
| P1 core broken | Business-day office hours |
| P2/P3 | support@llm-erp.example |

---

**Chinese version**: [`SUPPORT_RUNBOOK_ZH.md`](./SUPPORT_RUNBOOK_ZH.md)
**Last updated**: 2026-05-14 · v2.5

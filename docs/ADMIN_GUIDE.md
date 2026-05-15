# Admin Guide 管理員指南 — v3.0

> **本文件給：** IT 管理員 / 系統管理者 / 部署人員
> **For:** IT admins, system administrators, deployers

> ⚡ **v3.0 戰略軸轉通知 / Strategic Pivot Notice**
> §4.2「外協廠加入 / Outsource partner onboarding」於 v3.0 下架（外協 persona 砍掉）。
> 客戶反饋觸發後復活，詳見 ROADMAP Phase 7。

---

## 1. 系統架構 · System Architecture

請見 [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)。

---

## 2. 第一次部署 · First Deployment

### 2.1 環境需求 · Requirements

| 項目 | 最低 | 建議 |
|---|---|---|
| OS | Linux / macOS / Windows + WSL2 | Linux Ubuntu 22.04 |
| Docker | 20.10+ | 24.0+ |
| RAM | 2 GB | 4 GB+ |
| Disk | 5 GB | 20 GB |
| Python (本地開發) | 3.12 | 3.12 |
| Node.js (本地開發) | 20+ | 20 LTS |

### 2.2 一鍵部署

```bash
git clone <your-repo> opnetest
cd opnetest
cp backend/.env.example backend/.env
# 編輯 backend/.env（至少改 JWT_SECRET）
vi backend/.env
docker compose up -d --build
docker compose exec backend python -m scripts.seed
```

### 2.3 環境變數 · Environment Variables

詳見 `backend/.env.example`。關鍵幾項：

| 變數 | 預設 | 生產建議 |
|---|---|---|
| `JWT_SECRET` | `change-me-...` | **務必修改**（`openssl rand -hex 32`） |
| `DATABASE_DRIVER` | `sqlite` | `postgresql`（生產） |
| `LLM_PROVIDER` | `deepseek` | 視成本/隱私選擇 |
| `LLM_API_KEY` | `(空)` | 設定後 AI 助手才能用 |
| `LOG_LEVEL` | `INFO` | 生產用 `INFO`，debug 用 `DEBUG` |
| `LOG_JSON` | `false` | 生產 `true`（給 ELK / Loki） |
| `ALLOW_DEMO_BYPASS` | `true` | 設了 `JWT_SECRET` 後自動失效 |

> ⚠️ **重要**：`JWT_SECRET` 不改就會保留 Bearer "demo" 後門。設了之後 demo 自動消失。

---

## 3. 帳號與權限管理

### 3.1 預設角色

系統內建 **11 個角色**（透過 `scripts/seed_permissions.py` 載入）：

| 角色 code | 中文 | 對應 persona | 主要 scope |
|---|---|---|---|
| `super_admin` | 系統管理員 | IT | all（全域）|
| `boss` | 老闆 | 王董 | tenant（本廠）|
| `plant_manager` | 廠長 | 林廠長 | tenant |
| `sales_manager` | 業務主管 | – | tenant |
| `sales_rep` | 業務員 | 小陳 | own（只看自己）|
| `purchaser` | 採購 | 阿玲（採） | tenant |
| `warehouse_keeper` | 倉管 | 阿玲（倉） | tenant |
| `accountant` | 會計 | – | tenant |
| `inspector` | 品檢員 | – | tenant |
| `operator` | 作業員 | – | assigned（指派的）|
| `outsource_partner` | 外協廠 | 老吳 | assigned |

### 3.2 建立新員工

**步驟**（透過桌面 UI）：

1. 登入 admin
2. 進 **🛡️ 權限管理**（必要時複製內建角色為客製版）
3. 用 API 或 UI 建員工
4. 建使用者帳號（關聯員工）
5. 透過 `POST /api/permission/assignments` 指派角色

**步驟**（用 curl 範例）：

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# 建員工
curl -X POST http://localhost:8000/api/organization/employees \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"employee_no":"E0010","name":"張三","email":"san@example.com","department_id":"<id>"}'

# 建帳號
curl -X POST http://localhost:8000/api/auth/register \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"san","password":"changeme123","employee_id":"<emp-id>"}'

# 指派 sales_rep 角色
curl -X POST http://localhost:8000/api/permission/assignments \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"user_id":"<user-id>","role_id":"<sales-rep-role-id>","tenant_id":"<hq-id>","reason":"新進員工"}'
```

### 3.3 臨時授權（如代理）

```bash
# 給某人額外開放一個權限 7 天
curl -X POST http://localhost:8000/api/permission/overrides \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "user_id":"<user-id>",
    "permission_code":"purchase.order.export",
    "grant_or_revoke":"grant",
    "reason":"協助 5 月底結帳",
    "expires_at":"2026-05-31T23:59:59"
  }'
```

### 3.4 變更稽核

所有授權變更都寫入 `permission_audit` 表：

```bash
# 直接查 DB
docker compose exec backend python -c "
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.permission import PermissionAudit
async def q():
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(PermissionAudit).order_by(PermissionAudit.created_at.desc()).limit(10)
        )).scalars().all()
        for r in rows:
            print(f'{r.created_at} | {r.change_type} | actor={r.actor_id} target={r.target_user_id}')
asyncio.run(q())
"
```

---

## 4. 多廠 MESH 部署

### 4.1 加入新工廠節點

1. 申請新 tenant：
   ```bash
   curl -X POST http://localhost:8000/api/permission/tenants \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{
       "code": "FACTORY-D",
       "name": "高雄分廠",
       "tenant_type": "factory",
       "parent_id": "<hq-id>",
       "mesh_role": "node"
     }'
   ```

2. 在新廠機台部署 `factory_node.py`：
   ```bash
   FACTORY_ID=factory-d FACTORY_NAME="高雄分廠" \
   PORT=8004 HQ_URL=https://hq.example.com \
   python factory_node.py
   ```

3. 確認 HQ 看得到：
   ```bash
   curl http://localhost:8004/api/factory/health
   ```

### 4.2 外協廠加入

外協廠**不需獨立部署**——他們只用 LINE：
1. 主廠 ERP 列印含 QR 的派工單給外協廠
2. 外協廠掃 QR、用 LINE Bot 回報

設定：見 Phase 1 LINE Bot 設定文件。

---

## 5. 資料管理

### 5.1 備份

```bash
# SQLite (dev)
docker compose exec backend cp /app/erp.db /app/data/erp-$(date +%F).db

# PostgreSQL (prod)
docker compose exec postgres pg_dump -U erp erp | gzip > /backup/erp-$(date +%F).sql.gz
```

建議 cron：每日 03:00、保留 7 天滾動 + 月底永久保留。

### 5.2 還原

```bash
# SQLite
docker compose down
cp /backup/erp-2026-05-14.db opnetest/backend/erp.db
docker compose up -d

# PostgreSQL
docker compose exec postgres psql -U erp -c "DROP DATABASE erp; CREATE DATABASE erp;"
zcat /backup/erp-2026-05-14.sql.gz | docker compose exec -T postgres psql -U erp erp
```

### 5.3 資料生命週期

詳見 [DATA_LIFECYCLE.md](./DATA_LIFECYCLE.md)。

關鍵：
- `audit_logs` 預估 5 年 ~900 萬筆 → 規劃 90 天歸檔
- `conversation_logs` 365 天 TTL 自動清理
- 業務交易表永久保留

---

## 6. 監控與健康檢查

### 6.1 健康端點

```bash
curl http://localhost:8000/api/health
# {"status":"ok","app":"LLM-ERP","version":"2.0.0","db":"ok","llm_provider":"deepseek","demo_bypass":true}
```

### 6.2 Docker healthcheck

`docker-compose.yml` 已內建：
```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
  interval: 30s
  timeout: 5s
  retries: 5
```

### 6.3 觀測性（Phase 7 規劃）

- Prometheus exporter
- Grafana dashboards
- Loki log aggregation
- OpenTelemetry traces

---

## 7. 升級流程

```bash
# 1. 備份
docker compose exec backend python -m scripts.backup  # (Phase 1.5)

# 2. 停服
docker compose down

# 3. 拉取新版
git pull origin main

# 4. 重 build
docker compose up -d --build

# 5. 跑 migration
docker compose exec backend alembic upgrade head

# 6. 驗證
curl http://localhost:8000/api/health
```

### 7.1 SQLite → PostgreSQL 切換

詳見 [DEPLOYMENT.md §2](./DEPLOYMENT.md)。

---

## 8. 安全檢查清單

部署到生產前**必做**：

- [ ] `JWT_SECRET` 已改成隨機 64 字元
- [ ] `DEBUG=false`
- [ ] `LOG_JSON=true`
- [ ] `CORS_ORIGINS` 只設真實 frontend URL
- [ ] Demo 帳號 `admin` 改強密碼 / 停用
- [ ] HTTPS 已配置（nginx + Let's Encrypt）
- [ ] Database password 強密碼
- [ ] 備份策略已上線
- [ ] 監控 / 告警已上線
- [ ] 防火牆只開必要 port（80/443，內部 5432）

---

## 9. 常用診斷命令

```bash
# 看 backend log
docker compose logs -f backend --tail 100

# 進 backend container debug
docker compose exec backend bash

# 直接連 DB
docker compose exec backend python  # 啟動 REPL，再 from app.database import AsyncSessionLocal

# 列出所有 tables
docker compose exec backend python -c "
from app.core.base import Base
import app.models
for t in sorted(Base.metadata.tables.keys()): print(t)
"

# 列出所有 routes
docker compose exec backend python -c "
from app.main import app
for r in app.routes:
    if hasattr(r, 'methods'):
        print(','.join(sorted(r.methods - {'HEAD'})), r.path)
"

# 重 seed（會刪掉所有資料）
docker compose exec backend rm -f /app/erp.db
docker compose exec backend python -m scripts.seed
```

---

## 10. 聯絡支援

- **內部 IT**：(your contact)
- **Github Issues**：(your repo URL)
- **緊急熱線**：(your hotline)

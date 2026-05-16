# erpilot — Conversational AI-Native ERP for SMB Manufacturers

> **The desktop conversational ERP for 50–100 person factories — talk to it, no training required.**
> 給 50-100 人小型製造業的桌機對話式 ERP — 講話就能查/增/改/刪，AI 取代教育訓練。

[![Tests](https://img.shields.io/badge/tests-287%20passing-brightgreen)]()
[![Gates](https://img.shields.io/badge/self--verify-7%2F7%20green-brightgreen)]()
[![Docs](https://img.shields.io/badge/PDFs-35%20bilingual-blue)]()
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](./LICENSE)
[![Version](https://img.shields.io/badge/version-3.12-blueviolet)]()

> ⚡ **v3.0 戰略軸轉（2026-05-15）**：砍 LINE Bot / Mobile App / 外協協同三線，全力做桌機對話式 ERP。
> 細節見 [`CLAUDE.md` §10](./CLAUDE.md)。

---

## 🔐 First-time setup: install secret-scanning hook (10 秒)

**這是強制流程。** 避免 API key / DB / .env 被誤推：

```bash
# Mac / Linux / Git Bash
bash scripts/git-hooks/install_hooks.sh

# Windows
scripts\git-hooks\install_hooks.bat
```

之後每次 `git commit` 都會自動掃 `sk-` / `ghp_` / hardcoded password 等樣式，
偵測到立刻拒絕 commit。詳見 `scripts/git-hooks/pre-commit`。

---

## 🚀 一鍵啟動開發環境（30 秒）

無需 Docker。Windows 雙擊 `start_dev.bat`，會自動完成：

```
[1/5] 檢查 Python 3.12+ / Node 20+
[2/5] 若無 backend/.env → 從 .env.example 複製
[2/5] 若無 backend/erp.db → 自動 seed（admin/admin123 + 10 零件 + 4 客戶/供應商）
[2/5] 若無 frontend-desktop/node_modules → 自動 npm install
[3/5] 釋放占用的 :8000 / :5173 port
[3/5] 開新視窗起 backend uvicorn :8000
[4/5] 等 backend healthcheck 綠燈
[4/5] 開新視窗起 frontend vite :5173
[5/5] 等 frontend ready
      → 自動打開瀏覽器 http://localhost:5173

登入：admin / admin123
```

**關閉**：雙擊 `stop_dev.bat`（會用 port 5173/8000 精準找 PID 殺，不會誤殺其他 Python/Node）。

### 啟用 AI 對話（選做，5 分鐘）

```bash
# backend/.env
LLM_API_KEY=<YOUR_REAL_KEY_HERE_FROM_PROVIDER_CONSOLE>

# Windows 開發環境若 SSL 證書驗證失敗（DeepSeek 常見）
LLM_VERIFY_SSL=false
```

改完跑 `stop_dev.bat` → `start_dev.bat` 重啟。

### 想用 Docker 完整正式模式？

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.seed
open http://localhost:5173
```

詳見 [`docs/INSTALLATION_ZH.md`](./docs/INSTALLATION_ZH.md)。

---

## What's inside
- **FastAPI backend** with 12 business domains (Inventory, Purchase, Production, MPS/MRP, Quality, Sales, Accounting, Warehouse, CRM, HR, AI Governance)
- **Multi-Agent LLM Engine** — 10 agents, **40 tools**（22 read / 4 soft-write / 14 hard-write），DeepSeek 為預設供應商
- **ConfirmCard 確認卡** — hard-write 操作出卡，使用者點「確認」才執行（5 分鐘 TTL + Slot-filling 反問 + 90 秒 Undo）
- **Schema Mapping AI** — exact/alias/partial 3 級 confidence，把外部 DB（鼎新/正航/Excel）一鍵接進來
- **Event Engine** with EventBus, 16+ ConstraintChecker rules, and SSE broadcasting
- **React + Vite + Tailwind** desktop frontend — 完整 CRUD UI（EntityRowActions + EntityFormModal）
- **War-room HTML dashboard** that live-streams events via SSE
- **MESH factory nodes** (VMI-friendly: raw data never leaves the factory)
- **5-layer RBAC** + 多租戶隔離（TenantMixin + with_loader_criteria 自動過濾）
- **7-gate Self-Verification** suite (~290s, all green)
- **Pre-commit secret-scan hook** — sk-/ghp_/xoxb-/JWT_SECRET 模式自動攔截
- **Docker Compose** orchestration with health-checks + **Alembic** async migrations + seed script

---

## 60-Second Quickstart (Docker)

```bash
cd opnetest
cp backend/.env.example backend/.env       # optionally edit LLM_API_KEY etc.
docker compose up -d --build
docker compose exec backend python -m scripts.seed
```

Open in your browser:

| Service        | URL                              | Notes                                          |
|----------------|----------------------------------|------------------------------------------------|
| Desktop UI     | http://localhost:5173            | Login: `admin / admin123` or "Demo Mode"       |
| API docs       | http://localhost:8000/docs       | OpenAPI / Swagger                              |
| War Room       | http://localhost:8080            | Real-time event dashboard                      |
| Factory A      | http://localhost:8001/api/factory/health | MESH node health                         |
| Factory B      | http://localhost:8002/api/factory/health |                                          |

---

## Local Dev (no Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env                                 # adjust values
python -m scripts.seed                               # seeds DB + admin user
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend-desktop
npm install
npm run dev    # http://localhost:5173
```

### War Room

Just open `war-room/index.html` in a browser — it will connect to `http://localhost:8000`.

---

## Architecture

```
┌──────────────────┐  ┌─────────────┐
│  Desktop UI      │  │  War Room   │
│  (Vite/React +   │  │  (HTML+SSE) │
│   Chat + Confirm)│  │             │
└──────┬───────────┘  └──────┬──────┘
       │                     │
       └─────────────────────┘
                         │ HTTPS + Bearer JWT
              ┌──────────▼───────────┐
              │   FastAPI Backend     │
              │ ┌───────────────────┐ │
              │ │  Auth/Audit MW    │ │
              │ │  Exception MW     │ │
              │ └─────────┬─────────┘ │
              │           │           │
              │  ┌────────▼────────┐  │
              │  │ 12 Domain APIs  │  │
              │  │ + Multi-Agent   │  │
              │  │ + Event Engine  │  │
              │  │ + SSE stream    │  │
              │  └────────┬────────┘  │
              │           │           │
              │  SQLAlchemy Async + Alembic │
              │  SQLite(dev) / Postgres(prod)│
              └──────────┬───────────┘
                         │ VPN / structured queries
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
  Factory A          Factory B         Factory C
  (FastAPI:8001)    (FastAPI:8002)    (FastAPI:8003)
  Local DB / LLM    Local DB / LLM    Local DB / LLM
  ★ Raw data never leaves; only aggregates returned (VMI-friendly)
```

---

## Domain Map

| Domain          | API prefix           | Models                              | Agent           |
|-----------------|----------------------|-------------------------------------|-----------------|
| Auth & Org      | `/api/auth`, `/api/organization` | Department, Employee, User, Role | (none)          |
| Inventory       | `/api/inventory`     | Part, Inventory, InventoryTransaction | InventoryAgent |
| Purchase        | `/api/purchase`      | Supplier, PurchaseOrder, POItem     | PurchaseAgent   |
| Production      | `/api/production`    | Product, BOMItem, ProductionOrder, Operation | ProductionAgent |
| MPS / MRP       | `/api/mps-mrp`       | MpsMaster, MpsEntry, MrpMaster, MrpItem | MpsMrpAgent  |
| Quality         | `/api/quality`       | InspectionOrder, NonConformance, CAPA | QualityAgent  |
| Sales           | `/api/sales`         | Customer, SalesOrder, SalesOrderItem | SalesAgent     |
| Accounting      | `/api/accounting`    | Account, JournalEntry, AR, MonthEndClose | AccountingAgent |
| Warehouse       | `/api/warehouse`     | Zone, BinLocation, PickTask, CycleCount | WarehouseAgent |
| CRM             | `/api/crm`           | Lead, Opportunity, CrmEvent         | CrmAgent        |
| Events / SSE    | `/api/events`        | (in-memory ring buffer)             | —               |
| Chat            | `/api/chat-v2`       | ConversationLog                     | GeneralAgent    |

---

## Try the AI Assistant

After seeding, log in and go to **AI 助手**, then ask:

- 「列出庫存低於安全庫存的零件」 → InventoryAgent → `list_below_safety`
- 「進行中的工單有哪些？」 → ProductionAgent → `query_work_order`
- 「列出進行中的不良品 (NC)」 → QualityAgent → `list_non_conformances`
- 「本月有逾期的應收帳款嗎？」 → AccountingAgent → `list_receivables`

Each request: classifies intent → picks agent → builds scoped tool list → loops up to 5 tool-call rounds → returns natural-language answer.

---

## Try the Event Stream

1. Open **/events** in the desktop UI **and** http://localhost:8080 (war-room).
2. Trigger an event from another page — e.g. create a new Part (`/inventory`).
3. Watch both dashboards receive a `part.created` event in real time.

Or via curl:
```bash
curl -N http://localhost:8000/api/events/stream
```

---

## Production Switch-over (PostgreSQL)

1. Edit `.env`:
   ```
   DATABASE_DRIVER=postgresql
   DATABASE_URL_PROD=postgresql+asyncpg://user:pass@host:5432/erp
   JWT_SECRET=<openssl rand -hex 32>    # disables demo bypass automatically
   ```
2. Uncomment the `postgres` service block in `docker-compose.yml`.
3. Run migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

---

## File Layout

```
opnetest/
├── backend/
│   ├── app/
│   │   ├── core/          ← Base, logging, exceptions, deps
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── middleware/    ← auth, audit
│   │   ├── models/        ← 12 domain models (60+ tables)
│   │   ├── schemas/       ← Pydantic schemas
│   │   ├── services/      ← Business logic per domain
│   │   ├── api/           ← FastAPI routers per domain
│   │   ├── events/        ← EventBus, 16+ constraint rules
│   │   └── agents/        ← engine + 10 domain tool/agent modules
│   ├── scripts/
│   │   └── seed.py        ← seed parts/products/customers/admin
│   ├── alembic/           ← migrations
│   ├── factory_node.py    ← MESH node
│   ├── Dockerfile
│   └── requirements.txt
├── frontend-desktop/
│   ├── src/
│   │   ├── lib/api.ts     ← typed API client
│   │   ├── store/auth.ts  ← Zustand auth + persist
│   │   ├── pages/         ← 8 pages
│   │   └── components/Layout.tsx
│   ├── Dockerfile
│   └── nginx.conf
├── war-room/
│   ├── index.html         ← live SSE dashboard
│   └── Dockerfile
└── docker-compose.yml
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for production deployment details.

---

## Try the Conversational CRUD (v3.x 旗艦功能)

對 AI 助手講：
- **查**：「列出庫存低於安全庫存的零件」
- **增**：「跟長江廠下 100 個 M6 螺絲，交期下週五」→ **ConfirmCard** 出卡，點確認才下單
- **改**：「把 SO-2025-0042 的交期改到 6/10」→ ConfirmCard 出卡
- **刪/取消**：「取消 PO-2025-0099」→ ConfirmCard 出卡 + 90 秒內可 Undo

缺欄位時 AI 會**反問**（slot-filling），不會憑空編造。詳見：
- [`docs/CONVERSATIONAL_ERP_DESIGN_ZH.md`](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) — 6 層架構 + 7 設計原則
- [`docs/demos/deepseek_e2e_latest.md`](./docs/demos/deepseek_e2e_latest.md) — 真實 DeepSeek 跑 9/9 killer moments 全通（50 秒、21 tool calls）

---

## License

**AGPL-3.0** — see [LICENSE](./LICENSE).

簡單版說明：你可以自由使用、修改、商業部署本專案，但若你提供修改後的版本（包含 SaaS 託管），**你的修改必須以 AGPL 同等條款開源**。
適合社群協作 + 防大廠白嫖閉源轉售。商業授權（需閉源整合 / 嵌入專有產品）請洽專案維護者。

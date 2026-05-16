# erpilot — Conversational AI-Native ERP for SMB Manufacturers

> 🇹🇼 **給 50-100 人小型製造業的桌機對話式 ERP** — 講話就能查/增/改/刪，AI 取代教育訓練。
>
> 🇺🇸 **The desktop conversational ERP for 50–100 person factories** — talk to it, no training required.

[![Tests](https://img.shields.io/badge/tests-287%20passing-brightgreen)]()
[![Gates](https://img.shields.io/badge/self--verify-7%2F7%20green-brightgreen)]()
[![Docs](https://img.shields.io/badge/PDFs-35%20bilingual-blue)]()
[![License](https://img.shields.io/badge/license-AGPL--3.0%20%2B%20SBL%20%2B%20Commercial-blue)](./LICENSE)
[![Version](https://img.shields.io/badge/version-3.12-blueviolet)]()
[![Author](https://img.shields.io/badge/by-Peter-lightgrey)](https://github.com/fanchanyu)

> ⚡ **v3.0 戰略軸轉 / Strategic Pivot (2026-05-15)**
> 🇹🇼 砍 LINE Bot / Mobile App / 外協協同三線，全力做桌機對話式 ERP。
> 🇺🇸 Cut LINE Bot / Mobile App / external-vendor portals — focused 100% on desktop conversational ERP.
> See [`CLAUDE.md` §10](./CLAUDE.md) for the full rationale.

---

## 📑 目錄 / Table of Contents

- [⚡ 一句話價值主張 / 30-Second Pitch](#-一句話價值主張--30-second-pitch)
- [🔐 First-time setup](#-first-time-setup--首次設定-secret-scanning-hook)
- [🚀 30 秒啟動 / Quick Start](#-30-秒啟動--quick-start-30-seconds)
- [🎯 內含什麼 / What's Inside](#-內含什麼--whats-inside)
- [🏗 架構 / Architecture](#-架構--architecture)
- [🗺 領域對照 / Domain Map](#-領域對照--domain-map)
- [🤖 對話式 CRUD 範例 / Try the Conversational CRUD](#-對話式-crud-範例--try-the-conversational-crud)
- [📡 即時事件流 / Try the Event Stream](#-即時事件流--try-the-event-stream)
- [🐘 Production 切換 PostgreSQL / Production Switch-over](#-production-切換-postgresql--production-switch-over)
- [📂 檔案結構 / File Layout](#-檔案結構--file-layout)
- [⚖️ 三軌授權 / Tri-License Model](#️-三軌授權--tri-license-model)
- [🤝 貢獻 / Contributing](#-貢獻--contributing)

---

## ⚡ 一句話價值主張 / 30-Second Pitch

🇹🇼 **erpilot 是台灣中小製造業的對話式 ERP**：員工坐在電腦前打一句話（「跟長江廠下 100 個 M6 螺絲，交期下週五」），AI 就把它變成完整的採購單，跳出 ConfirmCard 確認卡讓你按確認才執行。**不用學系統、不用教育訓練、2 小時上手**。20 人以內的小公司**完全免費**用整套（含鼎新 / 正航 connector）。

🇺🇸 **erpilot is a conversational ERP for Taiwan SMB manufacturers.** Your staff types one sentence ("Order 100 M6 bolts from ChangJiang, delivery next Friday") and the AI turns it into a full purchase order, presenting a ConfirmCard for human approval before executing. **No training required, ready in 2 hours**. **Completely free for organizations with ≤20 concurrent users**, including closed-source connectors for 鼎新 / 正航 / SAP.

| 為什麼選 erpilot? / Why erpilot? | 我們的解法 / Our Answer |
|---|---|
| 🇹🇼 SAP / Oracle 太貴 / Too expensive | NT$30-50 万/年（小小企業 ≤20 人 NT$0）|
| 🇹🇼 員工不愛學系統 / No one wants training | 用講的就會用，AI 取代訓練 |
| 🇹🇼 改個欄位要等 IT 顧問 / IT bottleneck | Schema Mapping AI 自助接外部 DB |
| 🇹🇼 老闆要看數字 / Boss wants real-time data | Chat 一句話拿到老闆儀表板 |
| 🇹🇼 怕 AI 亂操作 / AI hallucination fear | ConfirmCard 強制人工確認 + 90 秒 Undo |

---

## 🔐 First-time setup — 首次設定 secret-scanning hook

🇹🇼 **這是強制流程**，避免 API key / DB 密碼 / .env 被誤推到 GitHub：
🇺🇸 **Mandatory step** — prevents accidental commit of API keys / DB passwords / .env files:

```bash
# Mac / Linux / Git Bash
bash scripts/git-hooks/install_hooks.sh

# Windows
scripts\git-hooks\install_hooks.bat
```

🇹🇼 之後每次 `git commit` 都會自動掃 `sk-` / `ghp_` / `xoxb-` / hardcoded password 等樣式，偵測到立刻拒絕 commit。
🇺🇸 Every `git commit` now scans for `sk-` / `ghp_` / `xoxb-` / hardcoded password patterns and refuses to commit if found.

詳見 / See `scripts/git-hooks/pre-commit`.

---

## 🚀 30 秒啟動 / Quick Start (30 seconds)

### 方式 A：開發環境 / Dev Mode (no Docker needed)

🇹🇼 Windows 雙擊 `start_dev.bat`，會自動完成：
🇺🇸 On Windows, double-click `start_dev.bat`. It will automatically:

```
[1/5] 檢查 Python 3.12+ / Node 20+         Verify Python 3.12+ / Node 20+
[2/5] 自動 seed admin/admin123 + sample data Auto-seed admin user + sample data
[3/5] 釋放占用的 :8000 / :5173 port         Free up ports :8000 / :5173
[4/5] 等 backend healthcheck 綠燈           Wait for backend healthcheck
[5/5] 自動打開 http://localhost:5173        Auto-open browser

登入 / Login: admin / admin123
```

🇹🇼 **關閉**：雙擊 `stop_dev.bat`（精準 PID kill 不誤殺其他 Python/Node）。
🇺🇸 **Stop**: double-click `stop_dev.bat` (precise PID kill — won't affect other processes).

### 方式 B：Docker 完整正式模式 / Full Docker Mode

```bash
cd opnetest
cp backend/.env.example backend/.env       # optionally edit LLM_API_KEY
docker compose up -d --build
docker compose exec backend python -m scripts.seed
```

| 服務 / Service  | URL                              | 說明 / Notes                            |
|----------------|----------------------------------|----------------------------------------|
| Desktop UI     | http://localhost:5173            | 登入 / Login: `admin / admin123`        |
| API docs       | http://localhost:8000/docs       | OpenAPI / Swagger                      |
| War Room       | http://localhost:8080            | 即時事件儀表板 / Real-time dashboard     |
| Factory A      | http://localhost:8001/api/factory/health | MESH 節點健康 / Node health      |
| Factory B      | http://localhost:8002/api/factory/health |                                |

### 啟用 AI 對話 / Enable AI Chat (optional, 5 min)

```bash
# backend/.env
LLM_API_KEY=<YOUR_KEY_FROM_DEEPSEEK_OR_ANTHROPIC_OR_OPENAI>

# Windows 開發環境若 SSL 證書驗證失敗（DeepSeek 常見）
# If SSL verification fails on Windows (common with DeepSeek)
LLM_VERIFY_SSL=false
```

🇹🇼 改完跑 `stop_dev.bat` → `start_dev.bat` 重啟。
🇺🇸 Restart with `stop_dev.bat` → `start_dev.bat`.

詳細安裝指南 / Detailed install guide: [`docs/INSTALLATION_ZH.md`](./docs/INSTALLATION_ZH.md) · [`docs/INSTALLATION_EN.md`](./docs/INSTALLATION_EN.md)

---

## 🎯 內含什麼 / What's Inside

| 模組 / Module | 中文 | English |
|---|---|---|
| **FastAPI backend** | 12 個業務領域（庫存/採購/生產/MPS/MRP/品質/銷售/會計/倉儲/CRM/HR/AI 治理）| 12 business domains (Inventory, Purchase, Production, MPS/MRP, Quality, Sales, Accounting, Warehouse, CRM, HR, AI Governance) |
| **Multi-Agent LLM Engine** | 10 agents、**40 tools**（22 read / 4 soft-write / 14 hard-write），DeepSeek 為預設供應商 | 10 agents, **40 tools** (22 read / 4 soft-write / 14 hard-write), DeepSeek as default LLM provider |
| **ConfirmCard 確認卡** | hard-write 操作出卡，使用者點「確認」才執行（5 分鐘 TTL + Slot-filling 反問 + 90 秒 Undo）| Hard-write actions issue confirmation cards; user must click "confirm" to execute (5-min TTL + slot-filling reverse-ask + 90s undo) |
| **Schema Mapping AI** | exact/alias/partial 3 級 confidence，把外部 DB（鼎新/正航/Excel）一鍵接進來 | 3-tier confidence mapping (exact/alias/partial) — one-click external DB integration (鼎新/正航/Excel) |
| **Event Engine** | EventBus + 16+ ConstraintChecker 規則 + SSE 廣播 | EventBus + 16+ ConstraintChecker rules + SSE broadcasting |
| **React + Vite + Tailwind** | 桌機前端，完整 CRUD UI（EntityRowActions + EntityFormModal）| Desktop frontend with full CRUD UI (reusable EntityRowActions + EntityFormModal components) |
| **War-room dashboard** | HTML + SSE 即時事件儀表板 | HTML + SSE live event dashboard |
| **MESH factory nodes** | VMI 友善：原始資料不離廠 | VMI-friendly: raw data never leaves the factory |
| **5-layer RBAC** | 多租戶隔離（TenantMixin + with_loader_criteria 自動過濾）| Multi-tenant isolation (TenantMixin + auto-filter via with_loader_criteria) |
| **7-gate Self-Verification** | ~290s 全綠才能 commit / push | ~290s suite, must be green before commit/push |
| **Pre-commit secret-scan** | sk-/ghp_/xoxb-/JWT_SECRET 模式自動攔截 | Auto-blocks commits with sk-/ghp_/xoxb-/JWT_SECRET patterns |
| **Docker Compose + Alembic** | 健康檢查 + async migration + seed 腳本 | Health checks + async migrations + seed script |

---

## 🏗 架構 / Architecture

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
  ★ 原始資料不離廠 / Raw data stays local; only aggregates returned (VMI-friendly)
```

🇹🇼 **VMI 友善設計**：每個工廠跑自己的本地 erpilot 節點（factory_node.py），中央只拿聚合資料、不直接存取原始細目，符合代工廠對「客戶資料保密」的硬性要求。
🇺🇸 **VMI-friendly design**: Each factory runs its own local erpilot node (factory_node.py); the central instance only receives aggregates, never raw details — meeting the strict data confidentiality requirements of contract manufacturers.

---

## 🗺 領域對照 / Domain Map

| 領域 / Domain   | API 路徑 / Prefix    | 模型 / Models                       | Agent           |
|-----------------|----------------------|-------------------------------------|-----------------|
| Auth & Org      | `/api/auth`, `/api/organization` | Department, Employee, User, Role | (none)          |
| Inventory 庫存   | `/api/inventory`     | Part, Inventory, InventoryTransaction | InventoryAgent |
| Purchase 採購    | `/api/purchase`      | Supplier, PurchaseOrder, POItem     | PurchaseAgent   |
| Production 生產  | `/api/production`    | Product, BOMItem, ProductionOrder, Operation | ProductionAgent |
| MPS / MRP       | `/api/mps-mrp`       | MpsMaster, MpsEntry, MrpMaster, MrpItem | MpsMrpAgent  |
| Quality 品質     | `/api/quality`       | InspectionOrder, NonConformance, CAPA | QualityAgent  |
| Sales 銷售       | `/api/sales`         | Customer, SalesOrder, SalesOrderItem | SalesAgent     |
| Accounting 會計  | `/api/accounting`    | Account, JournalEntry, AR, MonthEndClose | AccountingAgent |
| Warehouse 倉儲   | `/api/warehouse`     | Zone, BinLocation, PickTask, CycleCount | WarehouseAgent |
| CRM             | `/api/crm`           | Lead, Opportunity, CrmEvent         | CrmAgent        |
| Events / SSE    | `/api/events`        | (in-memory ring buffer)             | —               |
| Chat            | `/api/chat-v2`       | ConversationLog                     | GeneralAgent    |

---

## 🤖 對話式 CRUD 範例 / Try the Conversational CRUD

🇹🇼 對 AI 助手講以下任一句話：
🇺🇸 Talk to the AI Assistant with any of these:

| 操作 / Action | 範例 / Example |
|---|---|
| **查 / Read** | 「列出庫存低於安全庫存的零件」 / "List parts below safety stock" |
| **增 / Create** | 「跟長江廠下 100 個 M6 螺絲，交期下週五」→ **ConfirmCard** 出卡，點確認才下單<br>"Order 100 M6 bolts from ChangJiang, delivery next Friday" → **ConfirmCard** appears |
| **改 / Update** | 「把 SO-2025-0042 的交期改到 6/10」→ ConfirmCard 出卡<br>"Change SO-2025-0042 delivery date to 6/10" → ConfirmCard appears |
| **刪 / Delete** | 「取消 PO-2025-0099」→ ConfirmCard + 90 秒內可 Undo<br>"Cancel PO-2025-0099" → ConfirmCard + 90s undo window |

🇹🇼 缺欄位時 AI 會**反問**（slot-filling），不會憑空編造。
🇺🇸 When fields are missing, the AI **asks back** (slot-filling) instead of hallucinating.

詳見 / See:
- 🇹🇼 [`docs/CONVERSATIONAL_ERP_DESIGN_ZH.md`](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) — 6 層架構 + 7 設計原則
- 🇺🇸 [`docs/CONVERSATIONAL_ERP_DESIGN_EN.md`](./docs/CONVERSATIONAL_ERP_DESIGN_EN.md) — 6-layer architecture + 7 design principles
- 🎬 [`docs/demos/deepseek_e2e_latest.md`](./docs/demos/deepseek_e2e_latest.md) — 真實 DeepSeek 跑 9/9 killer moments 全通（50 秒、21 tool calls）/ Real DeepSeek run: 9/9 killer moments passed in 50s with 21 tool calls

---

## 📡 即時事件流 / Try the Event Stream

🇹🇼 同時打開兩個視窗：
🇺🇸 Open two windows:

1. **/events** in the desktop UI (http://localhost:5173/events)
2. **War Room** at http://localhost:8080

🇹🇼 從第三個視窗觸發事件（例：`/inventory` 新增料件），兩個 dashboard 都會即時收到 `part.created` 事件。
🇺🇸 Trigger an event from a third window (e.g., create a Part in `/inventory`); both dashboards receive `part.created` in real time.

或用 curl / Or via curl:
```bash
curl -N http://localhost:8000/api/events/stream
```

---

## 🐘 Production 切換 PostgreSQL / Production Switch-over

🇹🇼 開發用 SQLite，正式上線改 PostgreSQL：
🇺🇸 Dev uses SQLite; production switches to PostgreSQL:

1. 編輯 `.env` / Edit `.env`:
   ```
   DATABASE_DRIVER=postgresql
   DATABASE_URL_PROD=postgresql+asyncpg://user:pass@host:5432/erp
   JWT_SECRET=<openssl rand -hex 32>    # disables demo bypass automatically
   ```

2. 取消 `docker-compose.yml` 中 `postgres` 服務的註解 / Uncomment the `postgres` service in `docker-compose.yml`.

3. 跑 migration / Run migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

詳見 / See [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## 📂 檔案結構 / File Layout

```
opnetest/
├── backend/                    ← FastAPI 後端 / Backend
│   ├── app/
│   │   ├── core/              ← Base, logging, exceptions, deps
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── middleware/        ← auth, audit
│   │   ├── models/            ← 12 領域模型 / 12 domain models (60+ tables)
│   │   ├── schemas/           ← Pydantic schemas
│   │   ├── services/          ← 商業邏輯 / Business logic per domain
│   │   ├── api/               ← FastAPI routers per domain
│   │   ├── events/            ← EventBus, 16+ constraint rules
│   │   └── agents/            ← engine + 10 domain tool/agent modules
│   ├── scripts/seed.py        ← seed parts/products/customers/admin
│   ├── alembic/               ← migrations
│   ├── factory_node.py        ← MESH 節點 / MESH node
│   ├── Dockerfile
│   └── requirements.txt
├── frontend-desktop/           ← React 桌機 UI / Desktop frontend
│   ├── src/
│   │   ├── lib/api.ts         ← typed API client
│   │   ├── store/auth.ts      ← Zustand auth + persist
│   │   ├── i18n/              ← 中英雙語 / EN+ZH translations
│   │   ├── pages/             ← 8 pages
│   │   └── components/Layout.tsx
│   ├── Dockerfile
│   └── nginx.conf
├── war-room/                   ← 即時事件儀表板 / Live SSE dashboard
│   ├── index.html
│   └── Dockerfile
├── docs/                       ← 35 份雙語文件 / 35 bilingual docs
│   ├── CONVERSATIONAL_ERP_DESIGN_ZH.md / _EN.md
│   ├── COMMERCIAL_LICENSING_FAQ_ZH.md
│   └── ... (32 more)
├── LICENSE                     ← AGPL-3.0
├── LICENSE-SMALL-BUSINESS.md   ← 🌱 ≤20 人完全免費 / Free tier license
├── LICENSE-COMMERCIAL.md       ← 🔵 商業授權說明 / Commercial license info
├── CLA.md                      ← Contributor License Agreement (bilingual)
├── CONTRIBUTING.md
└── docker-compose.yml
```

---

## ⚖️ 三軌授權 / Tri-License Model

🇹🇼 erpilot 同時提供三種授權，依你的情境選擇：
🇺🇸 erpilot offers three license tracks — choose based on your scenario:

| 軌道 / Track | 條款 / Terms | 適用 / For | 費用 / Cost |
|---|---|---|---|
| 🟢 **AGPL 開源軌 / Open-source** | [AGPL-3.0](./LICENSE) | 🇹🇼 願意揭露 source 的所有人<br>🇺🇸 Anyone willing to disclose source | **免費 / Free** |
| 🌱 **小小企業軌 / Small Business** | [Small Business License](./LICENSE-SMALL-BUSINESS.md) | 🇹🇼 **≤ 20 concurrent users** 的單一公司，非 ISV / SaaS<br>🇺🇸 Single company with ≤20 concurrent users; non-ISV, non-SaaS | **完全免費（含閉源 connector）/ Fully free (incl. closed-source connectors)** |
| 🔵 **商業軌 / Commercial** | 個別協商 / Individually negotiated | 🇹🇼 > 20 users、ISV / OEM、SaaS provider、大企業<br>🇺🇸 >20 users, ISV/OEM, SaaS provider, enterprise | 🇹🇼 個別報價<br>🇺🇸 Custom pricing |

> 🌱 **「20 人以內全免費」戰略 / "Free for ≤20 users" strategy**
>
> 🇹🇼 對齊 erpilot「**讓小小企業也快速上手**」承諾。Taiwan SMB 1-20 人廠把整套（含鼎新 / 正航 / SAP connector）拿去白用，等你長到 21 人並離不開 erpilot 再聊商業合約。
>
> 🇺🇸 Aligned with erpilot's promise to help small businesses get started fast. Taiwan SMBs (1-20 employees) get the full suite — including 鼎新 / 正航 / SAP connectors — for free. Talk commercial contract only when you grow past 20 and can't live without it.

🇹🇼 不確定哪一軌？看 [`LICENSE-COMMERCIAL.md`](./LICENSE-COMMERCIAL.md) 決策樹。
🇺🇸 Not sure which track? See the decision tree in [`LICENSE-COMMERCIAL.md`](./LICENSE-COMMERCIAL.md).

詳細 FAQ / Detailed FAQ: [`docs/COMMERCIAL_LICENSING_FAQ_ZH.md`](./docs/COMMERCIAL_LICENSING_FAQ_ZH.md)

---

## 🤝 貢獻 / Contributing

🇹🇼 歡迎 PR！第一次貢獻請先看 [`CONTRIBUTING.md`](./CONTRIBUTING.md) + 簽 [`CLA.md`](./CLA.md)（DCO-style，`git commit -s` 即可）。
🇺🇸 PRs welcome! First-time contributors please read [`CONTRIBUTING.md`](./CONTRIBUTING.md) and sign the [`CLA.md`](./CLA.md) (DCO-style — just use `git commit -s`).

CLA Section 2(b) 是 dual-license 模式的命脈：你的 contribution 授權 maintainer 用任何條款（含商業）再授權。沒這條，整條商業軌作廢。
CLA Section 2(b) is the lifeline of the dual-license model: your contributions grant the maintainer the right to relicense under any terms (including commercial). Without it, the commercial track collapses.

---

## 📊 專案數據 / Project Stats

| 維度 / Metric | 數值 / Value |
|---|---|
| Backend tests | 287 passing |
| Self-verification gates | 7/7 green (~290s) |
| Bilingual PDFs | 35 |
| Domain models | 60+ tables across 12 domains |
| Multi-Agent tools | 40 (22 read / 4 soft-write / 14 hard-write) |
| Frontend pages | 10 (含 Permissions 管理) |
| Lines of code | ~50,000 (Python + TypeScript + docs) |
| Repo created | 2026-04 |
| Public since | 2026-05-16 |

---

<sub>by [Peter](https://github.com/fanchanyu) · [Issues](https://github.com/fanchanyu/erpilot/issues) · [Commercial License](./LICENSE-COMMERCIAL.md)</sub>

# LLM-ERP User Manual (English) — v3.0

> **Version**: v3.0.0 (Conversational ERP)
> **Audience**: Owner, Sales, Plant Manager, Purchaser/Warehouse, Inspector, Accountant
> **Language**: System supports both 繁體中文 and English with on-the-fly switching

> ⚡ **v3.0 Strategic Pivot Notice (2026-05-15)**
> The following features have been removed in v3.0:
> - **Mobile App chapter**: replaced by desktop Chat full CRUD
> - **Outsource partner chapter (formerly §5.5)**: outsource persona deprecated
> - **LINE Bot chapter**: replaced by desktop Toast + Email digest
>
> If other chapters still mention mobile/LINE/outsource, treat them as deprecated (moved to Phase 7 pending customer feedback).

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Quick Start (5 Minutes)](#2-quick-start)
3. [Login & Language Switching](#3-login--language)
4. [Navigation](#4-navigation)
5. [Role-based Guide](#5-role-based-guide)
6. [Using the AI Assistant](#6-using-the-ai-assistant)
7. [FAQ](#7-faq)
8. [Keyboard Shortcuts](#8-keyboard-shortcuts)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. System Overview

### 1.1 What is LLM-ERP?

LLM-ERP is an **AI-Native ERP** designed for **small manufacturers (10-100 employees)**.

**Core Features**:
- 🗣️ **Natural Language**: Ask in LINE or speak to your phone to query/operate
- 📱 **Mobile-First**: Phone, tablet, desktop all optimized
- 🔗 **Outsource-Friendly**: Outsource partners scan LINE QR — no registration needed
- 🌐 **MESH Multi-Factory**: HQ + branches sync in real-time, but data stays local
- 🛡️ **Row-Level Permissions**: Sales sees only their own customers; outsource sees only their own jobs

### 1.2 Who Is It For?

| Role | How to Use |
|---|---|
| 👔 **Owner** | LINE: "How's the factory today?" → AI replies |
| 👨‍💼 **Salesperson** | Mobile in front of customer: check stock, price, delivery |
| 👨‍🏭 **Plant Manager** | Mobile: WO progress, push notifications |
| 👩‍💻 **Purchaser/Warehouse** | Desktop: create POs; mobile: scan QR for stocktake |
| 👴 **Outsource Partner** | LINE: scan QR, report completion, no registration |

---

## 2. Quick Start

### 2.1 Start the System

For IT deployment, see [DEPLOYMENT.md](./DEPLOYMENT.md).
For trial users, follow these three steps:

```bash
# Step 1: Start full stack
docker compose up -d --build

# Step 2: Load demo data
docker compose exec backend python -m scripts.seed

# Step 3: Open in browser
# Desktop UI:    http://localhost:5173
# War Room:      http://localhost:8080
# API Docs:      http://localhost:8000/docs
```

### 2.2 Three Ways to Log In

| Method | Credentials | Best for |
|---|---|---|
| **Regular login** | `admin` / `admin123` | Full feature experience |
| **Demo Mode** | Click "Continue as Demo" | Quick trial, no registration |
| **Future: LINE Binding** | Add ERP official account | Owner-only |

> 💡 **Demo Mode** auto-disables once you set `JWT_SECRET` in production.

### 2.3 Load Industry-Specific Demo Data

```bash
# Metal machining (CNC bolts/nuts)
docker compose exec backend python -m scripts.seed_industries metal

# Plastic injection
docker compose exec backend python -m scripts.seed_industries plastic

# PCB assembly
docker compose exec backend python -m scripts.seed_industries pcb

# Food processing (bakery)
docker compose exec backend python -m scripts.seed_industries food

# Textile dyeing
docker compose exec backend python -m scripts.seed_industries textile

# All five industries combined
docker compose exec backend python -m scripts.seed_industries all
```

---

## 3. Login & Language

### 3.1 Login Page

Open `http://localhost:5173`, you'll see a beautiful gradient login screen:

1. **Top-right**: 🇹🇼 繁中 / 🇺🇸 EN toggle
2. **Center card**: Enter username + password
3. **Below**: Demo Mode for quick entry

### 3.2 Language Switching

The system auto-detects your browser language. To switch manually:

| Location | Action |
|---|---|
| Login page top-right | Click 🇹🇼 / 🇺🇸 |
| After login, top-right | Click globe icon → choose language |

**Switching is instant** — no need to log out. Your preference is saved.

---

## 4. Navigation

### 4.1 Main Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Sidebar                │  Header                              │
│ ┌──────────────┐       │  ┌──────────────────────────────┐   │
│ │ 🏠 LLM-ERP   │       │  │  🌐 Lang 🔔 Notif 👤 Profile │   │
│ │              │       │  └──────────────────────────────┘   │
│ │ Overview     │       │                                       │
│ │  📊 Dashboard│       │  Main Content                         │
│ │  💬 AI       │       │                                       │
│ │  📡 Events   │       │                                       │
│ │              │       │                                       │
│ │ Operations   │       │                                       │
│ │  📦 Inventory│       │                                       │
│ │  🛒 Purchase │       │                                       │
│ │  🏭 Production       │                                       │
│ │  💰 Sales    │       │                                       │
│ │  🔬 Quality  │       │                                       │
│ │              │       │                                       │
│ │ System       │       │                                       │
│ │  🛡️ Permissions      │                                       │
│ │  🔑 My Perms │       │                                       │
│ └──────────────┘       │                                       │
└──────────────────────────────────────────────────────────────┘
```

**Mobile**: Sidebar collapses into a drawer; tap the hamburger icon to open.

### 4.2 Universal UI Elements

| Element | Purpose |
|---|---|
| **🔔 Bell** | Real-time alerts (red dot = unread count) |
| **👤 Avatar** | Profile / My Permissions / Sign out |
| **🌐 Language** | Toggle ZH/EN |
| **↻ Refresh** | Reload current page data |
| **✕ Close** | Close modal / drawer |

### 4.3 Color Semantics

| Color | Meaning |
|---|---|
| 🔵 **Blue** | Primary action · In progress · Normal |
| 🟢 **Green** | Success · Completed |
| 🟡 **Yellow** | Warning · Pending · Partial |
| 🔴 **Red** | Error · Critical · Below safety |
| ⚪ **Gray** | Neutral · Inactive · Draft |

---

## 5. Role-based Guide

### 5.1 Owner — Run the Factory from LINE

#### 7:00 AM: Daily Briefing

Open LINE → ERP Official Account → auto-pushed:

```
Good morning! 📈

✅ Yesterday: 12 shipments ($580K)
⚠️ Today: 2 urgent WOs pending release
🔴 M6 Bolt stock at 300 (below safety)

[View Details] [Handle Urgent]
```

#### Anytime: Ask a Question

```
You:  How's the factory today?

Bot:
Today's highlights:
✓ 15 WOs in progress, avg progress 68%
⚠️ 3 WOs pending release (most urgent: SO-20260514-003)
✓ 12 sales, revenue $580,000
🔴 M6 Bolt out of stock — suggest order 2000 pcs
```

> 💡 **Tip**: Use natural language — no need for system jargon.

---

### 5.2 Salesperson — Query in Front of Customer

#### Scenario: Customer asks "How many can you deliver next batch?"

1. Open mobile app
2. Tap 💬 AI Assistant
3. Speak: "PRD-GEAR-A available delivery for next month"
4. 3 seconds later: "Available 500 units, earliest 6/15"

#### Scenario: "What was the last price I gave them?"

1. AI Assistant input: "Customer A historical pricing for PRD-GEAR-A"
2. Bot: "Last 3 times: 5/12 $4500, 4/20 $4400, 3/15 $4300"

> 💡 **Sales reps cannot see other reps' customers** — this is `own` scope protection.

---

### 5.3 Plant Manager — Push Notifications on Phone

#### Setup Push

1. Desktop UI → 🔑 My Permissions
2. Confirm `plant_manager` role
3. Subscribe events: `stock.below_safety` / `wo.completed` / `nc.created`

#### When Alert Hits

LINE / App pops up:
```
⚠️ WO Delay Alert

WO-20260514-002 (Bearing Block B)
Original ETA: 5/20
Progress: 30% (2 days behind)

[View Details] [Assign Urgent]
```

Tap → straight into mobile app WO page.

---

### 5.4 Purchaser/Warehouse — Mobile QR Scan

#### Receiving Goods

1. Goods arrive from supplier
2. Open mobile app → "Receive"
3. Scan PO's QR
4. System auto-fills:
   ```
   PO-20260514-001
   Da-Hua Precision
   M6-BOLT-20 × 1000
   ```
5. Enter actual qty "1000"
6. Take photo
7. Confirm → auto:
   - Inventory +1000
   - PO marked "Received"
   - LINE notify Plant Manager "Goods arrived"

#### Stocktake

1. Open mobile app → "Stocktake"
2. Select bin
3. Scan bin QR
4. Enter actual count
5. Take photo (if variance)
6. System auto:
   - Calculates variance
   - Flags as anomaly if > 5%
   - Notifies supervisor for review

---

### 5.5 Outsource Partner — LINE QR, No Registration

#### Wu's Story

Mr. Wu is a small electroplating outsource shop owner — just him and two apprentices.
He **doesn't use computers** and doesn't want to register new systems.

#### Completion Reporting Flow

1. Main factory prints "Outsource Dispatch Order" with QR
2. Mr. Wu finishes the job, opens LINE
3. Adds the main factory's ERP official account
4. Selects menu → "Report Outsource"
5. Bot: "Please scan the dispatch QR"
6. Mr. Wu scans
7. Bot shows:
   ```
   Order OS-20260514-003
   Item: M6 Bolt Electroplating
   Dispatched: 500 pcs
   Please enter completed qty
   ```
8. Wu replies: "500"
9. Bot: "Please send a completion photo"
10. Wu uploads
11. Bot: "✅ Reported. Thank you, Mr. Wu!"
12. Main factory's Plant Manager instantly gets LINE notification

**No registration, no new software, minimal typing.**

---

## 6. Using the AI Assistant

### 6.1 How to Ask

Use **natural language** — no system jargon:

| ✅ Good | ❌ Avoid |
|---|---|
| How much M6 bolt do we have? | execute SELECT FROM parts WHERE... |
| Any WOs in progress? | List all WO with status=in_progress |
| Which customer owes us money? | Query AR table |

### 6.2 What AI Can Do

| Module | Sample Questions |
|---|---|
| 📦 Inventory | "Top 5 lowest stock items?" "How many M6 bolts left?" |
| 🛒 Purchase | "Recent POs from Da-Hua" "Who did we buy SUS304 from last time?" |
| 🏭 Production | "Today's WOs in progress" "Progress of WO-001" |
| 💰 Sales | "Customer A pricing history" "Revenue this month" |
| 🔬 Quality | "Recent non-conformances" "Pass rate this month" |
| 💳 Accounting | "Overdue AR list" "Journal entries this month" |

### 6.3 AI Limitations

- **No writes yet (v2.0)** — read-only queries
- **AI asks for clarification** on ambiguous queries
- **Honest about unknowns**: "I'm not sure, please check the X page"

### 6.4 No LLM API Key?

AI Assistant displays: "[demo mode] Detected intent = xxx, but LLM_API_KEY not set."

**All other 11 pages still work perfectly** — only AI chat is disabled.
Once IT sets the API Key (DeepSeek / OpenAI / Anthropic), AI auto-resumes.

---

## 7. FAQ

### Q1: Why is a button grayed out?

→ Your role lacks that permission. Ask IT or owner to grant.
Check **🔑 My Permissions** for what you have.

### Q2: Why can't I see other salespeople's customers?

→ **By design**, not a bug. Each salesperson sees only their own customers (own scope) — prevents customer poaching.

### Q3: Where do I download the mobile app?

→ v2.0 uses browser (http://localhost:5173) — responsive design works great on mobile.
Native app is planned for Phase 1.

### Q4: Can I use both Chinese and English at the same time?

→ Yes — language is a personal preference. Same system, you see Chinese, your foreign colleague sees English. Data (part names, customer names) is in whatever language you entered.

### Q5: Forgot password?

→ v2.0 — ask IT to reset (backend updates hashed_password).
Phase 2 will add self-service reset via email.

### Q6: How do I export data?

→ Each page has an **Export CSV** button (Phase 2).
Currently you can use the API: `GET /api/<domain>/<resource>` returns JSON.

### Q7: Can multiple factories share one system?

→ **Yes** — this is core MESH design:
- HQ + N Factory Nodes
- Each factory's data stays local
- HQ can query aggregates across factories
- See [DEPLOYMENT.md](./DEPLOYMENT.md) §4

### Q8: One outsource shop serves multiple main factories?

→ Same Wu Electroplating can serve multiple main factories.
Each main factory's printed QR has independent token — Bot auto-identifies.

---

## 8. Keyboard Shortcuts

| Shortcut | Function |
|---|---|
| `Ctrl + K` (Win) / `⌘ + K` (Mac) | Global search (Phase 2) |
| `Esc` | Close modal / drawer |
| `Enter` | Submit form |
| `/` | Focus AI chat input |

---

## 9. Troubleshooting

### 9.1 Can't Reach Login

| Symptom | Fix |
|---|---|
| "Cannot reach backend" | Check backend: `docker compose ps` |
| 503 / 504 | Restart: `docker compose restart backend` |
| 401 keeps popping | Clear localStorage: F12 → Application → Clear |

### 9.2 No Data Showing

| Symptom | Fix |
|---|---|
| Empty list | Seed first: `docker compose exec backend python -m scripts.seed` |
| Only see own | This is row-level design (own scope), not a bug |
| 401 forbidden | Role lacks permission — ask IT |

### 9.3 AI Not Responding

| Symptom | Fix |
|---|---|
| "demo mode" message | Set `LLM_API_KEY` in `.env` |
| "LLM call failed" | Verify API key validity and quota |
| Long wait | LLM thinking — up to 60s |

### 9.4 Mobile Display Issues

| Symptom | Fix |
|---|---|
| Font too small | Pinch-zoom or browser font setting |
| Layout broken | Use Chrome / Safari (latest) |
| Touch unresponsive | Refresh page |

---

## 10. Advanced: Admin Only

### 10.1 Create New Employee

```
1. Desktop UI → System → Permissions (admin required)
2. System → Organization → Employees → Create
3. Fill: employee #, name, email, department
4. System → Organization → Users → Create
5. Username / default password / link employee
6. Permissions → assign role (e.g. sales_rep)
```

### 10.2 Temporary Delegation

Example: Owner traveling, Plant Manager delegates for 3 days

```
Desktop UI → Permissions → boss role → Clone →
Create boss_temp_2026_05_20 → Assign to Plant Manager →
Set expires 2026-05-22 23:59 → Save
```

Auto-revokes after expiry.

### 10.3 Audit Who Changed What

```
Desktop UI → System → Audit Trail (Phase 1.5)
Currently: query permission_audit table directly
```

---

## 11. Further Learning

- **Architecture Diagram**: [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)
- **Permission Model**: [PERMISSION_MODEL.md](./PERMISSION_MODEL.md)
- **API Docs**: http://localhost:8000/docs (auto-generated)
- **Strategy Landscape**: [STRATEGY_LANDSCAPE.md](./STRATEGY_LANDSCAPE.md)

---

## 12. Support

| Need | Contact |
|---|---|
| Bug report | Internal IT |
| Feature request | Team meeting or email |
| Training | Monthly online sessions |
| Emergency | (per your company SLA) |

---

## 13. Mobile App Usage (NEW in v2.3)

### 13.1 Install & Launch

Phase 1 ships an Expo mobile app skeleton (5 tabs).

**Prerequisites**: Node.js 18+, phone on the same Wi-Fi as backend.

```bash
cd frontend-mobile
npm install
# Edit app.json: set extra.apiBaseUrl to your computer's LAN IP
# Example: http://192.168.1.100:8000
npm start
```

After QR code appears in terminal:
- iOS: scan with Camera, opens Expo Go
- Android: scan with Expo Go app

### 13.2 Five Tabs

| Tab | Function |
|---|---|
| 📊 Dashboard | AI summary + 4 stat cards + low-stock list |
| 📦 Inventory | Searchable parts list |
| 📷 Scan | Full-screen barcode / QR scanner |
| 💬 AI Assistant | Chat interface + suggested prompts |
| 👤 Me | Profile + system info + logout |

### 13.3 Full Verification SOP

See `frontend-mobile/VERIFY_MOBILE.md` — 5-step procedure + 5-screenshot checklist + sign-off page.

---

## 14. MESH Multi-Factory (NEW in v2.3)

### 14.1 When to Enable

When you have **2+ factories / outsource shops** to interconnect but **don't want data centralized**:
- Main factory + Plating outsource + Inspection outsource (typical 3-shop)
- Multiple production sites in a group
- Customer demands "data stays in our factory"

### 14.2 Start Factory Node

On each factory's server:

```bash
FACTORY_ID=plating  FACTORY_NAME='Plating Outs' \
PORT=8002  HQ_URL=http://hq.your-domain.com:8000 \
python backend/factory_node.py
```

The factory auto-registers with HQ; HQ can then run aggregated queries.

### 14.3 HQ Cross-Factory Query

```bash
# List registered factories
curl http://hq:8000/api/factory/list

# Aggregate M6 bolt inventory across factories
curl -X POST 'http://hq:8000/api/factory/aggregate?domain=inventory&part_no=M6'

# Response: { total: 4500, per_factory: {main: 3000, plating: 1500}, ... }
```

### 14.4 Data Sovereignty Guarantee

The `/api/factory/aggregate` response contains **only aggregated numbers**, never raw rows (verified by 5 integration tests):
- ❌ Never returns created_at / qty_available / items / rows
- ✅ Only total / per_factory_total / responded_count

---

## 15. PDF Manual Export (NEW in v2.3)

Convert all customer-facing manuals to polished PDFs (14 documents in ZH + EN):

```bash
# Windows
build_pdfs.bat

# Mac/Linux
./build_pdfs.sh
```

Output `docs/pdf/*.pdf`, 14 beautiful PDFs (with Mermaid diagrams, A4 layout, page numbers).
See `scripts/build-pdfs/README.md` for details.

---

**Manual version**: v2.3 (2026-05-14)
**Chinese version**: [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md)
**Next update**: After LINE Bot launches

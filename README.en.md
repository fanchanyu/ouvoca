[繁體中文](./README.md) | **English**

# Ouvoca — An AI-Native ERP for Small Factories

> **Talk to your ERP.** Place orders, check stock, close the books, and file taxes by typing one sentence — no menu diving, no consultant, no six-figure implementation.
>
> Built for 50–100 person manufacturers. **Free for up to 20 concurrent users.**

[![CI](https://github.com/fanchanyu/ouvoca/actions/workflows/ci.yml/badge.svg)](https://github.com/fanchanyu/ouvoca/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-880%20passing-brightgreen)](#-developer-guide)
[![Version](https://img.shields.io/badge/version-3.70.0-blueviolet)](#-project-stats)
[![API](https://img.shields.io/badge/REST%20endpoints-242-informational)](./docs/API_REFERENCE.md)
[![Tables](https://img.shields.io/badge/tables-107-informational)](./docs/ARCHITECTURE_BLUEPRINT_EN.md)
[![AI tools](https://img.shields.io/badge/AI%20tools-201-orange)](./docs/AGENT_CATALOG_EN.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0%20%2B%20SBL%20%2B%20Commercial-blue)](./LICENSE)

---

## 🚀 Quick Start

| I want to… | Go here |
|---|---|
| **Install and try it** (double-click, no prerequisites) | 👉 [5-Minute Install](#-5-minute-install) |
| **Understand what it does** in 30 seconds | 👉 [What Is Ouvoca](#-what-is-ouvoca) |
| **Fix a failed install** | 👉 [Troubleshooting Guide](./docs/INSTALL_TROUBLESHOOTING_EN.md) |
| **Know what it costs** | 👉 [Licensing](#️-licensing) — free for ≤20 concurrent users |
| **Read the code** | 👉 [Developer Guide](#-developer-guide) |

---

## 🙋 Who Are You?

| Reader | Start with |
|---|---|
| 🏭 **Factory owner / operations lead** — evaluating whether this replaces your spreadsheets | [What Is Ouvoca](#-what-is-ouvoca) → [Feature Overview](#-feature-overview) → [Licensing](#️-licensing) |
| 👷 **Shop-floor user** — you'll actually type into it every day | [User Manual](./docs/USER_MANUAL_EN.md) |
| 👨‍💻 **Engineer / integrator** — you'll deploy, extend, or audit it | [Developer Guide](#-developer-guide) → [API Reference](./docs/API_REFERENCE.md) → [Architecture](./docs/ARCHITECTURE_BLUEPRINT_EN.md) |

---

## 📚 Documentation

| Start here | What it is |
|---|---|
| 🗂 **[`docs/README.md`](./docs/README.md)** | **The master index — read this first.** All 100 documents under `docs/`, each tagged 🟢 current / 🟡 partly stale / 🔴 known-outdated so you know what to trust, with a reading path per reader type and a dedicated **English Readers** section that also names the 21 documents which exist in Chinese only |
| 📕 [`docs/DOCUMENT_INDEX.md`](./docs/DOCUMENT_INDEX.md) | The 74 bilingual PDFs, per-file — for printing or taking to a shop floor with no network |
| 📜 [`docs/CHANGELOG_ZH.md`](./docs/CHANGELOG_ZH.md) | Plain-language release notes, v3.49 → v3.70 (Chinese only) |

---

## ⚡ What Is Ouvoca

Conventional ERP fails small factories for a predictable reason: the software is capable, but nobody
on the floor can operate it. Training a 60-person shop on a 400-screen system costs more than the
license ever did.

Ouvoca inverts the interface. **The primary UI is a conversation**, backed by a full relational ERP:

```
You:  Order 500 M6 bolts from Changjiang, delivery next Friday.

Ouvoca:  ┌─ Confirm Purchase Order ───────────────────────┐
         │ Supplier   Changjiang Metals (SUP-003)         │
         │ Item       M6-BOLT-20  x500 pcs @ 3.20         │
         │ Total      NT$ 1,600                           │
         │ Due        2026-08-14 (Fri)                    │
         │                                                │
         │ House rule: POs over NT$100,000 need           │
         │ manager approval - this one does not.          │
         │                                                │
         │   [ Confirm ]   [ Cancel ]   expires 29:47     │
         └────────────────────────────────────────────────┘
```

Three properties make this safe enough for real books:

1. **Nothing is written without a human click.** Every one of the 94 write-capable AI tools routes
   through a **ConfirmCard** that shows exactly what will change. The card holds for **30 minutes** —
   long enough to take a phone call mid-decision. Read-only queries answer immediately.
2. **Mistakes are reversible.** A **90-second undo window** covers the "wrong supplier" moment.
3. **The conversation is not the only door.** Everything is also a REST endpoint and, for the
   high-traffic modules, a conventional web UI. Chat is the fast path, not a cage.

### Why not just bolt ChatGPT onto an existing ERP?

Because the hard part isn't language — it's *governance*. An LLM that can write to your ledger needs
permission checks, an approval chain, an audit trail, and a way for the owner to encode "we don't do
that here." Those are the parts Ouvoca actually builds — see [House Rules](#️-house-rules--the-differentiator).

---

## 🏛️ House Rules — The Differentiator

Every factory has unwritten policies. In a traditional ERP, encoding them means paying a consultant
to write custom validation. In Ouvoca, the owner writes them in plain language, and they execute as
hard constraints on both the UI and the AI.

```
Owner types:  "Never release a work order without a complete recipe."
              "Purchase orders above NT$100,000 need my approval."
              "Receiving quantity may never exceed the quantity ordered."
```

These become enforced rules that block the transaction and explain why — whether the request came
from a human clicking a button or from the AI acting on a sentence. Ouvoca ships with
**23 default house rules** covering the mistakes that actually cost small factories money.

| | Traditional ERP | Ouvoca |
|---|---|---|
| Encode a policy | Consultant + custom code + release cycle | Owner types a sentence |
| Time to take effect | Weeks | Immediate |
| Applies to AI actions | N/A | Yes — same engine |
| Audit trail of blocks | Rare | Every blocked transaction logged |

`POST /api/policies/seed-defaults` loads all 23 in one call · [House Rules Guide](./docs/HOUSE_RULES_GUIDE_EN.md)

---

## 🔒 Where Does My Data Live? What Reaches the LLM Vendor?

The first question any owner should ask about an AI-native ERP. Answered below strictly from what the
code does — no marketing gloss, no scare tactics.

### 📁 Your data stays on your machine

**Ouvoca has no cloud back end. There is no code path that uploads your database anywhere.**

| Install method | Where the database lives |
|---|---|
| One-click installer (`install_easy.bat` / `.sh`) | `backend\erp.db` — a single SQLite file inside the folder you extracted (e.g. `C:\Ouvoca\backend\erp.db`) |
| Docker (`install.bat` / `docker compose`) | Docker volume `backend-data`, mounted at `/app/data/erp.db` |
| Production PostgreSQL | Whatever server you point `DATABASE_URL_PROD` at in `backend/.env` |

Uploaded attachments live in `backend\uploads\`, built-in backups in `backend\backups\backup-*.db` —
also on your own machine. Copy those yourself for off-site retention → [Backup SOP](./docs/BACKUP_RESTORE_SOP_EN.md).

### 🤖 What actually leaves the building when chat is enabled

Only the sentence you submit, and whatever was looked up to answer it, reaches your configured LLM
vendor (DeepSeek by default). Itemized:

| Sent to the vendor | Detail |
|---|---|
| ✅ The sentence you typed | e.g. "Order 500 M6 bolts from Changjiang" |
| ✅ The last **10 messages** of that chat session | `backend/app/api/chat.py` loads exactly 10 rows as context |
| ✅ Your username, employee ID, roles, and permission codes | Embedded in the system prompt so the model won't steer you toward actions you aren't authorized for |
| ✅ Tool definitions for the routed domain (name / description / parameters) | Schema only — contains none of your business data |
| ⚠️ **The rows a tool returned while answering you** | The one that matters. Ask "list parts below safety stock" and that list is posted back to the vendor — it is the only way the model can narrate it to you |

| Never sent | Why |
|---|---|
| ❌ The database file itself | No such code path exists |
| ❌ Database credentials | The model never receives connection details and never emits SQL. It may only pick one **registered tool** and fill its declared slots; the backend runs the query (`execute_tool` in `backend/app/agents/engine.py`) |
| ❌ Anything this question didn't touch | If no tool read it, it isn't in the payload |

> 📌 **In one line:** the vendor sees exactly the data fetched to answer your sentence — no more, no less.
> Which also means **whatever you ask about, you hand over**. If a customer list or cost structure must
> not leave the company, don't ask the AI about it — or run the offline option below.

The default vendor is DeepSeek (`https://api.deepseek.com/v1`); OpenAI, Anthropic, and Ollama are
selectable from the settings page. ⚠️ **DeepSeek, OpenAI, and Anthropic are all hosted abroad, so
using them means cross-border data transfer** — assess this against your privacy obligations first
→ [Taiwan compliance notes](./docs/COMPLIANCE_TW_EN.md).

### 🚫 Does it still work with the AI turned off?

**Yes — as a complete ERP.** With no API key set, the assistant returns a "not configured yet" card
and everything else runs normally: 17 web pages, 242 REST endpoints, house rules, approvals, RBAC,
backups, and PDF output need no LLM at all. The whole system can run on an air-gapped LAN; only the
install itself requires internet.

> ⚠️ One exception: modules marked **💬 only** in the [Feature Overview](#-feature-overview) — with
> neither 🖥️ nor 🔌 — currently **Cash cycle** (bank accounts, payment/receipt recording). Those ship
> as AI tools with no screen and no REST endpoint, so they are unreachable without chat enabled.

### 🏠 Fully offline: Ollama

For "not one byte leaves the building," switch the provider to **Ollama** — the model runs on your own
hardware (`http://localhost:11434` by default), the API key stays blank, and no conversation leaves
your LAN. Setup steps are in [`HOW_TO_GET_LLM_API_KEY_EN.md`](./docs/HOW_TO_GET_LLM_API_KEY_EN.md).

> ⚠️ **Honest limitation as of v3.70:** the Ollama path is **conversational only — it cannot create
> documents.** `_ollama_chat()` in `backend/app/agents/engine.py` does not forward tool definitions to
> the model and always returns an empty `tool_calls` list. So under Ollama, "order 500 bolts from
> Changjiang" produces **no ConfirmCard and no purchase order**. Transactional chat currently requires
> DeepSeek, OpenAI, or Anthropic.

📖 Data classification, retention, and pruning strategy → [`docs/DATA_LIFECYCLE.md`](./docs/DATA_LIFECYCLE.md) (Chinese only) ·
🔐 Vulnerability reporting → [`SECURITY.md`](./SECURITY.md)

---

## 🎯 Design Priorities — Deployability first

Capability is worthless if nobody can get it running. Every technical decision is resolved against
this order, and **when two priorities conflict, the higher one always wins**:

| Priority | Principle | What it means in practice |
|:---:|---|---|
| **1** | **A non-technical user can install it** | Double-click to install. No Docker, Python, or Node knowledge required. No PR may make this harder |
| **2** | Data is never lost | Automatic backup before upgrade, rescue copy before restore, explicit confirmation for destructive operations |
| **3** | Mistakes are recoverable | 90-second undo, audit trail, ConfirmCard preview before commit |
| **4** | Taiwanese factories actually need it | Uniform invoice, 401/405 VAT filing, and lot traceability rank above generic feature breadth |
| **5** | Elegant code | Considered last |

This principle was frozen by the project owner on 2026-05-22 and is enforced across four documents by
`tests/smoke/test_v349_deployability_first.py` — delete it from any one of them and the suite fails.

📖 Full rationale → [`ARCHITECTURE_DECISIONS.md`](./docs/ARCHITECTURE_DECISIONS.md)

---

## 🚀 5-Minute Install

**No IT background required.** If you can double-click and open a browser, you can install this.

### Recommended: zero-prerequisite mode

The installer downloads and sandboxes its own Python and Node.js into the project folder — you do
not need Docker, Python, or Node installed beforehand.

| Step | Action |
|---|---|
| 1️⃣ | Download the ZIP and extract it (e.g. to `C:\Ouvoca`) |
| 2️⃣ | Double-click **`install_easy.bat`** (Windows) or run **`bash install_easy.sh`** (macOS/Linux) |
| 3️⃣ | Wait 10–20 minutes → browser opens automatically → log in with `admin` / `admin123` |

| Task | Command |
|---|---|
| Start it again later | `start.bat` / `bash start.sh` |
| Update to a new version | `update.bat` — backs up your data, pulls, migrates, restarts |
| Uninstall completely | `uninstall_easy.bat` — also cleans Windows registry entries |

**Download:** ~556 MB (Python ~26 MB + Node ~30 MB + packages ~500 MB). **Disk after install:** ~750 MB, all inside the project
folder. **Time:** roughly 10 minutes on a 10 Mbps connection.

> ⚠️ **Antivirus software may flag the silent Python installer.** Whitelist the folder or disable
> real-time scanning for the duration of the install.
> ⚠️ **Change the default password immediately** after first login — just tell the chat
> *"change my password, the new one is …"*.

### Alternative: Docker

```bash
docker compose up -d          # backend :8000 · web UI :5173 (loopback-bound)
```

Ports bind to `127.0.0.1` only, so the system is not reachable from your office LAN until you
deliberately expose it. See [Network Deployment](./docs/NETWORK_DEPLOYMENT_EN.md).

### Runtime requirements (self-managed installs)

| | Version |
|---|---|
| Python | **3.11 or 3.12** (`requires-python = ">=3.11,<3.13"` in `backend/pyproject.toml`; CI runs 3.12) |
| Node.js | **20 LTS** (`>=20 <25`) |
| Database | SQLite by default · PostgreSQL for production ([switch-over guide](./DEPLOYMENT.md)) |
| LLM | DeepSeek (default), OpenAI, Anthropic, or **Ollama for fully offline operation** |

📖 [Full installation guide](./docs/INSTALLATION_EN.md) · [Troubleshooting](./docs/INSTALL_TROUBLESHOOTING_EN.md) · [What the installer downloads, and its licensing](./docs/THIRD_PARTY_DOWNLOADS_EN.md) · [Getting an LLM API key](./docs/HOW_TO_GET_LLM_API_KEY_EN.md)

---

## 📦 Feature Overview

**242 REST endpoints · 201 AI tools across 19 domains · 107 tables.** Every module below is
implemented and covered by the test suite.

The **Access** column matters: Ouvoca's newest financial and document modules are reachable through
chat and REST but do not yet have dedicated screens. This is deliberate — the AI layer ships first,
the UI follows. Knowing which is which saves you hunting through menus.

> 🖥️ Web UI · 💬 Chat · 🔌 REST API

### Core operations

| Module | What it does | Access |
|---|---|---|
| **Inventory** | Parts master, real-time on-hand/available quantities, safety-stock alerts, transactions, inter-warehouse transfers, physical count sheets, monthly Excel report with cost-column masking for non-finance roles | 🖥️ 💬 🔌 |
| **Purchasing** | Suppliers, purchase orders, approval, receiving, cancellation, PDF output, reorder suggestions with lead-time awareness, supplier price history, spend-concentration risk analysis | 🖥️ 💬 🔌 |
| **Sales** | Customers with credit limits, sales orders, confirmation, **atomic shipping** (deducts stock + issues delivery note + invoice + journal entry + receivable in one transaction), quotations with email delivery and SO conversion, customer profitability | 🖥️ 💬 🔌 |
| **Production** | Products, **recipes** (BOM — deliberately not called "BOM" in the UI), work orders, release with recipe validation, completion reporting with scrap, work centers, routing operations, dispatch logs | 🖥️ 💬 🔌 |
| **Planning** | Master production schedule, MRP explosion into planned orders, demand forecasting with automatic algorithm selection, bottleneck identification, DBR scheduling, capacity what-if simulation, order-acceptance decisions via throughput accounting | 💬 🔌 |
| **Quality** | Incoming/in-process/outgoing inspections, non-conformance records, CAPA tracking, inspection report PDFs | 🖥️ 💬 🔌 |
| **CRM** | Leads with conversion to customers, opportunity pipeline, interaction history, 360° customer view, fuzzy customer-name disambiguation | 🖥️ 💬 🔌 |
| **Warehouse** | Zones, bins, pick tasks, cycle counts | 💬 🔌 |

### Finance and accounting

| Module | What it does | Access |
|---|---|---|
| **General ledger** | **86-account Taiwan chart of accounts preloaded**, journal entries, posting, period close, receivables and AR aging, DSO | 🖥️ 💬 🔌 |
| 🆕 **Financial statements** | **Trial balance, income statement, balance sheet** — generated from posted entries | 💬 🔌 |
| 🆕 **3-way match** | Supplier invoices reconciled against **purchase order ↔ goods receipt ↔ invoice**, flagging quantity and price discrepancies before you pay | 💬 🔌 |
| 🆕 **Fixed assets** | Asset register with cost, salvage value, and useful life; automatic monthly depreciation posted as journal entries | 💬 🔌 |
| 🆕 **Promissory notes** | Receivable and payable note tracking with maturity alerts — standard practice in Taiwanese manufacturing | 💬 🔌 |
| 🆕 **COGS settlement** | Period-end transfer of shipped cost from finished goods to cost of goods sold | 💬 🔌 |
| 🆕 **Work order costing** | Per-order material + labor + overhead rollup: did this job make money? | 💬 🔌 |
| 🆕 **Cash cycle** | Bank accounts, payables aging, payment and receipt recording with automatic double-entry | 💬 |

### Taiwan tax and compliance

Taiwan mandates a government-issued uniform invoice (統一發票, *GUI*) for every B2B and B2C sale, and
a bi-monthly VAT return. Both are legal requirements, not conveniences — and both are where
imported ERP systems typically fail local manufacturers.

| Module | What it does | Access |
|---|---|---|
| **e-Invoice (電子發票)** | Issues government-compliant electronic uniform invoices — triplicate B2B and duplicate B2C — through a value-added service center, with 24-hour void window and the mandatory 5-year retention and query capability | 🖥️ 💬 🔌 |
| 🆕 **VAT returns (401/405)** | Generates the bi-monthly business tax return: output tax, input tax, and net payable, plus the 403 sales/purchase detail schedule and a printable 401 filing form | 💬 🔌 |
| **Tax ID validation** | Taiwan 8-digit unified business number checksum validation, with multi-country support | 🖥️ 🔌 |

📖 [Taiwan compliance details](./docs/COMPLIANCE_TW_EN.md) · [Tax & accounting legal notice](./docs/TAX_ACCOUNTING_LEGAL_NOTICE_EN.md)

### Document workflows

| Module | What it does | Access |
|---|---|---|
| 🆕 **Purchase requisition (PR)** | Floor requests a part → manager approves → converts into a formal purchase order | 💬 🔌 |
| 🆕 **Goods receipt note (GRN)** | Formal receiving document against a PO, updating received quantity and stock | 💬 🔌 |
| 🆕 **Material issue (MI)** | Work order draws material from stores with a cost snapshot at issue time | 💬 🔌 |
| 🆕 **Sales return / RMA** | Customer return → approval → back into stock | 💬 🔌 |
| 🆕 **RFQ** | Send a request for quotation to multiple suppliers, record their responses, **compare side by side with lowest price highlighted per line**, then award and convert to a PO in one step | 🖥️ 💬 🔌 |
| **Approvals** | Configurable multi-stage rules ("POs above X need a manager"), pending queue by role, approve/reject with mandatory reason, full decision history | 🖥️ 🔌 |

### Traceability

| Module | What it does | Access |
|---|---|---|
| 🆕 **Batch/lot traceability** | **Forward and backward tracing** — where did this lot come from, and which orders consumed it. The capability you need when a customer reports a defect, or an auditor asks | 🖥️ 💬 🔌 |
| 🆕 **Serial number tracking** | Per-unit status and associated documents | 🖥️ 💬 🔌 |
| 🆕 **Barcode scanning** | Scan a part, lot, or serial number and immediately see stock and available actions | 🖥️ 🔌 |
| 🆕 **QR labels** | 60×40 mm part labels for shelf and bin marking | 🖥️ 💬 🔌 |

### Security and administration

| Module | What it does | Access |
|---|---|---|
| 🆕 **MFA (TOTP)** | Standard authenticator-app two-factor authentication as a second login step | 🖥️ 🔌 |
| 🆕 **Login hardening** | Account lockout after repeated failures, without disclosing whether the username exists; changing a password immediately revokes every other session via a token version claim | 🖥️ 🔌 |
| 🆕 **Backup & restore** | On-demand backup, scheduled backups with retention, listing, deletion, and restore (destructive, explicitly gated) | 🖥️ 🔌 |
| 🆕 **Upload validation** | **Magic-byte content inspection** — a `.txt` renamed to `.pdf` is rejected — plus an optional antivirus scan hook (`AV_SCAN_URL`) | 🔌 |
| **RBAC** | **231 permission codes** across **10 preloaded roles** (admin, owner, plant manager, sales manager, sales rep, buyer, warehouse, accountant, QC, operator), role cloning, per-user overrides, effective-permission inspection, multi-tenancy | 🖥️ 💬 🔌 |
| 🆕 **System configuration** | **14 settings** — company details, tax ID, currency, tax rate, timezone, locale, backup schedule, lockout threshold, AI daily spend cap — resolved as environment variable → database → default | 🖥️ 🔌 |
| 🆕 **External database connectors** | Read from incumbent systems (Workflow/鼎新, ChengHang/正航, generic SQL, CSV) with **AES-GCM encrypted credentials**, schema mapping preview with confidence scores, and one-off data import | 💬 🔌 |
| **Live event stream** | Server-sent events with desktop notifications | 🖥️ 🔌 |
| **Multi-site mesh** | Branch plants register to headquarters for cross-site aggregate queries | 🔌 |

> ⚠️ **Deployment note:** multi-site mesh is **experimental**. Keep it on a trusted network and do
> not expose it to the public internet. Hardening of the cross-site and approval endpoints is
> tracked ahead of the first tagged public release — see [SECURITY.md](./SECURITY.md) for the
> supported-version policy and private vulnerability reporting.

### Turnkey — usable on first boot

Most ERP deployments die in configuration. Ouvoca ships with the setup already done:

| Package | Contents |
|---|---|
| Chart of accounts | **86 accounts**, Taiwan SMB manufacturing standard |
| Roles & permissions | **10 roles**, **231 permission codes** |
| House rules | **23 default policies** |
| System settings | **14 configuration keys** |
| Industry seed data | **5 verticals** — metalworking, plastic injection, PCB, food, textile — each with parts, products with recipes, suppliers, customers, work centers, and sample work orders |
| Document templates | Full bilingual PDF set — quotation, PO, SO, delivery note, inspection report, count sheet, part label |

```bash
python -m scripts.seed_industries metal    # load a vertical and start exploring
```

---

## 🏗 Architecture

```
                    ┌──────────────────────────────────────────┐
   Browser  ───────▶│  React 18 + Vite + Tailwind (17 pages)   │
   Chat / UI        └────────────────────┬─────────────────────┘
                                         │  REST + SSE
                    ┌────────────────────▼─────────────────────┐
                    │  FastAPI · 242 endpoints · 30 modules    │
                    │  ┌────────────────────────────────────┐  │
                    │  │ Agent engine · 201 tools/19 domains│  │
                    │  │   ConfirmCard 30 min · Undo 90 s   │  │
                    │  └────────────────────────────────────┘  │
                    │  ┌────────────────────────────────────┐  │
                    │  │ House rules · RBAC 231 · Audit log │  │
                    │  └────────────────────────────────────┘  │
                    └────────────────────┬─────────────────────┘
                                         │  SQLAlchemy 2.0 async
                    ┌────────────────────▼─────────────────────┐
                    │  SQLite (dev) / PostgreSQL (prod)        │
                    │  107 tables · Alembic v001 → v016        │
                    └──────────────────────────────────────────┘

   LLM: DeepSeek · OpenAI · Anthropic · Ollama (offline) - switchable at runtime
```

Every write-capable AI tool passes through three gates before it touches the database: **RBAC
permission check → house-rule evaluation → human ConfirmCard**. The LLM never holds database
credentials and never emits SQL; it selects a registered tool and fills its declared slots.

📖 [Architecture blueprint](./docs/ARCHITECTURE_BLUEPRINT_EN.md) · [System topology](./docs/SYSTEM_TOPOLOGY_EN.md) · [Design decisions](./docs/ARCHITECTURE_DECISIONS.md) · [Conversational ERP design](./docs/CONVERSATIONAL_ERP_DESIGN_EN.md) · [Agent catalog](./docs/AGENT_CATALOG_EN.md) · [Permission model](./docs/PERMISSION_MODEL.md)

---

## ⚖️ Licensing

Ouvoca is available under three tracks — pick the one matching your situation:

| Track | Terms | Who it's for | Cost |
|---|---|---|---|
| 🟢 **Open source** | [AGPL-3.0](./LICENSE) | Anyone willing to disclose source modifications | **Free** |
| 🌱 **Small Business** | [Small Business License](./LICENSE-SMALL-BUSINESS.md) | A single legal entity with **≤ 20 concurrent users**, not reselling or hosting | **Free — including closed-source connectors, with no AGPL disclosure obligation** |
| 🔵 **Commercial** | Negotiated individually | >20 users, ISV/OEM, SaaS providers, enterprises | Custom pricing |

**Small Business License eligibility** — all must hold: peak concurrent active users ≤ 20 in any
rolling 24-hour window (an active user being a logged-in session with an authenticated action in the
previous 15 minutes); use confined to a single legal entity; no service provided to outside parties;
no embedding into a product distributed to third parties.

> **Why give it away below 20 seats?** Because a 12-person shop cannot afford enterprise ERP and
> should not be running the business out of spreadsheets. Use the whole system — connectors
> included — for free. When you grow past 20 people and can't work without it, we'll talk.

> ⚠️ **Connector licensing caveat:** "free" means *Ouvoca charges no technical license fee*.
> Connecting to your incumbent commercial ERP may still be restricted by **that vendor's** contract.
> Confirm the authorization scope with them in writing before enabling a connector. Ouvoca is not a
> party to those agreements. See [External DB licensing notice](./docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md).

Not sure which track applies? The decision tree is in [`LICENSE-COMMERCIAL.md`](./LICENSE-COMMERCIAL.md).

---

## 📅 How Long Does Rollout Take, and Who Trains the Staff?

Installing it to try is a [5-minute job](#-5-minute-install). Getting a whole factory to *switch* —
legacy data migrated, staff operating it daily, the owner reading the reports — is a different
project. It's written up as a **14-day, day-by-day rollout SOP**:

| Phase | Days | What happens |
|---|---|---|
| 📋 Requirements interview | 1–2 | Four hours on site mapping current flows, documents, and unwritten rules |
| 🖥 Environment prep | 3–5 | Single machine vs. server decision tree, deployment checklist, account provisioning |
| 📦 Install + industry sample | 6–7 | Standard install (under 2 hours), then load one of the 5 industry seed packs |
| 📥 Customer data migration | 8–9 | Parts, suppliers, customers, BOMs in priority order; a data-quality check flags orphan records, duplicate master data, and malformed BOMs |
| 🧑‍💼 Administrator training | 10 | **2 hours**: accounts and permissions, backup, reading logs, upgrades, emergency restart |
| 👥 Department-head training | 11–12 | **5 sessions × 1 hour**, including a dedicated 60 minutes for the owner |
| 🧪 Internal pilot | 13 | Real documents, real flow, issues tracked to closure |
| 🚀 Go-live | 14 | Go-live ceremony; the playbook lists owner attendance as mandatory — it is the stated prevention for "nobody uses it after go-live" |
| 🩺 Hyper-care | +30 days | Week 1: daily usage review, any bug patched within 24 h. Day 30: retrospective report for the owner |

**Success metric:** daily active users ÷ headcount ≥ 60% within 30 days of go-live.
The playbook closes with a table of rollout pitfalls and their prevention steps — the customer never
hands over their data, staff resist the change, a firewall blocks the LLM API, the owner skips
go-live day.

📖 Full day-by-day playbook → [`docs/IMPLEMENTATION_PLAYBOOK_EN.md`](./docs/IMPLEMENTATION_PLAYBOOK_EN.md)
(interview checklists, training outlines, migration commands, acceptance checklist)

> ⚠️ Written for **implementation consultants, integrators, and in-house IT**, and it assumes a Docker
> deployment. Content dates to 2026-05 and has not fully caught up with v3.70 — it is tagged 🟡 in
> [`docs/README.md`](./docs/README.md). The schedule and training plan still hold; take the commands
> from [`INSTALLATION_EN.md`](./docs/INSTALLATION_EN.md) instead.
>
> 🌱 **The Small Business track does not include rollout services** — §3.4 of that license grants
> community support only, with no SLA. The playbook is public, so run it yourself or hand it to your
> own IT consultant. For hands-on help, that's the [commercial track](./LICENSE-COMMERCIAL.md).

---

## 🛠 Developer Guide

```bash
git clone https://github.com/fanchanyu/ouvoca.git && cd ouvoca

# Backend — Python 3.11 or 3.12
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m alembic upgrade head
python -m scripts.seed                               # demo data + admin account
uvicorn app.main:app --reload                        # http://localhost:8000/docs

# Frontend — Node 20
cd ../frontend-desktop && npm install && npm run dev  # http://localhost:5173
```

**Testing and verification**

```bash
cd backend && python -m pytest        # 880 passing, 2 skipped (883 collected)
bash scripts/run_gates.sh             # 4 self-verification gates — must be green before pushing
```

The gates cover compilation (ruff, mypy, smoke tests, TypeScript), behavior (a scripted
owner-persona end-to-end day), documentation (the PDF builder), and governance (migrations apply to
a fresh database, FK indexes exist, permission seeding leaves no gaps). The same script runs in
[CI](./.github/workflows/ci.yml) on every push and pull request.

**Configuration** — copy `backend/.env.example` to `backend/.env`:

```bash
LLM_PROVIDER=deepseek        # deepseek | openai | anthropic | ollama
LLM_API_KEY=sk-...           # or configure at runtime via Settings — no restart needed
DATABASE_URL=sqlite+aiosqlite:///./data/erp.db
```

**Project layout**

```
ouvoca/
├── backend/
│   ├── app/api/          30 modules  ·  242 endpoints
│   ├── app/agents/       engine + 33 domain tool modules (201 tools)
│   ├── app/models/       107 tables
│   ├── app/services/     business logic (house rules, policy engine, auth)
│   ├── alembic/          v001 → v016 migrations
│   └── tests/            883 tests
├── frontend-desktop/     React 18 + Vite + Tailwind · 17 pages
├── docs/                101 markdown docs · 74 bilingual PDFs
└── scripts/              gates, PDF builder, release tooling
```

📖 [Contributing](./CONTRIBUTING.md) · [Development SOP](./docs/DEVELOPMENT_SOP.md) · [API reference](./docs/API_REFERENCE.md) · [Deployment](./DEPLOYMENT.md) · [Backup SOP](./docs/BACKUP_RESTORE_SOP_EN.md) · [Secrets rotation](./docs/SECRETS_ROTATION_SOP_EN.md) · [Security policy](./SECURITY.md) · [Roadmap](./docs/ROADMAP.md)

---

## 📊 Project Stats

| Metric | Value |
|---|---|
| Version | **3.70.0** |
| Backend tests | **880 passing**, 2 skipped (883 collected, ~40 s) |
| REST endpoints | **242** under `/api` |
| AI tools | **201** — 106 read, 94 hard-write, 1 soft-write |
| AI tool domains | **19** |
| Database tables | **107** |
| Migrations | **v001 → v016** |
| Permission codes / roles | **231** / **10** |
| Default house rules | **23** |
| Chart of accounts | **86** |
| Industry seed packs | **5** |
| Frontend pages | **17** |
| Bilingual PDFs | **74** |
| Stack | FastAPI · SQLAlchemy 2.0 async · Alembic · React 18 · Vite · Tailwind |

> Counts are measured from the codebase at v3.70.0 — endpoints and tables by runtime introspection,
> tools from the agent registry, tests from a full pytest run.

---

## 🤝 Contributing

Issues and pull requests are welcome. Please read [CONTRIBUTING.md](./CONTRIBUTING.md) and the
[Code of Conduct](./CODE_OF_CONDUCT.md) first; contributions require signing the [CLA](./CLA.md).
Security vulnerabilities should be reported privately per [SECURITY.md](./SECURITY.md) rather than
in a public issue.

**Ouvoca** · [AGPL-3.0](./LICENSE) · [Small Business License](./LICENSE-SMALL-BUSINESS.md) · [Commercial](./LICENSE-COMMERCIAL.md) · built by [Peter](https://github.com/fanchanyu)

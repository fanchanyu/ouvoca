# Ouvoca User Manual (English)

> **Version**: v3.23 Conversational ERP (Ouvoca)
> **Audience**: First-time ERP users — Owner, Sales, Plant Manager, Purchaser, Warehouse
> **Reading time**: ~30 minutes to get productive; refer to §11 Troubleshooting when stuck
> **Languages**: System supports 🇹🇼 繁體中文 and 🇺🇸 English with instant switching

> 🆕 **v3.13-v3.16 new features (must read)**
> - ⚙️ **Settings page**: load demo / clear demo / upload business docs / configure AI API key (§3.5)
> - 🤝 **CRM page**: Lead pipeline / Opportunity Kanban / Customer 360 with activity timeline (§3.6)
> - 💡 **AskAI floating button**: always-on "live AI coach" on every page (§3.7)
> - 🤖 **Auto activity logging**: orders / lead conversions / opportunity stage changes auto-create CRM events

> 🚀 **v3.17-v3.22 new features (latest 6 sprints, 2026-05-18)**
> - 📝 **QuickCreate per page**: Sales/Purchase/Production add entity + 1-line order UI (§3.8)
> - 📒 **Accounting + E-Invoice**: Journals / AR / Chart of Accounts / e-invoice issue/lookup/void (§3.9)
> - 📈 **Reports center**: DSO/Inventory turn/Gross margin live + AR aging xlsx + 401 (§3.10)
> - 🌍 **Multi-country tax ID**: 6 built-in (TW/CN/US/JP/EU+GENERIC) + plug-in (§3.11)
> - 🔍 **Cmd+K global search**: Ctrl+K/Cmd+K fuzzy search customers/parts/orders (§3.12)
> - 🖨 **Print PDFs**: PO/SO/Delivery Note/Invoice one-click PDF for vendors/customers (§3.13)
> - ✅ **Multi-stage approval workflow**: rules + pending / history (§3.14)
> - 📊 **Process chain visualization**: 📊 button shows where the doc is in the chain (§3.15)
> - 📝 **Document notes**: internal remarks on every PO/SO/WO (§3.16)

> 🆕 **v3.23 new features (Sprint Q, 2026-05-18)**
> - 📋 **Dashboard Todo Center**: see "pending my approval / low stock / draft POs / draft WOs" on login
> - 📖 **Recipe Editor**: renamed from "BOM" — visual editor — **unblocks WO release**
> - 📜 **Inventory Transaction History**: new tab on Inventory page; every inbound/outbound logged

> 🏛️ **v3.25 new feature: "House Rules"** — Ouvoca's signature differentiator
> - **Not copying SAP/鼎新/Odoo's hardcoded rules** — Ouvoca data-fies rules: UI toggle / AI authoring / plugin extension
> - 3 default rules: WO release needs Recipe / PO > NT$100k needs manager / PO must have ≥1 item
> - Author by chat: "SO discount > 5% needs manager" → ConfirmCard → instant
> - Manager override + full audit log
> - **Full guide**: [`docs/HOUSE_RULES_GUIDE_EN.md`](./HOUSE_RULES_GUIDE_EN.md) 🇺🇸 / [`HOUSE_RULES_GUIDE_ZH.md`](./HOUSE_RULES_GUIDE_ZH.md) 🇹🇼

> 🎨 **v3.24 Ouvoca's original vocabulary (don't copy competitors — memorable for beginners)**
> - 🌱 **Sprout** = renamed from "Lead" (seed grows into customer)
> - 🎯 **Chase** = renamed from "Opportunity" (deals salespeople chase daily)
> - 📖 **Recipe** = renamed from "BOM" (like cooking recipe — what parts the product is made of)
> - 👤 **Customer Full View** = renamed from "Customer 360"
>
> Bilingual mapping: see `src/i18n/locales/{zh-TW,en}.ts` under `ouvocaTerms`

> 🏭 **v3.60–v3.69: everything that shipped after this manual's first edition (§12–§16)**
> Chapters 1–11 describe the product as of v3.25. The releases below arrived later and are documented in
> five new chapters at the end of this manual:
> - 📄 **§12 Procurement and shop-floor documents** — Purchase Requisition (PR) / Goods Receipt Note (GRN) / Material Issue (MI) / Return Note (RT) — *v3.63*
> - 📨 **§13 Sourcing with RFQ** — issue a request for quotation, record supplier quotes, compare, award, auto-convert to a PO — *v3.64*
> - 🔍 **§14 Traceability and barcode scanning** — scanner bar on the Inventory page, batch/lot and serial trace, 60 × 40 mm QR part labels — *v3.64*
> - 📒 **§15 Finance close** — trial balance / income statement / balance sheet, Taiwan VAT 401/405, supplier-invoice 3-way match, promissory notes, fixed assets and depreciation, COGS settlement, bank/payment/receipt — *v3.60–v3.61*
> - 🔐 **§16 Security and system administration** — MFA (TOTP), login lockout, backup and restore, 14 system settings, upload content validation — *v3.60–v3.64*
>
> ⚠️ **Read §15.1 before you go hunting for buttons.** A number of these features ship as REST API +
> AI chat only — no page has been built for them yet. Every section below states its entry point
> explicitly: **Screen**, **Chat**, or **API only**.

---

## A Note for First-Time Readers

If you're not a "computer person" and the word "ERP" makes your head spin — **don't worry, we redesigned it for you**.

This Ouvoca does not require you to memorize where menus live, what fields are called, or which button comes first.
**If you can type, you can use it.** Open your browser, type into the chat box:

> "List parts below safety stock"
> "Order 100 M6 bolts from Chang Jiang Precision, due next Friday"
> "Change SO-2025-0042's delivery date to 6/10"

The AI assistant understands your intent and queries / creates / updates / cancels on your behalf.
**Any action that writes data triggers a Confirm Card** that you must click — and if you click wrong, you have **90 seconds to undo**.

---

## Table of Contents

1. [System Overview (5 min)](#1-system-overview)
2. [First Login (3 min)](#2-first-login)
3. [Interface Tour (5 min)](#3-interface-tour)
4. [Talking to the AI: 4 CRUD Operations (10 min) — KEY CHAPTER](#4-talking-to-the-ai-4-crud-operations)
5. [ConfirmCard (3 min) — KEY](#5-confirmcard)
6. [Slot-filling: When the AI Asks Back (3 min)](#6-slot-filling-when-the-ai-asks-back)
7. [90-second Undo (2 min)](#7-90-second-undo)
8. [Four Personas in Action (10 min)](#8-four-personas-in-action)
9. [Three Licensing Tracks (2 min)](#9-three-licensing-tracks)
10. [FAQ (5 min)](#10-faq)
11. [Troubleshooting (5 min)](#11-troubleshooting)

**Added after the first edition — v3.60 to v3.69**

12. [Procurement and Shop-Floor Documents: PR, GRN, MI, RT (8 min)](#12-procurement-and-shop-floor-documents-pr-grn-mi-rt)
13. [Sourcing with RFQ: quote, compare, award (5 min)](#13-sourcing-with-rfq-request-for-quotation)
14. [Traceability and Barcode Scanning (6 min)](#14-traceability-and-barcode-scanning)
15. [Finance Close: statements, Taiwan VAT, assets, COGS (12 min)](#15-finance-close)
16. [Security and System Administration (8 min)](#16-security-and-system-administration)
17. [Quick Reference for v3.60–v3.69](#appendix-a-quick-reference-for-v360-v369)

---

## 1. System Overview

### 1.1 What is Ouvoca?

Ouvoca is a **Conversational ERP** designed for **small manufacturers with 50–100 employees**.

"ERP" in plain English: **software that manages inventory, orders, purchasing, production, and reports** for a company.
Traditional ERPs (SAP, Oracle) cost millions to license and require 1–3 months of staff training.

**Ouvoca flips that**: you don't learn the interface; you **type what you want to do** and the AI does it.

### 1.2 Three Core Promises

| Promise | Plain English |
|---|---|
| **🗣️ Natural language operation** | Just type what you want. No menu hunting. |
| **🛡️ Confirm everything + 90-second undo** | Every write (create/update/delete) shows a confirm card. Click wrong? You have 90 seconds to undo. |
| **⚡ Real-time, no waiting for month-end** | Owner asks "how's today" — answer in 10 seconds, not a monthly report. |

### 1.3 Who's it for?

This system is designed for **four roles in a 50–100-person manufacturer**:

| Persona | Job | Device |
|---|---|---|
| 👔 **Owner (Mr. Wang)** | Monitor company at a glance; check financials anytime | Office desktop, Chrome browser |
| 👨‍💼 **Sales (Steve)** | Answer stock/price/delivery in front of customers, in seconds | Laptop (Chrome + VPN when traveling) |
| 👨‍🏭 **Plant Manager (Lin)** | Spot bottlenecks; release WOs; adjust scheduling | Office desktop + factory floor war-room screen |
| 👩‍💻 **Purchaser/Warehouse (Lina)** | Create POs; receive goods; cycle counting | Desktop + USB barcode scanner |

### 1.4 What can you actually do?

Four operation classes (industry term: **CRUD**):

| Letter | Meaning | Example phrasing |
|---|---|---|
| **C** = Create | Add | "Order 100 M6 bolts from Chang Jiang Precision" |
| **R** = Read | Query | "List parts below safety stock" |
| **U** = Update | Change | "Change SO-2025-0042's due date to 6/10" |
| **D** = Delete | Cancel | "Cancel PO-2025-0107" |

---

## 2. First Login

### 2.1 Open the system

After IT has deployed the system (if not, see `INSTALLATION_EN.md`), all you do is:

1. Open **Chrome** (latest version recommended; Edge / Firefox also work)
2. In the address bar, type: `http://localhost:5173` (or the URL IT gave you)
3. Press Enter

You'll see the login screen:

```
┌─────────────────────────────────────────┐
│                                  🇹🇼 🇺🇸 │
│                                          │
│            Ouvoca Conversational ERP    │
│                                          │
│         ┌──────────────────────┐         │
│         │ Username              │         │
│         │ ┌──────────────────┐ │         │
│         │ │ admin             │ │         │
│         │ └──────────────────┘ │         │
│         │                       │         │
│         │ Password              │         │
│         │ ┌──────────────────┐ │         │
│         │ │ ••••••••          │ │         │
│         │ └──────────────────┘ │         │
│         │                       │         │
│         │   [ Sign In ]         │         │
│         │                       │         │
│         │  ── or ──             │         │
│         │  [ Enter Demo Mode ]  │         │
│         └──────────────────────┘         │
│                                          │
└─────────────────────────────────────────┘
```

### 2.2 Enter credentials

| Step | Action |
|---|---|
| 1 | Click the **Username** field |
| 2 | Type your username (default: `admin`) |
| 3 | Tab to or click the **Password** field |
| 4 | Type your password (default: `admin123`) |
| 5 | Click the blue **[ Sign In ]** button (or press Enter) |

> ⚠️ **Change the default password right after first login!**
> Top-right avatar → Profile → Change Password

### 2.3 Don't want to memorize credentials? Demo mode

If you're just trying things out:
- Click **[ Enter Demo Mode ]**
- All features are unlocked for exploration

> ⚠️ Demo mode is **turned off in production** by IT. Use real credentials when you go live.

### 2.4 Switch language

Top-right of the login screen has two flag buttons:

| Flag | Meaning |
|---|---|
| 🇹🇼 | Switch to 繁體中文 |
| 🇺🇸 | Switch to English |

Same toggle is in the top-right after login. **Switching is instant** — no re-login required.

---

## 3. Interface Tour

### 3.1 What the main screen looks like

```
┌──────────────────────────────────────────────────────────────────┐
│  [Left Sidebar]      │  [Top-right Header]                        │
│                       │           🇹🇼 / 🇺🇸    👤 admin  [Sign out]│
│  🏠 Home              │                                              │
│  📊 Dashboard         │                                              │
│  ─────────           │    Main content (changes by page)            │
│  📦 Inventory         │                                              │
│  🛒 Purchase          │    e.g. clicking Dashboard shows:            │
│  💰 Sales             │       - AI summary                           │
│  🏭 Production        │       - 4 key cards                          │
│  🔬 Quality           │       - Recent work orders                   │
│  📈 Reports           │       - Low-stock alerts                     │
│  ⚙️  Settings         │                                              │
│                       │                                              │
│  ─────────           │                                              │
│  💬 AI Assistant      │  ← Click here to chat with AI                │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Twelve pages in the left sidebar (v3.16+)

Three groups: **Overview** / **Operations** / **System**

#### 📊 Overview
| # | Icon | Name | Purpose |
|---|---|---|---|
| 1 | 📊 | **Dashboard** | KPI cards (revenue / WO / stock alerts) + charts |
| 2 | 💬 | **AI Assistant** | Conversational CRUD: query/create/update/delete by talking |
| 3 | 📡 | **Event Stream** | Real-time system events (new orders / WO complete / stock alerts) |

#### 🏭 Operations
| # | Icon | Name | Purpose |
|---|---|---|---|
| 4 | 📦 | **Inventory** | Parts, suppliers, stock queries |
| 5 | 🛒 | **Purchase** | PO creation, lookup, goods receipt |
| 6 | 🏭 | **Production** | Work orders (WO), progress tracking |
| 7 | 💰 | **Sales** | SO, customer list |
| 8 | 🤝 | **CRM** ✨ | **NEW** Lead pipeline / Opportunity Kanban / Customer 360 (see §3.6) |
| 9 | 🔬 | **Quality** | Inspection records (**read-only audit**; intentional) |

#### 🛡 System
| # | Icon | Name | Purpose |
|---|---|---|---|
| 10 | 🛡️ | **Permissions** | Roles, permission assignment (admin only) |
| 11 | 🔑 | **My Permissions** | See your own permissions |
| 12 | ⚙️ | **Settings** ✨ | **NEW** AI config / load demo / upload files (see §3.5) |

### 3.3 Three things in the top-right header

| Element | Purpose |
|---|---|
| 🇹🇼 / 🇺🇸 | Instant ZH/EN switch |
| 👤 admin (your name) | Click for Profile / My Permissions / Change Password |
| **[ Sign out ]** | End your session; recommended before leaving for the day |

### 3.4 Where's 💬 AI Assistant?

This is the **most important v3.x feature**. Click **💬 AI Assistant** in the sidebar; a chat panel opens:

```
┌──────────────────────────────────────────────────────┐
│  💬 Ouvoca AI Assistant                         ✕  │
├──────────────────────────────────────────────────────┤
│                                                       │
│  AI: Hi! I'm the Ouvoca assistant. Try saying:       │
│      "List today's in-progress work orders"           │
│      "Order 100 M6 bolts from Chang Jiang Precision"  │
│      "Change SO-2025-0042 due date to 6/10"           │
│                                                       │
│  ─────────────── Conversation history ──────────────  │
│                                                       │
├──────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐  │
│  │ Type your question...                          │  │
│  └──────────────────────────────────────────────┘  │
│                                          [ Send ]   │
└──────────────────────────────────────────────────────┘
```

**How to use**:

| Step | Action |
|---|---|
| 1 | Click in the "Type your question..." box |
| 2 | Type, e.g.: "List today's in-progress work orders" |
| 3 | Press Enter (or click **[ Send ]**) |
| 4 | Wait 2–10 seconds; the AI replies |

### 3.5 ⚙️ Settings Page ✨ NEW in v3.13

Click **⚙️ Settings** in the sidebar. Four sections (**everything a non-technical user needs is here**):

#### A. 🤖 AI Assistant Configuration

First-time install without an LLM API key? **Paste it here yourself** — no command line needed.

| Step | Action |
|---|---|
| 1 | Click the **Provider** dropdown → pick "DeepSeek (recommended)" |
| 2 | Click the **"No account? Sign up →"** link, follow steps for 5 min to get `sk-...` |
| 3 | Paste `sk-...` into the **API Key** field |
| 4 | Click **🧪 Test Connection (no save)** — should show ✅ green |
| 5 | Click **💾 Save (effective immediately)** — no restart needed |

💡 Full guide: [`HOW_TO_GET_LLM_API_KEY_EN.md`](./HOW_TO_GET_LLM_API_KEY_EN.md)

#### B. 📦 Demo Data

Built-in: 5 customers / 3 suppliers / 10 parts (with `DEMO-` prefix). Clear after trial:
- **➕ Load demo data** — writes demo data to DB (idempotent)
- **🗑 Clear demo data** — only removes `DEMO-` prefixed rows; your own data is safe

#### C. 📁 Upload Business Files

Upload customer quotes / invoices / specs / contracts (future AI parsing):

| Step | Action |
|---|---|
| 1 | Pick category (quote / invoice / contract / spec / general) |
| 2 | Write a brief description (optional) |
| 3 | **Drag file into the dropzone**, or click to browse |
| 4 | Wait for ✅ upload success |

Supports: PDF / Excel / CSV / Word / images, 25 MB max per file.

#### D. ℹ️ System Info

Version, license track, commercial inquiry link.

### 3.6 🤝 CRM Page ✨ NEW in v3.15

Click **🤝 CRM** in the sidebar. Three tabs:

#### Tab 1: 📋 Lead Pipeline

**What's a Lead?** A potential customer (from trade show / ad / referral) not yet a paying client.

4-column funnel: 🆕 New → 📞 Contacted → ✅ Qualified → ❌ Lost (or 🎯 Converted)

Click **➕ Create Lead** to add. Qualified leads have a **🎯 Convert to Customer** button.

#### Tab 2: 💼 Opportunity Kanban

**What's an Opportunity?** A customer with buying intent currently in active sales pursuit.

5 stages: 🔍 Prospect → 📝 Proposal → 🤝 Negotiation → 🎉 Won → ❌ Lost

Each card has a **Move to next →** button (no drag-and-drop needed).
The top shows **Weighted Pipeline NT$ X** = sum of (amount × probability%).

#### Tab 3: 👤 Customer 360

**The killer feature.** Pick one customer → see everything related in one view:

- Basic info (code / grade / contact)
- Stats (orders / opportunities / activities count)
- Orders list / Opportunities list
- **Activity timeline** — auto-populated when you place orders, convert leads, advance opportunities.
  Click **📝 Add Activity** for manual notes (calls / complaints / etc.).

### 3.7 💡 AskAI Floating Button ✨ NEW in v3.16 (Ouvoca original)

**Purple 💡 button** in the bottom-right corner of every page (except AI Assistant itself).

**Purpose**: Live AI coach for the page you're on. Stuck? Don't dig through docs — click and ask.

Features:
- Knows **which page you're on** (context-aware answers)
- 3 quick suggestion buttons: tap to send common questions
- No LLM key set? Shows a 3-step setup guide (not a cold error)

---

---

## 4. Talking to the AI: 4 CRUD Operations

**This is the most important chapter — read it carefully.**

Everything an ERP can do boils down to four classes: **Read / Create / Update / Delete**.
We made all four typeable. Below: one or two examples per class.

### 4.1 Read — no Confirm Card, instant answer

**Simplest case. AI answers directly (no data was changed).**

#### Example 1: list parts below safety stock

You type:

```
List parts below safety stock
```

AI replies (about 3–5 seconds):

```
Found 3 parts below safety stock:

┌────────────────┬────────┬──────────┬────────┐
│ Part No        │ OnHand │ Safety   │ Gap    │
├────────────────┼────────┼──────────┼────────┤
│ M6-BOLT-20     │  300   │   500    │  -200  │
│ SUS304-PLATE   │   12   │    50    │   -38  │
│ GEAR-A-3MM     │    0   │    20    │   -20  │
└────────────────┴────────┴──────────┴────────┘

Suggest restocking GEAR-A-3MM first (stockout).
```

#### Example 2: sales snapshot

You type:

```
What is this month's revenue? Top 3 customers?
```

AI replies:

```
This month (2026-05) revenue: NT$ 4,820,000

Top 3 customers:
1. China Steel Structure   NT$ 1,800,000 (37%)
2. Delta Electronics       NT$   980,000 (20%)
3. Hon Hai Precision       NT$   720,000 (15%)
```

> 💡 Read operations **don't require a Confirm Card** — the AI just answers.

---

### 4.2 Create — triggers ConfirmCard

**Anything that writes data → AI always shows a Confirm Card.**

#### Example 3: create a purchase order

You type:

```
Order 100 M6 bolts from Chang Jiang Precision, due next Friday
```

AI replies (no order created yet — a card appears):

```
┌────────────────────────────────────────────────────┐
│  📋 ConfirmCard: please confirm this PO             │
├────────────────────────────────────────────────────┤
│  Supplier  │ Chang Jiang Precision (S-0023)         │
│  Part No   │ M6-BOLT-20 (resolved from "M6 bolt")   │
│  Quantity  │ 100                                     │
│  Unit price│ NT$ 0.5 (last contract price)           │
│  Total     │ NT$ 50                                  │
│  Due date  │ 2026-05-22 (next Friday)                │
│  Terms     │ Net 30 (supplier default)               │
├────────────────────────────────────────────────────┤
│        [ ✓ Confirm ]   [ ✏ Edit ]   [ ✗ Cancel ]    │
│             Auto-cancels in 90s ⏱ 88                 │
└────────────────────────────────────────────────────┘
```

**Your action**:

| Want to | Click |
|---|---|
| Looks good, order it | **[ ✓ Confirm ]** |
| Quantity wrong, fix it | **[ ✏ Edit ]** (drops back to chat so you can say "make it 200") |
| Forget it | **[ ✗ Cancel ]** |

After clicking **[ ✓ Confirm ]**:

```
✅ PO-2026-0142 created.
   Notification sent to Chang Jiang Precision.
   ETA: 2026-05-22

   💡 Made a mistake? Within 90 seconds, say "undo last action" to revert.
```

---

### 4.3 Update — also triggers ConfirmCard

**Changing data is just as risky as creating; the AI also shows a Confirm Card.**

#### Example 4: change a sales order's due date

You type:

```
Change SO-2025-0042 due date to 6/10
```

AI replies:

```
┌────────────────────────────────────────────────────┐
│  📋 ConfirmCard: please confirm this update         │
├────────────────────────────────────────────────────┤
│  Sales Order │ SO-2025-0042                         │
│  Customer    │ China Steel Structure (C-0007)        │
│  Item        │ GEAR-A-3MM × 500                     │
│                                                     │
│  Field       │ Due date                             │
│  Old value   │ 2026-06-03                           │
│  New value   │ 2026-06-10 ⚠ +7 days                 │
├────────────────────────────────────────────────────┤
│        [ ✓ Confirm ]   [ ✏ Edit ]   [ ✗ Cancel ]    │
└────────────────────────────────────────────────────┘
```

Click **[ ✓ Confirm ]**:

```
✅ SO-2025-0042 due date updated to 2026-06-10.
   Customer contact auto-notified by email.
   Undo available for 90 seconds.
```

---

### 4.4 Delete / Cancel — red warning ConfirmCard

**Delete is the most dangerous; the AI shows a red card with a strong warning.**

#### Example 5: cancel a purchase order

You type:

```
Cancel PO-2026-0107
```

AI replies:

```
┌────────────────────────────────────────────────────┐
│  ⚠️  ConfirmCard: cancel PO (NOT recoverable)       │
├────────────────────────────────────────────────────┤
│  PO         │ PO-2026-0107                          │
│  Supplier   │ Da-Hua Precision                       │
│  Total      │ NT$ 28,500                            │
│  Status     │ Sent, not yet received                │
│                                                     │
│  📌 Impact:                                         │
│    - PO will be marked "Cancelled"                  │
│    - Supplier will be notified (email)              │
│    - Incoming inventory reduced by 300              │
├────────────────────────────────────────────────────┤
│   [ ✓ Yes, cancel ]    [ ✗ No, keep the PO ]        │
└────────────────────────────────────────────────────┘
```

> 💡 Note: **Quality inspection records cannot be deleted via AI** — they are an audit trail and are kept forever.

---

## 5. ConfirmCard

### 5.1 Why ConfirmCard must exist

**Because AI hallucinates** (industry term for "makes things up").

For example:
- You say "Chang Jiang", AI might pick the wrong "Chang" supplier
- You say "100 units", AI might hear "1000 units"
- You say "M6 bolt", but inventory has M6-BOLT, M6-NUT, and M6-WASHER

Without ConfirmCard, AI executes immediately → **you spend 10× too much, or order from the wrong supplier**.

**ConfirmCard design philosophy**:
> AI parses your sentence and drafts the action;
> **a human gives the final sign-off** by clicking confirm.

### 5.2 What's on a ConfirmCard

Every card has:

| Section | Content |
|---|---|
| **Title** | What action this is (create PO / update SO / cancel WO ...) |
| **Summary table** | Every field, with the value parsed by AI |
| **Impact note** | What downstream effects this triggers |
| **Three buttons** | ✓ Confirm / ✏ Edit / ✗ Cancel |
| **Countdown** | Auto-cancels after 90 seconds (in case you forget) |

### 5.3 Four risk tiers behind the scenes

Tools are classified into four risk tiers; cards differ by color:

| Tier | Color | Example | Card behavior |
|---|---|---|---|
| 🟢 **Read** | no card | "List inventory" | Instant answer, no card |
| 🟡 **Soft-write** | Yellow | "Save search filter" | Light card + easy undo |
| 🟠 **Hard-write** | Orange | "Create PO" / "Change due date" | **Full ConfirmCard + 90s Undo** |
| 🔴 **Critical** | Red | "Delete customer" / "Cancel large PO" | **Red card + type-to-confirm** |

---

## 6. Slot-filling: When the AI Asks Back

### 6.1 What is slot-filling?

A "slot" is just a field. If you leave fields out, the AI **does not invent values** — it asks back.

### 6.2 Example: incomplete input

You type:

```
Send a PO to China Steel
```

AI replies:

```
OK, you want a PO to China Steel. Please tell me:

1. Which part? (Part No or description)
2. Quantity?
3. Due date?

You can answer in one line, e.g. "M6-BOLT-20, 1000 pcs, next Friday"
```

You reply:

```
M6 bolt 1000 pcs next Friday
```

AI replies (still ambiguous):

```
"M6 bolt" matches 3 parts — please pick one:

   ┌─────────────────────────────────────┐
   │ ⓪ M6-BOLT-20 (hex bolt, most used)  │
   │ ① M6-NUT (M6 nut)                    │
   │ ② M6-WASHER (M6 washer)              │
   └─────────────────────────────────────┘

Reply with the number (e.g. "0") or the full Part No.
```

Reply `0` → AI shows the full ConfirmCard.

### 6.3 Why this design?

**No follow-up questions = AI guesses = your company orders wrong**.
We'd rather ask a couple extra questions than cost you money.

> 💡 **Max 3 follow-ups**: if AI still can't pin it down after 3 questions, it suggests you switch to the **Purchase** sidebar form to fill it manually.

---

## 7. 90-second Undo

### 7.1 How to undo

Within **90 seconds** of any create / update / delete, you can undo.

#### Method 1: type it

In the AI chat box:

```
Undo last action
```

or

```
Cancel the one I just did
```

AI replies:

```
✅ Undid PO-2026-0142 creation.
   PO marked as "Recalled".
   Chang Jiang Precision was notified of the recall.
```

#### Method 2: click the inline button

After every write, the AI's response includes a small button:

```
✅ PO-2026-0142 created.

   [ ↩ Undo (67s left) ]
```

Just click it.

### 7.2 Undo limitations

| Situation | Can undo? |
|---|---|
| Within 90s, PO not yet received | ✅ Yes |
| Within 90s, PO partially received | ❌ No (downstream side effects) |
| Past 90s | ❌ No — use the normal "Cancel document" workflow |
| Someone else confirmed it; you want to undo | ❌ No — only the confirmer can undo |

---

## 8. Four Personas in Action

### 8.1 👔 Mr. Wang (Owner) — desktop morning briefing

**Scenario**: 8:30 AM, walks into the office, wants today's status.

**Steps**:

| # | Action |
|---|---|
| 1 | Open Chrome → `http://localhost:5173` |
| 2 | Login as `boss_wang` |
| 3 | Lands on 📊 **Dashboard** by default; AI summary appears at the top |

AI summary looks like:

```
┌────────────────────────────────────────────────────┐
│ 📈 Morning, Mr. Wang! Today's brief (2026-05-17)    │
├────────────────────────────────────────────────────┤
│                                                     │
│ ✅ Yesterday: 12 shipments, NT$ 580,000 revenue     │
│ ⚠️  Pending releases today: 3 WOs (urgent SO-0042)  │
│ 🔴 Stock alert: M6 bolts 300 (< safety 500)         │
│ 💰 AR DSO: 48 days (+3 vs last month)               │
│                                                     │
│ [ View details ] [ Handle urgent ] [ Notify Lina ]  │
└────────────────────────────────────────────────────┘
```

**Want more?** Click **💬 AI Assistant** and type:

```
What's this month's gross margin? Compared to last month?
```

AI replies:

```
This month gross margin: 23.4% (NT$ 1,128K / NT$ 4,820K)
Last month: 21.8%
Change: +1.6 pp 📈

Main driver: CNC machined parts margin rose from 18% to 22%.
```

---

### 8.2 👨‍💼 Steve (Sales) — 3-second answer in front of customer

**Scenario**: Steve is at the customer's office. Customer asks: "Do you still have the GEAR-A I bought last time? How soon can you deliver?"

**Steps**:

| # | Action |
|---|---|
| 1 | Open laptop Chrome (VPN already connected) |
| 2 | Login, click **💬 AI Assistant** |
| 3 | Type |

Input:

```
GEAR-A-3MM for China Steel Structure — current stock and earliest commitable delivery?
```

AI replies (3–5 seconds):

```
China Steel Structure (C-0007) × GEAR-A-3MM:

   On hand:         420
   In production:   150 (WO-2026-0089, completes 5/22)
   Reserved:         80
   ─────────────────────────
   Available to promise:  490
   Earliest ship:    if ordered today, ship 5/23

   📌 Last price to China Steel: NT$ 4,500/pc (2026-04-20)
```

**Customer says "Order 300"**:

```
Create SO for China Steel Structure: GEAR-A-3MM × 300, use last price, due 5/30
```

AI shows ConfirmCard, Steve clicks **[ ✓ Confirm ]** → SO created in 30 seconds.

> 💡 Steve **cannot see other reps' customers** — this is RBAC (role-based access control).

---

### 8.3 👨‍🏭 Lin (Plant Manager) — desktop + war-room screen

**Scenario A: desk view**

Lin opens the dashboard, clicks **🏭 Production**, and sees the war-room view:

```
┌──────────────────────────────────────────────────────┐
│   🏭 Production War-Room (live)         2026-05-17 09:42│
├──────────────────────────────────────────────────────┤
│                                                       │
│   In-progress WOs: 15      Avg progress: 68%          │
│                                                       │
│   ⚠️  Delay alerts:                                   │
│   ┌────────────────────────────────────────────┐    │
│   │ WO-2026-0073  Bearing Block B  2 days late 🔴│   │
│   │ WO-2026-0081  Outer Casing     1 day late 🟡 │   │
│   └────────────────────────────────────────────┘    │
│                                                       │
│   📦 Material risk:                                   │
│   ┌────────────────────────────────────────────┐    │
│   │ M6-BOLT-20  300 left, weekly need 800 → -500│   │
│   └────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

**Scenario B: release a WO via chat**

Lin types:

```
Release WO-2026-0091 and assign to machine CNC-A
```

AI shows ConfirmCard, click **[ ✓ ]** → WO drops to the shop floor.

---

### 8.4 👩‍💻 Lina (Purchaser/Warehouse) — desktop + USB barcode scanner

**Scenario A: PO via chat**

Lina gets an email from Lin: "restock M6 bolts". She tells AI:

```
Order from Chang Jiang Precision: M6-BOLT-20 × 2000, due next Wed, Net 30
```

AI shows ConfirmCard, Lina confirms, PO created.

**Scenario B: receive goods with USB scanner**

| # | Action |
|---|---|
| 1 | Open **🛒 Purchase** → find `PO-2026-0142` |
| 2 | Click **Receive** — receiving form opens |
| 3 | Plug USB barcode scanner into the PC |
| 4 | Point at the supplier's box barcode, **beep** |
| 5 | System auto-fills Part No and expected quantity |
| 6 | Type the actual received quantity |
| 7 | Click **Confirm Inwarding** → stock +N, PO marked "Received" |

> 💡 Advanced USB-scanner workflows (multi-bin, batch/lot tracking) are scheduled for **Phase 2**. The current release supports the basic "beep, get the Part No" workflow only.

---

## 9. Three Licensing Tracks

Ouvoca ships under three licensing tracks — **picking the right one can save millions**.

| Track | For whom | Cost | Highlight |
|---|---|---|---|
| 🟢 **AGPL** | Want to inspect source, OK with sharing your modifications | Free | Fully open-source |
| 🌱 **Small Business** | 50–100-person factory, ≤ 20 concurrent users | **Completely free** | **Includes closed-source connectors** (Digiwin / Chain Sea integrations) <sup>※</sup> |
| 🔵 **Commercial** | > 20 concurrent users, ISVs, SaaS providers | Negotiated | Removes AGPL clauses |

> ⚠️ <sup>※</sup> **Recommended reading**: The connector is a **technical connectivity component**. If you connect Ouvoca to an **existing commercial ERP** (e.g., products from vendors such as Digiwin / Chain Sea / SAP B1 / Vitals), each vendor's license agreement may treat "shared / service account connections" differently; the specifics depend on your contract with that vendor. We recommend first confirming the authorization scope in writing with the incumbent ERP vendor and purchasing any required add-on licenses where applicable. Ouvoca **does not participate in or represent the customer in** any contracts or licensing matters with the incumbent ERP vendor; to the maximum extent permitted by applicable law, Ouvoca assumes no responsibility for consequences arising from a customer enabling a connection without obtaining appropriate authorization. See [`docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md).

### How to apply for Small Business?

It's free, but registration is required. See:

- 📄 **`LICENSE-COMMERCIAL.md`** (in the project root)
- 📄 **`docs/COMMERCIAL_LICENSING_FAQ_ZH.md`**

Email the licensing contact with your company name, headcount, and expected concurrent users. You'll receive a Small Business grant letter.

---

## 10. FAQ

### Q1: Does the AI handle typos?

→ Mostly yes. "M6 bolt", "m6 buoy", "M6 螺絲" all attempt to resolve.
When unsure, the AI asks back.

### Q2: What if the AI answers wrong?

→ For Read: re-ask with clearer phrasing.
For Create/Update/Delete: if the ConfirmCard looks wrong, click **[ ✏ Edit ]** or **[ ✗ Cancel ]** — do not confirm.

### Q3: How long is chat history kept?

→ Default 30 days (IT-configurable).
To view: top-right 👤 avatar → "My Conversations".

### Q4: Can I switch roles, e.g., a salesperson viewing the plant manager's screen?

→ One account = one role; **you can't self-switch**.
Ask IT / the owner to add a role under **⚙️ Settings → Users**.

### Q5: Can I export to Excel?

→ Every list page has **📥 Export CSV** in the top-right (CSV opens in Excel).
Native `.xlsx` export is scheduled for Phase 2.

### Q6: Forgot my password?

→ Ask IT to reset. Self-service email reset is scheduled for Phase 2.

### Q7: Can I use voice input?

→ **Phase 4** (Whisper speech-to-text). Currently text only.

### Q8: Can multiple factories share one system?

→ Yes — it's called **MESH multi-factory**: each site's data stays local, HQ runs aggregate queries. See `NETWORK_DEPLOYMENT_EN.md`.

### Q9: AI not responding?

→ See §11.3 Troubleshooting.

### Q10: What do I need before commercial use?

→ See Chapter 9 plus `LICENSE-COMMERCIAL.md`.

---

## 11. Troubleshooting

### 11.1 Can't reach the login page

| Symptom | Fix |
|---|---|
| Browser says "Cannot reach this site" | Have IT confirm backend is up: `docker compose ps` |
| 503 / 504 errors | Ask IT to restart: `docker compose restart backend` |
| 401 keeps popping up | Press F12 → Application → Storage → Clear site data, refresh |
| **Windows: page loads but forms / reports / printing all fail** | **Use `http://127.0.0.1:5173`** instead of `localhost` — Windows Docker Desktop sometimes resolves `localhost` to IPv6 `::1` and CORS blocks it. v3.25.7 fixed this by defaulting to 127.0.0.1 binding + adding 127.0.0.1 variants to CORS |
| F12 console keeps showing CORS errors | Same as above — try `http://127.0.0.1:5173`. If still failing, have IT add `CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://your-domain:5173"]` in `backend/.env` |

### 11.2 No data shown

| Symptom | Fix |
|---|---|
| Empty list | IT hasn't seeded demo data (`docker compose exec backend python -m scripts.seed`) |
| Only see customers you created | **By design** (RBAC). Not a bug |
| Button returns 403 | Your role lacks permission — ask IT to grant |

### 11.3 AI Assistant unresponsive

| Symptom | Fix |
|---|---|
| Shows "[demo mode]" | IT hasn't set the LLM API key in `.env` (`LLM_API_KEY`) |
| Shows "LLM call failed" | Key may be expired / out of quota — ask IT |
| Long wait (> 30s) | LLM is thinking; allow up to 60s; otherwise check backend logs |
| AI keeps asking the same thing | After 3 follow-ups it will suggest using the sidebar form instead |

### 11.4 ConfirmCard issues

| Symptom | Fix |
|---|---|
| Card auto-cancelled (countdown hit zero) | Just re-ask the AI |
| **[ ✏ Edit ]** does nothing | Refresh (F5) and re-ask |
| **[ ✓ Confirm ]** spins forever | Look for error in the bottom-right; have IT check the backend |

### 11.5 Undo failed

| Symptom | Fix |
|---|---|
| "Past 90 seconds, cannot undo" | Use the formal "Cancel document" workflow |
| "Action consumed by downstream flow" | E.g., PO partially received — return the goods first |
| "You are not the executor" | The person who confirmed must undo |

### 11.6 Still stuck?

Contact internal IT and include:
- Screenshot (Win+Shift+S)
- The exact phrasing you typed
- Error message (if any)
- Timestamp

Or email your company's ERP support contact.

---

## 12. Procurement and Shop-Floor Documents (PR, GRN, MI, RT)

> 🆕 **v3.63 "M3 form engineering"** — four documents that turn informal shop-floor traffic
> ("just grab the bolts off the rack") into records an auditor can follow.

### 12.0 How to read §12–§16

Every feature from here on is tagged with one of three entry points. **Check the tag before you go
looking for a button** — some of this functionality genuinely has no screen yet.

| Tag | Meaning |
|---|---|
| 🖥 **Screen** | There is a button or tab in the web UI. Screen labels are in Traditional Chinese; this manual prints the Chinese label followed by an English gloss, e.g. **🚚 進貨** *(Receive)*. |
| 💬 **Chat** | You type it into **💬 AI Assistant**. Anything that writes data raises a ConfirmCard first. |
| 🔌 **API only** | No button and no chat tool yet — IT calls the REST endpoint (or waits for a future release). |

> ⏱ **About the ConfirmCard countdown.** Cards raised by the tools in §12–§16 expire after
> **30 minutes**, not the 90 seconds quoted in §5 (`DEFAULT_TTL_SECONDS = 1800` in
> `backend/app/agents/confirm_card.py`). Trust the timer printed on the card in front of you.

### 12.1 Which document do I need?

| Document | Label on screen / in chat | What it records | Typical author | Status flow | Entry point |
|---|---|---|---|---|---|
| **PR** — Purchase Requisition | 請購單 | "We are going to run out of bolts" — a *request*, not a commitment to a supplier | Anyone on the floor | `draft` → `approved` → `converted` | 💬 create & convert · 🔌 approve |
| **GRN** — Goods Receipt Note | 收料單 | Formal proof that goods physically arrived against a PO | Warehouse | created as `posted` | 💬 (🖥 has a simpler receive button) |
| **MI** — Material Issue | 領料單 | Stock leaving the warehouse *for a specific work order*, with a cost snapshot | Warehouse / plant manager | created as `posted` | 💬 |
| **RT** — Return Note (RMA) | 退貨單 | Customer sends goods back to you | Sales | `draft` → `approved` → `processed` | 💬 create · 🔌 approve & process |

**Document numbers** come from the central numbering service added in v3.60
(`{PREFIX}-{TENANT}-{PERIOD}-{SEQ:04d}`), so a PR raised today reads like `PR-HQ-20260804-0001`.
The counter is atomic: two people creating documents in the same second cannot end up with the same
number.

---

### 12.2 Purchase Requisition (PR)

**Scenario** — Lin (plant manager) sees that M6 bolts will not last the week. He has no authority to
commit money to a supplier, but he can raise a requisition; Lina in purchasing turns it into a real PO.

**Steps**

| # | Where | What you do |
|---|---|---|
| 1 | 💬 AI Assistant | Type `請購 100 個 M6-BOLT-20，8/20 要` — *"Raise a requisition for 100 M6-BOLT-20, needed 8/20"* |
| 2 | ConfirmCard | Check part number, quantity and need date, then click **[ ✓ 確認執行 ]** *(Confirm)* |
| 3 | Write the PR number down | See the warning below — there is no PR list screen yet |
| 4 | Manager | Approves the PR — 🔌 `POST /api/purchase/requisitions/{pr_id}/approve` |
| 5 | 💬 Purchasing | Type `把 PR-HQ-20260804-0001 轉成給長江精密的採購單` — *"convert PR-… into a PO for Chang Jiang Precision"* → ConfirmCard → a real PO is created |

**What you'll see**

```
📋 ConfirmCard — 建立請購單 (Create purchase requisition)
   項目數 (lines): 1
     • M6-BOLT-20  六角螺栓  × 100
   需求日 (need by): 2026-08-20
   ────────────────────────────────
   [ 取消 ]              [ ✓ 確認執行 ]

→ after confirming:  pr_no = PR-HQ-20260804-0001, status = draft
```

On conversion the new PO inherits: the PR's lines and quantities, `Part.unit_cost` as the default
unit price (**not** a negotiated price — check it before you approve the PO), the PR's need date as
the expected delivery date, and the remark `由請購單 PR-… 轉入` *("converted from requisition PR-…")*.
The PR flips to `converted` and can never be converted twice.

> ⚠️ **There is no PR list — anywhere.** No sidebar page, no chat tool, no `GET` endpoint. Once the
> ConfirmCard returns the PR number, copy it into your notes or an email; otherwise the only way to
> find it again is a direct database query by IT. Raising a PR you cannot retrieve is the single most
> common way to lose work in this module.

**Troubleshooting**

| Message you'll see | What it means | What to do |
|---|---|---|
| `找不到料件 'M6BOLT20'` | Part number did not match exactly | PR creation matches `part_no` **exactly** — copy it from the Inventory page |
| `請購單狀態 'draft' 不可轉採購（需先核准）` | You tried to convert before approval | Get the PR approved first (step 4) |
| `此請購單已轉成採購單` | The PR is already `converted` | One PR converts to exactly one PO; raise a new PR |
| `找不到供應商「長江」` | Supplier name didn't match | Supplier lookup matches code exactly or name by "contains" — try the supplier code |
| HTTP 403 | Your role lacks `purchase.pr.create` / `purchase.pr.approve` / `purchase.pr.convert` | Ask an administrator on the **🛡️ Permissions** page |

---

### 12.3 Goods Receipt Note (GRN)

There are **two different ways to receive goods**, and they are not the same thing. Choose
deliberately.

| | 🖥 **Purchase page button** | 💬 **GRN via chat** |
|---|---|---|
| How | **🛒 採購** *(Purchase)* → **📋 採購單** *(Purchase Orders)* tab → row button **🚚 進貨** *(Receive)* | Type `收 PO-HQ-20260804-0001 全部到貨` *("receive PO-… in full")* |
| Quantity | **All remaining quantity on every line** — no editing | Full receipt by default; partial receipt supported |
| Creates a GRN document? | ❌ No | ✅ Yes, numbered `GRN-HQ-…-0001`, status `posted` |
| Updates PO received qty + stock? | ✅ Yes | ✅ Yes, atomically |
| Best for | Small factories that don't need receipt paperwork | Anyone who needs receiving evidence, or partial deliveries |

**Steps — 🖥 receive everything at once**

| # | Action |
|---|---|
| 1 | Open **🛒 採購** *(Purchase)*, stay on the **📋 採購單** *(Purchase Orders)* tab |
| 2 | Find the PO. The **🚚 進貨** button only appears when its status is `approved`, `sent` or `partial_received` |
| 3 | Click **🚚 進貨**. A plain browser dialog asks: `進貨：PO-… 全部訂購量都收到？` *("Receive PO-…: did everything ordered arrive?")* — with the hint `部分收貨請用 AI 對話` *("for partial receipts, use the AI chat")* |
| 4 | Click **OK**. Every line is received in full |
| 5 | You'll see `✅ 進貨完成：3 項` *("receipt complete: 3 lines")* and the PO status badge turns `received` |

**Steps — 💬 partial receipt or receiving paperwork**

| # | Action |
|---|---|
| 1 | Open **💬 AI Assistant** |
| 2 | Type e.g. `PO-HQ-20260804-0001 這批只到 60 個，先收這些` *("only 60 arrived on PO-…, receive those")* |
| 3 | Read the ConfirmCard: PO number, number of receipt lines, and the note that it will create a GRN, update received quantity and post stock **as one atomic operation** |
| 4 | **[ ✓ 確認執行 ]** *(Confirm)* |

**What you'll see afterwards** (both routes)

- PO status becomes `partial_received` if anything is outstanding, `received` when every line is complete.
- **📦 庫存** *(Inventory)* → **📜 異動歷史** *(Transaction history)* tab shows one **➕ 入庫** *(inbound)*
  row per line. The GRN route stamps the source as `goods_receipt_note`; the remark reads
  `GRN GRN-… 收貨（PO PO-…）`.
- GRNs can be listed by IT via `GET /api/purchase/grns`. There is no GRN screen yet.

**Troubleshooting**

| Message you'll see | What it means | What to do |
|---|---|---|
| No **🚚 進貨** button on the row | PO is still `draft`, or already `received` / `cancelled` | Approve the PO first (**✓ 核准** button) |
| `超收：PO 行 … 已收 100，再收 20 超過訂購量 100` | Over-receipt guard | You are receiving more than was ordered. If the supplier really over-shipped, raise a new PO for the extra |
| `採購單狀態 'draft' 不可收貨` | Same as above, from the chat route | Approve the PO |
| A house-rule message such as *"PO must be approved before receiving"* | A policy rule blocked the receipt | Follow the instruction in the message, or ask a manager to override |
| You clicked **🚚 進貨** *and* asked chat for a GRN | The second attempt hits the over-receipt guard | Pick one route per delivery |

---

### 12.4 Material Issue (MI)

**Scenario** — WO-2026-0091 has been released to the floor. The operator draws 100 bolts from the
rack. Without an MI the bolts vanish from the shelf but not from the system, and the work order's
cost is understated.

**Steps** — 💬 **Chat only**

| # | Action |
|---|---|
| 1 | Open **💬 AI Assistant** |
| 2 | Type `WO-2026-0091 領 100 個 M6-BOLT-20` — *"issue 100 M6-BOLT-20 to WO-2026-0091"* |
| 3 | ConfirmCard shows the work order, each part and quantity, and the note *"deducts raw-material stock + takes an issue-cost snapshot"* |
| 4 | **[ ✓ 確認執行 ]** *(Confirm)* |

**What you'll see**

```
issue_no = MI-HQ-20260804-0001, status = posted
```

Each issued line stores `unit_cost` **as it was at the moment of issue**, so raising the part's
standard cost next month does not silently rewrite what this work order consumed.

> ℹ️ **The snapshot is recorded, not yet reported.** Work-order costing (§15.8) currently values
> material from the product's **Recipe (BOM) × standard cost**, not from actual material issues.
> The MI cost snapshot is stored for future actual-cost reporting. Practical consequence: issuing
> more (or less) than the Recipe says will **not** change the work-order cost figure today.

Stock moves out as an `outbound` transaction referencing `material_issue`, with the remark
`MI MI-… 領料（WO WO-…）`. Issues can be listed by IT via `GET /api/production/material-issues`.

**Troubleshooting**

| Message you'll see | What it means | What to do |
|---|---|---|
| `工單狀態 'draft' 不可領料` | The work order has not been released | Release it on **🏭 生產** *(Production)* first — a WO with no Recipe cannot be released |
| `領料數量必須大於 0` | Quantity was zero or negative | Re-state the quantity |
| `找不到料件「…」` | Part number did not match exactly | Copy the exact part number from **📦 庫存** *(Inventory)* |
| HTTP 403 | Missing `production.material_issue.create` | Ask an administrator |

---

### 12.5 Return Note (RT / RMA)

**Scenario** — A customer rejects 10 pieces for a plating defect and ships them back. You need the
goods back on the shelf, but only after someone with authority agrees to accept the return.

**Steps**

| # | Where | Action |
|---|---|---|
| 1 | 💬 AI Assistant | Type `客戶富田精機退回 10 個 M6-BOLT-20，鍍層不良` — *"customer Fu-Tian returns 10 M6-BOLT-20, bad plating"* |
| 2 | ConfirmCard | Verify customer, lines, reason → **[ ✓ 確認執行 ]** *(Confirm)*. The note is created as `draft` |
| 3 | 🔌 Manager | `POST /api/sales/returns/{return_id}/approve` → status `approved` |
| 4 | 🔌 Warehouse | `POST /api/sales/returns/{return_id}/process` → stock goes **back in**, status `processed` |

Existing return notes can be listed via `GET /api/sales/returns` (optionally filtered by status).
Steps 3 and 4 have no button and no chat tool yet.

**What you'll see** — `return_no = RT-HQ-20260804-0001`. After processing, **📦 庫存 → 📜 異動歷史**
shows an **➕ 入庫** *(inbound)* row sourced from `return_note` with the remark `RT RT-… 退貨入庫`.

**Troubleshooting**

| Message you'll see | What it means | What to do |
|---|---|---|
| `退貨單狀態 'draft' 不可入庫（需先核准）` | Someone tried to put stock back before approval | Approve first (step 3) — this ordering is deliberate |
| `退貨單必須至少包含 1 個項目` | No lines were parsed from your sentence | Say the part number and quantity explicitly |
| `找不到客戶「…」` | Customer lookup failed | Customer code must match exactly; the customer *name* is matched by "contains" |

---

### 12.6 One-page summary

| I want to… | Say / click this |
|---|---|
| Ask purchasing to buy something | 💬 `請購 <qty> 個 <part_no>，<date> 要` |
| Turn an approved requisition into a PO | 💬 `把 <PR no> 轉成給 <supplier> 的採購單` |
| Receive a delivery in full, no paperwork | 🖥 **🛒 採購 → 📋 採購單 → 🚚 進貨** |
| Receive part of a delivery, or get a receipt document | 💬 `收 <PO no>，這次只到 <qty> 個` |
| Book material out to a work order | 💬 `<WO no> 領 <qty> 個 <part_no>` |
| Record a customer return | 💬 `客戶 <name> 退回 <qty> 個 <part_no>，<reason>` |

---

## 13. Sourcing with RFQ (Request for Quotation)

> 🆕 **v3.64** — the first module of the procurement chain that got a **real screen**:
> **🛒 採購** *(Purchase)* → **📨 RFQ 詢價** *(RFQ)* tab.

**What an RFQ is for**: instead of phoning one supplier and accepting whatever price you're given,
you publish "I need 1,000 of this part", collect prices from several suppliers, compare them side by
side, and award the business. The winning quote becomes a purchase order automatically — nobody
re-types quantities or prices, so the PO cannot disagree with what you agreed.

### 13.1 The five stages

```
   ＋ 建立詢價單          送出            登錄報價 × N          比價              決標
   Create RFQ    →     Send      →    Record quotes   →    Compare    →    Award
   status: draft      status: sent    (quote_count ↑)      (sorted)      status: awarded
                                                                              ↓
                                                                    a Purchase Order
                                                                    is created for you
```

### 13.2 Step by step (🖥 Screen)

**Scenario** — Lina needs 1,000 M6 bolts and wants three suppliers to bid.

| # | Action | What you'll see |
|---|---|---|
| 1 | **🛒 採購** *(Purchase)* → click the **📨 RFQ 詢價** *(RFQ)* tab | An RFQ table: **詢價單號** *(RFQ no)* / **狀態** *(status)* / **報價數** *(quotes received)* / **操作** *(actions)* |
| 2 | Click **＋ 建立詢價單** *(Create RFQ)* — top right | An inline form opens with **料件** *(part)* and **數量** *(quantity, defaults to 100)* |
| 3 | Pick the part, set the quantity, click **建立** *(Create)* | Green message `✅ RFQ 已建立`; a new row appears with status `draft` |
| 4 | Click **送出** *(Send)* on that row | Message `已送出詢價`; status becomes `sent` |
| 5 | Phone or e-mail your suppliers, then click **登錄報價** *(Record quote)* for each reply | A form appears: **供應商** *(supplier)* dropdown and **單價** *(unit price)* |
| 6 | Choose the supplier, type the unit price, click **登錄** *(Save)* | `✅ 報價已登錄`; the **報價數** *(quote count)* column increases |
| 7 | Click **比價** *(Compare)* | A **比價結果** *(comparison)* panel lists every quote **sorted cheapest first**, with columns **報價** / **金額** *(amount)* / **操作** |
| 8 | Click the red **決標** *(Award)* button on the winning row | Browser dialog: `決標後將自動轉採購單，確定？` *("awarding will convert this to a purchase order — are you sure?")* |
| 9 | Click **OK** | `✅ 已決標並轉成 PO-HQ-20260804-0007` and the new PO appears on the **📋 採購單** tab |

> ⚠️ **Step 4 does not e-mail anybody.** **送出** *(Send)* only flips the RFQ's status to `sent` so
> that quotes may be recorded against it. Contacting suppliers is still a human job — phone, e-mail,
> LINE, whatever you normally use.

> ⚠️ **The comparison table prints the supplier's internal ID, not its name.** Cross-check the ID
> against the **🏭 供應商** *(Suppliers)* tab before awarding, or run the comparison in chat
> (§13.3), which reports amounts per quote and the cheapest price per part.

### 13.3 Multi-part RFQs and everything else (💬 Chat)

The screen handles **one part per RFQ** and **one price per quote**. Anything richer goes through
chat:

| Task | Say this | Tool behind it |
|---|---|---|
| RFQ for several parts at once | `針對 M6-BOLT-20 1000 個和 SUS304-PLATE 50 片發詢價` | `create_rfq_with_confirm` |
| Record a multi-line quote | `長江精密報 M6-BOLT-20 1000 個 每個 5 元，交期 7 天` | `receive_quote_with_confirm` |
| Compare | `RFQ-HQ-20260804-0001 誰最便宜` *("who is cheapest on RFQ-…")* | `compare_quotes` (read-only, no card) |
| Award | `RFQ-HQ-20260804-0001 給長江精密得標` | `award_rfq_with_confirm` |

`compare_quotes` returns each quote's total and lead time **plus the lowest unit price per part
across all suppliers** — useful when no single supplier is cheapest on everything.

> 💡 Awarding via chat needs the internal `quote_id`, which `compare_quotes` prints. Run the
> comparison first, then award.

### 13.4 What awarding actually does

| Effect | Detail |
|---|---|
| Winning quote | status → `awarded`; the RFQ records it as the awarded quote |
| Losing quotes | every other `received` quote → `declined` (kept, not deleted — this is your audit trail for "why did we pick them?") |
| RFQ | status → `awarded`, linked to the new PO |
| New purchase order | Supplier, parts, quantities and **the quoted unit prices** are copied over; expected delivery date = the RFQ's need date; remark reads `由 RFQ RFQ-… 決標轉入` *("converted from awarded RFQ …")* |

The PO arrives as a normal draft purchase order — it still has to be approved
(**✓ 核准**) before it can be received, exactly like a hand-keyed PO.

### 13.5 Troubleshooting

| Symptom / message | What it means | What to do |
|---|---|---|
| `請選擇料件` | You clicked **建立** without picking a part | Choose a part in the dropdown |
| Dropdown is empty | No parts exist yet | Create parts on **📦 庫存** *(Inventory)* first |
| No **送出** button on the row | The RFQ is no longer `draft` | Only draft RFQs can be sent |
| `詢價單狀態 'draft' 不可收報價` | You tried to record a quote before sending | Click **送出** *(Send)* first |
| `請選擇供應商` | No supplier chosen on the quote form | Pick one from the dropdown |
| `此詢價單沒有可報價的項目` | The RFQ has no lines | Delete it and create a new RFQ with a part selected |
| `詢價單狀態 'awarded' 不可決標` | Already awarded | One RFQ awards once. Start a new RFQ for a re-bid |
| HTTP 403 on award | Missing `purchase.rfq.award` | Award authority is separate from creating RFQs — ask an administrator |

---

## 14. Traceability and Barcode Scanning

> 🆕 **v3.64** — a scanner bar on the Inventory page, batch/lot and serial registers, forward and
> backward tracing, and printable 60 × 40 mm QR labels.

**Why a Taiwanese subcontractor cares**: automotive, medical and food customers increasingly ask
*"which raw-material lot went into the parts you shipped us on 5 June?"* — and they want the answer
in hours, not days. Batch and serial records are what turn that question from an archaeology project
into a lookup.

### 14.1 The scanner bar (🖥 Screen)

Open **📦 庫存** *(Inventory)*. The bar sits directly under the page title and is visible on **both**
tabs:

```
┌────────────────────────────────────────────────────────────────────┐
│ 🔫  [ 掃描 / 輸入料號、批號或序號…            ]        [ 掃描 ]     │
│      Scan or type a part no. / lot no. / serial no.     (Scan)     │
└────────────────────────────────────────────────────────────────────┘
```

The input takes focus automatically when the page loads, so a **USB barcode scanner in
keyboard-wedge mode works with no configuration**: point, beep, done — the scanner types the code
and sends Enter, which triggers the lookup. You can equally type a code by hand and click **掃描**
*(Scan)*.

**What the system does with the code** — it tries three lookups in this order and stops at the first
hit:

| Order | Looks for | Result badge |
|---|---|---|
| 1 | An exact **part number** | 類型 = **料件** *(Part)* |
| 2 | A **serial number** | 類型 = **序號** *(Serial)* |
| 3 | A **lot / batch number** | 類型 = **批號** *(Batch)* |

**What you'll see** — a four-cell result strip:

| 類型 *(Type)* | 代碼 *(Code)* | 名稱 *(Name / status)* | 庫存 *(Qty)* |
|---|---|---|---|
| 料件 | M6-BOLT-20 | 六角螺栓 M6×20 | 300 |

plus context buttons: **🏷️ 列印標籤** *(Print label)* for parts, **🔍 追溯** *(Trace)* for serials
and batches.

**Troubleshooting**

| Symptom / message | What it means | What to do |
|---|---|---|
| `找不到對應料號/批號/序號：ABC123` (HTTP 404) | The code matches nothing in any of the three registers | Check for a leading/trailing space; confirm the part exists on this tenant; serials and batches must have been registered first (§14.3) |
| Scanner types the code but nothing happens | The scanner isn't sending Enter | Configure the scanner to append a carriage return, or click **掃描** *(Scan)* |
| HTTP 403 | Missing `inventory.inventory.read` | Ask an administrator |

### 14.2 Tracing a batch or a serial (🖥 / 💬)

**Scenario** — a customer complains about parts from lot `LOT-20260801`. You need to know where that
lot came from and which of your outbound documents consumed it.

**Steps** — scan or type the lot number, then click **🔍 追溯** *(Trace)*.

**What you'll see**

```
批號 LOT-20260801：流入 1 筆 / 流出 3 筆動向
Lot LOT-20260801: 1 inbound movement / 3 outbound movements
```

The same trace in chat (`追溯 LOT-20260801`) returns the full structure: the lot master record
(quantity, expiry date, status `active` / `consumed` / `expired` / `void`) and every movement with
its direction, quantity, document type and **resolved document number** — split into
`backward_received_from` (where it came from) and `forward_consumed_by` (where it went).

For a serial number, the trace answers a narrower question:

```
序號 SN-000123：in_stock
Serial SN-000123: in_stock
```

> ⚠️ **Know the current limits before you promise a customer anything.**
> - **Batch movements are matched on the batch number stamped on each stock transaction.** Receiving
>   through **🚚 進貨** or a GRN, issuing through an MI, and shipping do **not** stamp one today. The
>   only route that records a batch number on a movement is a manual stock transaction
>   (`POST /api/inventory/transactions` with `batch_no`). Until that changes, treat the batch module
>   as a **register plus manually-keyed movements**, not as automatic end-to-end pegging.
> - **A serial's "last document" field is not written by any flow yet**, so serial tracing currently
>   answers *"is this serial ours, and what state is it in"* rather than *"which delivery note did it
>   leave on"*.
>
> Both are known gaps rather than mistakes on your part. If lot-level pegging is contractually
> required, raise it with your integrator before you commit to a customer audit.

### 14.3 Registering batches and serials (💬 Chat only)

| Task | Say this | Notes |
|---|---|---|
| Create / update a lot | `料件 M6-BOLT-20 建批號 LOT-20260801，1000 個，2027-08-01 到期` | Re-using the same lot number for the same part **updates** quantity and expiry instead of creating a duplicate |
| Register serials in bulk | `登記 SN-000001 到 SN-000010 給 M6-BOLT-20，批號 LOT-20260801` | Serials are created with status `in_stock`; the batch is optional |

**Troubleshooting**

| Message | Meaning | Fix |
|---|---|---|
| `序號 SN-000123 已存在` | Serial numbers are globally unique | Use a different serial; the whole batch is rejected, so fix the list and re-run |
| `批號數量不能為負` | Negative quantity | Re-state the quantity |
| `找不到批號「…」` when registering serials | The lot must exist before serials can point at it | Create the lot first |

Lots can be listed by IT via `GET /api/warehouse/batches` (optionally per part). There is no batch
list screen yet — the scanner bar is the everyday entry point.

### 14.4 QR part labels (🖥 Screen)

**Scenario** — the rack labels are handwritten, half of them are wrong, and nobody can scan them.

**Steps**

| # | Action |
|---|---|
| 1 | Open **📦 庫存** *(Inventory)*, stay on the **📦 料件** *(Parts)* tab |
| 2 | Find the part row and click the **🏷️** button in the **操作** *(Actions)* column (tooltip: 列印 QR 標籤 — *Print QR label*) |
| 3 | Your browser downloads `label-M6-BOLT-20.pdf` |
| 4 | Open it and print. **Do not scale to fit** — the page is already exactly 60 mm × 40 mm |
| 5 | Stick it on the bin, rack or container |

The same button appears in the scanner result strip after scanning a part, which is the fastest way
to reprint a damaged label: beep the old one, print a new one.

**What's on the label**

```
┌──────────────────────────────┐  60 mm
│ M6-BOLT-20            ██▀█▄  │
│ 六角螺栓 M6×20        ▄█▄▀█  │  40 mm
│ QTY: 1000             ▀█▄██  │
└──────────────────────────────┘
```

Part number in bold, part name below it, an optional quantity line, and a **QR code containing the
part number** — so scanning your own label puts the part straight back into the scanner bar.

In chat, `印 M6-BOLT-20 標籤` *("print the label for M6-BOLT-20")* returns the same PDF.

**Troubleshooting**

| Symptom | Meaning | What to do |
|---|---|---|
| The download fails and IT sees an import error for `qrcode` or `PIL` | Label rendering needs `qrcode[pil]` and `reportlab` (both are in `backend/requirements.txt`) | IT reinstalls backend dependencies |
| Label prints tiny in the corner of A4 | The printer scaled a 60 × 40 mm page onto A4 | In the print dialog set scale to 100 % / actual size, or select the label stock |
| HTTP 403 | Missing `print.label` | Ask an administrator |
| The QR scans as the part number, not the batch | Correct — labels encode the **part number** | For lot-level identification, print the lot number on your own stock label and register it per §14.3 |

---

## 15. Finance Close

> 🆕 **v3.60 "cash loop"** (bank accounts, payments, receipts) and **v3.61 "M2 financial close"**
> (statements, VAT report, 3-way match, promissory notes, fixed assets, COGS settlement).

This is the chapter that turns Ouvoca from an operations tool into something your accountant can
work with. It is also the chapter with the largest gap between *what the system can do* and *what
you can click*, so start with §15.1.

### 15.1 Where these features live — read this first

The **📒 會計** *(Accounting)* page still has exactly three tabs — **📊 傳票** *(Journals)*,
**💵 應收帳款** *(Receivables)*, **📚 科目表** *(Chart of accounts)* — and the **📈 報表中心**
*(Reports)* page has four sections: KPIs, AR aging (Excel), monthly inventory (Excel), and the
Taiwan 401 report. Everything else in this chapter is reached from **💬 AI Assistant**.

| Feature | Entry point | Section |
|---|---|---|
| Trial balance / income statement / balance sheet | 💬 Chat | §15.2 |
| Taiwan VAT 401/405 figures | 💬 Chat | §15.3 |
| Printable Taiwan 401 return (bi-monthly) | 🖥 **📈 報表中心** *(Reports)* | §15.3 |
| Supplier invoice + 3-way match | 💬 Chat | §15.4 |
| Promissory notes (checks) | 💬 Chat | §15.5 |
| Fixed assets + depreciation | 💬 Chat | §15.6 |
| Bank accounts, payments, receipts | 💬 Chat | §15.7 |
| Work-order cost, COGS settlement | 💬 Chat | §15.8 |
| Closing a period | 🔌 API only (`POST /api/accounting/close-month/{period}`) | §15.9 |

> 💡 **Not knowing the exact wording is fine.** These are ordinary sentences, not commands. "How did
> we do last month?" reaches the income statement; "which supplier invoices don't match?" reaches the
> 3-way match report. The examples below are the shortest phrasings that work reliably.

---

### 15.2 The three financial statements

**Scenario** — It is the 5th. The owner wants to know whether last month made money, and the
accountant wants to know whether the books balance before she does anything else.

**Steps** — open **💬 AI Assistant** and ask for one statement at a time:

| Statement | Say this | What it answers |
|---|---|---|
| **Trial balance** 試算表 | `試算表平不平衡` — *"does the trial balance balance?"* | Do total debits equal total credits? Which accounts hold what? |
| **Income statement** 損益表 | `給我 202607 的損益表` | Revenue − cost = gross profit; minus expenses = operating income; then non-operating items and tax = net income |
| **Balance sheet** 資產負債表 | `202607 資產負債表` | Assets vs liabilities + equity, at a point in time |

Periods are `YYYYMM` (e.g. `202607`). Omit the period and you get **all periods combined**.

**What you'll see** (income statement, abridged)

```
Period 202607
  Revenue                        4,820,000
  Cost of goods sold            -3,692,000
  ─────────────────────────────────────────
  Gross profit                   1,128,000
  Operating expenses              -742,000
  ─────────────────────────────────────────
  Operating income                 386,000
  Non-operating income/expense      -8,000
  Income tax                       -75,600
  ─────────────────────────────────────────
  Net income                       302,400
```

The trial balance and balance sheet both return a **`balanced` flag** — a plain true/false that is
worth more than any subtotal. If it says false, stop and find the unbalanced entry before you
publish anything.

**Troubleshooting**

| Symptom | Cause | What to do |
|---|---|---|
| Every figure is zero | Statements are built from **posted** journal entries only | On **📒 會計 → 📊 傳票** *(Journals)*, post the drafts (`draft` → `posted`) |
| Balance sheet says not balanced | An entry with unequal debits/credits was posted, or an account is mapped to the wrong statement line | Run the trial balance first; check the chart of accounts on the **📚 科目表** tab |
| Net income on the balance sheet differs from the income statement | The balance sheet uses **cumulative** balances; the income statement uses the period you asked for | Compare like with like — ask for the same period, or omit the period on both |
| HTTP 403 | Missing `accounting.statement.read` | Financial statements are deliberately restricted; ask an administrator |

---

### 15.3 Taiwan VAT: GUI invoices and the 401/405 report

**Background for readers outside Taiwan.** Taiwanese businesses cannot simply write their own
invoice. Sales are documented on a **GUI — Government Uniform Invoice** (統一發票), issued from
government-allocated number ranges; today most are electronic (電子發票) and transmitted to the tax
authority through a value-added service centre. The standard **VAT rate is 5 %**. B2B sales use the
*triplicate* form (三聯式), which lets your customer reclaim the tax as input tax; B2C sales use the
*duplicate* form (二聯式).

VAT is settled by **offsetting**: output tax you charged on sales, minus input tax you paid on
purchases, equals the tax you owe (or carry forward). Filing is **bi-monthly** — January–February is
period 1, …, November–December is period 6 — which is exactly the period selector on the Reports
page. In Ouvoca's terms:

| Term | Side | Where the numbers come from |
|---|---|---|
| **401** | Output — what you sold | E-invoices issued **through Ouvoca** with status `issued`; voided invoices are excluded |
| **405** | Input — what you bought | Accounts-payable supplier invoices dated inside the period |

**Steps — 💬 the numbers**

| # | Action |
|---|---|
| 1 | Open **💬 AI Assistant** |
| 2 | Type `202606 的 401 405` — *"the 401/405 figures for June 2026"* |

**What you'll see**

```
period 202606, tax_rate 0.05
  401 sales   — sales_general 4,820,000 · tax_general 241,000 · invoices 128
                (zero-rated / exempt / export are reported as 0)
  405 purchase— purchase_general 3,100,000 · tax_general 155,000 · invoices 74
  ────────────────────────────────────────────────────────────
  net_tax_payable   86,000
```

Legacy payables that only carry a tax-inclusive total are split back out at 5 %
(`sales = total ÷ 1.05`), which is stated in the report's own note.

**Steps — 🖥 the printable return**

| # | Action |
|---|---|
| 1 | Open **📈 報表中心** *(Reports)* and scroll to **🧾 台灣營業稅 401 報表** *(Taiwan VAT 401 report)* |
| 2 | Set **年度** *(year)* and **期別** *(period)* — the dropdown reads 第 1 期（1-2 月） … 第 6 期（11-12 月） |
| 3 | Optionally type **公司名稱** *(company name)* for the report header |
| 4 | Click **📄 開 2026 年第 3 期報表** *(open the report)* — it opens in a new browser tab |
| 5 | Press **Ctrl+P** → choose **Save as PDF** |

**Troubleshooting**

| Symptom | Cause | What to do |
|---|---|---|
| Output tax looks far too low | Only e-invoices **issued through Ouvoca** are counted | Invoices issued on paper or in another system must be added by your accountant outside Ouvoca |
| Input tax looks too low | 405 reads accounts payable; a purchase with no supplier invoice recorded contributes nothing | Record supplier invoices (§15.4) before filing |
| A cancelled invoice is still counted in output tax | See the warning below — cancelling does not change the stored invoice record | Deduct cancelled invoices manually and tell IT |
| HTTP 403 | Missing `accounting.tax_report` | Ask an administrator |

> ⚠️ **Two things your accountant must know before trusting these numbers.**
> 1. **Cancelling an e-invoice does not remove it from the 401 total.** The cancel action goes to the
>    invoicing provider; the invoice record stored in Ouvoca keeps its `issued` status, and the 401
>    figure counts every `issued` record. Keep your own list of cancellations for the period.
> 2. **The shipped e-invoice provider is a mock adapter** intended for demo and testing. Connecting
>    a real value-added service centre is an IT integration task. Until that is done, treat invoice
>    issuing and cancelling inside Ouvoca as bookkeeping, not as transmission to the tax authority.

> ⚠️ **This is a working paper, not a filing.** Ouvoca produces the figures and a printable form;
> submitting the return (and reconciling it to the tax authority's records) remains your accountant's
> job. Note also that the chat report covers **one month** (`YYYYMM`) while an actual filing period is
> **two months** — add the two months, or use the printable bi-monthly report. Always have your
> accountant check the first period you produce this way.

---

### 15.4 Supplier invoices and 3-way match

**What "3-way match" means** — before paying a supplier, three documents must agree:

```
   Purchase Order          Goods Receipt            Supplier Invoice
   what we agreed    ↔    what actually arrived  ↔  what they're billing us
```

If all three agree, pay. If they don't, someone must explain the difference *before* money moves.
This single control is the cheapest protection a small factory has against over-billing.

**Steps** — 💬 **Chat**

| # | Action |
|---|---|
| 1 | Record the invoice: `記錄長江精密的發票 INV-100，對應 PO-HQ-20260804-0001，M6-BOLT-20 1000 個 每個 5 元` — *"record supplier invoice INV-100 from Chang Jiang against PO-…: 1,000 × M6-BOLT-20 at 5"* |
| 2 | Read the ConfirmCard: supplier, invoice number, net amount, tax, line count, linked PO, and the note that a 3-way match runs automatically |
| 3 | **[ ✓ 確認執行 ]** *(Confirm)* |
| 4 | Later, review the queue: `哪些供應商發票數量對不上` — *"which supplier invoices have quantity variances?"* |

If you don't state a tax amount, **5 % of the net line total** is assumed.

**What you'll see** — every invoice carries one of these statuses:

| Status | Meaning | Typical cause |
|---|---|---|
| `matched` | Quantity and price agree with the PO and the receipt | Pay it |
| `qty_variance` | Invoiced quantity ≠ **received** quantity on the PO line | The goods have not been received in Ouvoca yet, or a short delivery was billed in full |
| `price_variance` | Invoiced unit price ≠ PO unit price | A price increase nobody put on the PO |
| `unmatched` | The invoice line has no PO line behind it | The invoice was recorded without a PO reference |

**Troubleshooting**

| Symptom / message | Cause | What to do |
|---|---|---|
| Everything comes back `qty_variance` right after a delivery | Matching compares against **received** quantity, and nobody has receipted the PO | Receive it first (§12.3), then re-run the match |
| `找不到供應商 長江精密 的 PO 'PO-…'` | The PO number is wrong, or that PO belongs to a different supplier | Check the number on the **🛒 採購** page |
| Status is `unmatched` and you did quote a PO | The PO reference was left out of the sentence | Re-record it with `對應 PO-…` — one invoice links to one PO |
| HTTP 403 | Missing `accounting.supplier_invoice.create` / `.read` / `.match` | Ask an administrator |

---

### 15.5 Promissory notes (post-dated checks)

**Background for readers outside Taiwan.** Taiwanese B2B trade still runs heavily on **post-dated
checks** (支票 / 票據). A customer settles a July invoice with a check that matures on 1 October;
you hold a drawer full of paper that becomes cash on different dates. Knowing which checks mature
next week *is* your cash-flow forecast.

**Steps** — 💬 **Chat**

| Task | Say this |
|---|---|
| Record a check you received | `記錄客戶富田精機開的 50,000 元支票，台灣銀行，票號 AB123456，10/1 到期` |
| Record a check you issued | `記錄應付票據：開給長江精密 300,000，9/30 到期，票號 CD778899` |
| See what is coming due | `這個月到期的票有哪些` — *"which notes mature this month?"* (sorted by due date) |

Statuses follow the life of the paper: `on_hand` → `endorsed` / `deposited` → `cleared`, plus
`returned` (bounced) and `void`.

**Troubleshooting**

| Symptom | Cause | What to do |
|---|---|---|
| The AR still shows as unpaid after recording a check | **Correct.** The note register does not settle receivables and does not post a journal entry | Record an actual receipt (§15.7) when the check clears |
| No way to mark a check `cleared` | There is no status-update endpoint yet | Track clearing outside Ouvoca for now, or ask IT to update the record |
| A note is missing from the list | The list is filtered by status | Ask without a filter: `所有票據` |

---

### 15.6 Fixed assets and depreciation

**Scenario** — You bought a CNC lathe for NT$1,000,000. Accounting-wise it is not an expense this
month; it is an asset that loses value over its useful life, and each month a slice of that value
becomes a cost.

**Steps** — 💬 **Chat**

| # | Action |
|---|---|
| 1 | Register it: `新增固定資產 CNC 車床，成本 1000000，耐用 60 個月` — optionally add `殘值 100000` *(salvage value)* and a category |
| 2 | ConfirmCard shows cost, salvage value, useful life and category → **[ ✓ 確認執行 ]** |
| 3 | Each month: `幫 CNC 車床提 202608 的折舊` — *"post August 2026 depreciation for the CNC lathe"* |
| 4 | Any time: `機器設備現在帳面價值多少` — *"what is the net book value of our machinery?"* |

**What happens under the hood**

| Item | Behaviour |
|---|---|
| Method | Straight line: **monthly depreciation = (cost − salvage) ÷ useful life in months** |
| Categories | `machinery` (default) / `building` / `vehicle` / `furniture` |
| Journal entry | Created **and posted automatically**: DR **6310** depreciation expense / CR the accumulated-depreciation account for the category (machinery **1631**, building **1621**, vehicle **1641**, furniture **1651**) |
| Duplicate protection | The same asset cannot be depreciated twice for the same period |
| End of life | The final month is trimmed so accumulated depreciation never exceeds cost − salvage; the asset then becomes `fully_depreciated` |

**Troubleshooting**

| Message | Cause | What to do |
|---|---|---|
| `折舊科目不存在（請先 seed_accounts）` | The 86-account Taiwanese chart of accounts has not been loaded | IT runs the account seed; depreciation cannot post without accounts 6310 and 16x1 |
| `資產 FA-… 已於 202608 提列折舊（傳票 JE-…），請勿重複` | Already posted for that period | Nothing to do — this is the duplicate guard working |
| `資產狀態 'fully_depreciated' 不可再提折舊` | The asset is written down to its salvage value | Stop depreciating it |
| `耐用月數必須大於 0` | Useful life missing or zero | Re-state the useful life in months |
| You have 30 assets and posting each one is tedious | There is no "depreciate everything" batch command yet | Post them one at a time as part of the month-end routine (§15.9) |

---

### 15.7 Cash: bank accounts, payments and receipts

> 🆕 **v3.60 "cash loop" — 💬 chat only.** These have no REST endpoints and no screen.

| Task | Say this |
|---|---|
| Add a bank account | `新增台銀帳戶 台灣銀行 大安分行 1234-5678，期初餘額 500000` |
| Check balances | `銀行還有多少錢？` |
| What do we owe? | `我們欠供應商多少錢？` / `下週要付多少` |
| Pay a supplier | `付長江精密 50,000 元，沖 INV-100，從台銀帳戶` |
| Record a customer payment | `收到富田精機 30,000 元，存台銀` |
| Review cash movements | `上個月付了哪些錢？` |

**What a payment does**: settles the linked payable (`unpaid` → `partial` → `paid`) and **reduces the
bank account balance**. A receipt does the mirror image for a receivable. Both are numbered
documents (`PY-…`, `RC-…`).

> ⚠️ **Payments and receipts do not post journal entries.** They move the subsidiary ledgers (AP/AR)
> and the bank balance, but the general ledger effect must still be booked — by your accountant on
> **📒 會計 → 📊 傳票** *(Journals)*, or as part of your month-end routine. Do not assume the trial
> balance reflects a payment just because the AP shows as paid.

**Troubleshooting**

| Message | Cause | What to do |
|---|---|---|
| `超付：此應付帳款 100,000 已付 80,000，再加 30,000 會超過` | Over-payment guard | Pay the remaining balance only, or leave the invoice reference out to record an unapplied payment |
| `付款供應商與應付帳款供應商不一致` | The invoice you're settling belongs to a different supplier | Check the invoice number |
| `此應付帳款狀態 'paid' 不可再付款` | Already fully settled | Nothing to pay |
| `找不到銀行帳戶「台銀」` | Name/code didn't match | Ask `銀行還有多少錢？` to see the exact account names |

---

### 15.8 Work-order cost and COGS settlement

**Work-order cost** — `WO-2026-0091 這張單是賺是賠` *("did this work order make money?")* returns
three elements plus a unit cost:

| Element | How it is calculated |
|---|---|
| Material | The product's **Recipe (BOM)** exploded × quantity × each part's standard unit cost |
| Labour | For each operation: (setup time + run time × completed quantity) × the work centre's hourly rate |
| Overhead | Labour × **30 %** by default |

The quantity basis is the **completed** quantity, falling back to the ordered quantity if nothing has
been completed yet — so the figure for a work order still in progress is an estimate, not a result.

**COGS settlement (month end)** — `結 2026-08 的銷貨成本` *("settle August 2026 cost of goods sold")*:

| Step | Behaviour |
|---|---|
| What it sums | Every delivery-note line shipped inside that month × the part's unit cost, grouped by part |
| What it posts | One journal entry: **DR 5100** cost of goods sold / **CR 1340** finished goods |
| Run it twice? | Refused — the second attempt names the journal that already exists for the period |
| Nothing to settle? | Returns `settled: false` with a plain reason (`no shipments in the period`, or every shipped part has a zero unit cost) |

> ℹ️ The ConfirmCard for this action carries an old warning that repeating it produces duplicate
> journals. The server refuses duplicates outright. Trust the refusal, not the card text.

**Troubleshooting**

| Message | Cause | What to do |
|---|---|---|
| `期間 2026-08 已結轉銷貨成本（傳票 JE-…），請勿重複` | Already settled | Nothing to do |
| `出貨品項無成本（unit_cost 皆為 0）` | Parts were created without a unit cost | Set unit costs on **📦 庫存** *(Inventory)*, then settle |
| `期間內沒有出貨紀錄` | No delivery notes in that month | Check that shipments were entered against sales orders |
| Work-order cost shows zero material | The product has no Recipe, or Recipe parts have no unit cost | Edit the Recipe on **🏭 生產** *(Production)* |

---

### 15.9 A month-end sequence that works

| # | Do this | Where |
|---|---|---|
| 1 | Make sure every shipment and every goods receipt for the month is entered | 🖥 Sales / Purchase |
| 2 | Record supplier invoices and clear the 3-way match variances | 💬 §15.4 |
| 3 | Post depreciation for each active fixed asset | 💬 §15.6 |
| 4 | Settle cost of goods sold | 💬 §15.8 |
| 5 | Post any remaining draft journals | 🖥 **📒 會計 → 📊 傳票** |
| 6 | Run the trial balance and confirm `balanced` = true | 💬 §15.2 |
| 7 | Produce the income statement and balance sheet | 💬 §15.2 |
| 8 | Produce the 401/405 figures and the printable return | 💬 / 🖥 §15.3 |
| 9 | Check the period's close status — `2026-08 結帳了嗎？` | 💬 (read-only) |
| 10 | Close the period | 🔌 `POST /api/accounting/close-month/{period}` — no button or chat tool yet |

Closing a period is recorded once; asking to close an already-closed period is refused
(`期間 2026-08 已結帳`).

---

## 16. Security and System Administration

> 🆕 **v3.62** (login lockout, session revocation, backups, upload content validation),
> **v3.64** (MFA, virus-scan hook) and **v3.60** (system settings).

Almost everything in this chapter lives on one page: **⚙️ 設定** *(Settings)*. That page now renders
**seven** sections, in this order:

| # | Section | Covered in |
|---|---|---|
| 1 | 🤖 AI assistant configuration | §3.5 A |
| 2 | 🔐 **雙重驗證（MFA）** *(Two-factor authentication)* | §16.1 |
| 3 | 💾 **備份管理** *(Backup management)* | §16.3 |
| 4 | ⚙️ **系統組態** *(System settings)* | §16.4 |
| 5 | 📦 示範資料 *(Demo data)* | §3.5 B |
| 6 | 📁 上傳業務文件 *(File upload)* | §3.5 C and §16.5 |
| 7 | ℹ️ 系統資訊 *(System info)* | §3.5 D |

---

### 16.1 Two-factor authentication (MFA)

**Scenario** — The owner's account can approve purchase orders and restore backups. A stolen or
guessed password should not be enough to use it.

Ouvoca uses **TOTP** — the six-digit rolling code produced by Google Authenticator, Microsoft
Authenticator, Authy, 1Password and similar apps. No SMS, no phone number, works offline.

**Steps — turning it on**

| # | Action |
|---|---|
| 1 | Install an authenticator app on your phone |
| 2 | Open **⚙️ 設定** *(Settings)* → **🔐 雙重驗證（MFA）** |
| 3 | Click **啟用設定** *(Set up)* |
| 4 | The page shows a **密鑰** *(secret key)* you can type into the app manually, plus an **開啟 otpauth 連結** *(open otpauth link)* for apps that accept a link. The account appears in your app as **Ouvoca ERP** |
| 5 | Type the current six-digit code into **6 位驗證碼** and click **啟用** *(Enable)* |
| 6 | You'll see `MFA 已啟用` *(MFA enabled)* and a toggle labelled **MFA 已啟用（關閉需輸入驗證碼）** *(enabled — disabling requires a code)* |

**Steps — logging in afterwards**

| # | Action |
|---|---|
| 1 | Enter username and password as usual, click sign in |
| 2 | A second screen appears: `🔐 <your username> 已啟用雙重驗證 — 請輸入 Authenticator App 的 6 位驗證碼` |
| 3 | Type the six digits into the `000000` box |
| 4 | Click **驗證並登入** *(Verify and sign in)* |

The link **← 返回重新輸入帳號密碼** *(back to username and password)* takes you back if you picked the
wrong account.

**Steps — turning it off**: same section, type a current code into **驗證碼（停用時輸入）** and switch
the toggle off. You'll see `MFA 已停用`.

**Troubleshooting**

| Message / symptom | Cause | What to do |
|---|---|---|
| `驗證碼錯誤` *(wrong code)* | Wrong code, or the phone's clock has drifted | Codes are accepted within **±30 seconds** of the server's clock — enable automatic time sync on the phone and try the next code |
| `MFA 挑戰已失效，請重新登入` | The second step was left open too long — the challenge lasts **5 minutes** | Sign in again from the start |
| `嘗試次數過多，帳號已暫時鎖定，請 15 分鐘後再試` while entering codes | Failed **MFA** attempts count toward the lockout too (§16.2) | Wait 15 minutes |
| Phone lost or wiped after enabling MFA | Disabling requires a valid code, so you cannot self-recover | An administrator must clear the MFA flag on your account in the database. **Decide who that person is before you roll MFA out** |
| Re-enabling after disabling shows a different secret | Disabling deletes the old secret by design | Delete the stale entry in your authenticator app and scan the new one |

---

### 16.2 Password, lockout and session revocation

| Topic | Behaviour |
|---|---|
| **Changing your password** | 💬 Chat: type `改密碼` *(change password)* and follow the ConfirmCard. There is no password screen. The new password must be **at least 8 characters and contain a letter and a digit**; common choices such as `admin123` / `password` / `12345678` are rejected |
| **Login lockout** | After **5 consecutive failures** (configurable — see `security.login_lockout_threshold` in §16.4) the account is locked for **15 minutes**. A successful login resets the counter |
| **While locked** | Even the correct password is refused, and the message deliberately does not reveal whether the account exists: `嘗試次數過多，帳號已暫時鎖定，請 15 分鐘後再試` (HTTP 429) |
| **Session revocation** | Changing your password immediately invalidates every token issued before it. Other browsers and devices get `Token 已失效，請重新登入` *("session expired, please sign in again")* and must sign in again — this is how you lock out someone who has your old password |
| **A password change also clears the lock** | The failure counter and lock expiry are reset when the password changes |
| **The default account** | `admin` / `admin123` is printed on the login screen for first installs and is flagged with a warning toast after you sign in. Change it on day one |

---

### 16.3 Backup and restore

**Scenario** — Somebody deletes a year of purchase orders on a Friday afternoon. What happens next
depends entirely on whether backups were running.

**Steps — check that automatic backups are on**

| # | Action |
|---|---|
| 1 | Open **⚙️ 設定** *(Settings)* → **💾 備份管理** *(Backup management)* |
| 2 | The subtitle states the schedule: 每日 03:00 自動備份（保留 30 天） — *daily at 03:00, kept for 30 days* |
| 3 | Confirm the table is not empty. An empty table on a system that has been running for days means backups are **not** working — escalate to IT |

**Steps — take a backup before something risky** (a data import, a version upgrade)

| # | Action |
|---|---|
| 1 | Click **立即備份** *(Back up now)* |
| 2 | Wait for `✅ 備份完成：backup-20260804-141530-ouvoca.db` |

**Steps — restore** ⚠️ *destructive*

| # | Action |
|---|---|
| 1 | Pick the backup row you want and click the red **還原** *(Restore)* button |
| 2 | Read the confirmation carefully: `⚠️ 從 … 還原會覆蓋目前資料庫且不可逆！確定？` — *"restoring will overwrite the current database and cannot be undone"* |
| 3 | Confirm. You'll see `✅ 已還原 …（救援檔 pre-restore-…，請重新整理）` |
| 4 | **Have IT restart the backend service**, then check your data before letting anyone key in new work |

**What protects you during a restore**

- The file is verified to be a real database before anything is overwritten — a corrupt or foreign
  file is refused.
- The **current** database is copied to a rescue file (`pre-restore-…`) first, so a restore of the
  wrong backup is itself recoverable.
- Stale write-ahead-log files are cleared afterwards, which prevents the classic "restored, then
  half the old data came back" corruption.

**Troubleshooting**

| Message | Cause | What to do |
|---|---|---|
| `PostgreSQL 環境不支援檔案快照；請使用資料庫原生備份（pg_dump）` | Backups here are file snapshots and only work on the SQLite deployment | On PostgreSQL, IT must schedule `pg_dump` — the Settings page cannot manage those backups |
| `備份檔不是有效的 SQLite 資料庫，拒絕還原` | The file is corrupt or was replaced | Use an earlier backup |
| `備份不存在：…` | Deleted or renamed on disk | Refresh the list |
| Data still looks wrong after a restore | The service was not restarted | Restart the backend and reload the page |
| HTTP 403 | Restoring requires `system.backup.restore`, which is separate from `system.backup.create` | Deliberate — restore authority should sit with one or two people |

You can also drive backups from chat (`列出備份` / `立即備份` / `還原備份 …`); restore raises a
ConfirmCard first.

---

### 16.4 System settings

**⚙️ 設定** *(Settings)* → **⚙️ 系統組態** *(System settings)*. The subtitle states the resolution
order: **環境變數 > 資料庫 > 預設值** — *environment variable beats database beats built-in default*.

**What the page lets you change**

| Setting key | Plain English | Default |
|---|---|---|
| `finance.credit_limit_check` (toggle) | Enforce the customer's credit limit when a sales order is created | on |
| `backup.enabled` (toggle) | Run the automatic backup | on |
| `tax.vat_rate` | Taiwan VAT rate | `0.05` |
| `backup.retention_days` | How many days of backups to keep | `30` |
| `security.login_lockout_threshold` | How many wrong passwords before the account locks | `5` |
| `backup.schedule` | Time of day the automatic backup runs | `03:00` |

**How to change one**: for toggles, click the switch — it saves immediately. For the four value
fields, type the new value and then **click somewhere else on the page**; the field saves on losing
focus. You'll see `✅ <key> 已更新`.

**The other eight settings** exist with sensible defaults and can be read and written through the API
(`GET` / `PUT /api/system/settings/{key}`), but are not on the page yet: company name, tax ID
(統一編號), address and phone (used on printed documents), default currency `TWD`, timezone
`Asia/Taipei`, locale `zh-TW`, and the per-user daily AI call limit (`200`).

**Troubleshooting**

| Symptom | Cause | What to do |
|---|---|---|
| `⚠️ 更新失敗（可能權限不足）` | Missing `system.config.update` | Ask an administrator |
| You changed a value and nothing happened | An environment variable of the form `OUVOCA_SETTING_<KEY>` overrides both the page and the database (dots become underscores, e.g. `OUVOCA_SETTING_TAX_VAT_RATE`) | The toggle rows show their **來源** *(source)* — if it isn't the database, IT has to change the environment variable |
| A number was saved as text | Only plain numbers such as `0.05` or `30` are converted; anything else is stored verbatim | Re-enter digits only — no `%`, no thousands separators |
| A row is missing from the page | The page renders a fixed list of six keys | Use the API for the rest |

---

### 16.5 What happens to the files you upload

Uploads on **⚙️ 設定 → 📁 上傳業務文件** *(Upload business documents)* are checked in four ways
before anything is stored:

| Check | Rule | Message if it fails |
|---|---|---|
| Extension | Only `.pdf .xlsx .xls .csv .jpg .jpeg .png .docx .txt` | `檔案類型不支援：.zip。允許：…` |
| Size | 25 MB per file; empty files rejected | `檔案太大：30 MB（上限 25 MB）` / `檔案為空` |
| **Content signature** *(v3.62)* | The file's real content must match its extension — renaming `virus.exe` to `quote.pdf` does not get past this | `檔案內容與副檔名 .pdf 不符（內容簽名檢查失敗），已拒絕上傳` |
| Script markers in text files | `.csv` / `.txt` may not contain HTML or script markup | `檔案內容包含不允許的腳本標記，已拒絕上傳` |
| Virus scan *(v3.64, optional)* | Active only when IT has configured a scanning service | `檔案被偵測為病毒，已拒絕上傳：<name>` |

> 💡 If a supplier's file is rejected by the signature check, the usual cause is innocent: someone
> renamed a `.xls` to `.xlsx`, or exported a "PDF" that is really an HTML page. Ask them to re-export
> it. Do **not** work around the check by renaming the file again.

---

## Appendix A. Quick Reference for v3.60-v3.69

### A.1 Say this to the AI

Copy a line, replace the parts in `<>`, send it. Anything that writes data raises a ConfirmCard
first — nothing happens until you click **[ ✓ 確認執行 ]**.

| I want to… | Type this | § |
|---|---|---|
| Raise a purchase requisition | `請購 <qty> 個 <part_no>，<date> 要` | 12.2 |
| Convert an approved requisition to a PO | `把 <PR no> 轉成給 <supplier> 的採購單` | 12.2 |
| Receive part of a delivery | `收 <PO no>，這次只到 <qty> 個` | 12.3 |
| Issue material to a work order | `<WO no> 領 <qty> 個 <part_no>` | 12.4 |
| Record a customer return | `客戶 <name> 退回 <qty> 個 <part_no>，<reason>` | 12.5 |
| Request quotes for several parts | `針對 <part_no> <qty> 個發詢價` | 13.3 |
| Record a supplier's quote | `<supplier> 報 <part_no> <qty> 個 每個 <price> 元` | 13.3 |
| See who is cheapest | `<RFQ no> 誰最便宜` | 13.3 |
| Award and create the PO | `<RFQ no> 給 <supplier> 得標` | 13.3 |
| Register a lot | `料件 <part_no> 建批號 <lot_no>，<qty> 個，<date> 到期` | 14.3 |
| Register serial numbers | `登記 <SN-a> 到 <SN-b> 給 <part_no>` | 14.3 |
| Trace a lot | `追溯 <lot_no>` | 14.2 |
| Print a part label | `印 <part_no> 標籤` | 14.4 |
| Income statement | `給我 <YYYYMM> 的損益表` | 15.2 |
| Balance sheet | `<YYYYMM> 資產負債表` | 15.2 |
| Check the books balance | `試算表平不平衡` | 15.2 |
| VAT figures | `<YYYYMM> 的 401 405` | 15.3 |
| Record a supplier invoice | `記錄 <supplier> 的發票 <no>，對應 <PO no>，<part_no> <qty> 個 每個 <price> 元` | 15.4 |
| Find invoice mismatches | `哪些供應商發票數量對不上` | 15.4 |
| Record a check received | `記錄客戶 <name> 開的 <amount> 元支票，<bank>，票號 <no>，<date> 到期` | 15.5 |
| Checks maturing soon | `這個月到期的票有哪些` | 15.5 |
| Register a fixed asset | `新增固定資產 <name>，成本 <amount>，耐用 <n> 個月` | 15.6 |
| Post depreciation | `幫 <asset> 提 <YYYYMM> 的折舊` | 15.6 |
| Net book value | `機器設備現在帳面價值多少` | 15.6 |
| Bank balances | `銀行還有多少錢？` | 15.7 |
| Pay a supplier | `付 <supplier> <amount> 元，沖 <invoice no>，從 <bank> 帳戶` | 15.7 |
| Record a customer payment | `收到 <customer> <amount> 元，存 <bank>` | 15.7 |
| Work-order profitability | `<WO no> 這張單是賺是賠` | 15.8 |
| Settle cost of goods sold | `結 <YYYY-MM> 的銷貨成本` | 15.8 |
| Is the period closed? | `<YYYY-MM> 結帳了嗎？` | 15.9 |
| Change your password | `改密碼` | 16.2 |
| List / take / restore backups | `列出備份` · `立即備份` · `還原備份 <name>` | 16.3 |

### A.2 Click this on screen

| Feature | Path |
|---|---|
| Receive a whole PO | **🛒 採購** → **📋 採購單** tab → **🚚 進貨** on the row |
| Approve a PO | **🛒 採購** → **📋 採購單** tab → **✓ 核准** on the row |
| RFQ: create, send, record quotes, compare, award | **🛒 採購** → **📨 RFQ 詢價** tab |
| Scan a part / lot / serial | **📦 庫存** → the 🔫 bar at the top |
| Trace a lot or serial | scan it, then **🔍 追溯** |
| Print a QR part label | **📦 庫存** → **🏷️** on the part row |
| Stock movement history | **📦 庫存** → **📜 異動歷史** tab |
| Taiwan 401 printable return | **📈 報表中心** → **🧾 台灣營業稅 401 報表** |
| Turn on two-factor authentication | **⚙️ 設定** → **🔐 雙重驗證（MFA）** |
| Back up / restore the database | **⚙️ 設定** → **💾 備份管理** |
| Change VAT rate, lockout threshold, backup schedule | **⚙️ 設定** → **⚙️ 系統組態** |

### A.3 Features with no screen yet

Do not send staff looking for these buttons — they do not exist in this release.

| Feature | Available via | § |
|---|---|---|
| Approving a purchase requisition | REST API only | 12.2 |
| Listing purchase requisitions | Nothing — record the PR number when you create it | 12.2 |
| Approving and processing a customer return | REST API only | 12.5 |
| Requisition / GRN / material issue / return documents | Chat (create) + API (list) | 12 |
| All three financial statements | Chat | 15.2 |
| VAT 401/405 figures per month | Chat (the printable bi-monthly return is on the Reports page) | 15.3 |
| Supplier invoices and 3-way match | Chat | 15.4 |
| Promissory notes | Chat (no status updates yet) | 15.5 |
| Fixed assets and depreciation | Chat | 15.6 |
| Bank accounts, payments, receipts | Chat only — no REST API either | 15.7 |
| Work-order cost, COGS settlement | Chat | 15.8 |
| Closing an accounting period | REST API only | 15.9 |

### A.4 Permission codes behind the 403s

When a button or a chat request comes back with "permission denied", this is the code an
administrator has to grant on the **🛡️ 權限管理** *(Permissions)* page.

| Area | Codes |
|---|---|
| Requisitions | `purchase.pr.create` · `purchase.pr.approve` · `purchase.pr.convert` |
| Goods receipt | `purchase.grn.create` · `purchase.grn.read` |
| RFQ | `purchase.rfq.create` · `purchase.rfq.read` · `purchase.rfq.award` |
| Material issue | `production.material_issue.create` |
| Customer returns | `sales.return.create` · `sales.return.approve` · `sales.return.process` |
| Batches & serials | `inventory.batch.create` · `inventory.batch.read` · `inventory.serial.create` · `inventory.serial.read` |
| Scanning & labels | `inventory.inventory.read` · `print.label` |
| Statements & tax | `accounting.statement.read` · `accounting.tax_report` |
| Supplier invoices | `accounting.supplier_invoice.create` · `.read` · `.match` |
| Notes & assets | `accounting.note.read` · `accounting.note.create` · `accounting.fixed_asset.read` · `.create` · `.depreciate` |
| Cash | `accounting.bank.read` · `accounting.bank.write` · `accounting.payment.create` · `accounting.receipt.create` · `accounting.payment.read` · `accounting.ap.read` |
| Costing & close | `production.work_order.cost` · `accounting.cost_settle.execute` · `accounting.month_close.read` · `accounting.month_close.execute` |
| Backups & config | `system.backup.read` · `system.backup.create` · `system.backup.restore` · `system.config.read` · `system.config.update` |

---

**Manual version**: v3.22 (2026-05-18) — includes Settings / CRM / AskAI / QuickCreate / Accounting / E-Invoice / Reports / Multi-country tax ID / Cmd+K / Print PDF / Approval workflow / Process chain / Document notes
**Supplement**: §12–§16 + Appendix A cover v3.60–v3.69 — PR / GRN / MI / RT documents, RFQ sourcing, batch & serial traceability, barcode scanning & QR labels, financial statements, Taiwan VAT 401/405, 3-way match, promissory notes, fixed assets & depreciation, COGS settlement, MFA, backup & restore, system settings
**Chinese version**: [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md)
**Companion docs**: [`CONVERSATIONAL_ERP_DESIGN_EN.md`](./CONVERSATIONAL_ERP_DESIGN_EN.md) (architecture) / `LICENSE-COMMERCIAL.md` (licensing)

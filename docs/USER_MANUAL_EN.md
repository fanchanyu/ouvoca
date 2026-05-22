# LLM-ERP User Manual (English)

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

---

## A Note for First-Time Readers

If you're not a "computer person" and the word "ERP" makes your head spin — **don't worry, we redesigned it for you**.

This LLM-ERP does not require you to memorize where menus live, what fields are called, or which button comes first.
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

---

## 1. System Overview

### 1.1 What is LLM-ERP?

LLM-ERP is a **Conversational ERP** designed for **small manufacturers with 50–100 employees**.

"ERP" in plain English: **software that manages inventory, orders, purchasing, production, and reports** for a company.
Traditional ERPs (SAP, Oracle) cost millions to license and require 1–3 months of staff training.

**LLM-ERP flips that**: you don't learn the interface; you **type what you want to do** and the AI does it.

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

LLM-ERP ships under three licensing tracks — **picking the right one can save millions**.

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

**Manual version**: v3.22 (2026-05-18) — includes Settings / CRM / AskAI / QuickCreate / Accounting / E-Invoice / Reports / Multi-country tax ID / Cmd+K / Print PDF / Approval workflow / Process chain / Document notes
**Chinese version**: [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md)
**Companion docs**: [`CONVERSATIONAL_ERP_DESIGN_EN.md`](./CONVERSATIONAL_ERP_DESIGN_EN.md) (architecture) / `LICENSE-COMMERCIAL.md` (licensing)

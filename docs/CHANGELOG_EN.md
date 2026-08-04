# 📜 Ouvoca Release Notes (Plain-English Edition)

[繁體中文](./CHANGELOG_ZH.md) | **English**

> ⬅️ Back to the [README](../README.en.md)
>
> 🇺🇸 **No engineering jargon — every entry answers one question: what will you actually notice?**
> 🇹🇼 **不講工程術語，只說「你能用到什麼」。**

## How to read the version numbers

| Where | Current value | What it means |
|---|---|---|
| Latest git tag | `v3.70` | The public release |
| `backend/app/config.py` → `APP_VERSION` | `3.70.0` | The value shown on the Swagger `/docs` page |
| `frontend-desktop/package.json` | `3.70.0` | Front-end package version |
| Alembic migration head | `016_fk_indexes` (001 → 016) | Database schema version |

> v3.70 is the "version control and release readiness" release: the application version was aligned to `3.70.0` so that it matches the git tag.

---

## 🇹🇼 Background: Taiwan terms used below

<details>
<summary>If you are not familiar with Taiwanese tax and invoicing, open this first</summary>

Ouvoca is built for small and mid-sized manufacturers in **Taiwan**, so several release notes reference local tax concepts that have no direct equivalent elsewhere.

| Term | What it is |
|---|---|
| **統一發票 / GUI (Government Uniform Invoice)** | Taiwan does not let businesses print their own free-form invoices. Every sale must be documented on a government-issued uniform invoice with a number drawn from a government-allocated range. Retaining these records is a legal obligation (5 years), and the invoice date must follow **Taiwan local time (UTC+8)** — not the server's timezone. This is why "e-invoice records must survive a restart" and "invoice timezone" appear as compliance fixes rather than nice-to-haves. |
| **統編 / Unified Business Number (tax ID)** | An 8-digit company registration number. Whether the buyer has one determines what kind of invoice is issued — which is why several features branch on "customer has a tax ID". |
| **三聯式 (triplicate) vs. 二聯式 (duplicate) invoice** | A **triplicate** GUI is issued to a business buyer that has a tax ID; the buyer uses it to reclaim the 5% VAT as input tax. A **duplicate** GUI is issued to a consumer with no tax ID, and no input tax can be reclaimed. In the release notes below, "B2B (has tax ID)" corresponds to the triplicate case and "B2C (no tax ID)" to the duplicate case. |
| **401 / 405 VAT return (營業稅申報)** | Taiwanese businesses file a **bi-monthly** VAT return. Form **401** is the standard return covering output tax (sales) and input tax (purchases); **405** is the companion schedule used to report purchase-side detail. Taiwan's VAT rate for general business is **5%**. "401/405 support" means the system can aggregate the numbers the accountant needs for that filing. |
| **Tenant / multi-plant** | Ouvoca is multi-tenant: one deployment can serve several legal entities or plants, and every row of data is scoped to a tenant. Several fixes below are about making sure data from plant A can never surface in plant B. |

</details>

---

## 🆕 v3.70 (2026-08-04) — Version control and release readiness

| What changed | What you'll notice |
|---|---|
| 🗂 **Fresh installs get the performance indexes too** | The foreign-key index logic was extracted into `backend/app/services/db_indexes.py` and is now shared by `init_db()` and migration v016. A clean install measurably creates **300 indexes** where it previously created only 133 — a newly installed machine is no longer slower than an upgraded one |
| 🏷 **One version number, everywhere** | `APP_VERSION` and `package.json` are both `3.70.0`; the README test badge now reads 880 tests |
| 🚦 **A fourth CI gate: governance** | `scripts/run_gates.sh` gained **Gate 4 (governance)**: a from-scratch `alembic upgrade`, fresh-install index verification, and a `seed_permissions` audit that must report `MISSING=0`. This catches the "feature returns 403 after an upgrade" class of bug before release |
| 🛡 **Security policy and code of conduct added** | New `SECURITY.md` (supported versions, vulnerability reporting, built-in security controls, deployment checklist) and `CODE_OF_CONDUCT.md` |
| 🌐 **Bilingual UI strings verified complete** | The zh and en locale files hold **267 keys each, 0 missing** — the earlier "37 keys missing" report was a false positive from comparing character counts. The 399 hard-coded Chinese strings still sitting in JSX are recorded as a known limitation in the roadmap |
| 🔧 **A blank setting no longer stops the server** | `FACTORY_NODES=` (left empty) used to crash configuration parsing on startup; empty values and comma-separated lists are both accepted now |

## 🆕 v3.69 (2026-08-04) — Performance: still fast at tens of thousands of documents

| What changed | What you'll notice |
|---|---|
| 🐛 **The purchase order list stopped returning 400** | `GET /api/purchase/orders` was missing a `selectinload`; the list page works again |
| ⚡ **All 181 foreign-key columns are indexed** | 159 of them (87%) had **no index at all**. Migration `v016_fk_indexes` walks the schema and creates 142 composite `(tenant_id, foreign_key)` indexes plus `created_at` sort indexes. Measured against 20,000 purchase order lines: **6.9 ms → 0.007 ms, roughly 1,030×** |
| 🪶 **Lower fixed cost on every request** | The SecurityHeaders and RequestID middleware were rewritten as pure ASGI; user permission loading collapsed into a single JOIN; the audit log now records **write operations only**, so reads no longer generate log rows |
| 🔁 **Three N+1 query patterns eliminated** | Work-order labour costing batch-loads work centres, requisition-to-PO conversion batch-loads items, and RFQ comparison batch-loads quote lines |
| 🐘 **Larger PostgreSQL connection pool** | `DB_POOL_SIZE` raised from 20 to 30, so concurrent users stop queueing behind each other |

## 🆕 v3.68 (2026-08-04) — Turnkey: the six out-of-the-box bundles completed

| What changed | What you'll notice |
|---|---|
| 🏛 **House rules grew from 3 to 23** | `DEFAULT_RULES` now ships **23 rules**: work-order release requires a routing; purchases need approval above a threshold and at least one line; sales checks the credit limit and the B2B tax ID; shipments require confirmation; goods receipts require approval and cannot exceed the ordered quantity; journals enforce the period lock and debit/credit balance; returns, requisitions and RFQs have status gates; large payments and receipts need approval; material issue and completion require a released work order; quotations, work orders and payments have mandatory fields; low stock levels and lot expiry raise alerts. Five new condition types were added: `credit_check`, `has_customer_tax_id`, `period_open`, `field_in`, `not_empty` |
| 🖨 **Two more printable forms** | On top of the existing purchase order, sales order, delivery note, e-invoice, quotation and item label, this release adds an **inspection report PDF** and a **stock count sheet PDF** |
| 📚 **All six turnkey bundles are complete** | An 86-account chart of accounts, 10 roles across 231 permission codes, 23 house rules, the full set of form PDFs, 5 industry seed packs (metal / plastics / PCB / food / textile), and 14 system settings |

## 🆕 v3.67 (2026-08-04) — Three leftovers from the health check

| What changed | What you'll notice |
|---|---|
| 🏷 **QR labels are no longer clipped on the right** | About 1.7 mm was being cut off the right edge; after re-layout, both the QR code and the border sit fully inside 60 × 40 mm |
| 🧾 **Null unit prices in 3-way match are fully guarded** | `(unit_price or 0)` is applied in both the arithmetic and the formatting path, so an empty `unit_price` no longer raises |
| ✅ **Clean-environment verification is green** | `requirements.txt` now declares `qrcode[pil]` so Pillow is installed alongside it; a clean machine passes the full test suite straight after `pip install` |

## 🆕 v3.66 (2026-08-04) — 24 fixes from the professional health check (four of them P0)

| What changed | What you'll notice |
|---|---|
| 🔴 **MFA can no longer be bypassed** | The intermediate token issued during two-step login (`mfa_pending`) could be used as a full access token; it is now rejected with 401 |
| 🔴 **Accounts with MFA enabled can actually log in** | The login page gained the missing second step: enter the 6-digit code |
| 🔴 **RFQ listing and award stopped returning 500** | `selectinload` added in both places, with HTTP-level tests to keep it that way |
| 🔴 **The second partial receipt no longer fails** | The state machine now permits `sent` and `partial_received → partial_received` transitions |
| 🔑 **No more 403 on new features after an upgrade** | `update.bat` / `update.sh` run `seed_permissions` at the end of an upgrade, so permission codes introduced by the new version are inserted automatically |
| 💾 **Backup deletion works on Windows** | File handles are closed explicitly after validation, and backup filenames are allowlisted to block path traversal |
| 🐘 **PostgreSQL compatibility** | Report queries moved from SQLite's `strftime` to the dialect-neutral `extract(year/month)` |
| 🌐 **CORS moved to the outermost layer** | Browser preflight (`OPTIONS`) requests are no longer rejected with 401 by the auth layer |
| 🚫 **Over-receipt and over-payment are blocked** | Cumulative received quantity must stay at or below the ordered quantity; cumulative payments at or below the payable amount |
| 🔁 **Depreciation and COGS can't be posted twice** | If an entry already exists for the same period and source document, the repeat is rejected |
| 🐢 **Rate limits on login and AI chat** | Failed MFA verifications now also count toward account lockout |
| 📊 **Balance sheet semantics corrected** | It now uses cumulative balances (`entry_date` before the start of the following month) instead of only the current period |
| 🏢 **Codes are unique per tenant, not globally** | Bank account and fixed asset codes used to be globally unique, which blocked multi-plant deployments (migration v015) |

## 🆕 v3.65 (2026-08-04) — Front end catches up + Galaxy UI components

| What changed | What you'll notice |
|---|---|
| 📷 **A barcode scanner bar on the inventory page** | Scan an item, lot or serial number and go straight to a result card with a traceability button; every item row also gained a "Print QR label" action |
| ⚙️ **Three new sections in Settings** | MFA (TOTP) enrolment; backup management (back up now / list / restore / delete); system settings (credit limit checking, backup toggle, tax rate, retention days, lockout threshold) |
| 🛒 **An RFQ tab on the purchasing page** | Create an RFQ, send it out, enter each supplier's quote, compare, then award and convert to a purchase order — all from the UI |
| ✨ **Galaxy UI components** | The toggle and loading animations from uiverse-io/galaxy (MIT) are wrapped as `GalaxyToggle` and `GalaxyLoader` |

> ⚠️ **Being upfront about scope**: this release wired the front end to v3.60 system settings, v3.62 backups, and v3.64 barcode / traceability / RFQ / MFA.
> **v3.61 financial close M2** (the three financial statements, 401/405 VAT, 3-way match, notes receivable and payable, fixed assets, COGS transfer),
> **v3.63 M3 documents** (requisition PR, goods receipt GRN, material issue MI, return RMA) and **v3.60 cash cycle** (payments, receipts, bank accounts)
> are still reachable **only through the API and the AI chat** — there is no screen for them yet.

## 🆕 v3.64 (2026-08-04) — Shop floor: traceability, RFQ, labels, scanning, MFA

| What changed | What you'll notice |
|---|---|
| 🔍 **Forward and backward lot traceability** | See which purchase order a lot arrived on and which work orders or shipments consumed it, end to end (`GET /api/warehouse/batches/{lot_no}/trace`) |
| 🔢 **Serial number traceability** | The status of a single serial number and every document that touched it (`GET /api/warehouse/serials/{serial_no}/trace`) |
| 💱 **RFQ: request, compare, award** | Create an RFQ, send it to several suppliers, record their quotes, compare (the lowest price per item is highlighted), then award and convert straight into a purchase order |
| 🏷 **QR labels for items** | A 60 × 40 mm QR label PDF you can stick on the rack and scan with a phone or a barcode gun |
| 📷 **Barcode gun scanning** | `POST /api/warehouse/scan` resolves an item, lot or serial number in one call and returns the stock position plus the actions available |
| 🔐 **Multi-factor authentication (TOTP)** | Pair an authenticator app; login becomes two steps — password, then a 6-digit code |
| 🦠 **Antivirus scanning hook** | Set `AV_SCAN_URL` and uploaded files are sent for scanning first (a ClamAV-style REST endpoint). Leave it unset and the hook stays off |

## 🆕 v3.63 (2026-08-04) — M3 documents: requisition, goods receipt, material issue, return

| What changed | What you'll notice |
|---|---|
| 📝 **Purchase requisition (PR)** | The shop floor raises a need, a supervisor approves it, and one click converts it into a real purchase order (quantities carried over, unit price defaulted from cost) |
| 📥 **Goods receipt note (GRN)** | Book a formal receipt against a purchase order: the received quantity, the stock movement and the status transition are updated atomically |
| 📤 **Material issue (MI)** | A work order draws raw material from the warehouse and records a cost snapshot at the same time, which makes work-order costing more accurate |
| ↩️ **Return / RMA** | Customer return, document raised, supervisor approves, stock booked back in |

## 🆕 v3.62 (2026-08-04) — Security hardening and governance

| What changed | What you'll notice |
|---|---|
| 🔒 **Brute-force login lockout** | Five failed attempts locks the account for 15 minutes by default (configurable in system settings); during the lockout even the correct password is refused |
| 🚪 **Changing a password revokes every old session** | Sessions on other devices are invalidated the moment the password changes |
| 📎 **Uploaded file contents are validated** | Magic bytes are checked to confirm the real format (PDF / PNG / JPG / XLSX / DOCX / XLS), so a `.txt` renamed to `.pdf` is rejected |
| 🛡 **Prompt-injection defence** | Results from external database queries are wrapped in explicit data boundaries, and the system prompt states plainly that external content is data, not instructions |
| 🧾 **No more duplicate invoice numbers under concurrency** | Invoice numbering moved to a centralised atomic counter; the old `COUNT + 1` approach collided when two people issued invoices at the same moment |
| 💳 **Credit limits are enforced** | Creating a sales order checks that `credit limit − outstanding receivables ≥ order amount` and blocks the order if it doesn't hold (can be switched off in settings) |
| 💾 **Automated backup and restore** | Back up now, list, restore and delete, plus a retention policy and a schedule (03:00 daily by default). A rescue copy is taken before any restore |

## 🆕 v3.61 (2026-08-04) — Financial close M2: the books can finally be closed

| What changed | What you'll notice |
|---|---|
| 📊 **The three financial statements** | Trial balance, income statement and balance sheet, grouped by each account's `fs_line`, with automatic checks that debits equal credits and that assets equal liabilities plus equity |
| 🧾 **401 / 405 VAT return** | Form 401 output tax (from e-invoices) plus form 405 input tax (from accounts payable, with legacy data split at 5% automatically), and the resulting tax payable — the figures your accountant needs for the bi-monthly filing |
| 🔗 **3-way match** | Purchase order ↔ goods receipt ↔ supplier invoice reconciliation, surfacing quantity variances, price variances and lines that cannot be matched at all |
| 📜 **Notes receivable and payable** | Note tracking with collection status and maturity reminders |
| 🏭 **Fixed assets and depreciation** | Straight-line depreciation; posting a period generates the journal entry automatically (DR depreciation expense / CR accumulated depreciation) |
| 💰 **Three-element work order costing** | Material (BOM × unit cost) plus labour (operation hours × hourly rate) plus overhead, so you can tell whether an individual work order made or lost money |
| 📕 **COGS transfer** | At month end, shipments in the period × cost generate the journal entry automatically (DR 5100 Cost of Goods Sold / CR 1340 Finished Goods) |

> ⚠️ Everything above is reachable **only through the API and the AI chat** in this release; there are no screens for it yet.

## 🆕 v3.60 (2026-08-04) — All P0 security issues fixed + external DB encryption + centralised numbering

| What changed | What you'll notice |
|---|---|
| 🔴 **The AI chat no longer bypasses permissions** | Calling a tool through chat used to sidestep RBAC entirely; `execute_tool()` now performs its own permission check, and the permission cache TTL was cut from 300 s to 30 s |
| 🔴 **Tenant isolation added to 16 detail tables** | BOM, journal lines, order lines, contract pricing, approval steps, quotation lines, stock count lines, inspection results, operations, dispatches, process steps, purchase lines, MPS, MRP, replenishment rules and replenishment suggestions (migration v007, including a backfill of existing rows) |
| 🔐 **External database credentials are encrypted at rest** | Credentials are stored AES-256-GCM encrypted with tamper detection; previously they were plain text and lost on restart |
| 🔢 **Centralised document numbering** | Document numbers come from an atomic counter in the format `{prefix}-{tenant}-{period}-{4-digit sequence}`, so simultaneous users can no longer collide |
| 🚦 **Document state machines** | A table of legal transitions for 8 document types; confirm, ship, cancel, approve, receive and post are all validated for sales, purchasing and journals |
| 🏦 **Cash cycle foundations (AI chat only)** | Bank account, accounts payable, payment and receipt models, with payment-against-payable, receipt-against-receivable and atomic bank balance updates |
| ⚙️ **14 system settings** | Company letterhead, tax ID, currency, tax rate, timezone, backup schedule, lockout threshold and more (resolution order: environment variable, then database, then default) |
| 📗 **An 86-account Taiwanese chart of accounts** | Usable from first boot; you can add, edit and deactivate accounts, and system accounts are protected from deletion and edits |

---

<a id="v355-and-earlier"></a>

# 📦 v3.55 and earlier

> These entries were preserved from the original README "What's fixed recently" section (lines 30–157) when this changelog was split out. The English below is the same content, restructured for English readers; the Chinese original is kept verbatim in [`CHANGELOG_ZH.md`](./CHANGELOG_ZH.md).

### 🆕 v3.55 (2026-05-25) — Shipping automatically drives invoice, journal entry and receivable (the full O2C chain)

> Field feedback from 范展裕 (Fan Chan-yu): delivery notes had no matching journal entry or invoice number, and inventory, sales and accounting drifting out of sync would be a real problem.
> Fair point. v3.54 only added the fields; v3.55 makes "ship once, and the whole chain follows" actually true.

| What changed | What you'll notice |
|---|---|
| 📦 **Delivery notes are real records now** | A new `delivery_notes` table (rather than just `SO.status = 'shipped'`), with its own DN number `DN-YYYYMMDD-NNNN`, signature fields and a carrier tracking number |
| 🔗 **Shipping issues the invoice** | If the customer has a tax ID, a GUI e-invoice record is created automatically at 5% VAT, cross-linked in both directions (SO ↔ invoice) |
| 📋 **Shipping posts the journal entry** | Three lines, balanced automatically: DR 1200 Accounts Receivable / CR 4100 Sales Revenue / CR 2200 Output VAT |
| 💰 **Shipping creates the receivable** | An AR record on Net 30 terms by default, linked back to the sales order, the invoice and the journal entry |
| ⚛️ **One atomic operation** | All six objects are written inside a single transaction; a failure halfway through rolls everything back, so you never end up with half a set of paperwork |
| 🌐 **B2C is handled too** | When the customer has no tax ID, invoicing is skipped but the shipment, journal entry and receivable still complete |
| 📊 **Delivery note list API** | `GET /api/sales/delivery-notes`, filterable by date, sales order or status |
| ⚡ **Live SSE notifications** | Everyone else's screen reflects the new sales order status within about 3 seconds (mechanism introduced in v3.53) |

The complete order-to-cash chain:

```text
SO ─ship─▶ DeliveryNote ─auto─▶ EInvoice ─auto─▶ JournalEntry ─auto─▶ AR
                                     │                                  │
                                     └─────── back-link to SO ──────────┘
```

### 🆕 v3.54 (2026-05-25) — Three-axis fixes: regulatory compliance, data leakage, cross-border timezones

> Field feedback from 范展裕 (Fan Chan-yu): sales staff should not see financial reports; delivery notes need matching invoices and journal entries; how is UTC handled across countries; a leak of confidential figures would be serious.
> A three-axis audit surfaced 16 P0 issues; this release fixed the nine most critical.

| What changed | What you'll notice |
|---|---|
| 🔒 **Sales staff can no longer see cost** | `unit_cost` and `credit_limit` are stripped from responses for any role without the accounting permission |
| 📧 **The owner's dashboard can't be leaked** | The email digest preview and send endpoints were raised from `ai.agent.use` to `analytics.view`, and sends to external addresses are logged |
| 📊 **The inventory valuation report returns 403 for sales roles** | `inventory-monthly.xlsx` is accounting-only; the unprivileged variant does not even contain a `unit_cost` column |
| 🧾 **E-invoices are stored in the database** | The `EInvoiceRecord` table shipped, so records survive a restart — they were previously an in-memory dictionary, which breached Taiwan's 5-year retention obligation |
| 🔗 **Invoices link back to the sales order** | Pass `so_id` when issuing and `SO.invoice_no` is written back, so an auditor can follow the trail |
| 📋 **Invoice list API** | `GET /api/tax/tw/einvoice/list` with date, buyer and status filters, so an auditor can actually pull the records |
| ⏰ **Taiwan invoice timezone corrected** | `invoice_date` now uses Asia/Taipei. Under UTC, an invoice issued between midnight and 08:00 local time was dated to the previous day — a breach of the GUI regulations |
| 🔐 **demo-admin backdoor closed** | In production (`DEBUG=false`) the demo-admin token is refused, with the IP and user agent logged |
| 🎨 **The sidebar hides menus by permission** | A sales role no longer sees Accounting, Reports or Permissions — not merely a 403 from the backend, the entry is not rendered at all |
| 💰 **Payments and receipts post journal entries** | `record_payment` / `record_receipt` used to crash outright (they passed no lines); they now create the DR/CR entries and link back to the source SO or PO |

### 🆕 v3.53 (2026-05-25) — The three concurrency failure modes, all fixed

> Field feedback from 范展裕 (Fan Chan-yu): if several people are online at once, does the data stay in sync — because ordering in the morning and receiving in the afternoon would be a serious case.
> Correct. A three-axis audit surfaced 7 P0 issues; all were fixed. **This is an ERP-critical release.**

| What changed | What you'll notice |
|---|---|
| 🔒 **Atomic stock updates** | A receipt of 100 in the morning and a concurrent issue of 30 in the afternoon are guaranteed to land at +70. Previously an update could be lost, leaving you at −30 or +100 |
| ⚡ **The inventory page refreshes itself** | After a receipt is booked, the plant manager's screen updates within about 3 seconds — **no F5 needed** |
| 📋 **Purchasing and sales lists refresh too** | When somebody else changes a PO or SO status, your list syncs itself, so you can see what a colleague changed without asking |
| 🗄️ **SQLite no longer jams with several users** | WAL mode is enabled, which supports multiple writers and stops the random `database is locked` errors |
| 🚨 **SQLite in production is blocked outright** | Customers can no longer accidentally run production on SQLite — PostgreSQL is enforced |
| 🔐 **The event stream is isolated per tenant** | Events from company A are never pushed to company B's screens; multi-plant deployments stay fully separated |
| 🔧 **PO/SO receipts are genuinely atomic** | A failure midway rolls back instead of leaving "stock incremented but PO not updated", which used to cause double booking |

### 🆕 v3.52 (2026-05-24) — One-click update, with automatic data backup

| What changed | What you'll notice |
|---|---|
| 🆙 **One-click upgrade to the new version** | Double-click `update.bat` and it backs up your data, downloads the new code, upgrades the database and restarts — no git knowledge required |
| 💾 **A backup is taken before the update** | Your `erp.db`, `.env` and `uploads/` are copied to `backups/YYYYMMDD_HHMMSS/` |
| 🔄 **Works with either install method** | Whether you installed by `git clone` or by downloading a zip, the script detects it and uses the matching approach (`git pull` or a fresh zip download) |
| 🔧 **The database schema upgrades itself** | New columns or tables in the new version? `alembic upgrade head` runs automatically — no SQL required |
| ⏮ **Recoverable if something breaks** | The backup folder contains a README describing the restore, so three steps take you back to yesterday's state |

### 🆕 v3.51 (2026-05-24) — A complete uninstall path

| What changed | What you'll notice |
|---|---|
| 🗑 **Genuinely complete removal** | Double-click `uninstall_easy.bat` and even the Windows registry entries are cleared. The earlier claim that "uninstalling means deleting the folder" was an oversimplification — Python leaves an entry in Add/Remove Programs |
| 🛡 **Your data is only deleted if you say so** | The uninstaller asks twice whether ERP data should go as well; `erp.db`, `uploads/` and `.env` are kept by default so you cannot lose business records by accident |
| 💾 **Optional cache cleanup** | An advanced prompt offers to clear the global npm and pip caches — this frees around 500 MB but affects your other Node and Python projects |
| 🆘 **Rescue path if you deleted the folder first** | If you already removed the folder and then discovered the registry leftovers, the [troubleshooting guide](./INSTALL_TROUBLESHOOTING_EN.md#i-already-deleted-the-folder-and-found-python-residue) has a one-line PowerShell cleanup |

### 🆕 v3.50 (2026-05-24) — Six fixes held to a strict standard

| What changed | What you'll notice |
|---|---|
| 🐍 **Python versions stop fighting each other** | Whether your machine already has Python 3.12, 3.13 or nothing at all, the install will not conflict. `install_easy.bat` uses its own isolated 3.11 and **leaves your system Python untouched** |
| 🔒 **The wrong version is caught at install time** | pip and npm used to install something subtly broken that only exploded at runtime. Now a wrong version fails loudly and tells you to use `install_easy.bat` |
| 📄 **E-invoices download as a complete PDF** | "Print invoice" used to open nothing more than the browser print dialog. There is now a "Download PDF invoice" button and the **server generates a full A4 PDF** with the line-item table and embedded Chinese fonts |
| 📋 **Purchase order, sales order and delivery note PDFs are complete** | Printing used to produce a summary that said "see the system for full line items". Every document now has a PDF button and the **server returns a proper PDF with all line items, signature blocks and the company logo** |
| 👤 **Admins can actually create users and roles** | Clicking "add user" as an admin used to return 403 Forbidden; 22 missing permission codes were added, so **admin really can manage accounts now** |
| 🚨 **A privilege bug fixed** | An internal review found that the permission code checked when creating a user was the code for *reading* users (a copy-paste error). It now checks the create-user code, **closing a path to creating accounts with read-only rights** |

### 🆕 v3.49 (2026-05-22) — An install path for non-technical users

| What changed | What you'll notice |
|---|---|
| 🚀 **No Docker, nothing to install first** | Double-click `install_easy.bat` and the script downloads Python 3.11 and Node.js 20 into the project's own `tools\` folder — **no administrator rights, no changes to your system** |
| ⚖️ **It tells you before downloading, with a 5-second countdown** | The screen states that Python (PSF License) and Node (MIT) are about to be downloaded, giving you a chance to press Ctrl+C |
| 🆘 **Guided recovery when installation fails** | Open [`docs/INSTALL_TROUBLESHOOTING_EN.md`](./INSTALL_TROUBLESHOOTING_EN.md) and match your symptom to its fix; the usual culprits (antivirus, firewall, port already in use) are all listed |
| 🗑️ **Uninstall equals deleting the folder** | Everything lives inside the one folder — nothing in the registry, no system services, nothing in `Program Files`.<br>⚠️ **Corrected in v3.51**: that was an oversimplification; use `uninstall_easy.bat`, which also clears the Windows registry leftovers |

[👉 Open the full changelog list below](#-full-changelog)

---

## 📜 Full changelog

<details>
<summary>(Click to expand — newest first)</summary>

> 🏷 **2026-05-22 — renamed to Ouvoca following a trademark conflict** — see [RENAME_NOTICE_EN.md](./RENAME_NOTICE_EN.md) · [ZH](./RENAME_NOTICE_ZH.md)

- **v3.50** (2026-05-24) — 🛠 Strict-standard fixes on three axes: Python pinned to 3.11 across the whole codebase, the two PDF systems merged (e-invoice, PO, SO and delivery note all download as complete PDFs), 22 missing RBAC permission codes added, and one privilege-escalation bug fixed
- **v3.49** (2026-05-22) — 🚀 **Zero-dependency install for non-technical users** (double-click `install_easy.bat`, Python and Node download themselves, no Docker) plus legal disclosures and a troubleshooting guide
- **v3.48** (2026-05-22) — Second-pass six-axis audit across all modules, `TenantMixin` added to 12 models, legal text trimmed
- **v3.47** (2026-05-22) — Six-axis audit: fixes across installation, security, data and UX
- **v3.46** (2026-05-22) — Glossary persisted to the database, plus datetime fixes
- **v3.42** (2026-05-22) — User account management, global cross-table search, daily AI usage cap, Taiwanese working-day calendar, timezone settings · Legal notice [EN](./pdf/37_Polish_V342_Legal_EN.pdf) · [ZH](./pdf/37_第六輪卡關修補法律聲明_中文.pdf) — to be reviewed by IT, legal and HR leads before use
- **v3.41** (2026-05-22) — Customer gross margin, order follow-up, emailing PDFs, data health check · Legal notice [EN](./pdf/36_Polish_V341_Legal_EN.pdf) · [ZH](./pdf/36_第五輪卡關修補法律聲明_中文.pdf) — to be reviewed by a CPA plus legal and sales leads before use
- **v3.40** (2026-05-21) — Frozen hard-write safe mode, cross-user audit log search, Chinese relative-date parsing · Legal notice [EN](./pdf/35_Polish_V340_Legal_EN.pdf) · [ZH](./pdf/35_第四輪卡關修補法律聲明_中文.pdf) — to be reviewed by a CPA plus legal and internal control before use
- **v3.39** (2026-05-21) — Company logo on PDFs, the delete trio, LLM tool pagination · Legal notice [EN](./pdf/34_Polish_V339_Legal_EN.pdf) · [ZH](./pdf/34_第三輪卡關修補法律聲明_中文.pdf)
- **v3.38** (2026-05-21) — 30-minute ConfirmCard TTL, one-click backup, customer disambiguation · Legal notice [EN](./pdf/33_Polish_Legal_EN.pdf) · [ZH](./pdf/33_第二輪卡關修補法律聲明_中文.pdf)
- **v3.37** (2026-05-21) — All 14 blockers non-technical users hit: Chinese fonts in Docker, default password prompts, the onboarding wizard, the chat welcome screen · Legal notice [EN](./pdf/32_Setup_Wizard_Legal_EN.pdf) · [ZH](./pdf/32_安裝精靈法律聲明_中文.pdf)
- **v3.0** (2026-05-15) — ⚡ Strategic pivot: the LINE Bot, mobile app and outsourced-collaboration tracks were all cut · [ADR](./ARCHITECTURE_DECISIONS.md) (Chinese)

The full internal changelog lives in `docs/WORKLOG.md`, a working log that is `.gitignore`d and therefore absent from GitHub — no link is given because it would 404.

</details>

---

## Even earlier versions

Records before v3.0 are scattered across git history and the per-release legal notice PDFs. To look them up:

```bash
git log --oneline --reverse | head -80
```

Or see the legal notice PDF list in [`DOCUMENT_INDEX.md`](./DOCUMENT_INDEX.md) — numbers 29 to 38 correspond to v3.32 through v3.44.

---

**Last updated**: v3.70 (2026-08-04) · Sources: measured from the codebase plus [`V360_DELIVERY_REPORT_ZH.md`](./V360_DELIVERY_REPORT_ZH.md) (Chinese only)

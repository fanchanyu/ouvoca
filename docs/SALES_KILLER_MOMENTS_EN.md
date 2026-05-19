# LLM-ERP Sales Demo One-Pager — 9 Killer Moments (v3.5)

> **For sales team**: walk through these 9 moments in a 30-min demo = signed contract
> **Product status**: ~91% MVP, 193 tests green / 38 AI tools / 33 bilingual docs

For full Chinese version see `SALES_KILLER_MOMENTS_ZH.md`.

---

## One-Liner Pitch

> **"Conversational ERP for 50-100 person factories — open Chrome, type one sentence to Chat, do CRUD on all documents; AI auto-migrates legacy data (Dingxin/Chenghang). $30k/year."**

---

## Pain Points vs Our Answer

| Customer says | We answer |
|---|---|
| "Too expensive (SAP $200k+)" | $30k/year all-in |
| "Too hard (100s of screens)" | Just talk to it, 2hr to learn |
| "IT can't use it" | AI asks back to teach |
| "Employee misclicks?" | ConfirmCard + 90s Undo |
| "What about legacy data?" | AI Schema Mapping, 1hr migration, zero downtime |
| "No mobile?" | Desktop is enough; 80% of time at the PC |

---

## 9 Killer Moments

### Moment 1 — Conversational read (warmup)

```
Boss: "How's the factory today?"
→ AI runs preview_email_digest tool → 3 sections (alerts/events/KPI)
★ "30 seconds, no asking employees" ★
```

### Moment 2 — Conversational hard-write (CORE)

```
Procurement: "Order 100 M6 bolts from Changjiang, deliver 5/20"
→ AI auto-resolves Changjiang→SUP-001, "螺絲"→M6-BOLT-20 via glossary
→ Emits ConfirmCard with full details
→ Click confirm → PO created
★ "Don't learn the system, just talk" ★★
```

### Moment 3 — Slot-filling reverse-ask

```
Procurement: "place an order"
→ AI: "I need 4 things: supplier, items, qty, delivery date. Please tell me each."
★ "AI never fabricates — asks for what's missing" ★
```

### Moment 4 — Glossary smart resolution

```
Procurement uses old-timer nickname "鋼釘" (steel nail)
→ AI: lookup_term → M6-BOLT-20 (alias, confidence 0.9)
→ Order proceeds
★ "AI speaks veteran-worker language" ★
```

### Moment 5 — 90-second Undo

```
Procurement (30s after order): "cancel my last order"
→ AI finds PO created in last 90s by this user
→ Emits reverse ConfirmCard, shows remaining 60s
→ Click confirm → status=cancelled
★ "Click wrong? Undo in 90 seconds" ★
```

### Moment 6 — Cross-DB federated query

> ⚠️ **Recommended companion statement during demo**: "This feature requires connecting to your incumbent ERP. **We recommend first confirming the authorization scope in writing with your ERP vendor**; specific licensing terms depend on your contract with that vendor, and add-on licenses may be needed. erpilot does not participate in such contractual matters. See [`EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md)."

```
Boss: "What's our Dingxin order amount for May?"
→ AI: list_external_connections → list_external_tables → query_external_db
→ "Dingxin: $3.2M (45 orders) + LLM-ERP: $580K (12) = $3.78M"
★ "Don't kill Dingxin, run both" ★ (provided customer has obtained written authorization)
```

### Moment 7 — Schema Mapping + Migration (🏆 KILLER)

> ⚠️ **Same as above**: Access during a one-time migration still constitutes a use; we recommend the customer confirm authorization scope per their contract with the incumbent ERP vendor before proceeding. See [`EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md) §FAQ Q8.

```
Procurement: "migrate all customers from Dingxin"
→ AI: preview_schema_mapping → suggests:
       CustNo   → code   (0.95)
       CustName → name   (0.95)
       Grade    → grade  (1.0)
→ AI: migrate_from_external_with_confirm
       → ConfirmCard: 124 rows, 6 high-confidence mappings, skip on conflict
→ Click confirm → "✅ Imported 124 customers"
★★★ Customer signs on the spot ★★★
"My legacy data is saved, no IT, no consultants"
```

### Moment 8 — Desktop Toast push

```
Boss leaves for a meeting, EventBus emits stock.below_safety + so.created
→ Desktop notification:
   🔔 ⚠️ Stock below safety: M6-BOLT-20 (300 / 500)
   🔔 📥 New SO-2026-018  $24,000
→ Chat top-right banner slides in (5s auto-dismiss)
★ "Don't watch the screen — AI notifies you" ★
```

### Moment 9 — Daily Email digest

```
Boss: "Send daily digest to wang@example.com at 7am"
→ AI: preview → send_email_digest_with_confirm
→ ConfirmCard with recipient + content preview
→ Click confirm → "✅ Sent"
★ "Get factory status even at dinner" ★
```

---

## Post-Sale Onboarding

| Day | Activity |
|---|---|
| 1 | Docker one-click deploy + connect DB |
| 2 | Connect legacy (Dingxin/Chenghang/Excel) + Migration preview |
| 3-4 | RBAC roles + Glossary teach AI customer's nicknames |
| 5 | 5 key staff 2-hour training |
| 6-10 | Parallel run (old + new) |
| 11 | Full cutover / old system read-only |
| 12-14 | Online support + tuning + glossary expansion |

**vs SAP 6-18 months: 95% reduction**

---

## Competitor Comparison

| Competitor | Price | Mobile | AI | Legacy connect |
|---|---|---|---|---|
| **SAP B1** | $200k+ | Weak | None | DIY DI API |
| **Chenghang** | $50-100k | Weak | None | Same as SAP |
| **Dingxin Workflow** | $80-150k | Weak | None | Won't |
| **Odoo** | $0-30k | Mid | Weak | Write module |
| **Excel + LINE** | $0 | Strong | None | None |
| **LLM-ERP** | **$30k** | Desktop+Toast | **38 tools built-in** | **AI Schema Mapping** |

---

## 30-Second Customer Close

> **"We're not yet another ERP. We're the AI overlay on top of ERP."**
>
> Employees don't learn the system — just talk to it.
> Your legacy system doesn't get killed — we read it + migrate gradually (*we recommend the customer first confirm authorization scope in writing with the incumbent ERP vendor*).
> $30k/year, 2-week deployment, 2-hour onboarding.

---

> ⚠️ **Recommended reading for sales / consultants**: The above descriptions of "direct connection to incumbent ERPs (such as Workflow / ChengHang / SAP B1)" describe **technical feasibility**; specific authorization determinations should be based on the customer's contract with the relevant ERP vendor. See [`EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md) for the compliance reminder, the recommended customer preparation steps, and erpilot's scope of role. **We recommend focusing on technical capability and advising the customer to confirm licensing with the incumbent ERP vendor; please do not make definitive statements about any third-party vendor's policies or audit practices.**
>
> **Want a trial? We can demo 30 min this Thursday afternoon.**

---

**Last updated**: 2026-05-15 (v3.5 — 9 killer moments + Email digest)
**Demo script**: `docs/demos/crud_pipeline_demo.md`
**Commits**: v3.0~v3.5, 7 sprint commits total

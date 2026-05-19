# External ERP Licensing Compliance Notice

> **Required reading for legal compliance**: Before connecting erpilot to your **existing ERP** (Workflow ERP, ChengHang, SAP B1, Vitals, Odoo, Microsoft Dynamics, etc.), please read this document fully and complete the three actions listed.
>
> **Language**: English version. Traditional Chinese: [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md).

---

## ⚠️ One-Page Executive Summary

| Item | Detail |
|---|---|
| **Audience** | Customer **IT lead / purchasing decision-maker** intending to enable erpilot's "external DB connector / Schema Mapping AI / cross-DB query" features |
| **Core risk** | Most commercial ERPs are licensed **per-named-user** and **prohibit shared or service accounts** from connecting to the DB or API |
| **If violated** | Incumbent ERP vendor may issue **suspension / claims / back-licensing fees**; voided maintenance contracts; software audit (BSA / vendor periodic audit) findings |
| **Customer must do** | ① Obtain written authorization ② Purchase add-on licenses as required ③ Retain authorization documents |
| **erpilot does NOT do** | We **do not assist, represent, or assume liability** for contracts, licensing, or legal matters with third-party ERP vendors |
| **Bottom line** | **Technical "can connect" ≠ Legal "allowed to connect."** Always obtain authorization before enabling a connector. |

---

## 1. Why Licensing Risk Exists

### 1.1 Standard ERP Licensing Models

The following licensing models are common in Taiwan / global ERP markets — **triggering any of them may constitute a violation**:

| License model | Common vendors | Violation scenario |
|---|---|---|
| **Per-Named-User License** | 鼎新 Workflow, 正航 ChengHang, SAP B1, Oracle NetSuite | erpilot connects via "Integration" service account, but that account has no license |
| **Concurrent User License** | Some Workflow / Vitals editions | erpilot's persistent queries consume a concurrent slot beyond purchased quota |
| **Module License** | SAP B1, Microsoft Dynamics | erpilot queries across modules (e.g., FI + SD + MM), but customer only licensed FI |
| **API / Integration License** | SAP B1 Service Layer, Vitals REST | API is a separately-priced add-on; calling without purchase is a violation |
| **ODBC / External Database License** | Some 鼎新/正航 editions | Direct DB access requires a separate ODBC license |
| **Read-Only License** | Some large-ERP modules | Even read-only access by a third-party system without explicit permission can be a violation |

### 1.2 How Vendors Actually Audit

> "If I just connect via SQL Server, the vendor will never know, right?" — **Do NOT think this way.**

- **DB-side audit log**: Incumbent ERP vendor can retrieve DB connection logs during maintenance or upgrades
- **License Manager software**: Many ERPs include built-in license monitoring that reports telemetry back to the vendor
- **Annual audits (BSA / vendor periodic audit)**: Resellers bring license auditors to customer sites yearly
- **Competitive tip-off**: If the incumbent vendor's sales team learns the customer bought a competing ERP (erpilot), they may proactively initiate a compliance audit
- **DB connection metadata**: Service account names, connection strings, login frequency can all be analyzed

---

## 2. Three Mandatory Actions Before Enabling a Connection

### 2.1 ✅ Step 1 — Obtain Written Authorization

Obtain **written** confirmation from the incumbent ERP vendor / reseller covering any of:

> **Explicit agreement that a third-party system (erpilot) may use a shared or service account to access this ERP's database or API, with scope including [SELECT / partial UPDATE / Schema Mapping] operations.**

Acceptable forms:
- The incumbent ERP vendor's **official authorization letter**
- A **contract amendment**
- **Email reply** (retain full thread + vendor signature block)
- The reseller's **written confirmation letter**

> ⚠️ **Verbal consent does NOT count.** "Sales said it's fine" won't hold up under audit.

### 2.2 ✅ Step 2 — Purchase Required Add-Ons

Based on the vendor's response, you may need to purchase any of:

| Add-on | Typical market price (USD / year) | Applies when |
|---|---|---|
| Integration License | $1,000 - 10,000 | Any third-party system integration |
| ODBC License | $300 - 3,500 | Direct DB connection mode |
| Service Account License | $300 - 1,800 / account | Shared / service account |
| API License (per-call billing) | Usage-based | REST API / SOAP mode |
| Read-Replica License | $1,800 - 7,000 | Read-only replica / reporting DB |

> 💡 **Reference figures only**. **Actual amounts are subject to the incumbent ERP vendor's quote.** The erpilot connector is a technical component and **does not include** any of the above license fees.

### 2.3 ✅ Step 3 — Retain Documentation

Store the following documents **centrally** with the customer's Legal / IT lead:
- The incumbent ERP vendor's **written authorization**
- Add-on license **invoices / contracts**
- erpilot connector activation **internal approval records**

> ⚠️ Under audit, **the burden of proof is on the customer**. No written record = default violation.

---

## 3. erpilot's Scope of Responsibility

### 3.1 ✅ What We Provide

| Item | Description |
|---|---|
| **Connector code** | sqlite / csv / SQL Server / REST API technical components |
| **Schema Mapping AI** | 3-tier confidence (exact / alias / partial), AI auto-mapping columns |
| **ConfirmCard migration tools** | Preview + confirm, skip / overwrite conflict strategies |
| **Technical docs** | [External DB Integration Design](./EXTERNAL_DB_INTEGRATION_DESIGN_EN.md) |
| **Technical support** | Connector code bug fixes / Schema Mapping model improvements |

### 3.2 ❌ What We Do NOT Do

| Item | Description |
|---|---|
| Contract negotiation | We do NOT negotiate EULA / add-on licenses with third-party ERP vendors on the customer's behalf |
| Legal opinion | We do NOT provide any legal opinion or compliance opinion letters |
| License resale | We do NOT resell third-party ERP Integration / ODBC / API licenses |
| Audit response | We do NOT represent the customer in responding to BSA / third-party ERP vendor software audits |
| Liability for violations | erpilot **assumes no liability** for suspension / claims / losses caused by **the customer's failure to obtain authorization before connecting** |

### 3.3 Customer Acknowledgment (Required Before Connector Activation)

Before enabling any external DB connector, the customer is deemed to have acknowledged:

> **The Customer has independently confirmed the scope of authorization with the incumbent ERP vendor and assumes full compliance responsibility for erpilot connecting to said ERP. erpilot bears no liability for any licensing determination, audit outcome, or claim by the third-party ERP vendor.**

This acknowledgment is also recorded in the **audit log at connector activation time** for future reference.

---

## 4. FAQ

### Q1: We're a small company (30 employees). The incumbent ERP vendor won't audit us, right?
**A**: Audit likelihood is not directly tied to company size. Resellers have annual KPIs, and **buying a competing ERP often becomes an audit hotspot**. The risk is not "will I be audited," but "can I produce written authorization when audited."

### Q2: We only use erpilot to READ (SELECT), never to write to the original DB. Do we still need authorization?
**A**: **Yes.** EULAs typically govern "**access**," not just "**writes**." Even read-only third-party access is a violation.

### Q3: Can I just have my IT staff lend their personal account to erpilot? That counts as a "named user," right?
**A**: **Not recommended.**
- Most EULAs prohibit "sharing accounts with software / systems"
- If that employee leaves, erpilot loses connection immediately
- Personal accounts usually have **excessive privileges**; erpilot should use a "least-privilege service account"
- Audits that uncover system integration via a personal account often deem this a **clearer violation**

### Q4: The vendor says "I don't know" or "we don't offer that license" — what then?
**A**: Demand a **written** reply stating "the vendor is aware that the customer will integrate with a third-party system and does not require additional license fees." No written record = no authorization — **better to pause the connector than take the risk**.

### Q5: I've already connected via erpilot and only now realize I need authorization — what do I do?
**A**:
1. **Immediately disable the connector** (in erpilot Settings → External Connections → Disable)
2. Retain a copy of the "activation period / connection logs"
3. Proactively contact the incumbent ERP vendor to explain and retroactively license (**proactive vs. caught in audit** — the vendor's posture differs vastly)
4. Consult legal counsel

### Q6: Can erpilot help send an email to the incumbent vendor to negotiate licensing?
**A**: **No.** erpilot does not represent any customer in communications with third-party ERP vendors. **We recommend the customer's IT lead contact their incumbent reseller directly** (they know the EULA details best).

### Q7: We use a free / trial edition (e.g., Odoo Community). Does this still apply?
**A**: Open-source editions (AGPL / GPL) typically have **no such restriction**, but **Odoo Enterprise / SAP B1 trial / any commercial edition** are subject to this warning. Please confirm **which edition** you're running.

### Q8: Can I use erpilot to migrate data once, then disable the connector?
**A**: Technically yes — one-time migration then disconnect. But **the access during migration itself** requires authorization. Please follow §2 to obtain written authorization before any one-time migration.

---

## 5. Reminders for erpilot Consultants / Resellers

When demoing / pitching erpilot's "external DB connector" feature:

✅ **You may say**:
- "Our Schema Mapping AI can automatically connect to your ERP data"
- "Technically we can connect to your 鼎新 / 正航 SQL Server in 2 minutes"
- "Conversational ERP can read historical data from your legacy system"

❌ **You must NEVER say**:
- "Forget about your 鼎新 license, we'll work around it"
- "The vendor will never find out"
- "It's fine, everyone connects this way"

⚠️ **You must always add**:
- "However, please first obtain written confirmation of authorization scope from your incumbent ERP vendor"
- "erpilot is not responsible for original ERP licensing compliance"

---

## 6. Related Documents

| Topic | Where to look |
|---|---|
| **Technical design (how to connect)** | [`EXTERNAL_DB_INTEGRATION_DESIGN_EN.md`](./EXTERNAL_DB_INTEGRATION_DESIGN_EN.md) |
| **User manual** | [`USER_MANUAL_EN.md`](./USER_MANUAL_EN.md) |
| **Sales killer moments** | [`SALES_KILLER_MOMENTS_EN.md`](./SALES_KILLER_MOMENTS_EN.md) |
| **erpilot tri-license model** | [`COMMERCIAL_LICENSING_FAQ_ZH.md`](./COMMERCIAL_LICENSING_FAQ_ZH.md) (ZH-only) |
| **Chinese version of this notice** | [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md) |

---

**Last updated**: 2026-05-19 (v3.25.4 — added Third-Party ERP Licensing Compliance Notice)
**Legal nature**: This document is **a compliance reminder only** and does NOT constitute legal advice. For specific licensing determinations, consult your own legal counsel and the incumbent ERP vendor.
**Version**: 1.0

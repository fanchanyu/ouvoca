# External ERP Licensing Compliance Reminder

> **Nature of this document**: This is a compliance **reminder** only. It **does NOT constitute legal advice**, nor does it constitute any representation regarding the licensing policies of any specific third-party ERP vendor. Any specific licensing determination should be based on **the customer's contract with the relevant ERP vendor** and, where appropriate, the advice of legal counsel.
>
> **Language**: English version. Traditional Chinese: [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md).

---

## ⚠️ One-Page Executive Summary

| Item | Detail |
|---|---|
| **Intended audience** | Customer **IT lead / purchasing decision-maker** planning to enable erpilot's "external DB connector / Schema Mapping AI / cross-DB query" features |
| **Compliance consideration** | Some commercial ERP license agreements may include specific terms or restrictions regarding **connections via shared or service accounts** to the DB or API |
| **If appropriate authorization is not obtained** | Depending on the customer's contract with the ERP vendor, this may lead to contractual handling (e.g., service adjustments, retroactive license fees, dispute resolution) |
| **Recommended customer preparation** | ① Confirm authorization scope with the incumbent ERP vendor ② Purchase any necessary integration licenses ③ Retain relevant documentation |
| **erpilot's role** | We provide the connector as a technical component; we **do not participate in or represent the customer in** any contracts, licensing, or legal matters between the customer and the third-party ERP vendor |
| **Bottom line** | **Technical "ability to connect" and legal "compliance with licensing" may be separate questions.** We recommend confirming authorization scope before enabling a connector. |

---

## 1. Why We Recommend Confirming Authorization First

### 1.1 Common Commercial ERP Licensing Models

The following are licensing models commonly seen in the market. **Whether a specific model applies and how it treats "third-party system integration" varies by vendor and contract**—please refer to your **official license documentation or contract** with the incumbent ERP vendor as the authoritative source:

| Common licensing model | Description | Potential relationship to third-party integration |
|---|---|---|
| **Per-Named-User** | Billed per individually named user | Some vendors' contracts may have specific terms regarding "service-account access" |
| **Concurrent User** | Billed by concurrent sessions | A third-party system's persistent connections may occupy concurrent-user slots |
| **Module License** | Billed by purchased functional modules | Cross-module data access may touch on modules not licensed |
| **API / Integration License** | May be a separately-priced item per contract | Some vendors' APIs may be priced as an add-on |
| **ODBC / External DB License** | May be a separately-priced item per contract | Some vendors may have separate add-ons for direct DB access |
| **Read-Only / Read-Replica** | May be a separately-priced item per contract | Read-only access may still require appropriate authorization per contract |

> 💡 The above is a general overview and **does not represent that any specific vendor necessarily adopts any specific model or imposes any specific restriction**. For specific questions, please contact the ERP vendor's reseller or legal contact.

### 1.2 Channels Through Which Compliance Audits May Surface

Software compliance audits may be triggered or surface through channels including (but not limited to):

- **DB-side audit logs**: Many commercial ERPs retain connection records at the DB layer
- **License Manager / Telemetry**: Some ERPs include built-in license-monitoring components
- **Annual or periodic compliance audits**: Per the customer's contract with the vendor or reseller
- **DB connection metadata**: Service account names, connection strings, etc., may be analyzed

> ⚠️ We recommend handling authorization matters per your contract with the incumbent ERP vendor before enabling any external connection.

---

## 2. Recommended Preparation Before Enabling a Connector

### 2.1 ✅ Step 1 — Confirm Authorization Scope with the Incumbent ERP Vendor

We recommend confirming the following items in **writing** with your incumbent ERP vendor / reseller (adjust to your actual usage scenario):

> **Our company plans to have a third-party system (erpilot) read this ERP's database or API via a shared / service account, with usage scope including [SELECT / partial UPDATE / Schema Mapping, etc.]. Please confirm whether this usage falls within our current authorization scope; if not, please advise how to address it.**

Acceptable written forms (per your legal department's policy):
- Official reply letter from the incumbent ERP vendor
- Contract amendment
- Written confirmation from the reseller
- Email reply (we recommend retaining the full thread)

> 💡 **Recommendation**: Written confirmation generally provides better reference value than verbal assurances in the event of a future dispute.

### 2.2 ✅ Step 2 — Purchase Any Necessary Licenses Based on the Vendor's Reply

Based on the vendor's reply, the following add-ons may be required (**whether they are required and at what price varies by vendor and contract**):

| Potential add-on | When it may apply |
|---|---|
| Integration License | Third-party system integration |
| ODBC License | Direct DB access |
| Service Account License | Shared / service account |
| API License | REST API / SOAP mode |
| Read-Replica License | Read-only replica / reporting DB |

> 💡 The connector erpilot provides is a **technical component** and **does not include** any third-party ERP license fees. Actual license fees follow your quote or contract with that vendor.

### 2.3 ✅ Step 3 — Retain Relevant Documentation

We recommend retaining the following documents per your company's document-management policy:
- The incumbent ERP vendor's authorization confirmation
- Add-on license contracts / invoices
- Internal sign-off records for erpilot connector activation

> 💡 Proper document management supports future compliance review or dispute resolution.

---

## 3. erpilot's Role and Scope of Responsibility

### 3.1 ✅ What erpilot Provides

| Item | Description |
|---|---|
| **Connector code** | sqlite / csv / SQL Server / REST API technical components |
| **Schema Mapping AI** | 3-tier confidence (exact / alias / partial) column mapping |
| **ConfirmCard migration tools** | Preview + confirm, skip / overwrite conflict strategies |
| **Technical documentation** | [External DB Integration Design](./EXTERNAL_DB_INTEGRATION_DESIGN_EN.md) |
| **Technical support** | Connector code bug fixes / mapping model improvements |

### 3.2 ❌ What erpilot Does NOT Provide

| Item | Description |
|---|---|
| Third-party contract negotiation | We do not represent the customer in negotiating EULAs / add-on licenses with third-party ERP vendors |
| Legal opinion | We do not provide legal opinion or compliance opinion letters (please consult legal counsel) |
| License resale | We do not resell third-party ERP Integration / ODBC / API licenses |
| Audit representation | We do not represent the customer in software compliance audits by third-party ERP vendors |

### 3.3 Scope of Liability Statement

> **To the maximum extent permitted by applicable law, erpilot does not assume responsibility for the following:**
> - Contractual handling arising from the customer enabling a connection without obtaining appropriate authorization per this reminder (including but not limited to service adjustments, retroactive license fees, contract disputes)
> - Fees or losses arising from a third-party ERP vendor's licensing determinations, compliance audits, or contract enforcement
> - Changes in third-party ERP vendors' licensing policies

### 3.4 Customer Confirmation Before Activation

We recommend the customer complete the following internal procedures before activating a connector:

1. Complete the authorization confirmation, required procurement, and document retention described in §2
2. Obtain written internal sign-off from IT / Legal / Procurement leads
3. When activating the connector in erpilot, the system records the activation time, operator, and corresponding external data source in the **audit log** for the customer's future internal review

> 💡 The act of activating a connector indicates that the customer has independently evaluated and assumed the relevant compliance responsibilities.

---

## 4. FAQ

### Q1: We're a small company (30 employees). Do we still need to be aware of this?
**A**: Compliance responsibility is not directly tied to company size. We recommend handling per your contract with the incumbent ERP vendor. If in doubt, please contact the vendor or your legal counsel.

### Q2: We only use erpilot to READ (SELECT), never to write back. Do we still need to confirm authorization?
**A**: We recommend confirming with the vendor regardless. Many license agreements' applicable scope includes "access" behavior, not only "writes." Specific application depends on contract terms.

### Q3: Can we have an IT staff member's personal account used by erpilot?
**A**: This is technically possible, but **we recommend careful evaluation**:
- Some license agreements may have provisions regarding "scope of personal-account use"—please refer to contract terms
- erpilot will lose connectivity when that employee leaves
- Personal accounts typically have broader privileges; from a security best-practices standpoint, we recommend a "least-privilege service account"
- We recommend confirming with your legal team / incumbent ERP vendor whether this falls within the authorized scope

### Q4: The vendor says "unclear" or "no corresponding license item available" — what do we do?
**A**: We recommend requesting a **written reply** that explicitly records the vendor's understanding and position on this usage scenario. If no clear reply is available, we recommend careful evaluation before deciding whether to enable the connector, and consultation with legal counsel where appropriate.

### Q5: I already enabled the connector before seeing this reminder — what now?
**A**: We recommend:
1. Consider pausing the connection as appropriate
2. Retain connection logs from the activation period
3. Proactively communicate with the incumbent ERP vendor and follow their guidance
4. Consult legal counsel where appropriate

### Q6: Can erpilot help us communicate with the incumbent ERP vendor about licensing?
**A**: erpilot does not participate in communications between the customer and third-party ERP vendors. We recommend the customer's IT / Legal / Procurement lead contact the incumbent vendor or reseller directly (they are most familiar with the licensing terms).

### Q7: We use an open-source / trial edition of the ERP. Does this still apply?
**A**: Open-source licenses (AGPL / GPL, etc.) typically have fewer restrictions on third-party system access, but **commercial / trial editions** vary by version. Please refer to the **official license documentation** for the edition you are using.

### Q8: We just want to do a one-time data migration then disconnect. Do we still need to confirm authorization?
**A**: A one-time migration is technically feasible. However, "access during the migration period" still constitutes a use, and we recommend confirming authorization scope per §2 before proceeding.

---

## 5. Guidance for erpilot Consultants / Resellers

When introducing erpilot's "external DB connector" feature, we recommend:

✅ **Suitable content to present**:
- The technical capabilities of erpilot's Schema Mapping AI
- The data source types the connector supports (sqlite / csv / SQL Server / REST API, etc.)
- The conversational ERP experience for cross-source query and migration

✅ **Recommended companion statements**:
- "**The connector is a technical component; before enabling, we recommend that your company first confirm the authorization scope in writing with the incumbent ERP vendor**"
- "erpilot does not participate in contracts / licensing matters between your company and third-party ERP vendors"
- "Specific authorization determinations should be based on your contract with the incumbent ERP vendor"
- "**Detailed compliance reminder**: see [`EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md)"

❌ **Not recommended**:
- Making definitive statements about any third-party ERP vendor's licensing policies or audit practices
- Speculating on behalf of the customer about whether a vendor "will" or "won't" take particular action
- Suggesting in any way that the customer should bypass or disregard the incumbent ERP vendor's licensing terms

---

## 6. Related Documents

| Topic | Where to look |
|---|---|
| **Technical design (how to connect)** | [`EXTERNAL_DB_INTEGRATION_DESIGN_EN.md`](./EXTERNAL_DB_INTEGRATION_DESIGN_EN.md) |
| **User manual** | [`USER_MANUAL_EN.md`](./USER_MANUAL_EN.md) |
| **Sales killer moments** | [`SALES_KILLER_MOMENTS_EN.md`](./SALES_KILLER_MOMENTS_EN.md) |
| **erpilot tri-license model** | [`COMMERCIAL_LICENSING_FAQ_ZH.md`](./COMMERCIAL_LICENSING_FAQ_ZH.md) (ZH-only) |
| **Chinese version** | [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md) |

---

## Statement of Legal Nature

- This document is a **compliance reminder** and **does NOT constitute legal advice, a compliance opinion, or any representation about any third-party vendor's licensing policies**.
- The licensing models, audit channels, and compliance steps described herein are general overviews. **The applicability to any specific situation should be based on the customer's contract with the relevant ERP vendor.**
- For specific licensing determinations, compliance assessments, or dispute handling, please consult **your own legal counsel** and confirm with **the relevant ERP vendor**.
- The content of this document may be updated as industry practices or regulations change, without separate notice.

**Last updated**: 2026-05-19 (v3.25.5 — legal-language polishing pass)
**Version**: 1.1

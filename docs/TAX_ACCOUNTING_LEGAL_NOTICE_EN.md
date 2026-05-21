# Tax / Accounting / Approval Module Legal & Compliance Notice (v3.34)

> **Nature of this document**: Compliance reminder for tax / financial reporting / approvals. **Does NOT constitute tax, accounting, or legal advice.**
> Applies cumulatively with all §6 disclaimers from v3.25.10 → v3.34.
>
> **中文版**: [`TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md`](./TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md)

---

## ⚠️ Important: Tax / Financial Reporting is High-Compliance Sensitive Domain

erpilot v3.34's new LLM tools involve:
- **eInvoice issuance / voiding** (affects business tax filing)
- **Payment / receipt recording** (affects cash flow, financial reporting)
- **AR / AP queries** (decision basis)
- **Multi-step approval** (affects contractual validity)

Errors in these operations **may trigger**:
- 🔴 Tax audit (revenue authority investigation)
- 🔴 Financial misstatement (CPA signoff liability)
- 🔴 Contractual disputes (with customers / suppliers)
- 🔴 Internal control violations (SOX / ISO / GMP certification revocation)

**Please follow this guide and have CPA / tax advisor / legal counsel review major operations.**

---

## 1. eInvoice (issue / void)

### 1.1 issue_einvoice_with_confirm

| Risk | Customer Responsibility |
|---|---|
| Tax ID error | **Must** use `validate_tax_id_tool` to verify before issuance; incorrect B2B invoice cannot be deducted by buyer |
| Amount error | Erroneous amounts are included in current filing; corrections require credit note |
| Upload to revenue authority | erpilot does **NOT** directly upload; customer must integrate cloud-invoice platform / tracking-code management API |
| Tracking code allocation | erpilot does **NOT** manage tracking codes; follow your company's revenue-authority allocation rules |

### 1.2 void_einvoice_with_confirm

| Risk | Customer Responsibility |
|---|---|
| **24-hour limit** | Voiding possible within 24 hours of issuance; **after that, use credit note workflow** |
| Cloud notification | Voiding must be reported to revenue authority / cloud invoice platform; erpilot's ConfirmCard **only marks internal status** |
| Already-deducted scenario | If buyer has filed for deduction, voiding may cause complex reconciliation; coordinate with buyer beforehand |

### 1.3 validate_tax_id_tool

| Limitation | Description |
|---|---|
| Format + checksum only | Algorithm follows Taiwan revenue authority public rules; does **NOT verify name correspondence** (e.g., "is 12345678 actually 'XX Company'?") |
| No status check | Does not verify if company is closed / suspended |
| TW only | US / China / EU VAT/EIN validation not implemented; for other countries **use that country's official validator** |

### 1.4 query_monthly_sales_tax

| Risk | Description |
|---|---|
| **NOT Form 401** | This tool estimates from SO data; **NOT directly usable as filing basis** |
| Missing items | Excludes input tax, zero-rated, tax-exempt sales, returns/allowances |
| Books vs filing | This tool reads SO records; filing requires **issued-but-unrecorded** and **recorded-but-unissued** adjustments |
| **CPA review mandatory** | Before filing, **must** be reviewed by CPA / bookkeeping firm |

---

## 2. Payment / Receipt

### 2.1 Record Payment to Supplier

| Operation | Impact |
|---|---|
| `record_payment_to_supplier_with_confirm` | Creates **draft JE**: debit AP, credit bank |
| Followup | Must be posted by accountant via `post_journal_entry_with_confirm` to take effect |

**Critical warnings**:
- erpilot's JE is **draft**; **not posted = no financial-statement impact**
- After posting, **locked**; requires reversal voucher to undo
- For major amounts (e.g., > 5% of annual revenue), use **maker-checker**
- Reconciliation with supplier statements is separate; erpilot does NOT replace reconciliation

### 2.2 Record Customer Receipt

| Risk | Customer Responsibility |
|---|---|
| Receipt date vs invoice date | erpilot uses creation timestamp; **tax recognition timing may differ** |
| Partial receipts | No "installment receipt" model; manually handle half-payments |
| Refunds | No one-click LLM refund; use JE reversal + bank operations |

### 2.3 AR / AP Queries

| Tool | Limitation |
|---|---|
| `query_outstanding_ar` | Based on `AccountsReceivable` table with status=open/partial; may miss credit sales without AR records |
| `query_outstanding_ap` | Estimated from PO with status=received/partial_received; may miss direct expenses, payroll, taxes |

**Important**:
- Amounts are **advisory**, **not official financial statements**
- Before month-end close, CPA must reconcile

---

## 3. Multi-Step Approval

### 3.1 Approve / Reject Legal Effect

`approve_request_with_confirm`'s **legal significance**:
- Approver's `employee_id` written to ApprovalStep, **forming audit trail**
- If approval later deemed **negligent** (e.g., approving over-budget purchase), liability rests with that employee / supervisor
- erpilot's audit log can serve as **internal audit basis**, but **external legal litigation** still requires formal documentation

### 3.2 Reject Requires Reason

`reject_request_with_confirm` **enforces** non-empty comment:
- **Equal treatment principle** for legal / internal control compliance
- Employee's **basis for appealing** rejected proposals
- For future disputes, reasons can be traced

### 3.3 LLM Slot Extraction Risk

When user says "approve that PO," LLM may:
- Match a different PO's approval request
- Return without completing all steps (multi-step scenario)

**ConfirmCard is the defense**: users must review request_id specifics (entity_type + amount + initiator) before confirming.

---

## 4. Warehouse Picking

### 4.1 Create Pick Task

`create_pick_task_with_confirm` risks:
- Creates one PickTask **per SO item** (may be excessive)
- Does **NOT check inventory sufficiency** (shortage discovered at picking)
- Assigned operator without permission causes picking to stall

**Recommendation**: combine with `query_inventory` to pre-verify stock.

---

## 5. Quality NCR / CAPA

### 5.1 NCR Legal Nature

Records created by `create_ncr_with_confirm`:
- **Do NOT constitute** a claim against supplier (separate written notice required)
- **Do NOT constitute** disciplinary basis against employee (per labor law + internal rules)
- **Do NOT constitute** customer recall notice (legal + PR judgment required)

### 5.2 CAPA Compliance Status

`create_capa_with_confirm` records can serve as:
- Corrective action tracking for **ISO 9001 / GMP / IATF 16949** etc. quality management systems
- Evidence in **customer audits**

But do **NOT constitute**:
- Basis for insurance claims (independent assessment report required)
- Notification to regulatory authorities for recalls (follow each country's regulatory procedures)

---

## 6. Disclaimer Clause

**To the maximum extent permitted by applicable law**, erpilot assumes **no liability** for:

### Tax
1. **Tax penalties** from LLM mis-extracting SO number / tax ID causing wrong invoice issuance
2. **Business tax filing irregularities** from voiding past 24-hour window / missed voiding
3. **Tax evasion risk** from misusing `query_monthly_sales_tax` data as filing basis
4. **Buyer deduction disputes** from missing tax ID validation (e.g., closed companies)

### Accounting
5. **Financial misstatement** from LLM-created draft JE posted incorrectly
6. **Cash flow misjudgment** from AR/AP query omissions
7. **Reconciliation mismatches** from incorrect payment / receipt records

### Approval
8. **Contractual disputes** from LLM mis-extracting request_id causing wrong approval
9. **Internal control failures** from ConfirmCard mis-click / inattentive review

### Warehouse / Quality
10. **Shipping delays** from incorrect pick task creation
11. **Quality certification revocation** from incomplete NCR / CAPA records

### Third Parties
12. **Any disputes** by third parties (customers, suppliers, employees, tax authorities, insurance companies, certification bodies) acting on this system

---

## 7. Cumulative Applicability of Predecessor Disclaimers

This version overlays v3.25.10 → v3.33. **All predecessors' §6 disclaimers apply cumulatively**:

| Predecessor | Key cumulative point |
|---|---|
| v3.25.10 §6 | MRP is planning advisory; deterministic |
| v3.26 §6 | CLSP NP-hard heuristic |
| v3.27 §6 | Provenance ≠ legal causation; TOC heuristic |
| v3.28 §6 | TA ≠ GAAP/IFRS; antitrust warning |
| v3.29 §6 | Forecast not guarantee; unforeseen events |
| v3.30 §6 | LLM slot extraction risk |
| v3.31 §6 | hard-write 5 customer responsibility points |
| v3.32 §6 | Quotation / Count / PO-SO modification contract warnings |
| v3.33 §6 | Inventory-sales deepening contract warnings |
| **v3.34** (this doc) | **Tax / FR / Approval high-compliance warning** (not tax / accounting / legal advice) |

---

## 8. Recommended Practice

### Tax
- **Mandatory** `validate_tax_id_tool` before issuing invoices
- By 5th of each month, have **CPA / bookkeeping firm** reconcile erpilot estimates against actual Form 401
- Major invoices (e.g., > NT$1M) use **dual-issuance + supervisor review**
- Cloud invoice upload integrated by IT (erpilot's mock does NOT replace)

### Accounting
- Major payments / receipts (e.g., > 5% of annual revenue) **must** use maker-checker (creator ≠ poster)
- Month-end / quarter-end / year-end **mandatory** CPA reconciliation
- External financial reports follow **GAAP / IFRS** standards; erpilot's internal analysis NOT a substitute

### Approval
- Approve / reject **legal evidence strength** limited; major decisions retain written + signature
- Rejection comment should be **specific** (not just "disagree"), facilitating future dispute tracing

### Quality
- NCR / CAPA records for **internal QMS use**; external (insurance, recall) requires independent process
- Before certification audit, have QA supervisor review NCR / CAPA completeness

---

## 9. Cultural Reminder: LLM Does NOT Replace Professionals

erpilot's promise: **"natural language replaces training"**, **NOT** **"replaces CPA / tax advisor / legal counsel."**

| AI Can | Professional Judgment Still Required |
|---|---|
| Quickly issue invoices (per input) | Filing strategy / tax planning |
| Integrate AR/AP data | Month-end close / financial reporting |
| Recommend approve / reject | Major contracts / legal disputes |
| Create NCR / CAPA | External recall / insurance claims |

Final decisions should rest with:
- Sales / Procurement / Warehouse / Plant Manager / QA — per their expertise
- Accountant / CPA — per their expertise
- Supervisor / Legal / Tax Advisor — per their authority
- Owner — per their role

**Together.**

---

**Last updated**: 2026-05-21 (v3.34)
**Version**: 1.0
**Chinese**: [`TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md`](./TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md)

# LLM-ERP Taiwan Compliance Reference (English)

> **For accountants / legal / IT leads to confirm**
> What Taiwan regulations we support, what we don't, what the customer must configure themselves.

---

## 📑 Contents

1. [Tax Compliance](#1-tax-compliance)
2. [E-Invoice](#2-e-invoice)
3. [Personal Data Protection](#3-personal-data-protection)
4. [Labor Law / NHI](#4-labor-law--nhi)
5. [Industry-Specific Regulations](#5-industry-specific-regulations)
6. [Compliance Level Matrix](#6-compliance-level-matrix)
7. [Self-Configuration Checklist](#7-self-configuration-checklist)

---

## 1. Tax Compliance

### 1.1 Business Tax (VAT 5%)

| Item | Status | Feature |
|---|---|---|
| Form 401 (general VAT return) | ✅ Full | `GET /api/tax/tw/401?year=2026&period_no=1` |
| Form 403 (input/output detail) | ✅ Full | `GET /api/tax/tw/403?direction=sales` |
| Form 405 (zero-rated sales) | 🟡 Partial (needs customer = "export") | Phase 1.5 |
| Bi-monthly filing period | ✅ Built-in | period_no 1-6 |
| Invoice number track mgmt | ✅ Built-in | Random + track pattern |
| Tax ID checksum validation | ✅ Built-in | `validate_tax_id()` |

### 1.2 Filing Periods

| Period | Months | Filing Deadline |
|---|---|---|
| P1 | Jan-Feb | Mar 15 |
| P2 | Mar-Apr | May 15 |
| P3 | May-Jun | Jul 15 |
| P4 | Jul-Aug | Sep 15 |
| P5 | Sep-Oct | Nov 15 |
| P6 | Nov-Dec | Jan 15 (next year) |

LLM-ERP auto-pushes LINE reminder 5 days before each deadline (planned).

### 1.3 Corporate Income Tax (25%/20%)

| Item | Status |
|---|---|
| Monthly P&L estimation | ✅ `GET /api/analytics/gross-margin` |
| Annual estimated tax | 🟡 Manual export |
| Final tax return (401-1) | ❌ Requires CPA assistance |

---

## 2. E-Invoice

### 2.1 Regulation Mapping

| Regulation | Our Support |
|---|---|
| Article 7 of Unified Invoice Act | ✅ EInvoice structure compliant |
| MOF MIG 3.2.1 | ✅ `to_mig_dict()` aligned |
| B2B / B2C e-invoice | ✅ Both (buyer_tax_id optional) |
| Mobile barcode carrier (3J0002) | ✅ carrier_type / carrier_id fields |
| Natural-person cert (EJ0113) | ✅ Same |
| Donation code | ✅ npo_id field |
| Credit note | 🟡 cancel API exists; CN format pending |
| Void / cancel | ✅ `cancel(invoice_no, reason)` |

### 2.2 VAC Provider Integration

We provide an **Adapter interface** + Mock provider. To connect production VAC:

```python
# In backend/app/integrations/einvoice_tw.py, replace default_provider
class GuanTradeProvider(EInvoiceProvider):
    """GuanTrade Network — major VAC."""
    def submit(self, inv): ...
    def cancel(self, invoice_no, reason): ...
```

Planned VAC integrations:
- GuanTrade Network (GVB)
- Chunghwa Telecom HiCloud
- Cathay Green / ECPay
- Sinopac e-Pay

### 2.3 Built-in Self-Validation

- ✅ Tax ID 8-digit checksum + all-same-digit rejection
- ✅ Invoice number format (AB12345678 / AB-12345678)
- ✅ Tax calculation (5%) + rounding
- ✅ Total = sales + tax (±1 NTD tolerance)

---

## 3. Personal Data Protection

| Personal Data Act | Status |
|---|---|
| Art. 6 (sensitive data) | 🟡 Don't collect (recommended); customer avoids storing |
| Art. 8 (notification) | ❌ Customer provides own privacy policy |
| Art. 11 (update/delete) | ✅ Customer/employee models have soft delete |
| Art. 12 (security) | ✅ bcrypt / RBAC / Audit |
| Art. 27 (breach notification) | 🟡 Traceable via AuditMiddleware |
| Personal data inventory | 🟡 List of fields (below) |

### 3.1 Personal Data Collected

| Subject | Fields |
|---|---|
| **Employee** | Name / Email / Phone / Dept / Title / Hire date |
| **Customer contact** | Name / Email / Phone |
| **Supplier contact** | Name / Email / Phone |
| **User** | Username / hashed password / Last login |

**Not collected**: National ID / NHI card / Bank account / Credit card (outside scope)

### 3.2 GDPR Alignment (for International Brand Exports)

| Right | Our Support |
|---|---|
| Right to access | `GET /api/auth/me` |
| Right to erasure | Reserved API (customer enables) |
| Right to portability | Built-in CSV / xlsx export |
| Data localization | MESH multi-factory — data stays at each site |

---

## 4. Labor Law / NHI

| Item | Status |
|---|---|
| Employee data | ✅ Employee model |
| Attendance | 🟡 3rd-party integration (Phase 2+) |
| Payroll calculation | ❌ Not in scope (use 8thlife / 102 etc.) |
| 2nd-gen NHI supplementary premium | ❌ Not in scope |
| 6% labor retirement | ❌ Not in scope |

> Design choice: **HR doesn't dive into payroll**. Position is "ERP + AI", not HRIS.
> APIs provided for 3rd-party payroll integration.

---

## 5. Industry-Specific Regulations

### 5.1 Food Processing

| Regulation | Status |
|---|---|
| Food Safety Act Art. 9 (traceability) | 🟡 lot/batch fields exist; recording manual |
| Imported food inspection | ❌ Separate system needed |
| HACCP record | ❌ Phase 2+ |

### 5.2 Medical Device

| Regulation | Status |
|---|---|
| UDI (Unique Device Identification) | 🟡 lot_no field usable |
| GMP document control | ❌ Separate QMS needed |

### 5.3 Chemicals / Hazardous

| Regulation | Status |
|---|---|
| Toxic chemical registry | ❌ Separate chem management |
| SDS linkage | 🟡 Part.remark for link storage |

---

## 6. Compliance Level Matrix

| Compliance Level | LLM-ERP Coverage | Customer Must Add |
|---|---|---|
| **Solo (<5 people)** | 100% ✅ | None |
| **SMB Manufacturer (50-100 people, ICP)** | 90% ✅ | External payroll |
| **Cross-border group (500+ people)** | 60% 🟡 | + Consolidation / multi-currency / multi-company |
| **Listed company** | 40% 🟠 | + Material info / IFRS / internal control reports |
| **Finance / Healthcare** | Not suitable ❌ | Use industry-specific systems |

---

## 7. Self-Configuration Checklist

Items the customer must configure during rollout:

### Company Basic Info
- [ ] Company tax ID
- [ ] Company name (ZH + EN)
- [ ] Company address (ZH + EN)
- [ ] Legal representative / invoice track
- [ ] Business activity codes
- [ ] Tax authority branch

### Tax Settings
- [ ] Applicable rate (5% / zero-rated / exempt)
- [ ] Bi-monthly vs monthly filing (default bi-monthly)
- [ ] E-invoice usage decision
- [ ] VAC provider selection

### Banking / Payment
- [ ] Company bank account (for AR/AP records)
- [ ] Payment gateway (ECPay / JKOPay / LinePay, if any)

### Legal / Privacy
- [ ] Privacy notice (for employees / customers to sign)
- [ ] Customer / supplier / employee consent forms

---

## 📞 Compliance Consultation

| Category | Recommended Contact |
|---|---|
| Tax (401/403/annual) | Retained CPA firm |
| E-invoice setup | VAC provider / tax authority |
| Personal data compliance | Retained lawyer / DPO course |
| LLM-ERP config issues | support@llm-erp.example |

---

**Chinese version**: [`COMPLIANCE_TW_ZH.md`](./COMPLIANCE_TW_ZH.md)
**Last updated**: 2026-05-14 · v2.5

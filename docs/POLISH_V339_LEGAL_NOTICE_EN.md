# Third-Round Beginner-Fix Legal & Compliance Notice (v3.39)

> **Document nature**: Compliance reminder for LOGO upload, delete trio, batch print, pagination, digest trigger, slot-filling 3-strike fallback, auto-start. **Does not constitute legal advice.**
> Cumulatively applies to all §6 disclaimers in v3.25.10 → v3.38.
>
> **Chinese version**: [`POLISH_V339_LEGAL_NOTICE_ZH.md`](./POLISH_V339_LEGAL_NOTICE_ZH.md)

---

## ⚠️ Important: v3.39 fixes 8 issues found after v3.38 audit

v3.39 covers:
- **PDF company LOGO** (K1) — uploaded image embedded in all outbound PDFs
- **Delete customer / supplier / part** (K2) — irreversible, with pre-checks
- **Batch print ZIP** (K7) — up to 50 PDFs packaged for download
- **LLM tool pagination** (K3) — handle 1000+ records without context blowup
- **Manual daily digest trigger** (K6) — scheduling delegated to OS cron / Task Scheduler
- **Slot-filling 3-strike fallback** (K4) — 3 consecutive failures route to form page
- **Backend offline guidance** (K5) — Login shows "open Docker Desktop"
- **Docker container auto-start** (K8) — `restart: unless-stopped` on all services

---

## 1. PDF LOGO Embedding (K1)

### 1.1 Copyright Boundary

- Customer-uploaded LOGO must be **owned by the company**
- Using **third-party LOGOs** (brand marks, designer work without license) may violate Copyright Act §91
- erpilot does **not** verify LOGO copyright ownership

### 1.2 Display Limits

- LOGO max 4cm × 1.5cm (keep PDF clean)
- File ≤ 500 KB (avoid bloated PDFs)
- Only PNG / JPG (image/* MIME)

### 1.3 Outbound PDF Legal Effect

- LOGO appears at the top of Quotations / POs / SOs / Delivery Notes
- Once sent, **third parties may recognize the PDF as your company's official document**
- Customer should establish internal control: **only authorized LOGOs may be uploaded**

---

## 2. Delete Customer / Supplier / Part (K2)

### 2.1 Irreversible + Pre-checks

Deletion is **permanent**. v3.38's `undo_last_admin_change` does **not** cover deletes.

Pre-checks:
- **Customer**: any SalesOrder → blocked (use is_active=false)
- **Supplier**: any PurchaseOrder → blocked
- **Part**: any BOMItem / PurchaseOrderItem / InventoryTransaction → blocked

### 2.2 ConfirmCard TTL 10 min

- Delete operations get a shorter 10-min thinking window (vs. 30-min default), **forcing in-moment decision**
- After expiry, re-invoke the tool

### 2.3 Statutory Retention Obligations

Before delete, confirm:
- Business Accounting Act §38: transaction vouchers must be kept 5 years — orders related to a customer/supplier **must not be deleted with the master**
- PDPA: customer PII used during contract performance **must not be arbitrarily deleted**
- For "right to be forgotten" (GDPR-equivalent) — use **anonymization** instead of delete

### 2.4 erpilot Responsibility

- erpilot pre-checks **business associations** and blocks dangerous deletes
- erpilot does **not** check **legal retention periods** or **contractual obligations**
- Customer must self-verify **legal permission** before executing

---

## 3. Batch Print ZIP (K7)

### 3.1 Limits

- Max **50 PDFs** per batch (avoid backend OOM)
- Supports SO / PO / Quotation only
- Failed nos. listed in `failed_list`

### 3.2 ZIP Custody

- ZIP contains **complete outbound PDFs** (same as v3.36 §2)
- Customer should encrypt at rest, not leak
- **Delete local ZIP file promptly** after printing

---

## 4. LLM Tool Pagination (K3)

### 4.1 Design

- `list_customers_paginated` accepts `page` + `page_size` (max 50)
- Returns `total` / `total_pages` / `items`
- Suggests "next page" in natural language

### 4.2 Risk

- Pagination may be chained into **complete data download** (call all pages)
- Customer should monitor abnormal download patterns at enterprise SSO / API gateway layer

---

## 5. Daily Digest Trigger (K6)

### 5.1 Scheduling

- v3.39 provides **manual trigger**: `trigger_daily_digest_now`
- **Automated scheduling** delegated to OS cron / Windows Task Scheduler / docker-compose-restart
- Example (Linux): `0 8 * * * curl -X POST http://localhost:8000/api/email-digest/send -H "Authorization: Bearer $TOKEN"`

### 5.2 Email Legal Boundary

- Email contains **business data** (KPIs / receivables / pending approvals)
- Customer must **verify recipient** is authorized personnel (not personal email)
- Sending should have **audit log** (v3.x roadmap)

---

## 6. Slot-filling 3-Strike Fallback (K4)

### 6.1 Behavior

3 consecutive missing-slot failures on the same tool → system returns `retry_exceeded=true` + suggestion "use form page".

### 6.2 Limits

- Counter is **in-memory** (cleared on backend restart)
- Isolated per user × per tool (failure on A doesn't affect B)
- Auto-reset on successful completion

### 6.3 Customer Responsibility

- If 3 retries still fail, **LLM response quality may degrade** → review question clarity
- Multiple failures may reflect **model bias** or **training gap** → customer can report to erpilot

---

## 7. Backend Offline Guidance (K5)

### 7.1 Message Content

When Login can't reach backend, show:
- "Is Docker Desktop running?"
- "Run `docker compose ps` to check containers"
- "Firewall blocking port 8000?"

### 7.2 Disclaimer

- Guidance is **a general checklist**
- Customer's **specific environment** (corp firewall / VPN / proxy) requires IT
- erpilot does **not** remotely diagnose customer's network issues

---

## 8. Docker Container Auto-Start (K8)

### 8.1 Configuration

`docker-compose.yml` adds `restart: unless-stopped` to all services:
- erpilot containers auto-start when Docker starts
- Containers auto-restart on crash (unless explicitly `docker compose stop`)

### 8.2 Companion Requirement

- Customer must **enable Docker Desktop "Start when log in"**
- erpilot does **not** register as a Windows Service (to avoid conflict with Docker Desktop)
- After OS reboot: launch Docker Desktop → erpilot auto-follows

### 8.3 Risk

- Auto-restart may **mask** true crash root cause (logs in `docker compose logs backend`)
- Customer IT should **periodically review** logs (v3.x roadmap: log rotation)

---

## 9. Disclaimer (Cumulative v3.25.10 → v3.39)

To the maximum extent permitted by applicable law:

**1. LOGO Upload**
erpilot does **not** verify the **copyright ownership** of uploaded LOGOs; customer must **self-verify** legal use rights; erpilot is **not liable** for copyright infringement disputes.

**2. Delete Trio**
erpilot pre-checks business associations; customer must **self-verify** statutory retention, contractual obligations, GDPR / PDPA compliance; erpilot is **not liable** for irreversible data loss, contract disputes, or audit failures.

**3. Batch Print**
ZIP contains complete trade secrets; customer must safeguard; erpilot is **not liable** for ZIP leakage disputes.

**4. Pagination**
Pagination does **not** replace formal data-export compliance flow; customer must monitor abnormal downloads at SSO / Gateway layer.

**5. Daily Digest**
Manual trigger is a **convenience**; automated **scheduling, sending, recipient control** is customer-configured; erpilot is **not liable** for mis-send / miss / wrong recipient.

**6. Slot-filling 3-Strike**
3-retry is a **heuristic suggestion**; does **not** replace full conversation-quality review; customer should adjust based on real UX.

**7. Backend Offline Guidance**
General checklist only; erpilot is **not** responsible for resolving customer's network / firewall / VPN issues.

**8. Docker Auto-Start**
Via `restart: unless-stopped`; customer must **co-configure** Docker Desktop auto-start; erpilot does **not** register as Windows Service.

---

## 10. Pre-Adoption Checklist (v3.39 reinforced)

### 10.1 LOGO Use
- [ ] LOGO is **owned** by the company (or licensed)
- [ ] LOGO scaled to 4cm × 1.5cm and clearly readable
- [ ] Test-printed a PDF to confirm LOGO display

### 10.2 Deletion Policy
- [ ] Established **internal control flow** for data deletion (who can delete, who must sign off)
- [ ] Confirmed **statutory retention period** has passed, safe to delete
- [ ] Trained employees: **customers with orders cannot be deleted, use "deactivate" instead**

### 10.3 Batch Print
- [ ] **Delete local ZIP** promptly after printing
- [ ] Batch print audit log enabled (for "who printed what" later)

### 10.4 Auto-Start
- [ ] Docker Desktop "Start when log in" enabled
- [ ] Tested "reboot → erpilot auto-available" flow

### 10.5 Cumulative with Existing Checklists
- [ ] Completed **all** v3.25.10 → v3.38 checklists

---

**Version**: v3.39 (2026-05-21)
**Author**: erpilot Legal Team (internal)
**Corresponds to code**:
- `backend/app/agents/domains/polish_v339_tools.py` (7 LLM tools)
- `backend/app/services/print_service.py` (LOGO rendering)
- `backend/app/agents/engine.py` (slot-filling 3-strike fallback)
- `frontend-desktop/src/pages/Login.tsx` (backend offline guidance)
- `docker-compose.yml` (restart: unless-stopped)
- `install.bat` (K8 Docker auto-start guide)

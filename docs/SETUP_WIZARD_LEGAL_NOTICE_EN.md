# Setup Wizard / Day 0-7 Computer-Illiterate Fix — Legal & Compliance Notice (v3.37)

> **Document nature**: Compliance reminder for the install wizard, default password, auto-download, and proactive alerts. **Does not constitute legal advice.**
> Cumulatively applies to all §6 disclaimers in v3.25.10 → v3.37.
>
> **Chinese version**: [`SETUP_WIZARD_LEGAL_NOTICE_ZH.md`](./SETUP_WIZARD_LEGAL_NOTICE_ZH.md)

---

## ⚠️ Important: v3.37 fixes 14 "beginner blocker" issues

v3.37 covers:
- **Company master write** (PDF outbound documents' company name / tax ID / address / phone)
- **Password change** (critical to access control)
- **Default credentials admin/admin123** (must be replaced immediately)
- **Auto-download of PDF / Excel** (browser triggers file download automatically)
- **Proactive alerts** (overdue receivables / low stock / pending approvals)

Misuse may trigger:
- 🔴 PDF with wrong company name (contract dispute)
- 🔴 Default password not changed → security incident
- 🔴 Auto-download triggers browser warning (beginner thinks attacked)
- 🔴 False-positive alerts → wrong business decisions

**Use only under authorized review; complete §7 checklist before going live.**

---

## 1. Company Master (`set_company_info_with_confirm`)

### 1.1 Write takes effect immediately on PDFs

- After save, **all subsequent** PDFs (Quotation / PO / SO / Delivery Note) use the new info
- **Not retroactive**: previously generated PDFs retain old data

### 1.2 Taiwan Tax ID

- System does **basic format check only** (8 numeric digits) — does **not** verify legal validity
- Customer must self-verify; otherwise B2B invoices cannot be tax-deducted by buyer

### 1.3 Legal effect of company name / address

- PDF company name should be the **Ministry of Economic Affairs (MOEA) registered name**
- Using abbreviation / nickname instead of full name may be rejected by counterparty in disputes
- Name change should be authorized by an officer (Director / GM)

---

## 2. Default Password (admin/admin123)

### 2.1 Mandatory replacement

- First login shows warning toast: "You are using the default password"
- Login page shows hint: "⚠️ After login, change password immediately"
- install.bat / install.sh ending also says "change default password immediately"

### 2.2 Risk if not replaced

Industry-standard considers unchanged default passwords a basic security failure:
- 🔴 Unauthorized access by employees / visitors / interns
- 🔴 Violates PDPA Enforcement Rules Article 12 ("data security measures")
- 🔴 Violates ISO/IEC 27001, CMMI security requirements
- 🔴 Customers / suppliers may **refuse** business continuation after security audit

### 2.3 Password strength requirements

v3.37 enforces:
- Length ≥ 8 characters
- At least 1 letter + 1 digit
- Not a common password (admin123 / password / 12345678)

Stricter (recommended): ≥ 12 chars + mixed case + special chars.

---

## 3. Auto-Download PDF / Excel (v3.37 D1-2/D1-3)

### 3.1 Behavior

When LLM dialogue contains "print SO-001" / "export customers", the Chat component detects `pdf_base64` / `base64` in tool responses and auto-triggers browser download.

### 3.2 Browser Security

- Some browsers (Chrome / Edge) prompt **allow auto-download** on consecutive triggers
- Customer should guide users to **allow erpilot origin**
- If denied, user manually clicks the [Download PDF] link in the chat message

### 3.3 File handling

- Downloaded PDF / Excel contains **PII + trade secrets**
- Customer must follow v3.36 §2 file control after download

---

## 4. Proactive Alerts (`proactive_alerts`)

### 4.1 Detection logic (v3.37 default)

- **Overdue receivables**: SO `payment_status=unpaid` AND `order_date` > 30 days AND `status in (delivered/confirmed/shipped)`
- **Low stock**: Inventory `qty_on_hand` < Part `safety_stock`
- **Pending approval**: ApprovalRequestV2 `status=pending`

### 4.2 Limits

- Heuristic reminder — **not** a substitute for formal collection / purchase / approval flow
- Owner should **not** directly call to chase payment based solely on alert → consult accountant aging report first
- Does **not** handle: cross-year aging / partial payment / agreed deferrals

### 4.3 False positive risk

- If SO `payment_status` not updated in time (e.g. customer paid but system not recorded) → false alert
- Customer should **reconcile regularly** to keep `payment_status` accurate

---

## 5. Auto-Download & Security (Browser Layer)

### 5.1 Concept

- Auto-download **does not** equal "user-authorized download"
- If customer's IT policy (e.g. block downloading financial PDFs to local) conflicts → **disable** auto-download

### 5.2 How to disable

To disable:
- Frontend: remove `triggerAutoDownload(data.tool_calls)` call in `Chat.tsx`
- Backend: change LLM tool response's `pdf_base64` / `base64` to `null` (keep `download_url` for manual click)

---

## 6. Disclaimer (Cumulative v3.25.10 → v3.37)

To the maximum extent permitted by applicable law:

**1. Install Wizard**
erpilot's OnboardingWizard is a **functional guide**; not liable for business loss from customer entering wrong data or skipping the wizard.

**2. Default Password**
erpilot has **alerted** customer to change the default. erpilot is **not liable** for **any security incident, data leak, or contract dispute** arising from un-changed defaults.

**3. Company Master**
erpilot **does not validate** the **legal authenticity** of tax ID / company name / address; customer must self-verify consistency with MOEA registration.

**4. Auto-Download**
Auto-download is a **convenience feature**; customer must evaluate IT policy compatibility; post-download file handling is the customer's responsibility.

**5. Proactive Alerts**
`proactive_alerts` is a **heuristic reminder**; not a substitute for formal AR/AP aging, safety stock replenishment, or ECO/ECN; customer must **not** rely solely on alerts for major decisions.

---

## 7. Pre-Adoption Checklist (v3.37 reinforced)

Before adopting erpilot v3.37, please confirm:

### 7.1 D0 Install
- [ ] Ran install.bat / install.sh and saw "Installation Done"
- [ ] Browser auto-opened `http://localhost:5173`
- [ ] Docker image includes `fonts-noto-cjk` (print a sample Quotation PDF to verify Chinese)

### 7.2 D0 First login
- [ ] Logged in with admin/admin123 + saw warning toast
- [ ] **Immediately** in Chat: "change password MyN3wP@ssw0rd!"
- [ ] Logged out + logged back in with new password

### 7.3 D0 Company info
- [ ] In Chat: "company name is [Your Co.] tax id [8 digits]"
- [ ] Print a SO PDF → verify header shows new company name (not "erpilot 範例公司")

### 7.4 D1 First conversation
- [ ] Chat opens with "Hello! I'm erpilot AI assistant" greeting
- [ ] Click any example question → AI responds
- [ ] Say "print SO-XXX" → browser auto-downloads PDF (or prompts for permission)

### 7.5 D2-7 Business operations
- [ ] Say "add customer [Co. Name]" → ConfirmCard appears + auto-generated code CUS-####
- [ ] Say "list roles" → see Chinese role names
- [ ] Say "import Excel customer list" → 3-step flow shown
- [ ] Say "what should I watch today?" → proactive alerts shown

### 7.6 Pre-production compliance
- [ ] Completed **all** v3.25.10 → v3.36 checklists (PDPA / trade secrets / font licensing)
- [ ] **Officially replaced** default password (all employees included)
- [ ] **Established** outbound PDF **sign-off workflow**
- [ ] **Trained employees** on a 1-hour erpilot orientation

---

**Version**: v3.37 (2026-05-21)
**Author**: erpilot Legal Team (internal)
**Corresponds to code**:
- `backend/app/agents/domains/setup_wizard_tools.py`
- `backend/app/services/print_service.py` (company master integration)
- `backend/app/agents/domains/hard_write_tools.py` (customer auto-code)
- `backend/app/agents/domains/print_export_tools.py` (empty-items warning)
- `backend/Dockerfile` (Chinese fonts)
- `frontend-desktop/src/pages/{Login,Chat,Dashboard}.tsx`
- `install.bat`, `install.sh`

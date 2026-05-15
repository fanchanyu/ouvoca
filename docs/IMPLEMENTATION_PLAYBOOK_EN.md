# LLM-ERP Implementation Playbook (Consultant Edition · English) — v3.0

> **2-week go-live, day-by-day SOP**
> For implementation consultants / integrators / internal IT

> ⚡ **v3.0 Strategic Pivot Notice**: All "Mobile App / LINE Bot / Outsource QR" steps in Day 1-14 are skipped in v3.0.
> v3.0 deploys only: backend + frontend-desktop + PostgreSQL + Redis + MinIO (no Expo, no LINE Channel application).

---

## 📑 Contents

1. [Process Overview](#1-process-overview)
2. [Pre-Sales](#2-pre-sales)
3. [Day 1-2 Contract + Requirements](#3-day-1-2)
4. [Day 3-5 Environment Setup](#4-day-3-5)
5. [Day 6-7 Docker Install + Industry Samples](#5-day-6-7)
6. [Day 8-9 Customer Data Migration](#6-day-8-9)
7. [Day 10 Admin Training](#7-day-10)
8. [Day 11-12 Department Heads Training](#8-day-11-12)
9. [Day 13 Internal Pilot](#9-day-13)
10. [Day 14 Go-Live](#10-day-14)
11. [30-Day Hyper-care](#11-30-day-hyper-care)
12. [Common Pitfalls](#12-common-pitfalls)

---

## 1. Process Overview

```
Pre-Sales        Implementation (2 weeks)         Hyper-care (30 days)
─────────  ────────────────────────────────────  ──────────────────
Requirements    Day 1-2 Contract + Interview       Weekly visits
PoC trial       Day 3-5 Environment                Log monitoring
Quote           Day 6-7 Install + Demo data        Immediate hotfix
Sign            Day 8-9 Customer data migration    Month-end review
                Day 10  Admin training (2h)
                Day 11-12 Dept training (5×1h)
                Day 13 Pilot
                Day 14 Go-live
```

**Core KPI**: 30 days post go-live, DAU/total users ≥ 60%.

---

## 2. Pre-Sales

### 2.1 Requirements Questionnaire (12 questions)

Fill before visiting the customer:

```
Company Info
─ Headcount: _____ 
─ Industry: metal / plastic / PCB / food / textile / other ____
─ Revenue: NT$ _____ M / year
─ Customer count: _____ Major customers: _____
─ Supplier count: _____ Major suppliers: _____
─ Multi-factory: yes / no   Sites: _____

Pain Points (multi-select)
□ ERP too expensive
□ Inventory out of sync
□ Owner waits days for numbers
□ Outsource collaboration hard
□ Sales can't get real-time stock
□ Employees can't use existing system
□ Other: _____

Digital Status
─ Current tools: Excel / SAP / Custom / None
─ Monthly IT budget: NT$ _____
─ Has IT staff: yes / no
─ Uses LINE groups: yes / no
─ Willing to deploy LINE Bot: yes / no
```

### 2.2 14-Day PoC

- Send install package + INSTALLATION_EN.pdf
- Customer runs `install.bat` → Demo Mode
- Consultant follows up via LINE every 3 days
- Day-12: 30-min review call

---

## 3. Day 1-2 Contract + Interview

### Contract Checklist

- [ ] Contract version: v_____
- [ ] Subscription plan: Basic / Pro / Enterprise
- [ ] Annual fee confirmed
- [ ] One-time setup fee confirmed
- [ ] Payment: 50% prepaid / 50% on go-live
- [ ] SLA tier: 8h / 2h / 1h
- [ ] Add-ons: customization / extra training / etc.

### Day 2 Requirements Interview (4 hours on-site)

Interview these roles:

| Role | Duration | Key Questions |
|---|---|---|
| Owner | 30 min | Top 3 numbers you care about? What do you usually ask LINE? |
| Sales head | 30 min | Most embarrassing moment in front of customer? |
| Plant manager | 30 min | Where do orders most often get stuck? |
| Procurement head | 30 min | How do you track material delays? |
| Warehouse | 30 min | How do you stocktake? How often? |
| IT (if any) | 60 min | Hardware / network / backup status? |
| Accounting | 30 min | Month-end close date? Invoice flow? |

**Record** the interview (with consent). Produce a **Requirements Confirmation Doc** within 24 hours.

---

## 4. Day 3-5 Environment Setup

### 4.1 Hardware/Cloud Decision Tree

```
Q1: Do they have their own server?
  → Yes → Q2
  → No → Managed cloud (GCP/AWS/Azure)
  
Q2: Is the spec sufficient? (4-core / 8GB / 100GB SSD)
  → Yes → Self-host → Q3
  → No → Upgrade or cloud
  
Q3: Have IT staff?
  → Yes → Hand off to customer's IT
  → No → Our engineer remote pairing
```

### 4.2 Deployment Checklist

- [ ] Hardware / VM meets spec
- [ ] OS: Linux Server (recommend Ubuntu 22.04+)
- [ ] Docker 24+ installed
- [ ] Firewall: port 5173/8000 open on intranet
- [ ] Public access (if LINE Bot): Cloudflare Tunnel configured
- [ ] Domain (if self-hosted SaaS): DNS A record set

### 4.3 Customer Account Provisioning

- [ ] Default admin account (password changed at onboarding)
- [ ] Open accounts for: owner / sales head / plant mgr / procurement / warehouse
- [ ] Confirm LINE group includes our support bot

---

## 5. Day 6-7 Docker Install + Industry Samples

### Day 6 Standard Install (<2 hours)

```bash
cd /opt/llm-erp
git clone https://github.com/your-org/llm-erp.git
cd llm-erp
cp backend/.env.example backend/.env
# Edit .env: JWT_SECRET, LLM_API_KEY, DATABASE_URL (if not SQLite)
docker compose up -d --build
```

After completion, health check:

```bash
curl http://localhost:8000/api/health | jq
# Should see status=ok, db=ok
```

### Day 7 Load Industry Samples

Pick by customer's industry:

```bash
docker compose exec backend python -m scripts.seed_industries metal
# or plastic / pcb / food / textile / all
```

**On-site demo** with customer:
- Login to desktop UI
- Show Dashboard 4 stat cards
- Click "Inventory" to see sample parts
- Try AI chat: "Today's factory status"

---

## 6. Day 8-9 Customer Data Migration

### Migration Priority

```
🟢 Mandatory (affects go-live)
  1. Employees + departments + roles (with RBAC)
  2. Customers (at least top 20)
  3. Suppliers (at least top 20)
  4. Parts + BOM (core 30 items)

🟡 Can defer (after go-live)
  5. Full customer list
  6. Full parts list
  7. Historical orders (last 3 months)
  8. Historical inventory transactions
```

### Migration Tools

Excel templates (under `templates/`):
- `import_employees.xlsx`
- `import_customers.xlsx`
- `import_suppliers.xlsx`
- `import_parts.xlsx`
- `import_bom.xlsx`

Run:

```bash
docker compose exec backend python -m scripts.import_excel employees.xlsx
```

### Data Quality Check

Always run after migration:

```bash
docker compose exec backend python -m scripts.data_quality_check
# Outputs: orphan records / duplicate master data / abnormal BOM
```

---

## 7. Day 10 Admin Training (2 hours)

Audience: customer's IT lead / system administrator

### Agenda

| Time | Content |
|---|---|
| 30 min | System architecture in 30 seconds (SYSTEM_TOPOLOGY) |
| 30 min | RBAC 5 layers + account/permission management |
| 30 min | Monitoring / backup / upgrade SOP |
| 30 min | Q&A + troubleshooting drill |

### Five Must-Teach Items

1. **Account management** — add / disable / change permission
2. **Data backup** — `docker compose exec backend cp /app/erp.db /tmp/backup.db`
3. **Read logs** — `docker compose logs -f backend | grep ERROR`
4. **Upgrade** — `git pull && docker compose up -d --build`
5. **Emergency restart** — `docker compose restart`

### Materials

- `docs/ADMIN_GUIDE.md` (full admin guide)
- `docs/SUPPORT_RUNBOOK_EN.md` (incident handling)

---

## 8. Day 11-12 Department Heads Training (5 × 1 hour)

### Recommended Schedule

| Slot | Audience | Focus |
|---|---|---|
| Day 11 09:00 | Owner | LINE Bot + Dashboard numbers |
| Day 11 14:00 | Sales head | Mobile inventory lookup + quotes + AI |
| Day 11 16:00 | Plant manager | Mobile WO + push notification setup |
| Day 12 09:00 | Procurement head | Desktop PO + mobile QR receiving |
| Day 12 14:00 | Warehouse | Mobile stocktake + transfer |

### Owner Training (most critical 60 minutes)

```
00:00  Add LINE OA + bind account (10 min)
00:10  Try "today's status" live (5 min)
00:15  Dashboard 4 numbers meaning (15 min)
00:30  Red alert intro (5 min)
00:35  Demo 5 frequent questions (15 min)
00:50  Q&A + add to LINE group (10 min)
```

---

## 9. Day 13 Internal Pilot

### Pilot Checklist

- [ ] All employees can log in
- [ ] Each department completes at least 1 real-world operation
- [ ] AI assistant: at least 5 successful interactions
- [ ] Mobile app: at least 3 installs
- [ ] Owner LINE Bot interactions ≥ 5
- [ ] Any bug / friction → immediate logging

### Issue Tracking

| Time | Reporter | Issue | Handler | Status |
|---|---|---|---|---|
| | | | | |

---

## 10. Day 14 Go-Live

### Go-Live Ceremony

09:00 All-hands (video or onsite):
- Owner's 1-minute speech
- Consultant demos "today's AI ask" for 5 minutes
- Immediately switch to LLM-ERP (no more legacy / Excel)

### Day-14 Must-Do

- [ ] Run `bash scripts/run_gates.sh`, confirm all green
- [ ] Confirm all employees notified of go-live
- [ ] Customer IT confirms backup schedule active
- [ ] Consultant standby 4 hours for issues
- [ ] Collect 50% remaining payment

---

## 11. 30-Day Hyper-care

### Week 1 (high attention)

- Daily LINE group check-in
- Daily check `GET /api/analytics/summary` for usage
- Any bug patched within 24h

### Week 2-3 (transition)

- Check-in every 3 days
- Interview 3 individual employees: "What's still painful?"
- Tune RBAC permissions

### Day-30 Review

Bring this report to owner:

```
┌─────────────────────────────────────┐
│ LLM-ERP 30-Day Review               │
├─────────────────────────────────────┤
│ • Total users _____ / Active _____  │
│ • DAU avg _____ (target 60%)        │
│ • AI chats: _____ times             │
│ • Mobile adoption: _____ %          │
│ • Bugs found and fixed: _____       │
│ • Customer NPS (10-point): _____    │
│ • Top 3 priorities next month:      │
│   1. _________                      │
│   2. _________                      │
│   3. _________                      │
└─────────────────────────────────────┘
```

---

## 12. Common Pitfalls

| Pitfall | Prevention |
|---|---|
| Customer won't submit data | Lock "submit by Day 8" into contract |
| Owner not interested in LINE | Day 11 owner uses LINE live with consultant |
| Employees resist | Send USER_MANUAL.pdf + tutorial videos beforehand |
| Network issues | Test `curl from phone` before Day 5 |
| Firewall blocks LLM API | Test `/api/chat-v2` before Day 3 |
| Pilot bugs | Day 13 must be thorough |
| No usage after go-live | Owner attendance Day 14 mandatory |

---

**Chinese version**: [`IMPLEMENTATION_PLAYBOOK_ZH.md`](./IMPLEMENTATION_PLAYBOOK_ZH.md)
**Last updated**: 2026-05-14 · v2.5

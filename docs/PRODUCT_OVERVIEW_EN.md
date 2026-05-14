# LLM-ERP Product Overview (English)

> **One-page snapshot → Full buying guide for decision makers**
> Audience: Owners / Procurement managers / IT directors / System integrators / Consultants

---

## 📑 Contents

1. [One-Page Snapshot](#1-one-page-snapshot)
2. [Product Positioning](#2-product-positioning)
3. [12 Core Modules](#3-12-core-modules)
4. [Key Differentiators](#4-key-differentiators)
5. [Technical Spec](#5-technical-spec)
6. [Deployment Options](#6-deployment-options)
7. [Integration Capabilities](#7-integration-capabilities)
8. [Security & Compliance](#8-security--compliance)
9. [Onboarding Process & Timeline](#9-onboarding-process--timeline)
10. [Service & Support](#10-service--support)
11. [Procurement FAQ](#11-procurement-faq)
12. [Competitive Comparison](#12-competitive-comparison)
13. [How to Buy](#13-how-to-buy)

---

## 1. One-Page Snapshot

| Item | Detail |
|---|---|
| **Product** | LLM-ERP (AI-Native ERP for SMB Manufacturers) |
| **Positioning** | The **LINE-Native ERP** for 50-100 person factories |
| **Core Promise** | The owner runs the factory from LINE; live in 2 weeks, productive in 2 hours |
| **Three Weapons** | ① Natural language ops ② Mobile-first ③ Outsource LINE collaboration |
| **Tech Foundation** | FastAPI + PostgreSQL/SQLite + Multi-Agent LLM + React/Expo |
| **Deployment** | One-click Docker, self-host / cloud / MESH multi-factory |
| **Language** | Traditional Chinese + English (full i18n) |
| **Devices** | Desktop browser + iOS app + Android app + LINE Bot |
| **Onboarding Time** | < 2 weeks (vs SAP 6-18 months) |
| **Training / employee** | < 2 hours (vs traditional 1-3 months) |
| **Typical Price** | NT$ 300K-500K / year (vs SAP NT$ 2M+) |

**In one sentence**: We collapse "6-month rollout, 3-month training" pain into "2 weeks live, 2 hours productive" by letting **AI translate the system for users**.

---

## 2. Product Positioning

### 2.1 Ideal Customer Profile (ICP)

| Dimension | Range |
|---|---|
| **Headcount** | 50-100 people (often 10-20 in-house + outsource chain) |
| **Industry** | Metal machining / Plastic injection / PCB / Food / Textile dyeing |
| **Revenue** | NT$ 100M-1B / year |
| **Digital maturity** | Low-to-mid (still on Excel + LINE groups) |
| **IT budget** | NT$ 300K-1M / year |
| **Owner role** | Reads numbers personally, no dedicated IT department |

### 2.2 Five Typical Users (Persona)

| Role | Daily Scene | Primary Device |
|---|---|---|
| **Owner (Mr. Wang)** | 06:30 asks LINE "today's status" → gets one-page dashboard | LINE |
| **Salesperson (Chen)** | In customer's office, looks up M6 stock on phone, quotes in 3s | Phone |
| **Plant Manager (Lin)** | On factory floor, gets push notification "WO-2026-100 stuck" | Phone + LINE |
| **Buyer/Warehouse (Ling)** | Scans QR on incoming carton, inventory auto-increments | Phone (scan) |
| **Outsource Master (Wu)** | LINE receives drawing, snaps photo to report progress, no registration | LINE |

### 2.3 Pains We Solve

| Customer Voice | Our Solution |
|---|---|
| "ERP is too expensive, we can't afford SAP" | Open-source core + NT$ 300K/year subscription |
| "6-month rollout? Who can endure that?" | Docker one-click + natural language → live in 2 weeks |
| "Training employees is hell" | LINE + AI chat interface → no system to learn |
| "Inventory out of sync, sales quote wrong stock" | Live DB + SSE push + 3-second mobile query |
| "Outsource shops can't see our progress" | LINE QR + Bot reporting → no registration needed |
| "Boss wants live numbers, not month-end reports" | LINE Bot real-time dashboard |
| "We only notice missing parts when it's too late" | EventBus proactive alerts |

---

## 3. 12 Core Modules

Each domain has a complete RESTful API + desktop UI + mobile UI + natural-language interface.

| # | Domain | Key Features | Primary Users |
|---|---|---|---|
| 1 | **Inventory** | Parts / BOM / Transactions / Safety stock alerts / Multi-warehouse | Warehouse + Sales |
| 2 | **Purchase** | Supplier tiering (T1-T3) / PO / Receiving / 3-way match / Auto AP | Buyer |
| 3 | **Sales** | Customer / Quote / SO / Shipment / Auto AR | Sales + Owner |
| 4 | **Production** | Work orders / BOM explode / Dispatch / Reporting / OEE | Plant Mgr + Operator |
| 5 | **Quality** | Inspection / Non-conformance / CAPA / Customer complaints | QC + QA |
| 6 | **Warehouse** | Multi-warehouse / Barcode count / Transfer / Auto replenishment | Warehouse |
| 7 | **MPS/MRP** | Master schedule / Material req planning / Simplified for SMB | Planner + Plant Mgr |
| 8 | **Accounting** | AR / AP / Month-end close / Auto journals | Finance |
| 9 | **CRM** | Lead → Opportunity → Customer funnel + Visit log | Sales |
| 10 | **HR** | Employee / Department / Role / Training | HR + Manager |
| 11 | **AI Governance** | DecisionLog (auditable AI calls) / Model switching | IT + Audit |
| 12 | **Permission** | RBAC 5 layers / 109 perms / 11 roles / Row-Level filter | IT + Owner |

### 3.1 Cross-Domain Intelligence

- **Multi-Agent AI**: 10 specialist agents (Inventory / Sales / Production / Quality / Purchase / Planning / Warehouse / Accounting / CRM / General) + 26 tools
- **EventBus**: 16 Constraint Rules auto-fire across domains (e.g. "PO approved" → notify supplier + warehouse)
- **MESH Multi-Factory**: Cross-factory inventory aggregation / VMI (raw data stays in each factory)
- **SSE Live Push**: Inventory changes, WO status, AI alerts reach users in sub-second

---

## 4. Key Differentiators

### 4.1 Natural Language Operation (Killer Feature #1)

```
Owner types: "Today's factory status"
↓
IntentClassifier → ProductionAgent
↓
Tool call: query_today_summary
↓
Reply: 12 WOs today (8 in-progress), 3 items below safety stock,
       5 shipments on track 95%
```

**Contrast**: Traditional ERP requires 7 menu clicks + 3 reports for the same info.

### 4.2 Mobile-First Design

| Principle | Realization |
|---|---|
| Mobile-first | 5 tabs, big buttons, minimal typing |
| 3-tap rule | Any function ≤ 3 taps |
| Offline degrade | AsyncStorage caches token + basic data |
| Large fonts | Readable outdoor by owner / plant manager |
| One-hand reach | Key actions in thumb zone |

### 4.3 Outsource LINE Collaboration (Industry First)

```
HQ → Via LINE Bot sends drawing + process + one-time QR token
       ↓
Outsource master (no registration in any system) → opens LINE → scans QR
       ↓
Reports "80% complete" + photo
       ↓
HQ work order auto-updates / EventBus triggers QC notification
```

**Industry pain**: Traditional ERPs require outsource shops to register / learn new software. Masters refuse.
**Our solution**: Outsource shops **don't register** at all. If they use LINE, they can use this.

### 4.4 MESH Multi-Factory Data Sovereignty

```
HQ ── WireGuard VPN ──┐
                       ├── Main Factory (A) :8001
                       ├── Plating Outsource (B) :8002
                       ├── Inspection Outsource (C) :8003
                       └── Nth Outsource

HQ asks "Total M6 across all factories?" →
  • HQ parallel-fans to N factories /api/factory/mesh/query
  • Each factory returns only its own aggregated sum (no raw rows)
  • HQ totals: 3000 + 1500 + 800 = 5300

★ HQ NEVER sees "which batch, who bought it"
★ Integration test 5/5 PASS — not a stub, actually works
```

---

## 5. Technical Spec

### 5.1 System Requirements

| Resource | Min | Recommended |
|---|---|---|
| **CPU** | 2 core | 4 core |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 20 GB SSD | 100 GB SSD |
| **OS** | Win 10 / Mac / Linux | Linux Server |
| **Docker** | 20.10+ | 24+ |
| **Network** | 100 Mbps LAN | 1 Gbps |
| **Public access** | HTTPS (LINE Bot only) | Cloudflare Tunnel free tier |

### 5.2 Backend Stack

| Layer | Tech |
|---|---|
| Web | FastAPI (Python 3.12+) async |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL 15+ / SQLite (sufficient for SMB) |
| Migration | Alembic |
| Auth | JWT (HS256) + RBAC 5-layer |
| Real-time | Server-Sent Events (SSE) |
| LLM Adapter | Claude / DeepSeek / OpenAI / Ollama (pluggable) |
| Container | Docker Compose |

### 5.3 Frontend Stack

| Surface | Tech |
|---|---|
| **Desktop UI** | React 18 + Vite + Tailwind + Zustand + TypeScript strict |
| **Mobile App** | Expo SDK 51 + React Native + expo-router |
| **LINE Bot** | LINE Messaging API + Webhook (planned) |
| i18n | Custom lightweight (zh-TW + en) |

### 5.4 Performance Targets

| Operation | Target latency | Measured |
|---|---|---|
| Health check | < 100 ms | ~20 ms |
| Login | < 500 ms | ~200 ms |
| List query (<1000 rows) | < 1 s | ~300 ms |
| AI chat (simple) | < 5 s | 2-5 s (LLM-dependent) |
| AI chat (multi-step tool) | < 30 s | 6-15 s |
| MESH aggregate (3 factories) | < 3 s | ~500 ms |
| SSE push latency | < 2 s | < 1 s |

### 5.5 Scale Limits (Single Instance)

| Dimension | Limit |
|---|---|
| Concurrent users | 100-200 |
| Requests / sec | 200-500 RPS |
| Inventory parts | 100,000 |
| Work orders | 100,000 / year |
| Conversation log | 1,000,000 entries |
| MESH nodes | 10-20 |

> Beyond this scale, recommend factory-distributed + MESH aggregation.

---

## 6. Deployment Options

### 6.1 Four Modes

```
Mode A: Single-machine Docker  (simplest, 50-person factory)
├── HQ backend + Desktop UI + DB all on one box
└── One-click install.bat / install.sh

Mode B: Managed cloud  (for factories without IT)
├── We host on GCP/AWS/Azure
├── Customer sees only https://your-company.llm-erp.app
└── Monthly fee covers host + backup + upgrade

Mode C: Customer self-host  (data sovereignty)
├── Customer buys VM / on-prem server
├── We provide Docker image + deployment guide
└── Customer's IT maintains

Mode D: MESH multi-factory  (group / multi-site owners)
├── HQ + N Factory Nodes
├── WireGuard VPN mesh
├── Each factory's data stays on-site
└── HQ sees aggregates only
```

### 6.2 Install Time

| Mode | First install | Customer does |
|---|---|---|
| A — Single Docker | **10 min** | Double-click install.bat |
| B — Managed cloud | **Next day live** | Fill form + pay |
| C — Self-host | 0.5-1 day | Remote pairing with our engineer |
| D — MESH | 1-3 days / factory | Install per factory + setup VPN |

---

## 7. Integration Capabilities

### 7.1 Outbound Integrations

| Target | Method | Purpose |
|---|---|---|
| **LINE** | Messaging API + Bot Webhook | Owner dashboard / outsource reporting |
| **Excel** | CSV / xlsx export | Owners prefer Excel |
| **Email** | SMTP (SendGrid-compatible) | PO PDF / reports |
| **3rd-party ERP** | REST API + Webhook | Upstream customer / group |
| **Customs / Gov** | Reserved interface | Export / customs filing |

### 7.2 LLM Providers (Pluggable)

| Provider | Best For | Monthly Cost (50p) |
|---|---|---|
| **Anthropic Claude** | International brand orders, strictest | NT$ 3,000-8,000 |
| **OpenAI GPT-4o** | Industry standard | NT$ 2,500-6,000 |
| **DeepSeek** | Chinese context, best ROI | NT$ 800-2,000 |
| **Ollama local (gemma3 / qwen2.5)** | **Zero data egress** | **NT$ 0** (one-time hardware) |

Switching LLM = edit one `.env` line + restart. See [LLM Benchmark Report](./LLM_BENCHMARK_REPORT_EN.md).

---

## 8. Security & Compliance

### 8.1 Security Architecture

| Layer | Mechanism |
|---|---|
| **AuthN** | JWT (HS256) + bcrypt password hash |
| **AuthZ** | RBAC 5-layer (Tenant→User→Role→Permission→Row-Level) |
| **Audit** | AuditMiddleware logs all requests + DecisionLog (AI calls) |
| **Transport** | HTTPS (nginx / Cloudflare Tunnel) |
| **Multi-factory** | WireGuard VPN + factory VLAN |
| **Secrets** | `.env` + HashiCorp Vault recommended (enterprise) |
| **Demo bypass** | Active only when JWT_SECRET is default; auto-disables in production |

### 8.2 Data Sovereignty

- **MESH multi-factory mode**: Raw rows **physically** stay in each factory's SQLite/PostgreSQL
- HQ can only call `/api/factory/aggregate` for aggregated numbers
- Integration test verified: aggregate response contains **none** of `created_at` / `qty_available` / `items` / `rows`

### 8.3 Compliance Readiness

| Standard | Status |
|---|---|
| GDPR (right to erasure) | API endpoint reserved, customer enables |
| ISO 27001 | Documentation 70% complete, requires 3rd-party audit |
| China PIPL | Can deploy to China DC (DeepSeek/Ollama) |
| HIPAA | Healthcare requires custom encryption |

---

## 9. Onboarding Process & Timeline

### 9.1 Standard Rollout (2-Week Model)

```
Day 1-2   Contract + Requirements interview
Day 3-5   Environment prep (server / accounts / network)
Day 6-7   Docker install + industry-sample data load
Day 8-9   Customer data import (from Excel)
Day 10    Admin training (2 hours)
Day 11-12 Department head training (5 roles × 1 hour)
Day 13    Internal pilot
Day 14    Go-live
```

### 9.2 Extended Rollout (Multi-factory MESH, 4-6 weeks)

Additional: per-factory install, WireGuard VPN setup, cross-factory permissions, aggregation tests.

### 9.3 Training Hours

| Role | Hours |
|---|---|
| Owner / Plant Mgr | **1 hour** (LINE-based) |
| Sales / Buyer | **2 hours** (incl. mobile app) |
| Warehouse / Operator | **3 hours** (incl. barcode scan) |
| IT Admin | **1 day** (incl. RBAC + deployment) |

> Compare with industry-average 1-3 months for SAP.

---

## 10. Service & Support

### 10.1 Service Level Agreements

| Tier | Response Time | Applicable |
|---|---|---|
| **Basic** | Business day, 8h | Standard subscription |
| **Pro** | Business day, 2h | Add-on |
| **24/7** | Anytime, 1h | Enterprise |

### 10.2 Support Channels

- Internal IT / integrator
- Monthly online training
- LINE customer support group
- Emergency phone (Pro+)
- Remote TeamViewer assist (Pro+)

### 10.3 Upgrade & Maintenance

- **Minor**: Monthly, auto-built + customer clicks upgrade
- **Major**: Quarterly, new features + training session
- **Data migration**: Auto migration test across major versions

---

## 11. Procurement FAQ

### Q1: Why so much cheaper than SAP / Oracle?

**Because we don't charge license fees**. SAP's NT$ 2M is mostly "license" + "implementation consultant". We're open-source core + subscription (annual fee). Customers buy subscription + service, not "ownership of software".

### Q2: Isn't open-source risky?

No. LLM-ERP is a commercial project; **open-source core** lets customers: ① see the code ② leave anytime without lock-in ③ find someone else to maintain. **Our value is in service**, not in trapping customers.

### Q3: Is our data safe?

Four layers of protection:
1. **Architectural**: MESH mode keeps data in each factory
2. **Transport**: HTTPS + WireGuard VPN
3. **Storage**: bcrypt passwords + optional disk encryption
4. **Audit**: AuditMiddleware logs all + DecisionLog

Can choose Ollama local LLM for **zero data egress**.

### Q4: Can we customize?

Yes, three ways:
- **Configuration**: change settings via admin UI (free)
- **Extension**: write new domain / agent / tool (consulting fee)
- **Core modification**: open source so you can fork (manage your own fork)

### Q5: What if your company goes under?

Open-source core continues to work; data is in customer's hands. Any Python engineer can maintain it (widespread stack). MESH mode means factory data is fully self-owned, even safer.

### Q6: Payment terms?

- Annual (standard)
- Quarterly (+10%)
- One-time license (self-host mode only, ≈ 3× annual)

### Q7: Can we try first?

Yes. **Demo Mode 14-day free trial**, no signup:
1. Double-click `install.bat`
2. Click "Demo Mode" button
3. Use sample data to explore everything

### Q8: Do you have training materials?

Complete set:
- User Manual (ZH/EN)
- Installation Guide (ZH/EN)
- System Architecture (ZH/EN)
- LLM Benchmark Report (ZH/EN)
- Network Deployment Plan (ZH/EN)
- Video tutorials (planned)

All exportable to PDF (`build_pdfs.bat`).

---

## 12. Competitive Comparison

### 12.1 Three Solutions

| Dimension | SAP Business One | Odoo Enterprise | **LLM-ERP** |
|---|---|---|---|
| **License / year** | NT$ 1-2M | NT$ 300-800K | **NT$ 300-500K** |
| **Rollout time** | 6-18 months | 2-4 months | **< 2 weeks** |
| **Training / employee** | 1-3 months | 2-4 weeks | **< 2 hours** |
| **Mobile UX** | Weak (legacy UI) | Mid (responsive) | **Strong (native app)** |
| **AI natural language** | None | None | **Core feature** |
| **LINE Bot integration** | Custom | Custom | **Built-in** |
| **Outsource LINE collab** | None | None | **Industry first** |
| **Multi-factory sovereignty** | Centralized | Centralized | **MESH** |
| **Customization** | Low (closed) | Mid (open) | **High (open + AI)** |

### 12.2 Why Not Just Excel?

| Scenario | Excel | LLM-ERP |
|---|---|---|
| Owner asks "today's status" | Flip 5 sheets | One sentence reply |
| Sales checks stock | Open front desk PC | 3-second mobile |
| Real-time sync | Impossible | SSE push |
| Outsource collaboration | Chaotic LINE group | QR + auto-update |
| Audit trail | None | AuditMiddleware full log |

---

## 13. How to Buy

### 13.1 Purchase Process

```
Step 1  Download and install → Demo Mode trial (14 days)
Step 2  Fill requirements form (industry / size / customization)
Step 3  Our consultant 30-min requirements interview
Step 4  Quote (annual fee + one-time implementation)
Step 5  Sign + 50% prepayment
Step 6  Day 1 onboarding starts
Step 7  Day 14 go-live + final payment
```

### 13.2 Contact

| Need | Contact |
|---|---|
| Trial issues | LINE @llmerp |
| Sales inquiry | sales@llm-erp.example |
| Tech support | support@llm-erp.example |
| Integrator partnership | partners@llm-erp.example |

---

## 📎 Related Documents

- [Installation Guide (English)](./INSTALLATION_EN.md) / [中文](./INSTALLATION_ZH.md)
- [User Manual (English)](./USER_MANUAL_EN.md) / [中文](./USER_MANUAL_ZH.md)
- [System Architecture & Topology](./SYSTEM_TOPOLOGY_EN.md) / [中文](./SYSTEM_TOPOLOGY_ZH.md)
- [LLM Benchmark Report](./LLM_BENCHMARK_REPORT_EN.md) / [中文](./LLM_BENCHMARK_REPORT_ZH.md)
- [Network Deployment Plan](./NETWORK_DEPLOYMENT_EN.md) / [中文](./NETWORK_DEPLOYMENT_ZH.md)
- **Chinese version**: [`PRODUCT_OVERVIEW_ZH.md`](./PRODUCT_OVERVIEW_ZH.md)

---

**Version**: 2.3 · **Last updated**: 2026-05-14 · **© 2026 LLM-ERP Project**

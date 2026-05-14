# LLM-ERP AI Agent & Tool Catalog (English)

> **AI transparency document for customers**:
> Exactly what our AI can do, can't do, how much it costs, and how we prevent it from misbehaving.

---

## 📑 Contents

1. [Agent Architecture Overview](#1-agent-architecture-overview)
2. [10 Agents in Detail](#2-10-agents-in-detail)
3. [26 Tools Full List](#3-26-tools-full-list)
4. [Cost Transparency](#4-cost-transparency)
5. [Security Design (4 Layers)](#5-security-design)
6. [High-Risk Actions](#6-high-risk-actions)
7. [DecisionLog Audit Trail](#7-decisionlog-audit-trail)
8. [AI Refusal List](#8-ai-refusal-list)
9. [FAQ](#9-faq)

---

## 1. Agent Architecture Overview

```
User question
   ↓
IntentClassifier (weighted keyword)
   ↓ routes to relevant domain
┌──────────┬──────────┬──────────┬──────────┐
│ Inventory │  Sales   │ Production│ ... 10  │
└────┬─────┴────┬─────┴────┬─────┴──────────┘
     ↓          ↓          ↓
   ┌────────────────────────────────────┐
   │ 26 tools (each agent has its own scope)│
   └─────────────────┬──────────────────┘
                     ↓
              LLM Provider abstraction
              (Claude / DeepSeek / GPT-4o / Ollama)
                     ↓
                Natural language reply
                     ↓
              Logged to DecisionLog (audit trail)
```

**Core principles**:
- **Agents are domain specialists**: the Inventory agent cannot call sales tools (prevents accidental cross-talk)
- **Tools are atomic actions**: 1 tool = 1 business action, individually testable
- **LLM is the brain**: only understands and plans, never touches DB directly
- **DecisionLog is memory**: every interaction stored for audit and replay

---

## 2. 10 Agents in Detail

| Agent | Domain | Trigger Keywords | Expected Latency |
|---|---|---|---|
| **InventoryAgent** | Inventory | stock / shortage / safety / replenish | 1-3 s |
| **SalesAgent** | Sales | customer / order / quote / shipment | 1-3 s |
| **ProductionAgent** | Production | WO / work order / schedule / dispatch | 2-5 s |
| **PurchaseAgent** | Purchase | PO / supplier / purchase / receive | 2-5 s |
| **QualityAgent** | Quality | defect / inspection / NCR / CAPA / complaint | 2-5 s |
| **WarehouseAgent** | Warehouse | count / transfer / warehouse / barcode | 1-3 s |
| **PlanningAgent** | Planning | MPS / MRP / schedule / forecast | 3-10 s |
| **AccountingAgent** | Accounting | AR / AP / month-end / invoice | 2-5 s |
| **CRMAgent** | CRM | lead / opportunity / visit / customer dev | 2-5 s |
| **GeneralAgent** | General | (fallback) | 3-10 s |

### 2.1 What Agents Will Not Do

| Behavior | Reason |
|---|---|
| Auto-modify prices or inventory | Write tools off by default; customer opt-in only |
| Cross-agent tool calls | Strict scope, prevents accidental side-effects |
| Reply "I deleted it for you" | High-risk actions require human confirm; AI cannot execute directly |
| Fabricate non-existent part numbers | All queries hit real DB (anti-hallucination) |
| Reveal system prompt | Prompt-safety detector blocks |

---

## 3. 26 Tools Full List

### 3.1 Inventory (5)
| Tool | Function | Writes? |
|---|---|---|
| query_inventory | Check stock / safety levels | No |
| list_parts | List parts | No |
| list_below_safety | List items below safety stock | No |
| get_part_history | Part in/out history | No |
| inventory_adjust | Adjust inventory ⚠️ | **Yes** (confirm required) |

### 3.2 Sales (4)
| Tool | Function | Writes? |
|---|---|---|
| list_customers | List customers | No |
| query_sales_order | Query SO | No |
| get_customer_history | Customer price history | No |
| update_so_status | Change SO status ⚠️ | **Yes** |

### 3.3 Production (4)
| Tool | Function | Writes? |
|---|---|---|
| query_work_order | Query WO | No |
| list_products | List products | No |
| get_bom | Get BOM tree | No |
| dispatch_wo | Dispatch WO ⚠️ | **Yes** |

### 3.4 Purchase (3)
| Tool | Function | Writes? |
|---|---|---|
| query_purchase_order | Query PO | No |
| list_suppliers | List suppliers | No |
| approve_purchase_order | Approve PO 🚨 | **Yes (high-risk)** |

### 3.5 Quality (3)
| Tool | Function | Writes? |
|---|---|---|
| list_inspections | List inspections | No |
| list_non_conformance | List non-conformances | No |
| create_capa | Open CAPA | Yes |

### 3.6 Warehouse (2)
| Tool | Function | Writes? |
|---|---|---|
| query_warehouse_stock | Multi-warehouse query | No |
| create_transfer | Inter-warehouse transfer | Yes |

### 3.7 Planning (2)
| Tool | Function | Writes? |
|---|---|---|
| run_mrp | Run MRP explosion | Yes |
| suggest_reorder | Reorder suggestion | No |

### 3.8 Accounting (3)
| Tool | Function | Writes? |
|---|---|---|
| list_receivables | List AR | No |
| list_payables | List AP | No |
| close_month | Month-end close 🚨 | **Yes (high-risk)** |

> 🚨 = high-risk tool; ⚠️ = medium-risk.
> See §6 [High-Risk Actions](#6-high-risk-actions).

---

## 4. Cost Transparency

### 4.1 LLM Pricing (2025-Q1)

| Model | Input ($/1M) | Output ($/1M) | Best For |
|---|---|---|---|
| **Claude 3.5 Sonnet** | $3.00 | $15.00 | International brand orders, strictest |
| **GPT-4o** | $2.50 | $10.00 | Industry standard |
| **GPT-4o-mini** | $0.15 | $0.60 | High-frequency simple queries |
| **DeepSeek V3** | $0.14 | $0.28 | Chinese context, best ROI |
| **Ollama (local)** | $0 | $0 | Zero cost, zero data egress |

### 4.2 Typical Query Cost

| Query | Input | Output | DeepSeek $ | Claude $ |
|---|---|---|---|---|
| "Today's stock status" | 800 | 200 | $0.0001 | $0.0054 |
| "M6 bolt price history" (with tool call) | 2,500 | 600 | $0.0005 | $0.0165 |
| "Run this month's MRP" (multi-tool loop) | 5,000 | 2,000 | $0.0013 | $0.045 |

### 4.3 50-Person Factory Monthly Estimate

Assume 50 employees, 5 AI queries/day each, 22 working days:
- Monthly queries: 50 × 5 × 22 = 5,500
- Avg tokens: 3,500 in + 1,000 out

| LLM | Monthly USD | Monthly TWD |
|---|---|---|
| DeepSeek only | $4.20 | NT$ 130 |
| GPT-4o-mini only | $6.30 | NT$ 200 |
| Claude Sonnet only | $140 | NT$ 4,300 |
| **3-tier routing** (rules 40% + Ollama 50% + Claude 10%) | **$14** | **NT$ 430** |

---

## 5. Security Design (4 Layers)

```
[Layer 1] Prompt safety detector (regex)
          ├─ Detects "ignore instructions", "dump data" patterns
          ├─ Match → reject + log, never send to LLM (saves $$$ and risk)
          └─ Adversarial test: 32 cases all blocked
                ↓
[Layer 2] Agent domain restriction
          ├─ Inventory agent can only call 5 inventory tools
          ├─ Even if LLM tries to cross-domain, scope rejects
          └─ Attack surface = 1/10 size
                ↓
[Layer 3] RBAC permission check
          ├─ Every tool call checks user's permissions
          ├─ Row-level filtering (sales sees only own customers)
          └─ AI cannot exceed user's privileges
                ↓
[Layer 4] Human-in-the-loop
          ├─ High-risk tools (e.g. approve_PO) wait for human confirm
          ├─ Amount > $10,000 auto-triggers
          └─ AI cannot directly execute high-risk actions
                ↓
[Across all] DecisionLog records every interaction
          ├─ user / agent / model / tokens / cost / risk / decision
          └─ Replayable for forensics + auditable
```

---

## 6. High-Risk Actions

These tools require **human click on confirm button**, even in demo mode:

| Tool | Risk |
|---|---|
| approve_purchase_order | Approving PO = authorizing payment |
| approve_sales_order | Sales confirm impacts inventory allocation |
| post_journal_entry | Posting journal affects financial reports |
| close_month | Month-end close = data freeze |
| delete_customer | Customer record deletion |
| delete_supplier | Supplier record deletion |
| delete_part | Part record deletion |
| bulk_inventory_adjust | Batch inventory change |
| bulk_price_update | Batch price change |
| send_email_blast | Mass email |
| send_line_broadcast | Mass LINE message |

**+ Amount condition**: any tool with `amount/total/qty/value` ≥ $10,000 also triggers confirm.

---

## 7. DecisionLog Audit Trail

Every AI interaction writes one row, schema:

| Field | Purpose |
|---|---|
| session_id | Chat session |
| user_id | Who asked |
| domain | Which domain |
| agent_name | Which agent handled |
| query | Original question |
| decision | AI's answer |
| reasoning | Thought process |
| alternatives | Other options considered |
| model | Which LLM used |
| input_tokens / output_tokens | Usage |
| cost_usd | Converted USD |
| latency_ms | Duration |
| risk_flagged | Whether flagged by safety detector |
| human_confirmed | Whether high-risk got human approval |

**Query interface**: `GET /api/analytics/ai-cost` — see monthly cost breakdown.

---

## 8. AI Refusal List

The following requests are **rejected before reaching LLM**:

1. Reveal system prompt / developer mode
2. Cross-tenant query (read another company's data)
3. Direct SQL injection attempts
4. Mass batch deletion (unless via dedicated batch API + confirm)
5. Bypass RBAC to access data user has no permission for
6. Auto-respond "I did it" when actually nothing happened (anti-hallucination)

---

## 9. FAQ

### Q1: What if AI answers wrong?

Every reply has a DecisionLog entry, replayable by session_id. Report errors with session_id attached.
AI never auto-writes anything, so wrong answers are just "wrong words", never corrupted data.

### Q2: Does AI train on our data?

**Depends on which LLM you choose**:
- Anthropic Claude API: **No**, doesn't train on API data (public policy)
- OpenAI API: **No**, doesn't train on API data (public policy)
- DeepSeek API: Policy unclear (China DC), sensitive data avoid
- **Ollama local**: **Zero egress**, zero risk

### Q3: Can we switch LLMs?

Yes. Change `backend/.env` `LLM_PROVIDER` + `LLM_MODEL`, restart backend, all agents use new LLM immediately.

### Q4: Where do I see token usage?

`GET /api/analytics/ai-cost?period_days=30` — monthly breakdown by agent.

### Q5: Can we fully disable AI?

Yes. `backend/.env` set `LLM_PROVIDER=disabled`. Chat endpoints return demo mode. The other 11 domains work fully.

---

**Chinese version**: [`AGENT_CATALOG_ZH.md`](./AGENT_CATALOG_ZH.md)
**Last updated**: 2026-05-14 · v2.5

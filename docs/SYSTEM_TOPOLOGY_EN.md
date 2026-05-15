# System Topology & Flow Diagram (English) — v3.0

> **Six perspectives from shallow to deep, static to dynamic** — making LLM-ERP understandable to both technical and non-technical readers.
>
> - **Visual**: [`system_flow_topology.svg`](./system_flow_topology.svg) (beautiful SVG for slides / A3 print)
> - **Static legacy**: [`architecture_diagram.svg`](./architecture_diagram.svg) (5-layer)
>
> **Chinese version**: [`SYSTEM_TOPOLOGY_ZH.md`](./SYSTEM_TOPOLOGY_ZH.md)

> ⚡ **v3.0 Strategic Pivot Notice**: SVG may still show "👴 Outsource LINE / Plating Outsource / Inspection Outsource" nodes.
> v3.0 deprecates outsource / LINE / Mobile (moved to Phase 7). SVG redraw pending Phase 1 completion.

---

## View 1: Six-Layer Overall Architecture (Owner 30-sec scan)

```mermaid
graph TB
    subgraph CLIENT["L1 · Client Touchpoints"]
        L1A["👔 Owner LINE"]:::client
        L1B["👨‍💼 Sales Mobile"]:::client
        L1C["👨‍🏭 Plant Mgr Mobile"]:::client
        L1D["👩‍💻 Warehouse Scan QR"]:::client
        L1E["🖥️ Desktop UI"]:::client
        L1F["📡 War Room"]:::client
        L1G["👴 Outsource LINE"]:::client
    end

    subgraph GATEWAY["L2 · API Gateway · Auth/Permission/Audit"]
        L2["🔐 Auth → 📋 Audit → 🛡️ RBAC → 🪟 Row-Level Filter"]:::gateway
    end

    subgraph AGENT["L3a · Multi-Agent · AI Brain"]
        L3A["🤖 IntentClassifier → 10 Agents → 26+ Tools<br/>LLM: Claude / DeepSeek / GPT-4o / Ollama"]:::agent
    end

    subgraph EVENT["L3b · Event Engine"]
        L3B["⚡ EventBus<br/>+ 16 Constraint Rules<br/>+ Notification Dispatcher<br/>→ SSE / LINE Push / FCM"]:::event
    end

    subgraph DOMAIN["L4 · 12 Domain Services"]
        L4["📦 Inventory · 🛒 Purchase · 🏭 Production · 💰 Sales<br/>🔬 Quality · 💳 Accounting · 📍 Warehouse · 👥 CRM<br/>📊 MPS/MRP · 🔗 Outsource · 🏛️ Organization · 🤖 AI Gov"]:::domain
    end

    subgraph DATA["L5 · Data Layer"]
        L5["🗄️ PostgreSQL/SQLite · 66 tables · 19 with tenant_id<br/>📜 Audit Trail · ♻️ Hot/Cold Tiering"]:::data
    end

    subgraph MESH["L6 · MESH Multi-Factory · Data Stays Local"]
        L6A["🏛️ HQ"]:::mesh
        L6B["🏭 Main 8001"]:::mesh
        L6C["🔧 Plating Outs 8002"]:::mesh
        L6D["🔬 Inspect Outs 8003"]:::mesh
        L6E["⚙️ Nth Factory"]:::mesh
    end

    CLIENT --> GATEWAY
    GATEWAY --> AGENT
    GATEWAY --> DOMAIN
    AGENT <--> EVENT
    AGENT --> DOMAIN
    DOMAIN --> EVENT
    DOMAIN --> DATA
    EVENT --> DATA
    DATA -. WireGuard VPN .-> L6A
    L6A <--> L6B
    L6A <--> L6C
    L6A <--> L6D
    L6A <--> L6E

    classDef client fill:#06b6d4,stroke:#0e7490,color:#fff
    classDef gateway fill:#fbbf24,stroke:#b45309,color:#000
    classDef agent fill:#a78bfa,stroke:#6d28d9,color:#fff
    classDef event fill:#10b981,stroke:#047857,color:#fff
    classDef domain fill:#3b82f6,stroke:#1d4ed8,color:#fff
    classDef data fill:#1e3a5f,stroke:#0c4a6e,color:#fff
    classDef mesh fill:#f97316,stroke:#9a3412,color:#fff
```

---

## View 2: Full Request Lifecycle (Engineer "how data flows")

```mermaid
sequenceDiagram
    autonumber
    participant U as 👨‍💼 Sales Chen
    participant M as 📱 Mobile App
    participant N as 🌐 nginx
    participant A as 🔐 AuthMW
    participant R as 🛡️ RBAC
    participant API as 📡 API Endpoint
    participant Agent as 🤖 Multi-Agent
    participant LLM as 💬 LLM Provider
    participant Tool as 🛠️ Tool Function
    participant DB as 🗄️ Database
    participant E as ⚡ EventBus
    participant SSE as 📡 SSE Stream

    U->>M: Customer A pricing history?
    M->>N: POST /api/chat-v2<br/>Authorization: Bearer JWT
    N->>A: HTTPS reverse proxy
    A->>A: Verify JWT signature
    A->>R: load_user_context()
    R->>DB: Query UserRoleAssignment
    DB-->>R: roles + permissions
    R-->>A: UserContext (with tenant_id)
    A->>API: require_permission("ai.agent.use") ✓

    API->>Agent: classify_intent("...pricing...")
    Agent-->>API: intent = "sales"
    API->>Agent: pick agent = SalesAgent

    Agent->>LLM: chat_completion(system + user + tools)
    Note over LLM: 4 providers selectable<br/>(Claude / DeepSeek / GPT / Ollama)
    LLM-->>Agent: tool_calls = [query_sales_order(...)]

    Agent->>Tool: execute query_sales_order
    Tool->>DB: SELECT ... WHERE customer="A"<br/>+ apply_row_filter (own scope)
    DB-->>Tool: 3 historical records
    Tool-->>Agent: JSON result

    Agent->>LLM: Round 2 (with tool result)
    LLM-->>Agent: Final natural language reply

    Agent->>DB: Write ConversationLog + DecisionLog
    Agent->>E: emit "chat.completed"
    E->>SSE: broadcast (to War Room)
    Agent-->>API: ChatResponse
    API-->>N: 200 OK + JSON
    N-->>M: HTTPS response
    M-->>U: Last 3 times — 5/12 $4500, 4/20 $4400, 3/15 $4300
```

**Key flow notes**:
1. **Steps 6-7**: Permission load = single JOIN query, 5-min TTL cache
2. **Step 11**: IntentClassifier uses weighted keywords
3. **Step 14**: LLM tool calling can loop up to 5 rounds
4. **Step 18**: `apply_row_filter` auto-adds `WHERE created_by = chen` (Chen sees only own customers)
5. **Step 23**: All AI decisions written to DecisionLog for audit

---

## View 3: Multi-Agent Internals (AI Engineer)

```mermaid
flowchart TD
    Start([User Question]) --> IC[IntentClassifier<br/>Weighted Keywords]

    IC -->|inventory keywords| AInv[InventoryAgent]
    IC -->|sales keywords| ASales[SalesAgent]
    IC -->|production keywords| AProd[ProductionAgent]
    IC -->|quality keywords| AQual[QualityAgent]
    IC -->|other 6 domains| AOther[...6 more Agents]
    IC -->|no match| AGen[GeneralAgent fallback]

    AInv --> Tools1[query_inventory<br/>list_parts<br/>list_below_safety]
    ASales --> Tools2[query_sales_order<br/>list_customers<br/>...]
    AProd --> Tools3[query_work_order<br/>get_bom<br/>list_products...]

    Tools1 & Tools2 & Tools3 --> Loop{Tool Calling Loop<br/>max 5 rounds}

    Loop -->|LLM: more queries| LLM[LLM Provider<br/>Claude/DeepSeek/GPT/Ollama]
    LLM --> Loop
    Loop -->|LLM: done| Reply[Natural language reply<br/>+ Markdown table]

    Reply --> Log[Write<br/>ConversationLog<br/>DecisionLog]
    Log --> Out([Return to user])

    classDef agent fill:#a78bfa,stroke:#6d28d9,color:#fff
    classDef tool fill:#3b82f6,stroke:#1d4ed8,color:#fff
    classDef llm fill:#f59e0b,stroke:#b45309,color:#fff
    class AInv,ASales,AProd,AQual,AOther,AGen agent
    class Tools1,Tools2,Tools3 tool
    class LLM llm
```

**Each Agent has scoped tools** — preventing LLM from misfiring cross-domain:
- `InventoryAgent` only sees 4 inventory tools
- `SalesAgent` only sees 4 sales tools
- → Inventory agent cannot accidentally trigger sales operations

---

## View 4: MESH Multi-Factory Flow (Multi-Site Owner)

```mermaid
sequenceDiagram
    participant Owner as 👔 Owner (LINE)
    participant HQ as 🏛️ HQ
    participant FactA as 🏭 Main :8001
    participant FactB as 🔧 Plating Outs :8002
    participant FactC as 🔬 Inspect Outs :8003

    Owner->>HQ: Total M6 bolts across factories?
    HQ->>HQ: classify intent → mesh.factory.query

    par Concurrent query (data stays local)
        HQ->>+FactA: GET /api/factory/inventory?part=M6
        FactA->>FactA: Query local DB
        Note over FactA: Local LLM optional<br/>(qwen2.5:7b)
        FactA-->>-HQ: {qty: 3000} (only aggregate)
    and
        HQ->>+FactB: GET /api/factory/inventory?part=M6
        FactB->>FactB: Query local DB
        FactB-->>-HQ: {qty: 2500}
    and
        HQ->>+FactC: GET /api/factory/inventory?part=M6
        FactC->>FactC: Query local DB
        FactC-->>-HQ: {qty: 1800}
    end

    HQ->>HQ: Aggregate (3000+2500+1800=7300)
    HQ->>Owner: Total 7,300 pcs<br/>Main 3000 / Plating 2500 / Inspect 1800

    Note over HQ,FactC: ★ HQ NEVER sees which-batch or who-bought-it<br/>★ Only aggregates — raw data stays local
```

**Three MESH highlights**:
1. **Data sovereignty**: Each factory's data **physically** stays on-premise
2. **Offline-capable**: Factory keeps working even when HQ disconnects
3. **Infinite scale**: Adding the Nth outsource partner takes 50 lines of config

---

## View 5: Permission Check Flow (Security / IT)

```mermaid
flowchart LR
    Req([HTTP Request<br/>Authorization: Bearer JWT]) --> AuthMW{AuthMiddleware<br/>Public path?}

    AuthMW -->|Yes| Pass1([Skip verification])
    AuthMW -->|No| Verify[Verify JWT]

    Verify --> CheckSig{Signature OK?}
    CheckSig -->|No| Reject401([401 Unauthorized])
    CheckSig -->|Yes| LoadCtx[load_user_context]

    LoadCtx --> CacheHit{Cache hit?<br/>5min TTL}
    CacheHit -->|Yes| FromCache[From cache]
    CacheHit -->|No| QueryDB[Query DB<br/>JOIN UserRoleAssignment]
    QueryDB --> SaveCache[Save to cache]

    FromCache & SaveCache --> UCtx[UserContext<br/>+ permissions dict<br/>+ tenant_id]

    UCtx --> ReqPerm{require_permission<br/>code match}
    ReqPerm -->|No permission| Reject403([403 Permission Denied])
    ReqPerm -->|Has permission| Endpoint[Execute endpoint]

    Endpoint --> RowFilter[apply_row_filter<br/>Auto-add WHERE]
    RowFilter --> ScopeCheck{Scope?}
    ScopeCheck -->|own| OwnQ[WHERE created_by=user]
    ScopeCheck -->|tenant| TenQ[WHERE tenant_id=user.tenant]
    ScopeCheck -->|assigned| AssignQ[WHERE assigned_to=user]
    ScopeCheck -->|all| AllQ[No filter]

    OwnQ & TenQ & AssignQ & AllQ --> DB[(Database)]
    DB --> Response([HTTP 200 + Data])

    classDef reject fill:#ef4444,stroke:#991b1b,color:#fff
    classDef pass fill:#10b981,stroke:#047857,color:#fff
    class Reject401,Reject403 reject
    class Pass1,Response pass
```

**Five layers of permission gates**:
1. **JWT verification**: Is the token valid
2. **UserContext load**: Who are you, what role
3. **require_permission**: Can you do this action
4. **apply_row_filter**: Which rows can you see (Sales A can't see Sales B's customers)
5. **Audit Trail**: Record who did what when

---

## View 6: Typical Business Lifecycle (Inquiry → Payment)

```mermaid
journey
    title Customer Order → Shipment → Payment Journey
    section Inquiry
      Customer LINE inquiry: 5: Customer
      Sales mobile AI checks ATP: 5: Sales Chen
      AI provides commitment date: 5: AI
    section Order
      Create Sales Order: 5: Sales Chen
      Constraint credit check: 5: System
      Event so.confirmed → notify production: 5: System
    section Planning
      MRP material explosion: 5: System
      Replenish → Purchase: 4: Purchaser Ling
      PO approval: 4: Owner
    section Production
      WO release: 5: Plant Mgr
      Outsource dispatch (QR): 4: Plant Mgr
      Outsource LINE scan QR: 5: Outsource Wu
      Completion → stock-in: 5: Warehouse
    section Shipment
      Picking scan QR: 5: Warehouse Ling
      Shipment confirmed: 5: Sales
      Event so.shipped → LINE owner: 5: Owner
    section Payment
      Auto-create AR: 5: System
      AR aging tracking: 4: Accountant
      Payment confirmed: 5: Accountant
```

**Events triggered at each stage**:

| Stage | Event | Auto Action |
|---|---|---|
| Inquiry | `chat.completed` | DecisionLog records AI recommendation |
| Order | `so.confirmed` | Notify production_manager |
| Planning | `mrp.generated` | Push to purchaser |
| Purchase | `po.approved` | Notify supplier + warehouse |
| Production | `wo.released` | Push to plant_manager + operators |
| Outsource | `outsource.completed` | Push to warehouse + accounting |
| Shipment | `so.shipped` | LINE push to owner, auto-create AR |
| Payment | `payment.received` | Notify sales + accounting |

---

## Tech / Business Dual-Track Summary

| Dimension | Tech View | Business View |
|---|---|---|
| **L1 Client** | React/Expo/HTML+SSE | Owner / Sales / Plant Mgr / Outsource |
| **L2 API Gateway** | FastAPI Middleware Stack | "Identity verified before entry" |
| **L3a Multi-Agent** | IntentClassifier + Tool Calling | "AI auto-finds the right function" |
| **L3b Event Engine** | EventBus + Constraint Rules | "Anomalies push automatically" |
| **L4 Domain** | 12 service modules | "12 business domains integrated" |
| **L5 Data** | PostgreSQL + Row-Level | "Data isolated by factory & user" |
| **L6 MESH** | WireGuard + Aggregate Query | "Outsource data stays at outsource" |

---

## Reading Order by Role

| Reader | Suggested Order |
|---|---|
| 👔 **Owner** | View 1 (30s scan) → View 6 (business journey) |
| 👨‍💼 **Sales** | View 6 → View 2 (one request lifecycle) |
| 🧑‍💻 **Developer** | View 2 → View 3 (Multi-Agent) → View 5 (Permission) |
| 🛡️ **IT/Security** | View 5 (Permission) → View 4 (MESH) |
| 🌐 **Multi-Site Mgr** | View 4 (MESH) → View 1 (overview) |

---

## Related Documents

- 📐 [`ARCHITECTURE_DIAGRAM.md`](./ARCHITECTURE_DIAGRAM.md) — Static 5-layer
- 📡 [`NETWORK_DEPLOYMENT_EN.md`](./NETWORK_DEPLOYMENT_EN.md) — Network deployment
- 🛡️ [`PERMISSION_MODEL.md`](./PERMISSION_MODEL.md) — Permission model
- 🤖 [`LLM_BENCHMARK_REPORT_EN.md`](./LLM_BENCHMARK_REPORT_EN.md) — LLM benchmark
- 🏗️ [`ARCHITECTURE_DECISIONS.md`](./ARCHITECTURE_DECISIONS.md) — ADRs

---

**Last updated**: 2026-05-14
**Chinese version**: [`SYSTEM_TOPOLOGY_ZH.md`](./SYSTEM_TOPOLOGY_ZH.md)

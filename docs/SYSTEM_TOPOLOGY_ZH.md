# 系統架構流程關聯拓樸圖（繁體中文）

> **本檔提供六種視角**，由淺入深、由靜態到動態，讓技術與非技術讀者都能掌握 LLM-ERP 全貌。
>
> - **視覺版**：[`system_flow_topology.svg`](./system_flow_topology.svg)（精美 SVG，可貼簡報、印 A3）
> - **舊版靜態圖**：[`architecture_diagram.svg`](./architecture_diagram.svg)（5 層分層）
>
> **對應英文版**：[`SYSTEM_TOPOLOGY_EN.md`](./SYSTEM_TOPOLOGY_EN.md)

---

## 視角 1：六層整體架構（給老闆看 30 秒懂）

```mermaid
graph TB
    subgraph CLIENT["L1 · 客戶觸點"]
        L1A["👔 王董 LINE"]:::client
        L1B["👨‍💼 業務手機"]:::client
        L1C["👨‍🏭 廠長手機"]:::client
        L1D["👩‍💻 倉管掃 QR"]:::client
        L1E["🖥️ Desktop UI"]:::client
        L1F["📡 War Room"]:::client
        L1G["👴 外協 LINE"]:::client
    end

    subgraph GATEWAY["L2 · API Gateway · 認證/權限/稽核"]
        L2["🔐 Auth → 📋 Audit → 🛡️ RBAC → 🪟 Row-Level Filter"]:::gateway
    end

    subgraph AGENT["L3a · Multi-Agent · AI 大腦"]
        L3A["🤖 IntentClassifier → 10 Agents → 26+ Tools<br/>LLM: Claude / DeepSeek / GPT-4o / Ollama"]:::agent
    end

    subgraph EVENT["L3b · Event Engine · 事件引擎"]
        L3B["⚡ EventBus<br/>+ 16 Constraint Rules<br/>+ Notification Dispatcher<br/>→ SSE / LINE Push / FCM"]:::event
    end

    subgraph DOMAIN["L4 · 12 個 Domain Services · 業務邏輯"]
        L4["📦 Inventory · 🛒 Purchase · 🏭 Production · 💰 Sales<br/>🔬 Quality · 💳 Accounting · 📍 Warehouse · 👥 CRM<br/>📊 MPS/MRP · 🔗 Outsource · 🏛️ Organization · 🤖 AI Gov"]:::domain
    end

    subgraph DATA["L5 · Data Layer · 資料層"]
        L5["🗄️ PostgreSQL/SQLite · 66 tables · 19 帶 tenant_id<br/>📜 Audit Trail · ♻️ 冷熱分層"]:::data
    end

    subgraph MESH["L6 · MESH 多廠 · 資料不外流"]
        L6A["🏛️ HQ 總部"]:::mesh
        L6B["🏭 主廠 8001"]:::mesh
        L6C["🔧 鍍鋅外協 8002"]:::mesh
        L6D["🔬 檢驗外協 8003"]:::mesh
        L6E["⚙️ 第 N 個"]:::mesh
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

## 視角 2：一個請求的完整生命週期（給工程師看「資料怎麼跑」）

```mermaid
sequenceDiagram
    autonumber
    participant U as 👨‍💼 業務小陳
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

    U->>M: 「A 客戶歷史單價?」
    M->>N: POST /api/chat-v2<br/>Authorization: Bearer JWT
    N->>A: HTTPS 反向代理
    A->>A: 驗證 JWT 簽章
    A->>R: load_user_context()
    R->>DB: 查 UserRoleAssignment
    DB-->>R: roles + permissions
    R-->>A: UserContext (含 tenant_id)
    A->>API: require_permission("ai.agent.use") ✓

    API->>Agent: classify_intent("A 客戶歷史單價")
    Agent-->>API: intent = "sales"
    API->>Agent: pick agent = SalesAgent

    Agent->>LLM: chat_completion(system + user + tools)
    Note over LLM: 4 個 provider 可選<br/>(Claude / DeepSeek / GPT / Ollama)
    LLM-->>Agent: tool_calls = [query_sales_order(...)]

    Agent->>Tool: execute query_sales_order
    Tool->>DB: SELECT ... WHERE customer="A"<br/>+ apply_row_filter (own scope)
    DB-->>Tool: 3 筆歷史紀錄
    Tool-->>Agent: JSON 結果

    Agent->>LLM: 第二輪 (含 tool result)
    LLM-->>Agent: 最終自然語言回答

    Agent->>DB: 寫 ConversationLog + DecisionLog
    Agent->>E: emit "chat.completed"
    E->>SSE: broadcast (給 War Room)
    Agent-->>API: ChatResponse
    API-->>N: 200 OK + JSON
    N-->>M: HTTPS 回傳
    M-->>U: 「最近 3 次：5/12 $4500、4/20 $4400、3/15 $4300」
```

**關鍵流程說明**：
1. **第 6-7 步**：權限載入是 single JOIN query，5 分鐘 TTL cache（不每次都查 DB）
2. **第 11 步**：IntentClassifier 用加權關鍵字（「客戶」+「單價」→ sales）
3. **第 14 步**：LLM tool calling 可循環最多 5 round
4. **第 18 步**：`apply_row_filter` 自動加 `WHERE created_by = 小陳`（小陳看不到別人的客戶）
5. **第 23 步**：所有 AI 決策都寫 DecisionLog，事後可稽核

---

## 視角 3：Multi-Agent 內部運作（給 AI 工程師看）

```mermaid
flowchart TD
    Start([使用者問題]) --> IC[IntentClassifier<br/>加權關鍵字]

    IC -->|inventory keywords| AInv[InventoryAgent]
    IC -->|sales keywords| ASales[SalesAgent]
    IC -->|production keywords| AProd[ProductionAgent]
    IC -->|quality keywords| AQual[QualityAgent]
    IC -->|other 6 domains| AOther[...其他 6 個 Agent]
    IC -->|no match| AGen[GeneralAgent fallback]

    AInv --> Tools1[query_inventory<br/>list_parts<br/>list_below_safety]
    ASales --> Tools2[query_sales_order<br/>list_customers<br/>...]
    AProd --> Tools3[query_work_order<br/>get_bom<br/>list_products...]

    Tools1 & Tools2 & Tools3 --> Loop{Tool Calling Loop<br/>max 5 rounds}

    Loop -->|LLM: 還需要查| LLM[LLM Provider<br/>Claude/DeepSeek/GPT/Ollama]
    LLM --> Loop
    Loop -->|LLM: 完成| Reply[自然語言回答<br/>+ Markdown 表格]

    Reply --> Log[寫入<br/>ConversationLog<br/>DecisionLog]
    Log --> Out([回傳給使用者])

    classDef agent fill:#a78bfa,stroke:#6d28d9,color:#fff
    classDef tool fill:#3b82f6,stroke:#1d4ed8,color:#fff
    classDef llm fill:#f59e0b,stroke:#b45309,color:#fff
    class AInv,ASales,AProd,AQual,AOther,AGen agent
    class Tools1,Tools2,Tools3 tool
    class LLM llm
```

**Agent 各擁有 scoped tools**——避免 LLM 誤呼叫跨領域工具：
- `InventoryAgent` 只看到 4 個庫存相關 tools
- `SalesAgent` 只看到 4 個銷售相關 tools
- 換言之：庫存代理人不會誤觸發銷售操作

---

## 視角 4：MESH 多廠協同流程（給多廠老闆看）

```mermaid
sequenceDiagram
    participant Wang as 👔 王董 (LINE)
    participant HQ as 🏛️ HQ 總部
    participant FactA as 🏭 主廠 :8001
    participant FactB as 🔧 鍍鋅外協 :8002
    participant FactC as 🔬 檢驗外協 :8003

    Wang->>HQ: 「全廠 M6 螺絲庫存?」
    HQ->>HQ: classify intent → mesh.factory.query

    par 並發查詢（資料不外流）
        HQ->>+FactA: GET /api/factory/inventory?part=M6
        FactA->>FactA: 查本地 DB
        Note over FactA: 本地 LLM 可選參與<br/>(qwen2.5:7b)
        FactA-->>-HQ: {qty: 3000} (只送聚合)
    and
        HQ->>+FactB: GET /api/factory/inventory?part=M6
        FactB->>FactB: 查本地 DB
        FactB-->>-HQ: {qty: 2500}
    and
        HQ->>+FactC: GET /api/factory/inventory?part=M6
        FactC->>FactC: 查本地 DB
        FactC-->>-HQ: {qty: 1800}
    end

    HQ->>HQ: 聚合 (3000+2500+1800=7300)
    HQ->>Wang: 「總計 7300 個<br/>主廠 3000 / 鍍鋅 2500 / 檢驗 1800」

    Note over HQ,FactC: ★ 重點：HQ 永遠看不到「哪批料、誰買的」<br/>★ 只取聚合數字，原始資料留在各廠
```

**MESH 三大特色**：
1. **資料主權**：每廠資料**物理上**留在自己廠內
2. **離線可用**：工廠斷網仍可本地運作
3. **可無限擴展**：第 N 個外協廠加入只需 WireGuard 設定 + 50 行 config

---

## 視角 5：權限檢查流程（給資安 / IT 看）

```mermaid
flowchart LR
    Req([HTTP Request<br/>Authorization: Bearer JWT]) --> AuthMW{AuthMiddleware<br/>路徑是公開?}

    AuthMW -->|是| Pass1([跳過驗證])
    AuthMW -->|否| Verify[驗證 JWT]

    Verify --> CheckSig{簽章 OK?}
    CheckSig -->|否| Reject401([401 Unauthorized])
    CheckSig -->|是| LoadCtx[load_user_context]

    LoadCtx --> CacheHit{快取命中?<br/>5min TTL}
    CacheHit -->|是| FromCache[從 cache 取]
    CacheHit -->|否| QueryDB[Query DB<br/>JOIN UserRoleAssignment]
    QueryDB --> SaveCache[寫入 cache]

    FromCache & SaveCache --> UCtx[UserContext<br/>+ permissions dict<br/>+ tenant_id]

    UCtx --> ReqPerm{require_permission<br/>code 比對}
    ReqPerm -->|無此權限| Reject403([403 Permission Denied])
    ReqPerm -->|有權限| Endpoint[執行 endpoint]

    Endpoint --> RowFilter[apply_row_filter<br/>自動加 WHERE]
    RowFilter --> ScopeCheck{Scope?}
    ScopeCheck -->|own| OwnQ[WHERE created_by=user]
    ScopeCheck -->|tenant| TenQ[WHERE tenant_id=user.tenant]
    ScopeCheck -->|assigned| AssignQ[WHERE assigned_to=user]
    ScopeCheck -->|all| AllQ[無過濾]

    OwnQ & TenQ & AssignQ & AllQ --> DB[(資料庫)]
    DB --> Response([HTTP 200 + Data])

    classDef reject fill:#ef4444,stroke:#991b1b,color:#fff
    classDef pass fill:#10b981,stroke:#047857,color:#fff
    class Reject401,Reject403 reject
    class Pass1,Response pass
```

**5 層權限把關**：
1. **JWT 驗證**：是不是合法 token
2. **UserContext 載入**：你是誰、什麼角色
3. **require_permission**：能不能做這個動作
4. **apply_row_filter**：能看到哪些資料（業務 A 看不到業務 B 的客戶）
5. **Audit Trail**：紀錄誰在何時做了什麼

---

## 視角 6：典型業務生命週期（從詢價到收款）

```mermaid
journey
    title 客戶下單 → 出貨 → 收款 完整旅程
    section 詢價階段
      客戶 LINE 詢價: 5: 客戶
      業務手機 AI 查 ATP: 5: 業務小陳
      AI 提供可承諾交期: 5: AI
    section 訂單階段
      建立銷售單 SO: 5: 業務小陳
      Constraint 信用額度檢查: 5: 系統
      Event so.confirmed → 通知生產: 5: 系統
    section 規劃階段
      MRP 物料展開: 5: 系統
      補貨建議 → 採購: 4: 採購阿玲
      PO 簽核: 4: 老闆
    section 生產階段
      工單釋放: 5: 廠長林
      派工外協 (QR 派工單): 4: 廠長林
      外協 LINE 掃 QR 回報: 5: 外協老吳
      完工入庫: 5: 倉管
    section 出貨階段
      揀貨掃 QR: 5: 倉管阿玲
      出貨確認: 5: 業務
      Event so.shipped → LINE 通知老闆: 5: 王董
    section 收款階段
      自動建立 AR: 5: 系統
      應收帳款追蹤: 4: 會計
      收款確認: 5: 會計
```

**每個階段觸發的 Event**：

| 階段 | 觸發事件 | 自動動作 |
|---|---|---|
| 詢價 | `chat.completed` | DecisionLog 紀錄 AI 推薦 |
| 訂單 | `so.confirmed` | 通知 production_manager |
| 規劃 | `mrp.generated` | 推給 purchaser |
| 採購 | `po.approved` | 通知 supplier + warehouse |
| 生產 | `wo.released` | 推給 plant_manager + operators |
| 外協 | `outsource.completed` | 推給 warehouse + accounting |
| 出貨 | `so.shipped` | 推 LINE 給老闆、自動建 AR |
| 收款 | `payment.received` | 通知 sales + accounting |

---

## 技術 / 業務雙軌總表

| 維度 | 技術視角 | 業務視角 |
|---|---|---|
| **L1 客戶端** | React/Expo/HTML+SSE | 王董 / 業務 / 廠長 / 外協 |
| **L2 API Gateway** | FastAPI Middleware Stack | 「進來前都驗證身份」 |
| **L3a Multi-Agent** | IntentClassifier + Tool Calling | 「AI 自動找對的功能用」 |
| **L3b Event Engine** | EventBus + Constraint Rules | 「異常自動推播」 |
| **L4 Domain** | 12 個 service modules | 「12 個業務領域整合」 |
| **L5 Data** | PostgreSQL + Row-Level | 「資料分廠別、分業務」 |
| **L6 MESH** | WireGuard + 聚合查詢 | 「外協廠資料留在外協廠」 |

---

## 給不同讀者的閱讀順序

| 讀者 | 建議順序 |
|---|---|
| 👔 **老闆** | 視角 1（30 秒懂）→ 視角 6（業務旅程） |
| 👨‍💼 **業務** | 視角 6 → 視角 2（一個請求生命週期）|
| 🧑‍💻 **開發者** | 視角 2 → 視角 3（Multi-Agent）→ 視角 5（權限）|
| 🛡️ **IT/資安** | 視角 5（權限）→ 視角 4（MESH）|
| 🌐 **多廠主管** | 視角 4（MESH）→ 視角 1（全景）|

---

## 對應文件

- 📐 [`ARCHITECTURE_DIAGRAM.md`](./ARCHITECTURE_DIAGRAM.md) — 靜態 5 層架構
- 📡 [`NETWORK_DEPLOYMENT_ZH.md`](./NETWORK_DEPLOYMENT_ZH.md) — 網路部署
- 🛡️ [`PERMISSION_MODEL.md`](./PERMISSION_MODEL.md) — 權限模型
- 🤖 [`LLM_BENCHMARK_REPORT_ZH.md`](./LLM_BENCHMARK_REPORT_ZH.md) — LLM 評比
- 🏗️ [`ARCHITECTURE_DECISIONS.md`](./ARCHITECTURE_DECISIONS.md) — ADR

---

**最後更新**：2026-05-14
**英文版**：[`SYSTEM_TOPOLOGY_EN.md`](./SYSTEM_TOPOLOGY_EN.md)

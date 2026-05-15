# LLM-ERP 系統架構拓樸圖 — v3.0

> 兩個版本：
> - **`architecture_diagram.svg`**：精美視覺版（可貼簡報、印 A3）
> - **下方 Mermaid**：技術文件版（GitHub / Notion / Markdown 渲染）

> ⚡ **v3.0 戰略軸轉通知**：SVG 與 Mermaid 內仍可能顯示「📱 LINE Bot」「鍍鋅外協」等舊節點。
> v3.0 已刪 mobile / LINE / 外協（功能下架到 Phase 7）。圖示更新待下次重畫，文字描述以本 v3.0 banner 為準。

---

## SVG 預覽

直接打開 [`architecture_diagram.svg`](./architecture_diagram.svg)（瀏覽器或 IDE 預覽）。

---

## Mermaid 版（彩色分層）

```mermaid
graph TB
    %% ─── 客戶端層 ───
    subgraph "📱 客戶端層 Client Tier"
        LINE["📱 LINE Bot<br/>王董・老吳<br/>老闆儀表板・外協回報"]
        Mobile["📲 Mobile App<br/>小陳・林廠長・阿玲<br/>掃 QR・推播"]
        Desktop["🖥️ Desktop UI<br/>React + Vite + Tailwind<br/>10 頁面・中英雙語"]
        WarRoom["📡 War-Room<br/>HTML + SSE<br/>中央指揮台"]
    end

    %% ─── 中介層 ───
    subgraph "🔐 API Gateway 中介層"
        Auth["JWT + RBAC 權限"]
        Audit["Audit Middleware"]
        Exc["Exception Handler"]
    end

    %% ─── 應用核心 ───
    subgraph "⚡ Application Core 應用核心（FastAPI · 102 endpoints）"
        Domains["🏢 12 Domain APIs<br/>Inventory・Purchase・Production<br/>Sales・Quality・Accounting<br/>Warehouse・CRM・MPS/MRP<br/>Organization・Outsource・MESH"]
        Agents["🤖 Multi-Agent Engine<br/>10 Agents・26+ Tools<br/>IntentClassifier<br/>LLM: Anthropic/OpenAI/DeepSeek/Ollama"]
        Events["⚡ Event Engine<br/>16 ConstraintChecker<br/>EventBus + SSE<br/>NotificationDispatcher"]
    end

    %% ─── 資料層 ───
    subgraph "🗄️ Data Layer 資料層"
        DB[("PostgreSQL / SQLite<br/>66 tables + 19 tenant_id")]
        RBAC["🛡️ RBAC<br/>109 permissions<br/>11 roles<br/>6 row scopes"]
    end

    %% ─── MESH ───
    subgraph "🌐 MESH Multi-Factory · VMI 友善"
        F1["🏭 主廠<br/>:8001"]
        F2["🔧 鍍鋅外協<br/>:8002"]
        F3["🔬 檢驗外協<br/>:8003"]
        FN["⚙️ N 個工廠節點…"]
    end

    LINE --> Auth
    Mobile --> Auth
    Desktop --> Auth
    WarRoom --> Auth

    Auth --> Audit --> Exc
    Exc --> Domains
    Exc --> Agents
    Exc --> Events

    Domains -.->|emit| Events
    Agents -.->|use tools| Domains
    Events -.->|notify| Agents

    Domains --> DB
    Events --> DB
    RBAC -.->|check| Auth

    DB -. VPN/SSL .-> F1
    DB -. VPN/SSL .-> F2
    DB -. VPN/SSL .-> F3
    DB -. VPN/SSL .-> FN

    classDef client fill:#06b6d4,stroke:#0e7490,color:#fff
    classDef gateway fill:#fbbf24,stroke:#b45309,color:#000
    classDef core fill:#3b82f6,stroke:#1d4ed8,color:#fff
    classDef ai fill:#8b5cf6,stroke:#6d28d9,color:#fff
    classDef event fill:#10b981,stroke:#047857,color:#fff
    classDef data fill:#1e3a5f,stroke:#0c4a6e,color:#fff
    classDef rbac fill:#7c2d12,stroke:#9a3412,color:#fff
    classDef mesh fill:#f59e0b,stroke:#b45309,color:#fff

    class LINE,Mobile,Desktop,WarRoom client
    class Auth,Audit,Exc gateway
    class Domains core
    class Agents ai
    class Events event
    class DB data
    class RBAC rbac
    class F1,F2,F3,FN mesh
```

---

## 關鍵設計亮點

### 1. 五層分明的分層架構

| 層 | 角色 | 元素 |
|---|---|---|
| **Client** | 觸達使用者 | LINE Bot · Mobile · Desktop · War-Room |
| **API Gateway** | 認證 / 授權 / 稽核 | JWT · RBAC · Audit · Exception |
| **Application Core** | 業務邏輯 | 12 Domains · Multi-Agent · Event Engine |
| **Data** | 持久化 | PostgreSQL / SQLite + RBAC schema |
| **MESH** | 多廠協同 | Factory Nodes · VMI · 資料不外流 |

### 2. 三大核心引擎並列

```
        Domain APIs ←→ Multi-Agent ←→ Event Engine
         (CRUD)       (AI 大腦)       (即時通知)
            ↓             ↓              ↓
         直接呼叫       自然語言       事件驅動
         (HTTP)        (LLM tools)    (SSE/Push)
```

### 3. 多租戶 + MESH 共生

- **單一 codebase**, 一份 Docker
- 透過 `tenant_id` 欄位 + Row-Level Filter 隔離資料
- 工廠節點獨立部署，僅回**聚合結果**

### 4. AI 為一等公民

不是事後加 chatbot，而是：
- **IntentClassifier**：分類使用者意圖
- **Multi-Agent**：10 個 domain 專家
- **Tool Calling**：26+ 個可呼叫工具
- **DecisionLog**：每個 AI 決策可追溯

### 5. 安全為基礎不是補丁

- **架構級 RBAC**：109 個權限碼從 Day 1 就有
- **Row-Level Filter**：業務只看自己客戶
- **多租戶隔離**：MESH 廠別資料牆
- **Audit Trail**：所有寫入操作不可竄改紀錄

---

## 資料流範例：「業務小陳問 AI」

```
1. 小陳手機開 App，問「客戶 A 的歷史單價」
       ↓
2. Mobile → POST /api/chat-v2 (Bearer JWT)
       ↓
3. AuthMiddleware: JWT 解析 → 小陳的 employee_id
       ↓
4. UserContext 載入：sales_rep 角色 + own scope
       ↓
5. IntentClassifier: 「客戶」+「單價」→ sales agent
       ↓
6. LLM 解析 → 呼叫 query_sales_order tool
       ↓
7. Tool 執行 → apply_row_filter(scope=own)
       → SELECT ... WHERE created_by = '小陳' AND customer_id = 'A'
       ↓
8. 回傳 3 筆歷史單價
       ↓
9. LLM 整理回覆「最近 3 次：5/12 $4500、4/20 $4400、3/15 $4300」
       ↓
10. EventBus emit `conversation.completed` → audit_logs + SSE
       ↓
11. 小陳在客戶面前 3 秒拿到答案 ✓
```

---

## 給投資人 / 客戶看的版本

打開 [`architecture_diagram.svg`](./architecture_diagram.svg)，一頁簡報就講完。
A3 列印給工廠老闆，三秒看懂「資料怎麼跑」。

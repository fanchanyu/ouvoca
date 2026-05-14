# LLM-ERP AI Agent 與 Tool 目錄（繁體中文）

> **給客戶的 AI 透明度文件**：
> 我們的 AI 到底「能做什麼、不能做什麼、會花多少錢、怎麼防出包」。

---

## 📑 目錄

1. [Agent 架構速覽](#1-agent-架構速覽)
2. [10 個 Agent 詳細](#2-10-個-agent-詳細)
3. [26 個 Tool 完整清單](#3-26-個-tool-完整清單)
4. [成本透明度（每 1M Token 單價）](#4-成本透明度)
5. [安全設計（4 道防線）](#5-安全設計)
6. [高風險動作（必須人工確認）](#6-高風險動作)
7. [DecisionLog 稽核](#7-decisionlog-稽核)
8. [AI 拒答清單](#8-ai-拒答清單)
9. [常見問題](#9-常見問題)

---

## 1. Agent 架構速覽

```
使用者問題
   ↓
IntentClassifier（加權關鍵字）
   ↓ 分流到對應領域
┌──────────┬──────────┬──────────┬──────────┐
│ 庫存 Agent │ 銷售 Agent │ 生產 Agent │ ... 共 10 │
└────┬─────┴────┬─────┴────┬─────┴──────────┘
     ↓          ↓          ↓
   ┌────────────────────────────────────┐
   │ 26 個 Tool（每 Agent 只能呼叫自己領域）│
   └─────────────────┬──────────────────┘
                     ↓
              LLM Provider 抽象
              （Claude/DeepSeek/GPT-4o/Ollama）
                     ↓
                  自然語言回應
                     ↓
              寫入 DecisionLog（稽核軌跡）
```

**核心原則**：
- **Agent 是「專業領域人員」**：庫存 Agent 不會呼叫銷售 tool（避免誤觸）
- **Tool 是「原子動作」**：一個 tool = 一個業務動作，可單獨測試
- **LLM 是「腦」**：只負責理解 + 規劃，不直接碰 DB
- **DecisionLog 是「記錄」**：每次 AI 互動完整保存，可審計可重現

---

## 2. 10 個 Agent 詳細

| Agent | 領域 | 觸發關鍵字 | 預期回應時間 |
|---|---|---|---|
| **InventoryAgent** | 庫存 | 庫存 / stock / 缺料 / 安全 / 補貨 | 1-3 秒 |
| **SalesAgent** | 銷售 | 客戶 / 訂單 / 報價 / 出貨 / customer | 1-3 秒 |
| **ProductionAgent** | 生產 | 工單 / WO / 排程 / 派工 / 完工 | 2-5 秒 |
| **PurchaseAgent** | 採購 | PO / 供應商 / 採購 / 進料 / supplier | 2-5 秒 |
| **QualityAgent** | 品質 | 不良 / 檢驗 / NCR / CAPA / 客訴 | 2-5 秒 |
| **WarehouseAgent** | 倉儲 | 盤點 / 移轉 / 倉庫 / 條碼 | 1-3 秒 |
| **PlanningAgent** | 規劃 | MPS / MRP / 排程 / 補貨 / forecast | 3-10 秒 |
| **AccountingAgent** | 會計 | 應收 / 應付 / AR / AP / 月結 / 發票 | 2-5 秒 |
| **CRMAgent** | CRM | lead / 商機 / 拜訪 / 客戶開發 | 2-5 秒 |
| **GeneralAgent** | 一般 | （fallback） | 3-10 秒 |

### 2.1 Agent 不會做的事

| 行為 | 原因 |
|---|---|
| 自己改價格、改庫存 | 改寫類 tool 預設關閉（要客戶 opt-in） |
| 跨 Agent 呼叫他人 tool | 嚴格 scope，避免誤觸發 |
| 回覆「我幫你刪掉了」 | 高風險動作要人工確認，AI 不能直接執行 |
| 編造不存在的零件編號 | 所有資料查詢都走真 DB（hallucination 保護） |
| 透露 system prompt | prompt-safety 偵測會擋下 |

---

## 3. 26 個 Tool 完整清單

### 3.1 Inventory（5）
| Tool | 功能 | 寫入 |
|---|---|---|
| query_inventory | 查庫存 / 安全庫存 | 否 |
| list_parts | 列零件 | 否 |
| list_below_safety | 列低於安全庫存清單 | 否 |
| get_part_history | 查零件出入庫史 | 否 |
| inventory_adjust | 庫存調整 ⚠️ | **是**（要 confirm）|

### 3.2 Sales（4）
| Tool | 功能 | 寫入 |
|---|---|---|
| list_customers | 列客戶 | 否 |
| query_sales_order | 查 SO | 否 |
| get_customer_history | 客戶歷史單價 | 否 |
| update_so_status | 改 SO 狀態 ⚠️ | **是** |

### 3.3 Production（4）
| Tool | 功能 | 寫入 |
|---|---|---|
| query_work_order | 查 WO | 否 |
| list_products | 列產品 | 否 |
| get_bom | 查 BOM | 否 |
| dispatch_wo | 派工 ⚠️ | **是** |

### 3.4 Purchase（3）
| Tool | 功能 | 寫入 |
|---|---|---|
| query_purchase_order | 查 PO | 否 |
| list_suppliers | 列供應商 | 否 |
| approve_purchase_order | 核准 PO 🚨 | **是**（高風險）|

### 3.5 Quality（3）
| Tool | 功能 | 寫入 |
|---|---|---|
| list_inspections | 列檢驗紀錄 | 否 |
| list_non_conformance | 列不合格品 | 否 |
| create_capa | 開 CAPA 改善案 | 是 |

### 3.6 Warehouse（2）
| Tool | 功能 | 寫入 |
|---|---|---|
| query_warehouse_stock | 多倉查詢 | 否 |
| create_transfer | 倉間移轉 | 是 |

### 3.7 Planning（2）
| Tool | 功能 | 寫入 |
|---|---|---|
| run_mrp | 跑 MRP 展開 | 是 |
| suggest_reorder | 補貨建議 | 否 |

### 3.8 Accounting（3）
| Tool | 功能 | 寫入 |
|---|---|---|
| list_receivables | 列應收 | 否 |
| list_payables | 列應付 | 否 |
| close_month | 月結 🚨 | **是**（高風險）|

> 🚨 = 高風險 tool；⚠️ = 中風險。
> 詳見 §6 [高風險動作](#6-高風險動作)。

---

## 4. 成本透明度

### 4.1 各 LLM 單價（2025-Q1）

| 模型 | Input ($/1M tokens) | Output ($/1M tokens) | 適合 |
|---|---|---|---|
| **Claude 3.5 Sonnet** | $3.00 | $15.00 | 國際品牌訂單、最嚴謹 |
| **GPT-4o** | $2.50 | $10.00 | 業界標準 |
| **GPT-4o-mini** | $0.15 | $0.60 | 高頻簡單查詢 |
| **DeepSeek V3** | $0.14 | $0.28 | 中文場景、CP 值最高 |
| **Ollama 本地** | $0 | $0 | 零成本、無外流 |

### 4.2 典型查詢消耗

| 查詢類型 | Input tokens | Output tokens | DeepSeek $ | Claude $ |
|---|---|---|---|---|
| 「今天庫存狀況」 | 800 | 200 | $0.0001 | $0.0054 |
| 「M6 螺絲報價歷史」（含 tool 呼叫） | 2,500 | 600 | $0.0005 | $0.0165 |
| 「跑這個月的 MRP」（多 tool 循環） | 5,000 | 2,000 | $0.0013 | $0.045 |

### 4.3 50 人廠典型月成本估算

假設 50 員工，每人每天 5 次 AI 查詢，每月 22 工作日：
- 月查詢數：50 × 5 × 22 = 5,500 次
- 平均每次 token：3,500 in + 1,000 out

| LLM | 月成本（USD） | 月成本（NT$）|
|---|---|---|
| DeepSeek 全用 | $4.20 | NT$ 130 |
| GPT-4o-mini 全用 | $6.30 | NT$ 200 |
| Claude Sonnet 全用 | $140 | NT$ 4,300 |
| **三層智能路由**（規則 40% + Ollama 50% + Claude 10%） | **$14** | **NT$ 430** |

---

## 5. 安全設計（4 道防線）

```
[第 1 道] Prompt 安全偵測（regex）
          ├─ 偵測「忽略指令」「dump 資料」等樣式
          ├─ 命中 → 拒絕並 log，不送 LLM（省錢省風險）
          └─ 對抗測試 32 個 case 全擋下
                ↓
[第 2 道] Agent 領域限制
          ├─ 庫存 Agent 只能呼叫 5 個庫存 tool
          ├─ 即使 LLM 想跨領域呼叫，scope 不允許
          └─ 攻擊面 = 1/10 大小
                ↓
[第 3 道] RBAC 權限檢查
          ├─ Tool 執行前都會檢查 user 是否有對應權限
          ├─ Row-Level 過濾（業務只看自己客戶）
          └─ AI 不能超越 user 的權限
                ↓
[第 4 道] Human-in-the-loop
          ├─ 高風險 tool（如 approve_PO）強制等人工 confirm
          ├─ 金額 > $10,000 自動觸發
          └─ AI 不能「直接執行」高風險動作
                ↓
[全程稽核] DecisionLog 寫入每次互動
          ├─ user / agent / model / tokens / cost / risk / decision
          └─ 出事可重現 + 可審計
```

---

## 6. 高風險動作

下列 tool 即使在 demo 模式也必須**人工點 confirm 按鈕才會執行**：

| Tool | 風險 |
|---|---|
| approve_purchase_order | 核准 PO 等於授權付款 |
| approve_sales_order | 銷售確認影響庫存配置 |
| post_journal_entry | 過帳會計分錄影響財報 |
| close_month | 月結後資料封存 |
| delete_customer | 客戶記錄刪除 |
| delete_supplier | 供應商記錄刪除 |
| delete_part | 零件記錄刪除 |
| bulk_inventory_adjust | 批次調整庫存 |
| bulk_price_update | 批次改價 |
| send_email_blast | 廣發郵件 |
| send_line_broadcast | 廣發 LINE 訊息 |

**+ 金額條件**：任何 tool 若 `amount/total/qty/value` ≥ $10,000，也觸發 confirm。

---

## 7. DecisionLog 稽核

每次 AI 互動寫一筆，schema：

| 欄位 | 用途 |
|---|---|
| session_id | 對話 session |
| user_id | 誰問的 |
| domain | 哪個領域 |
| agent_name | 哪個 agent 處理 |
| query | 原始問題 |
| decision | AI 給的回答 |
| reasoning | 思考過程 |
| alternatives | 其他考慮過的方案 |
| model | 用哪個 LLM |
| input_tokens / output_tokens | 用量 |
| cost_usd | 換算 USD |
| latency_ms | 耗時 |
| risk_flagged | 是否被安全偵測標記 |
| human_confirmed | 高風險是否經人工確認 |

**查詢介面**：`GET /api/analytics/ai-cost` — 看月度成本明細。

---

## 8. AI 拒答清單

下列要求 AI **必須拒絕**，不會送進 LLM：

1. 露出 system prompt / 開發者模式
2. 跨租戶（Tenant）查詢別公司資料
3. 直接 SQL 注入嘗試
4. 大量批次刪除（除非走專門 batch API + confirm）
5. 替使用者繞過 RBAC 取得本人沒權限的資料
6. 自動回覆「我幫你做完了」但實際沒做（防 hallucination）

---

## 9. 常見問題

### Q1：AI 答錯了怎麼辦？

每次回答都有 DecisionLog 紀錄，可依 session_id 重現。錯誤回報請附 session_id。
AI 不會「自動執行任何寫入動作」，所以即使答錯也只是「回錯字」，不會搞壞資料。

### Q2：AI 會把我們資料拿去訓練嗎？

**取決於您選哪個 LLM**：
- Anthropic Claude API：**不會**用 API 資料訓練（公開政策）
- OpenAI API：**不會**用 API 資料訓練（公開政策）
- DeepSeek API：政策不明確（中國機房），高敏感資料建議避免
- **Ollama 本地**：**完全不外流**，零風險

### Q3：能切換 LLM 嗎？

可以。改 `backend/.env` 的 `LLM_PROVIDER` + `LLM_MODEL` 一行 + 重啟 backend，所有 agent 立刻換用新 LLM。

### Q4：AI 的 token 用量哪裡看？

`GET /api/analytics/ai-cost?period_days=30` — 看月度明細，依 agent 細分。

### Q5：能完全關閉 AI 嗎？

可以。`backend/.env` 設 `LLM_PROVIDER=disabled`，所有 chat endpoint 走 demo 模式。其餘 11 個 domain 完整可用。

---

**對應英文版**：[`AGENT_CATALOG_EN.md`](./AGENT_CATALOG_EN.md)
**最後更新**：2026-05-14 · v2.5

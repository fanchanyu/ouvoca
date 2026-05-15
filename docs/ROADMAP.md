# 分階藍圖（ROADMAP）— v3.0 對話式 ERP 版

> **2026-05-15 v3.0 戰略軸轉**：在 v2「客戶導向」基礎上再收斂——
> - 砍掉 **LINE Bot / Mobile App / 外協協同**（v2 Phase 1 全砍）
> - Phase 1 改成 **桌機 Chat 對話式 CRUD**
> - 砍掉 v2 Phase 2 的行動化深化（行動部分）
> - 砍掉 v2 Phase 4 的 LINE Bot 多廠 routing
>
> 「客戶能立刻感受到價值」仍是每個 Phase 的驗收金標準。
>
> 詳細邏輯請見 [CUSTOMER_POSITIONING.md](./CUSTOMER_POSITIONING.md) 與 [MVP_DEFINITION.md](./MVP_DEFINITION.md)。

---

## 全景圖（One-Pager）— v3.0

```
┌──────────────────────────────────────────────────────────────────────┐
│                  MVP 範圍（前 5 個 Phase，含 P0）                       │
│                                                                       │
│   P0 ✅      P1 🔥         P2 💬         P3 🔔         P4 🌐           │
│   基礎      對話式        對話智能       桌機體驗      MESH 收尾       │
│   ERP       CRUD          (Glossary/    (Toast/      (3 任務)         │
│   完成      2 週           Undo)        Email/USB)                    │
│             最高優先       2.5 週        1 週         1 週             │
│                                                                       │
│   ↓ 累計約 6-7 週後具備量產可賣狀態（vs v2 的 10-12 週） ↓             │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
              │
              │ MVP 客戶上線 → 收集真實反饋
              ↓
┌──────────────────────────────────────────────────────────────────────┐
│                  進階階段（依客戶反饋啟動）                              │
│                                                                       │
│   P5 ⏸️ 進階規劃     P6 ⏸️ MES 增強      P7 ⏸️ 行動化重啟              │
│   APS/演算法        OEE/Pegging         LINE / Mobile / 外協           │
│   （只在 200+ 廠     （只在客戶要求       （只在客戶簽約後               │
│    需要時開發）      OEE 時開發）        明確要求時開發）                │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0 ✅ 已完成（ERP 基礎 + Multi-Agent）

**時間**：2026-05-13 ~ 2026-05-15（多個會話）

**交付物**：
- 12 個 domain、58 個 tables、87 個 API endpoints
- 10 個 LLM Agent、26 個工具、16 條 ConstraintChecker
- 8 個前端頁面（含 Login / Sales / Quality / Events / Chat 升級版）
- War-room HTML SSE 即時看板
- Docker Compose 全棧 + Healthcheck
- 完整 seed + .env.example + Alembic async
- **Tool registry 框架 + 11/26 tools 已入新 registry**（會話 #17 開工）

**對 MVP 貢獻**：62%

---

## Phase 1.5 🔌 **外部 DB 串接**（v3.1 並行加入）

**時間**：2 週並行 Phase 1（10.5 工作日）
**目標**：客戶舊系統（鼎新 / 正航 / 叡揚 / Excel）讀得到，AI 對話即可跨 DB 查 + 一次性遷移。

詳見 [EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md](./EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md)。

### Phase 1.5 為什麼最重要

**遷移恐懼是 ERP 採購第一殺手**。沒這能力 demo 過不去；有了 → 「鼎新不用砍，AI 慢慢幫你搬」。

### Phase 1.5 交付清單

| # | 任務 | 工時 | 狀態 |
|---|---|---|---|
| 1.5.1 | Connector framework（base + registry + exceptions） | 0.5d | ✅ 完成（會話 #19） |
| 1.5.2 | SqliteConnector + CsvFolderConnector（PoC） | 0.5d | ✅ 完成 |
| 1.5.3 | external_db_tools.py（list_conn / list_tables / query） | 0.5d | ✅ 完成 |
| 1.5.4 | test_connectors.py（21 tests, 1.36s） | 0.5d | ✅ 完成 |
| 1.5.5 | SqlServerConnector（pyodbc + 鼎新/正航 profile） | 1d | ❌ |
| 1.5.6 | Postgres + MySQL connectors | 1d | ❌ |
| 1.5.7 | RestApiConnector + 叡揚 / SAP B1 profile | 2d | ❌ |
| 1.5.8 | Schema mapping AI（preview_schema_mapping tool） | 2d | ❌ |
| 1.5.9 | migrate_from_external_with_confirm（hard-write） | 1.5d | ❌ |
| 1.5.10 | external_connection DB 表 + 加密儲存 | 1d | ❌ |

**目前**：4/10 完成（PoC 階段 ~40%）。

---

## Phase 1 🔥 **對話式 CRUD**（最高優先）— v3.0

**時間**：2 週（10 工作日）
**目標**：把「Chat 只能查」做到「**Chat 能查/增/改/刪**」。

### 1.1 為什麼這是最高優先

| 原因 | 說明 |
|---|---|
| **這是產品核心承諾** | 「自然語言取代教育訓練」必須做到 CRUD 4/4 |
| **桌機 Chat 是唯一入口** | v3.0 砍 mobile 後，桌機 Chat 必須做到極致 |
| **誤操作恐懼是關鍵障礙** | ConfirmCard + Undo 是說服客戶「敢給員工用」的關鍵 |
| **完成度從 1.5/8 升到 6/8** | 對銷售故事和 demo 都是大躍升 |

### 1.2 交付清單

| # | 任務 | 工時 | 解決誰 | 對應 GAP | 狀態 |
|---|---|---|---|---|---|
| 1.1 | `@register_tool` decorator + RiskTier + Slot 框架 | 0.5d | 全員 | G-101 | ✅ 完成 |
| 1.2 | 26 個 read tool 全部入新 registry | 1.5d | 全員 | G-102 | 🟡 42% |
| 1.3 | ConfirmCard schema（pydantic + endpoint） | 1d | 阿玲 | G-103 | ❌ |
| 1.4 | ConfirmCard 前端組件 | 1d | 阿玲 | G-104 | ❌ |
| 1.5 | hard-write tool: `create_purchase_order_with_confirm` | 1d | 阿玲 | G-105 | ❌ |
| 1.6 | Slot-filling 反問機制 | 1d | 全員 | G-106 | ❌ |
| 1.7 | hard-write tool: `update_sales_order_with_confirm` | 0.5d | 小陳 | G-107 | ❌ |
| 1.8 | hard-write tool: `release_work_order_with_confirm` | 0.5d | 林廠長 | G-108 | ❌ |
| 1.9 | 表格列 Edit / Delete 按鈕 UI（接 AI tool） | 1d | 全員 | G-109 | ❌ |
| 1.10 | E2E demo 錄影（DeepSeek 跑 CRUD 全打通） | 1d | 行銷 | G-110 | ❌ |
| 1.11 | WORKLOG + KNOWLEDGE_MAP 收尾 | 0.5d | – | – | ❌ |

**合計**：10 個工作日（2 週）

### 1.3 新增檔案/模組

```
backend/
├── app/
│   ├── agents/
│   │   ├── registry.py                    ✅ 已建
│   │   ├── confirm_card.py                ❌ Phase 1 Day 2
│   │   └── domains/
│   │       ├── *_tools.py                 🟡 5/8 檔已 refactor
│   │       └── purchase_write_tools.py    ❌ Phase 1 Day 3
│   └── api/
│       └── confirm_card.py                ❌ Phase 1 Day 2

frontend-desktop/
└── src/
    └── components/
        └── ConfirmCard.tsx                ❌ Phase 1 Day 2
```

### 1.4 驗收劇本（必須跑通）

**劇本 A：阿玲下 PO**
1. 阿玲打字「跟長江廠下 100 個 M6 螺絲，交期 5/20」
2. AI 出 ConfirmCard：供應商/品項/單價/總金額/交期
3. 點「確認」→ PO 建立 + 庫存預留 + 林廠長收到 Toast

**劇本 B：林廠長調工單**
1. 林廠長打字「把 WO-XXX 的工序 30 移到機台 M-05」
2. AI 出 ConfirmCard：工單號/工序/原機台→新機台/影響時程
3. 點「確認」→ 工單調整 + audit log

**劇本 C：小陳改交期**
1. 小陳打字「客戶 CUST-A001 下次出貨改 5/22」
2. AI Slot-filling：「請問是 SO-20260514-001 還是 SO-20260514-002?」
3. 小陳回「002」
4. AI 出 ConfirmCard → 確認 → SO 改交期

**劇本 D：王董問狀況**
1. 王董打字「今天賺多少？」
2. AI 回 5 行摘要 + 一張圖（read tool，不需 ConfirmCard）

**劇本 E：誤操作 Undo**（Phase 2 跑通，Phase 1 留 hook）
- 確認 PO 後 30 秒內打「取消剛剛那筆」→ Undo

---

## Phase 2 💬 **對話智能**（讓 AI 不會幻覺）

**時間**：2.5 週（12.5 工作日）
**目標**：把「AI 偶爾講錯」做到「**AI 不會講錯、不會編造、可撤銷**」。

| # | 任務 | 工時 | 對應 GAP |
|---|---|---|---|
| 2.1 | Glossary 表（料件/客戶/供應商同義詞） | 2d | G-201 |
| 2.2 | Disambiguation（多選彈窗） | 2d | G-202 |
| 2.3 | Workflow guide（AI 主動建議下一步） | 1.5d | G-203 |
| 2.4 | Undo（90 秒撤銷） | 2d | G-204 |
| 2.5 | Memory（記使用者偏好） | 1.5d | G-205 |
| 2.6 | Risk Class 4 級完整化 | 1d | G-206 |
| 2.7 | LLM 成本追蹤 + 自動 fallback | 1d | G-207 |
| 2.8 | E2E 滲透測試 + Confidence calibration | 1d | G-208 |

**合計**：12 個工作日

---

## Phase 3 🔔 **桌機體驗補完**

**時間**：1 週（5.5 工作日）
**目標**：把「Chat 是唯一入口」做到「**Chat + 必要桌機輔助**」。

| # | 任務 | 工時 | 對應 GAP |
|---|---|---|---|
| 3.1 | 桌面 Toast 通知（Browser Notification API） | 1d | G-301 |
| 3.2 | 每日 Email 摘要（cron + SMTP） | 1d | G-302 |
| 3.3 | USB 條碼槍輸入頁（盤點/收料） | 1.5d | G-303 |
| 3.4 | 列印模組（QR 標籤、出貨單） | 1d | G-304 |
| 3.5 | Chat 語音輸入（Whisper API） | 1d | G-305 |

---

## Phase 4 🌐 MESH 多廠收尾

**時間**：1 週（5 工作日）
**目標**：補完 v2 已 80% 的 MESH，不做 LINE Bot 多廠 routing（v3.0 砍）。

| # | 任務 | 工時 | 對應 GAP |
|---|---|---|---|
| 4.1 | Factory Node 接 Ollama 本地 LLM | 2d | G-401 |
| 4.2 | HQ ↔ Factory 結構化查詢協議補完 | 1d | G-402 |
| 4.3 | 多廠庫存聚合 Chat tool | 1d | G-403 |
| 4.4 | VPN/SSL 加固 + 認證 | 1d | G-404 |

### 4.A VMI 經典場景（v3.0 更新）

劇本：
1. HQ 王董桌機 Chat「全廠 M6 螺絲庫存」
2. AI tool 並發查詢主廠 / 分廠 A / 分廠 B
3. 各廠本地 LLM 解析 → 查本地 DB → 回傳**聚合數字**
4. HQ 聚合 → AI 回王董「總計 7300，主廠 3000 / 分廠 A 2500 / 分廠 B 1800」

**核心安全**：原始資料**不離廠**。

---

## MVP 完成節點（Phase 0~4 累計）— v3.0

**累計工時**：~33 工作日 = **6-7 週**（vs v2 的 10-12 週，省 4-5 週）
**功能完成度**：MVP 6 大功能 100%

**此時可以**：對外銷售、接 3-5 個試點客戶、收集真實反饋。

---

## Phase 5+ ⏸️ 進階階段（按客戶反饋啟動）

> ⚠️ **此 Phase 之後的功能不主動開發**。
> 等 MVP 上線、收集 5+ 客戶反饋，才決定優先級。

### Phase 5 候選功能（憑客戶投票決定）

| 候選功能 | 對應 PDF 章節 | 觸發條件 |
|---|---|---|
| APS/FCS 三向排程 | §6.4 | 客戶廠成長到 150+ 人 |
| RCCP/CRP 細產能 | §6.2-6.3 | 客戶要求 OEE 分析 |
| 演算法引擎（GA/SA/TS） | §10 | 學術合作或大廠合作 |
| S&OP 月度產銷 | §3 | 50+ 員工廠需求 |
| What-if 多情境模擬 | §7.5 | 客戶決策支援需求 |
| 複雜成本會計 | – | 客戶上市櫃 |
| MPS 完整時間柵欄 | §2.3 | 客戶要求 |
| MRP 多階遞迴 + 批量規則 | §5.3, §5.6 | 客戶要求 |

### Phase 6 候選（按客戶反饋）

- MES 完整化（OEE / Pegging / Andon）
- 全流程追溯（Lot/Serial 正反向）
- 設備接機台 PLC/SCADA

### Phase 7 候選 — 行動化重啟（**v3.0 砍的功能在這復活**）

| 候選功能 | 觸發條件 |
|---|---|
| **LINE Bot Webhook + 老闆儀表板** | 5+ 客戶要 LINE 介面 |
| **Mobile App（Expo / PWA）** | 5+ 客戶要行動端 |
| **外協 QR + LINE 回報** | 5+ 客戶有外協協同需求 |
| **Speech-to-Text 行動端** | 配合 Mobile 上線 |

---

## 時程總覽 — v3.0

| Phase | 名稱 | 工時 | 累計 | 預計完成 | 對 MVP 貢獻 |
|---|---|---|---|---|---|
| P0 | 基礎 ERP + Multi-Agent | – | – | ✅ 已完成 | 62% |
| **P1** | **🔥 對話式 CRUD** | 10d | 10d | ~ 2026-05-30 | +20% → **82%** |
| **P2** | **💬 對話智能** | 12d | 22d | ~ 2026-06-20 | +10% → **92%** |
| **P3** | **🔔 桌機體驗** | 5.5d | 27.5d | ~ 2026-06-30 | +5% → **97%** |
| **P4** | **🌐 MESH 多廠** | 5d | 32.5d | ~ 2026-07-10 | +3% → **100%** |
| — | **🎯 MVP 完成、開始接客戶** | – | – | **~ 2026-07 月** | — |
| P5+ | 進階功能（依反饋啟動） | TBD | – | – | – |
| P7 | 行動化重啟（如客戶要） | TBD | – | – | – |

---

## 關鍵依賴

```
P0 (基礎) ──→ P1 (對話式 CRUD) ──→ P2 (對話智能) ──→ MVP 上線
                  │                       │
                  │                       ↓
                  │                  P3 (桌機體驗補完)
                  │                       │
                  ↓                       ↓
              P4 (MESH 收尾)         真實客戶反饋
                                          │
                                          ↓
                                   P5+ (依反饋啟動)
                                   P7 (行動化重啟，如客戶要)
```

---

## 重要原則

1. **Phase 1-4 是 MVP**：必須做完且做好。
2. **Phase 5+ 不主動**：等 5 個客戶有相同需求才開發。
3. **每個 Phase 都要能演示給王董看**：不能演示 = 沒做完。
4. **每個功能都要對應 persona**：找不到 persona = 不做。
5. **客戶反饋 > 我們的想像**：定期訪談客戶，更新優先級。
6. **v3.0 新增**：能砍就砍，mediocre × 3 不如 excellent × 1。

---

## v1 → v2 → v3 變更摘要

| 項目 | v1（理論導向） | v2（客戶導向） | v3（對話式 ERP） |
|---|---|---|---|
| **Phase 1 主題** | 規劃層完整化 | LINE-Native + 行動化 | **對話式 CRUD** |
| **Phase 2 主題** | APS + 三元排程 | 行動化深化 | **對話智能** |
| **Phase 3 主題** | MES 增強 | 規劃層精簡 | **桌機體驗補完** |
| **Phase 4 主題** | 演算法引擎 | MESH 多廠 | **MESH 多廠收尾** |
| **Phase 5+ 主題** | S&OP | 進階候選池 | **進階候選池 + 行動化重啟** |
| **核心信念** | PDF 七層全做才完整 | 客戶痛點解決就 OK | **單一 DNA + 對話優先** |
| **核心新增** | 演算法 / S&OP | LINE / Mobile / 外協 | **ConfirmCard / Slot-filling / Undo** |
| **核心移除** | – | RCCP / APS / 演算法 | **LINE Bot / Mobile / 外協** |
| **MVP 累計工時** | ~80d | ~50d | **~33d**（省 17 天） |

---

**最後更新**：2026-05-15（v3.0：5 個 Phase 全部重排 + 行動化降到 P7）

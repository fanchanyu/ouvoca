# 系統差距分析（GAP Analysis）— v3.0 對話式 ERP 版

> **本檔目的**：把所有可能的差距（PDF 理論 + 客戶導向實務）以單一表盤點，明確哪些是 MVP 必做、哪些等客戶要求才做。
>
> **2026-05-15 v3.0 改版**：戰略軸轉砍掉 mobile/LINE/外協，原 v2 的 G-101~G-112 + G-201~G-207 + G-303 + G-406 共 22 項全部移到 Phase 7（行動化重啟，等客戶反饋）。
> v3.0 新增 G-101~G-208 + G-301~G-305 共 16 項對話式 ERP 缺口。

---

## 1. 優先級規範

| 級別 | 意義 | 觸發條件 |
|---|---|---|
| **P0 Critical** | MVP 必做、阻塞客戶採用 | Phase 1-2 |
| **P1 High** | MVP 強化、提升體驗 | Phase 2-3 |
| **P2 Medium** | 完整性需要、可延後 | Phase 3-4 |
| **P3 Low** | 加分項、非必須 | Phase 4 |
| **P5+ Deferred** | 等客戶反饋才開發 | Phase 5+（暫緩） |
| **P7 Deferred-Mobile** | v3.0 砍的 mobile/LINE/外協，客戶要才復活 | Phase 7 |

---

## 2. Phase 1（最高優先）— 對話式 CRUD

### G-101 Tool registry framework
- **嚴重度**：P0 Critical
- **狀態**：✅ 已完成（會話 #17 Wave 1）
- **解決誰**：全員
- **應有**：
  - `@register_tool` decorator + `RiskTier` enum + `Slot` + `ToolMeta`
  - 強制 hard-write 必有 `required_permission`
  - 向後兼容舊 `engine.register_tool()`
- **檔案**：`backend/app/agents/registry.py`, `tests/smoke/test_tool_registry.py`
- **工時**：0.5 天

### G-102 26 read tool 入新 registry
- **嚴重度**：P0 Critical
- **狀態**：🟡 42%（11/26 完成）
- **解決誰**：全員
- **應有**：
  - inventory ×3 ✅ / sales 部分 / purchase ×3 ✅ / production ×4 ✅
  - 待 refactor：accounting / quality / warehouse / crm / mps_mrp / general / sales 後半段（15 個）
- **檔案**：`backend/app/agents/domains/*_tools.py`
- **工時**：1.5 天

### G-103 ConfirmCard schema + endpoint
- **嚴重度**：P0 Critical
- **狀態**：❌
- **解決誰**：阿玲、林廠長、小陳
- **應有**：
  - pydantic `ConfirmCardSchema`（含 tool_name, slots, risk_tier, confirm_url, cancel_url, ttl）
  - `POST /api/agents/confirm/{card_id}` 後端 endpoint
  - `redis://` 暫存（5 分鐘 TTL）
- **檔案**：`app/agents/confirm_card.py`, `app/api/confirm_card.py`
- **工時**：1 天

### G-104 ConfirmCard 前端組件
- **嚴重度**：P0 Critical
- **狀態**：❌
- **應有**：
  - Chat 訊息流中彈出卡片（含 slot 表格 + 確認/取消按鈕）
  - 點確認 → POST confirm_url → 回 Chat
  - 過期自動消失
- **檔案**：`frontend-desktop/src/components/ConfirmCard.tsx`
- **工時**：1 天

### G-105 第一個 hard-write tool: `create_purchase_order_with_confirm`
- **嚴重度**：P0 Critical
- **狀態**：❌
- **解決誰**：阿玲
- **應有**：
  - 接「跟 X 廠下 N 個 Y 料，交期 Z」
  - 缺欄位走 Slot-filling 反問
  - 出 ConfirmCard 給人類確認
  - 確認後呼叫 `create_purchase_order` service
- **工時**：1 天

### G-106 Slot-filling 反問機制
- **嚴重度**：P0 Critical
- **狀態**：❌
- **應有**：
  - LLM tool call 時 detect 缺漏 required slot
  - 自動回反問訊息（不執行）
  - 最多 3 次反問後 fallback「請改用表單頁面」
- **工時**：1 天

### G-107 hard-write tool: `update_sales_order_with_confirm`
- **嚴重度**：P0 Critical
- **解決誰**：小陳
- **工時**：0.5 天

### G-108 hard-write tool: `release_work_order_with_confirm`
- **嚴重度**：P0 Critical
- **解決誰**：林廠長
- **工時**：0.5 天

### G-109 表格列 Edit / Delete 按鈕 UI
- **嚴重度**：P1 High
- **應有**：
  - 表格每列加 ✏️ / 🗑 按鈕
  - 點下去也走 AI tool（轉成 Chat 對話 + ConfirmCard）
  - 統一所有「寫入」路徑
- **工時**：1 天

### G-110 E2E demo 錄影
- **嚴重度**：P1 High
- **應有**：
  - 12 query + 4 個 CRUD 場景全跑通
  - DeepSeek 真實 API
  - 螢幕錄影 + Markdown summary
- **工時**：1 天

---

## 3. Phase 2 — 對話智能

### G-201 Glossary 表（料件/客戶/供應商同義詞）
- **嚴重度**：P0 Critical
- **應有**：
  - DB 表 `glossary`（term, canonical_id, domain, language）
  - LLM pre-translation：使用者輸入先過 glossary 替換
  - 管理頁面（CRUD glossary）
- **工時**：2 天

### G-202 Disambiguation（多選彈窗）
- **嚴重度**：P0 Critical
- **應有**：
  - tool call 回 N 個 candidate 時自動彈出選擇 UI
  - 「中華」→「中華汽車 / 中華電信 / 中華工程」
  - 選擇後記憶該 session 後續用同一個
- **工時**：2 天

### G-203 Workflow guide
- **嚴重度**：P1 High
- **應有**：
  - 完成某操作後 AI 主動建議下一步
  - 「建好 PO 了，要寄通知給供應商嗎？」
- **工時**：1.5 天

### G-204 Undo（90 秒撤銷）
- **嚴重度**：P0 Critical
- **應有**：
  - audit log 加 `undo_recipe` 欄位
  - 「取消剛剛那筆」自動找最近 90s 內 hard-write 紀錄
  - 出 ConfirmCard 確認後執行反向操作
- **工時**：2 天

### G-205 Memory（記使用者偏好）
- **嚴重度**：P1 High
- **應有**：
  - 記住「阿玲常買的供應商是長江」「小陳常用的客戶是 CUST-A001」
  - 下次相關操作自動帶入
- **工時**：1.5 天

### G-206 Risk Class 4 級完整化
- **嚴重度**：P1 High
- **應有**：
  - read / soft-write / hard-write / dangerous 四級
  - dangerous（如刪資料、改大金額）一律雙人確認
- **工時**：1 天

### G-207 LLM 成本追蹤儀表板
- **嚴重度**：P1 High
- **應有**：
  - 每次 call 記 cost
  - 超閾值自動 fallback 廉價模型
  - admin 頁面看每日/每月成本
- **工時**：1 天

### G-208 Confidence calibration + 滲透測試
- **嚴重度**：P1 High
- **應有**：
  - LLM 出 tool call 帶 confidence 分數
  - 低於 0.7 強制反問確認
  - prompt injection 攻擊測試集
- **工時**：1 天

---

## 4. Phase 3 — 桌機體驗補完

### G-301 桌面 Toast 通知
- **嚴重度**：P0 Critical
- **應有**：
  - Browser Notification API
  - SSE → Toast / Desktop Notification
  - 訂閱主題（缺料 / 異常 / 急單）
- **工時**：1 天

### G-302 每日 Email 摘要
- **嚴重度**：P1 High
- **應有**：
  - cron 每天 07:00 跑
  - 給王董寄昨日摘要
  - SMTP / SendGrid
- **工時**：1 天

### G-303 USB 條碼槍輸入頁
- **嚴重度**：P1 High
- **應有**：
  - 條碼槍刷碼 → 自動填入表單
  - 盤點頁、收料頁、發料頁都支援
- **工時**：1.5 天

### G-304 列印模組（QR 標籤、出貨單）
- **嚴重度**：P2 Medium
- **應有**：
  - 儲位標籤、料件標籤、出貨單
  - HTML A4 + 熱感應紙 template
- **工時**：1 天

### G-305 Chat 語音輸入（Whisper）
- **嚴重度**：P2 Medium
- **應有**：
  - 桌機麥克風 → Whisper API → 文字 → Chat
  - 中文（繁體）優先
- **工時**：1 天

---

## 5. Phase 1.5 — 外部 DB 串接（v3.1 補強）

### G-501 Connector framework
- **嚴重度**：P0 Critical
- **狀態**：✅ 已完成（會話 #19）
- **檔案**：`backend/app/integrations/connectors/{base,registry,exceptions}.py`
- **工時**：0.5 天

### G-502 SqliteConnector + CsvFolderConnector PoC
- **嚴重度**：P0 Critical
- **狀態**：✅ 已完成
- **檔案**：`backend/app/integrations/connectors/{sqlite,csv}_connector.py`
- **工時**：0.5 天

### G-503 3 個 read tool（list_conn / list_tables / query）
- **嚴重度**：P0 Critical
- **狀態**：✅ 已完成
- **檔案**：`backend/app/agents/domains/external_db_tools.py`
- **工時**：0.5 天

### G-504 Smoke tests
- **嚴重度**：P0 Critical
- **狀態**：✅ 已完成（21 tests, 1.36s）
- **檔案**：`backend/tests/smoke/test_connectors.py`
- **工時**：0.5 天

### G-505 SqlServerConnector（pyodbc）
- **嚴重度**：P0 Critical
- **解決誰**：阿玲、王董（接鼎新 / 正航）
- **工時**：1 天

### G-506 Postgres + MySQL connectors
- **嚴重度**：P1 High
- **工時**：1 天

### G-507 RestApiConnector + 叡揚 / SAP B1 profile
- **嚴重度**：P1 High
- **工時**：2 天

### G-508 Schema mapping AI（preview_schema_mapping tool）
- **嚴重度**：P0 Critical
- **應有**：AI 看外部 table schema → 自動推薦 LLM-ERP domain 對映
- **工時**：2 天

### G-509 migrate_from_external_with_confirm
- **嚴重度**：P0 Critical
- **應有**：hard-write tool，出 ConfirmCard 給人類確認筆數 + 衝突策略
- **工時**：1.5 天

### G-510 external_connection DB 表 + 加密儲存
- **嚴重度**：P1 High
- **應有**：把 in-memory dict 換成 DB 表，password / connection string AES 加密
- **工時**：1 天

---

## 6. Phase 4 — MESH 多廠收尾

### G-401 Factory Node 本地 LLM
- **嚴重度**：P2 Medium
- **應有**：Factory Node 接 Ollama（如 Qwen2.5:7B）
- **工時**：2 天

### G-402 HQ ↔ Factory 結構化查詢協議
- **嚴重度**：P2 Medium
- **應有**：定義 JSON Schema 查詢協議
- **工時**：1 天

### G-403 多廠庫存聚合 Chat tool
- **嚴重度**：P2 Medium
- **應有**：HQ Chat 看得到全廠合計、各廠分項
- **工時**：1 天

### G-404 VPN/SSL 加固
- **嚴重度**：P2 Medium
- **應有**：WireGuard 或 OpenVPN + mTLS
- **工時**：1 天

---

## 6. Phase 5+ ⏸️ 進階階段（暫緩）

> 以下 PDF 理論缺口**原本是 v1 Phase 1-4 必做**，現在依客戶定位**降級到 Phase 5+**，等客戶要求才做。

### 來自 v1 的延後項

| 編號 | 原 v1 名稱 | 對應 PDF | 延後原因 | 觸發條件 |
|---|---|---|---|---|
| ~~G-001~~ | MPS 完整時段化 | §4.3 | 小廠不需要時間柵欄 | 客戶要求 |
| ~~G-002~~ | MRP 多階遞迴 | §5.3 | 小廠 BOM 多在 2 階 | 4+ 階 BOM 客戶 |
| ~~G-004~~ | MRP 提前期偏移 | §5.5 | 小廠多固定庫存 | 客戶要求 |
| ~~G-005~~ | MRP 4 種批量規則 | §5.6 | 小廠用逐批訂購 | 客戶要求 |
| ~~G-006~~ | MRP 行動訊息 5 種 | §5.7 | Cancel/Firm 用不到 | 客戶要求 |
| ~~G-007~~ | RCCP 粗產能 | §6.2 | 機台少，目視管理夠 | 客戶要求 OEE |
| ~~G-008~~ | 8 種派工規則 | §9.3 | 老師傅憑經驗排得快 | 客戶要求 |
| ~~G-009~~ | 時間柵欄強制 | §2.3 | 太重 | 客戶要求 |
| ~~G-010~~ | APS 三向排程 | §6.4 | 太重 | 150+ 人廠 |
| ~~G-011~~ | 三元排程人維度 | §11 | 太重 | 多技能廠 |
| ~~G-012~~ | 機台換線矩陣 | §11.3 | 太重 | 客戶要求 |
| ~~G-013~~ | APS What-if | §7.5 | 太重 | 決策支援需求 |
| ~~G-014~~ | APS 多目標最佳化 | §7.4 | 太重 | 客戶要求 |
| ~~G-015~~ | OEE 計算 | §8.5 | 小廠少用 | 客戶要求 |
| ~~G-016~~ | Pegging 追溯 | §5.7 | 小廠少用 | 客戶要求 |
| ~~G-018~~ | GA/SA/TS/RL 演算法 | §10 | 太重 | 學術合作 |
| ~~G-023~~ | S&OP 銷售與作業規劃 | §3 | 50+ 員工才需要 | 客戶要求 |
| ~~G-024~~ | 看板與拉式生產 | §9.5 | 太重 | 客戶要求 |

---

## 7. Phase 7 ⏸️ 行動化重啟（v3.0 砍的功能在這復活）

> ⚠️ 以下 v2 規劃的 mobile/LINE/外協項目於 2026-05-15 戰略軸轉**全部移到 Phase 7**。
> 復活條件：**5+ 客戶簽約後明確要求行動端**。

| 編號 | v2 原名稱 | 砍除原因 | 復活條件 |
|---|---|---|---|
| ~~G-101~~ (v2) | LINE Bot Webhook 接入 | 桌機 Chat 已涵蓋 | 5+ 客戶要 LINE |
| ~~G-102~~ (v2) | LINE Bot 老闆儀表板 | 桌機 Chat + Email 摘要替代 | 同上 |
| ~~G-103~~ (v2) | LINE Bot 自然語言查詢 | 桌機 Chat 已涵蓋 | 同上 |
| ~~G-104~~ (v2) | LINE Bot 推播警示 | 桌面 Toast + Email 替代 | 同上 |
| ~~G-105~~ (v2) | Expo Mobile App 骨架 | 桌機 Chat 涵蓋 80% 場景 | 5+ 客戶要行動端 |
| ~~G-106~~ (v2) | Mobile 登入 + 儀表板 + 庫存 | 同上 | 同上 |
| ~~G-107~~ (v2) | Mobile 工單列表 + 推播訂閱 | 同上 | 同上 |
| ~~G-108~~ (v2) | 外協工序 model + API | 4 persona 全砍 老吳 | 5+ 客戶要外協 |
| ~~G-109~~ (v2) | 外協 QR 派工單列印頁 | 同上 | 同上 |
| ~~G-110~~ (v2) | LINE Bot 外協回報 | 同上 | 同上 |
| ~~G-111~~ (v2) | 行動端語音輸入 | 桌機 Whisper 替代 | 配合 Mobile 上線 |
| ~~G-112~~ (v2) | LINE Bot 業務工具 | 桌機 Chat 已涵蓋 | 5+ 客戶要 LINE |
| ~~G-201~~ (v2) | Mobile 掃 QR 盤點 | USB 條碼槍替代 | 客戶要相機掃碼 |
| ~~G-202~~ (v2) | Mobile 報工頁 | 桌機接條碼槍替代 | 客戶要現場掃碼 |
| ~~G-203~~ (v2) | Mobile 收料頁 | 桌機接條碼槍替代 | 同上 |
| ~~G-204~~ (v2) | MinIO 圖片儲存 | v3.0 暫不需要拍照 | 客戶要拍照存證 |
| ~~G-205~~ (v2) | Push Notification（FCM/APNs） | 桌面 Toast + Email 替代 | 5+ 客戶要行動推播 |
| ~~G-206~~ (v2) | 列印模組（行動端） | 桌機列印 G-304 替代 | – |
| ~~G-303~~ (v2) | LINE Bot MRP 推播 | Email 摘要替代 | – |
| ~~G-406~~ (v2) | LINE Bot 多廠 routing | – | – |

---

## 8. 進度追蹤總表（v3.0）

| Phase | P0 Critical | P1 High | P2 Medium | 合計 | 預估工時 |
|---|---|---|---|---|---|
| **Phase 1（對話式 CRUD）** | G-101~G-108（8 項） | G-109, G-110（2 項） | – | 10 項 | ~10 天 |
| **Phase 2（對話智能）** | G-201, G-202, G-204（3 項） | G-203, G-205~G-208（5 項） | – | 8 項 | ~12 天 |
| **Phase 3（桌機體驗）** | G-301（1 項） | G-302, G-303（2 項） | G-304, G-305（2 項） | 5 項 | ~5.5 天 |
| **Phase 4（MESH 收尾）** | – | – | G-401~G-404（4 項） | 4 項 | ~5 天 |
| **Phase 5+ 暫緩** | – | – | – | ~18 項 | TBD |
| **Phase 7 行動化重啟** | – | – | – | 20 項 | TBD |
| **MVP 合計** | **12** | **9** | **6** | **27 項** | **~32.5 天** |

---

## 9. Phase 1 啟動清單（可立即動工）

### 第 1 週（CRUD 基礎）
- [x] G-101 Tool registry framework（0.5d）✅ 完成
- [ ] G-102 15 個 read tool refactor（1.5d）🟡 7/15 完成
- [ ] G-103 ConfirmCard schema（1d）
- [ ] G-104 ConfirmCard 前端組件（1d）
- [ ] G-105 create_purchase_order_with_confirm（1d）

### 第 2 週（CRUD 完整化）
- [ ] G-106 Slot-filling 反問（1d）
- [ ] G-107 update_sales_order_with_confirm（0.5d）
- [ ] G-108 release_work_order_with_confirm（0.5d）
- [ ] G-109 Edit / Delete 按鈕 UI（1d）
- [ ] G-110 E2E demo 錄影（1d）

---

## 10. 變更紀錄

| 日期 | 改動 |
|---|---|
| 2026-05-14 v1 | 初始 27 個 PDF 理論缺口（G-001~G-027） |
| 2026-05-14 v2 | 客戶定位明確化，新增 G-101~G-406 共 25 個客戶導向缺口；原 G-001~G-027 多數延後到 Phase 5+ |
| **2026-05-15 v3** | **戰略軸轉**：砍 22 項 mobile/LINE/外協缺口到 Phase 7；重新編號 16 個對話式 ERP 缺口（G-101~G-208 + G-301~G-305） |

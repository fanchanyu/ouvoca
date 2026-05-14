# 系統差距分析（GAP Analysis）— v2 客戶導向版

> **本檔目的**：把所有可能的差距（PDF 理論 + 客戶導向實務）以單一表盤點，明確哪些是 MVP 必做、哪些等客戶要求才做。
>
> **2026-05-14 v2 改版**：基於客戶定位（50-100 人小型製造業），新增 G-100~G-499 序列（客戶導向缺口），原 G-001~G-027（PDF 理論缺口）多數改為 P5+ 延後。

---

## 1. 優先級規範

| 級別 | 意義 | 觸發條件 |
|---|---|---|
| **P0 Critical** | MVP 必做、阻塞客戶採用 | Phase 1-2 |
| **P1 High** | MVP 強化、提升體驗 | Phase 2-3 |
| **P2 Medium** | 完整性需要、可延後 | Phase 3-4 |
| **P3 Low** | 加分項、非必須 | Phase 4 |
| **P5+ Deferred** | 等客戶反饋才開發 | Phase 5+（暫緩） |

---

## 2. Phase 1（最高優先）— LINE-Native + 行動化

### G-101 LINE Bot Webhook 接入
- **嚴重度**：P0 Critical
- **解決誰**：王董、小陳、林廠長、阿玲、老吳（全員）
- **應有**：
  - LINE Channel + Messaging API
  - `/api/line/webhook` 接 LINE 推送
  - 訊息簽章驗證（HMAC SHA256）
  - LINE User ↔ Employee 綁定 model
- **檔案**：`app/integrations/line_bot/webhook.py`, `app/models/line_binding.py`
- **工時**：2 天
- **驗收**：LINE 加 ERP 官方帳號，輸入員工編號完成綁定

### G-102 LINE Bot 老闆儀表板
- **嚴重度**：P0 Critical
- **解決誰**：王董
- **應有**：
  - 每日 7:00 自動推「昨日摘要」Flex Message
  - 包含：出貨 / 應收 / 工單進度 / 庫存警示 / 待辦
  - 點擊可展開詳情
- **檔案**：`app/agents/domains/boss_dashboard_tools.py`, `app/integrations/line_bot/push.py`
- **工時**：2 天
- **驗收**：劇本 A 跑通

### G-103 LINE Bot 自然語言查詢
- **嚴重度**：P0 Critical
- **解決誰**：全員
- **應有**：
  - LINE 文字訊息 → Multi-Agent → 回覆
  - 支援 26 個現有 tools
  - 回覆格式為 Flex Message（可點擊）
- **檔案**：`app/integrations/line_bot/intent.py`
- **工時**：1.5 天

### G-104 LINE Bot 推播警示
- **嚴重度**：P0 Critical
- **解決誰**：王董、林廠長
- **應有**：
  - 訂閱事件（庫存警示 / 工單延遲 / 品質異常 / 大金額 PO）
  - 依角色路由（沿用現有 NotificationDispatcher）
  - 推 LINE Flex Message
- **檔案**：`app/services/notification.py`
- **工時**：1.5 天

### G-105 Expo Mobile App 骨架
- **嚴重度**：P0 Critical
- **解決誰**：小陳、林廠長、阿玲
- **應有**：
  - Expo SDK 49+
  - React Native + TypeScript
  - 共用 backend API（沿用 frontend-desktop/src/lib/api.ts 結構）
  - Zustand auth store
  - React Navigation
- **檔案**：`frontend-mobile/*`（新建專案）
- **工時**：2 天

### G-106 Mobile 登入 + 儀表板 + 庫存
- **嚴重度**：P0 Critical
- **解決誰**：小陳
- **應有**：
  - Login 頁（含 Demo Mode）
  - Dashboard（卡片式統計）
  - Inventory 列表 + 搜尋 + 詳情頁
- **工時**：2 天

### G-107 Mobile 工單列表 + 推播訂閱
- **嚴重度**：P0 Critical
- **解決誰**：林廠長
- **應有**：
  - WorkOrders 列表 + 篩選（狀態/優先級）
  - 詳情頁 + 一鍵釋放
  - 推播訂閱設定頁
- **工時**：1.5 天

### G-108 外協工序 model + API
- **嚴重度**：P0 Critical
- **解決誰**：林廠長、老吳
- **應有**：
  - `OutsourceOrder`（外協工單）
  - `OutsourceReport`（回報紀錄）
  - QR token 產生 + 驗證
  - API：建立 / 列印 / 回報
- **檔案**：`app/models/outsource.py`, `app/services/outsource.py`, `app/api/outsource.py`
- **工時**：1.5 天

### G-109 外協 QR 派工單列印頁
- **嚴重度**：P0 Critical
- **解決誰**：林廠長
- **應有**：
  - HTML 列印模板（A4 / 熱感應紙都可）
  - 含 QR Code（編碼 OS-XXX）
  - 含派工資訊（品名/數量/交期/聯絡人）
- **檔案**：`print-templates/outsource_dispatch.html`
- **工時**：1 天

### G-110 LINE Bot 外協回報
- **嚴重度**：P0 Critical
- **解決誰**：老吳
- **應有**：
  - 不需註冊（QR 內含 token，限定該外協使用）
  - 流程：選單 → 掃 QR → 輸入數量 → 拍照 → 送出
  - 完成後自動 emit 事件
- **工時**：2 天

### G-111 語音輸入整合
- **嚴重度**：P1 High（建議 Phase 1 做，可延 Phase 2）
- **解決誰**：小陳、老吳
- **應有**：
  - Whisper API 或本地 Whisper.cpp
  - Mobile App + LINE Bot 都支援語音訊息
  - 中文（繁體）優先
- **工時**：1.5 天

### G-112 LINE Bot 業務工具
- **嚴重度**：P0 Critical
- **解決誰**：小陳
- **應有**：
  - 「客戶 X 的歷史價格」
  - 「產品 Y 下月可承諾交期」
  - 「應收 X 客戶現況」
- **工時**：1 天

---

## 3. Phase 2 — 行動化深化

### G-201 Mobile 掃 QR 盤點頁
- **嚴重度**：P0 Critical
- **解決誰**：阿玲
- **應有**：
  - 相機掃 QR → 自動跳出儲位 + 系統量
  - 輸入實際量 → 自動算差異
  - 拍照存證
  - 差異 > 5% 自動標記異常
- **工時**：2 天

### G-202 Mobile 報工頁
- **嚴重度**：P0 Critical
- **解決誰**：作業員
- **應有**：
  - 掃 QR 開工（記錄機台、人員、時間）
  - 掃 QR 完工（輸入完工數、不良數）
  - 不良時必填原因
- **工時**：2 天

### G-203 Mobile 收料頁
- **嚴重度**：P1 High
- **解決誰**：阿玲
- **應有**：
  - 掃 QR 自動帶出 PO 資訊
  - 輸入收貨量 → 自動更新 PO + 庫存
  - 拍照存證
- **工時**：1.5 天

### G-204 圖片儲存（MinIO）
- **嚴重度**：P1 High
- **應有**：
  - MinIO 整合（自架 S3）
  - 拍照上傳 + URL 儲存
  - 圖片壓縮
- **工時**：1.5 天

### G-205 Push Notification
- **嚴重度**：P0 Critical
- **應有**：
  - FCM（Android）+ APNs（iOS）
  - Token 註冊 + 訂閱主題
  - 與 LINE Bot 並行（使用者可選擇）
- **工時**：1.5 天

### G-206 列印模組強化
- **嚴重度**：P1 High
- **應有**：
  - QR 標籤（儲位 / 物料）
  - 出貨單
  - 採購單
- **工時**：2 天

### G-207 LLM 寫入工具擴充
- **嚴重度**：P0 Critical
- **應有**：
  - 5+ 寫入類 tools
  - 每個寫入操作走 ConstraintChecker
  - LINE confirmation flow（「確認要執行 X 嗎？」按鈕）
- **工時**：2 天

---

## 4. Phase 3 — 規劃層精簡版

### G-001（簡化版）MPS 時段化
- **嚴重度**：P1 High
- **應有**：簡化版 PAB/ATP，**不做時間柵欄**
- **工時**：1.5 天

### G-002（簡化版）MRP 2 階展開
- **嚴重度**：P1 High
- **應有**：只展 2 階（小廠 BOM 多在 2 階以內）
- **工時**：1 天

### G-003 MRP 淨需求公式
- **嚴重度**：P1 High
- **應有**：完整公式（毛 - 在手 - 在途 + 已分配 + 安全）
- **工時**：1 天

### G-006（簡化版）MRP 行動訊息
- **嚴重度**：P1 High
- **應有**：3 種訊息（Release / Reschedule In / Reschedule Out），不做 Cancel/Firm
- **工時**：1 天

### G-301 簡易產能負載視覺化
- **嚴重度**：P1 High
- **應有**：甘特圖前端，**不做 FCS 演算法**
- **工時**：2 天

### G-302 補貨建議 → 一鍵 PO
- **嚴重度**：P1 High
- **應有**：低於 ROP 自動產生 ReplenishSuggestion，一鍵轉 PO
- **工時**：1 天

### G-303 LINE Bot MRP 推播
- **嚴重度**：P1 High
- **應有**：MRP 跑完後 LINE 通知採購
- **工時**：1 天

---

## 5. Phase 4 — MESH 多廠

### G-401 Factory Node 本地 LLM
- **嚴重度**：P2 Medium
- **應有**：Factory Node 接 Ollama（如 Qwen2.5:7B）
- **工時**：2 天

### G-402 HQ ↔ Factory 結構化查詢協議
- **嚴重度**：P2 Medium
- **應有**：定義 JSON Schema 查詢協議
- **工時**：2 天

### G-403 多廠庫存聚合 dashboard
- **嚴重度**：P2 Medium
- **應有**：HQ 看得到全廠合計、各廠分項
- **工時**：1.5 天

### G-404 VPN/SSL 加固
- **嚴重度**：P2 Medium
- **應有**：WireGuard 或 OpenVPN + mTLS
- **工時**：1.5 天

### G-405 LLM 多廠查詢
- **嚴重度**：P2 Medium
- **應有**：HQ Bot 並發查 N 個廠 → 聚合
- **工時**：2 天

### G-406 LINE Bot 多廠 routing
- **嚴重度**：P2 Medium
- **應有**：依使用者所屬廠路由查詢
- **工時**：1.5 天

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
| ~~G-017~~ | Andon 異常通知 | §8.3 | LINE 推播已替代 | 客戶要求 |
| ~~G-018~~ | GA 演算法 | §10.3 | 太重 | 學術合作 |
| ~~G-019~~ | SA 演算法 | §10.4 | 太重 | 學術合作 |
| ~~G-020~~ | TS 演算法 | §10.2 | 太重 | 學術合作 |
| ~~G-021~~ | RL 演算法 | §10.2 | 太重 | 學術合作 |
| ~~G-022~~ | 8 種排程績效指標 | §13.2 | 太重 | 客戶要求 |
| ~~G-023~~ | S&OP 銷售與作業規劃 | §3 | 50+ 員工才需要 | 客戶要求 |
| ~~G-024~~ | 看板與拉式生產 | §9.5 | 太重 | 客戶要求 |
| ~~G-025~~ | 排程問題分類器 | §13.1 | 太學術 | 永遠不做 |
| ~~G-026~~ | 完工自動入庫 | §12.5 | 改為手動 + Mobile 報工 | Phase 2 已包含 |
| ~~G-027~~ | 成本結算差異分析 | §12.5 | 小廠多用年底盤 | 客戶上市櫃 |

---

## 7. 進度追蹤總表

| Phase | P0 Critical | P1 High | P2 Medium | 合計 | 預估工時 |
|---|---|---|---|---|---|
| **Phase 1** | G-101~G-110, G-112（11 項） | G-111（1 項） | – | 12 項 | ~19 天 |
| **Phase 2** | G-201, G-202, G-205, G-207（4 項） | G-203, G-204, G-206（3 項） | – | 7 項 | ~12.5 天 |
| **Phase 3** | – | G-001, G-002, G-003, G-006, G-301, G-302, G-303（7 項） | – | 7 項 | ~8.5 天 |
| **Phase 4** | – | – | G-401~G-406（6 項） | 6 項 | ~10.5 天 |
| **Phase 5+** | – | – | – | 26 項（暫緩） | TBD |
| **MVP 合計** | **15** | **11** | **6** | **32 項** | **~50.5 天** |

---

## 8. Phase 1 啟動清單（可立即動工）

> ⚠️ 等 LLM_API_KEY 到位才能完整測 LINE Bot 自然語言，但 model/schema/QR 等前置可先做。

### 第 1 週（基礎建設）
- [ ] G-105 Expo Mobile App 骨架（2d）
- [ ] G-108 外協工序 model + API（1.5d）
- [ ] G-101 LINE Bot Webhook 接入（2d）

### 第 2 週（LINE Bot 主幹）
- [ ] G-103 LINE Bot 自然語言查詢（1.5d）⚠️ 需 API Key
- [ ] G-104 LINE Bot 推播警示（1.5d）
- [ ] G-102 LINE Bot 老闆儀表板（2d）

### 第 3 週（行動 + 外協）
- [ ] G-106 Mobile 登入+儀表板+庫存（2d）
- [ ] G-107 Mobile 工單列表（1.5d）
- [ ] G-109 外協 QR 派工單列印（1d）
- [ ] G-110 LINE Bot 外協回報（2d）
- [ ] G-112 LINE Bot 業務工具（1d）
- [ ] G-111 語音輸入（1.5d）⚠️ 需 API Key

---

## 9. 變更紀錄

| 日期 | 改動 |
|---|---|
| 2026-05-14 v1 | 初始 27 個 PDF 理論缺口（G-001~G-027） |
| 2026-05-14 v2 | **客戶定位明確化**，新增 G-101~G-406 共 25 個客戶導向缺口；原 G-001~G-027 多數延後到 Phase 5+ |

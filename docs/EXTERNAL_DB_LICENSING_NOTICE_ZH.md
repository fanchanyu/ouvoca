# 第三方 ERP 授權合規通知（External ERP Licensing Compliance Notice）

> **本檔是法律合規必讀**：要把 erpilot 接到您**既有的 ERP**（鼎新 Workflow / 正航 / SAP B1 / 叡揚 / Odoo / Microsoft Dynamics …）之前，請先讀完並完成本檔列示的三件事。
>
> **語言**：本文以**繁體中文**為主，英文版見 [`EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md)。

---

## ⚠️ 一頁式重點摘要

| 項目 | 內容 |
|---|---|
| **誰要看** | 任何打算開啟 erpilot 「外部 DB connector / Schema Mapping AI / 跨 DB 查詢」功能的**客戶 IT 主管 / 採購決策者** |
| **核心風險** | 多數商用 ERP 採「**每位具名使用者授權（per-named-user）**」，禁止以**共用 / 服務帳號**連線 DB 或 API |
| **若違規** | 原 ERP 廠商可發出**停權通知 / 求償 / 追加授權費**；維護合約失效；軟體稽核（BSA / 廠商定期稽核）被認定違規 |
| **客戶必做** | ① 取得書面授權 ② 必要時加購整合授權 ③ 留存證明文件 |
| **erpilot 不負責** | **不協助、不代理、不承擔**與第三方 ERP 廠商的合約 / 授權 / 法律事務 |
| **底線** | **技術上「能連」≠ 法律上「能合法連」**。請先取得授權再啟用 connector |

---

## 1. 為什麼會有授權風險

### 1.1 ERP 業界的標準授權模式

下列幾種授權模式在台灣 / 全球 ERP 市場相當普遍——**任一種被觸發都可能違約**：

| 授權模式 | 常見廠商 | 違規情境 |
|---|---|---|
| **Per-Named-User License**（每位具名使用者）| 鼎新、正航、SAP B1、Oracle NetSuite | erpilot 用「Integration」這個服務帳號連線，但該帳號未付授權費 |
| **Concurrent User License**（同時上線授權）| 部分 Workflow、叡揚 | erpilot 持續性查詢佔用一個 concurrent 名額，超過買的數量 |
| **Module License**（模組授權）| SAP B1、Microsoft Dynamics | erpilot 跨模組查詢（如 FI + SD + MM），但客戶只買了 FI 模組 |
| **API / Integration License**（API 整合授權）| SAP B1 Service Layer、叡揚 REST | API 屬於另外加購項目，未購買即呼叫違規 |
| **ODBC / 外接資料庫授權** | 鼎新、正航部分版本 | DB 直連需另購 ODBC 授權 |
| **Read-Only License** | 大型 ERP 部分模組 | 即使僅讀取，未明文允許「第三方系統讀取」仍違約 |

### 1.2 廠商實際稽核手段

> 「我用 SQL Server 直接連，廠商不會知道吧？」—— **不要這樣想**。

- **DB 端 audit log**：原 ERP 廠商在維護或升級時可調出 DB 連線記錄
- **License Manager 軟體**：許多 ERP 內建授權監控元件，會回傳 telemetry 給原廠
- **年度稽核（BSA / 廠商定期稽核）**：經銷商每年帶授權稽核員到客戶端比對
- **競爭通報**：原廠業務若得知客戶買了競品 ERP（erpilot），會主動發起合規稽核
- **DB 連線 metadata**：service account 名稱、connection string、login frequency 都可被分析

---

## 2. 客戶開啟連線前**必做**的三件事

### 2.1 ✅ Step 1 — 書面授權

與原 ERP 廠商 / 經銷商**書面**確認以下其一：

> **明確同意第三方系統（erpilot）以共用 / 服務帳號讀取本 ERP 之資料庫或 API，使用範圍包含 [SELECT / 部分 UPDATE / Schema Mapping] 等動作。**

形式可以是：
- 原 ERP 廠商的**正式授權書**（officially licensed）
- **合約增補附件**（amendment）
- **電子郵件回覆**（保留 thread + 廠商簽名檔）
- 經銷商的**書面確認函**（reseller authorization letter）

> ⚠️ **口頭同意不算**。「業務說沒問題」這種承諾在稽核時派不上用場。

### 2.2 ✅ Step 2 — 必要時加購對應授權

依據原廠回覆，可能需要加購以下任一種：

| 授權附加項目 | 一般市價（台幣 / 年） | 適用情境 |
|---|---|---|
| Integration License | 3 - 30 萬 | 任何第三方系統介接 |
| ODBC License | 1 - 10 萬 | DB 直連模式 |
| Service Account License | 1 - 5 萬 / 帳號 | 共用 / 服務帳號 |
| API License（呼叫量計費） | 看次數 | REST API / SOAP 模式 |
| Read-Replica License | 5 - 20 萬 | 唯讀副本 / 報表 DB |

> 💡 **參考數字**：實際金額**請以原 ERP 廠商報價為準**。erpilot 提供的 connector 屬技術元件，**不含**任何上述授權費。

### 2.3 ✅ Step 3 — 留存證明文件

把下列文件**集中保存**在公司法務 / IT 主管處：
- 原 ERP 廠商的**書面授權證明**
- 加購授權的**發票 / 合約**
- erpilot connector 啟用日期的**內部簽核紀錄**

> ⚠️ 若日後遭稽核，**舉證責任在客戶**——拿不出書面，等於默認違規。

---

## 3. erpilot 的責任界線

### 3.1 ✅ 我們提供（What We Provide）

| 項目 | 說明 |
|---|---|
| **Connector 程式碼** | sqlite / csv / SQL Server / REST API 等技術元件 |
| **Schema Mapping AI** | exact / alias / partial 3 級信心度，AI 自動對映欄位 |
| **ConfirmCard 遷移工具** | 預覽 + 確認，skip / overwrite 衝突策略 |
| **技術文件** | [外部 DB 串接設計](./EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md) |
| **技術支援** | connector 程式碼 bug 修復 / Schema Mapping 模型優化 |

### 3.2 ❌ 我們不負責（What We Do NOT Do）

| 項目 | 說明 |
|---|---|
| 合約協商 | 不與第三方 ERP 廠商代理客戶談 EULA / 加購授權 |
| 法律意見 | 不提供任何法律意見書 / 合規意見書 |
| 授權代購 | 不轉售第三方 ERP 的 Integration / ODBC / API 授權 |
| 稽核應對 | 不代客戶應對 BSA / 第三方 ERP 廠商之軟體稽核 |
| 違規後果承擔 | 因客戶**未取得授權即連線**所造成之停權 / 求償 / 損失，erpilot **一概不負責任** |

### 3.3 客戶責任聲明（必須同意才能啟用 connector）

啟用任何 external DB connector 前，客戶應視同已聲明：

> **本客戶已自行確認與原 ERP 廠商之授權範圍，並承擔 erpilot 連接該 ERP 所衍生之一切合規責任。erpilot 對第三方 ERP 廠商之授權判定、稽核結果或求償，不負任何責任。**

此聲明也將寫入**啟用 connector 時的 audit log**，作為日後留存紀錄。

---

## 4. 常見問答（FAQ）

### Q1：我們是小公司（30 人），原 ERP 廠商不會稽核吧？
**A**：稽核機率與公司規模沒有直接關係。經銷商每年都有 KPI，**買了競品 ERP** 反而是稽核熱點。風險不在「會不會被稽核」，而在「被稽核時拿不拿得出書面」。

### Q2：我們只用 erpilot 讀（SELECT），不會改原 DB，這也要授權？
**A**：**要**。EULA 通常規範的是「**存取**」而非「**寫入**」。即使唯讀，第三方系統存取仍屬違規範圍。

### Q3：我請我們 IT 同事的個人帳號讓 erpilot 用，這樣算「named user」吧？
**A**：**不建議**。
- 多數 EULA 禁止「將帳號分享給軟體 / 系統使用」
- 若該員離職，erpilot 立刻斷線
- 個人帳號的權限通常**過大**，erpilot 應該使用「最小權限服務帳號」
- 稽核時若發現是用個人帳號讓系統介接，**反而更明確違規**

### Q4：原廠說「我不知道」「我們沒這種授權」怎麼辦？
**A**：要求對方**書面**回覆「明知客戶將以第三方系統介接，且本公司不要求額外授權費」。沒有書面就是沒授權——**寧可暫緩 connector，也不要冒這個險**。

### Q5：我已經用 erpilot 接了，現在才發現要授權，怎麼辦？
**A**：
1. **立即停用 connector**（在 erpilot 設定 → External Connections → Disable）
2. 留存「啟用期間 / 連線 log」副本
3. 主動聯繫原 ERP 廠商說明、補簽授權（**主動處理 vs 被稽核發現**，廠商態度差很多）
4. 諮詢法律顧問

### Q6：erpilot 可以幫忙寄信給原 ERP 廠商溝通授權嗎？
**A**：**不行**。erpilot 不代理任何客戶與第三方 ERP 廠商之溝通。**建議由客戶 IT 主管直接洽詢原經銷商**（他們最熟 EULA 細節）。

### Q7：我們是用免費版 / 試用版 ERP（如 Odoo Community）連，這樣呢？
**A**：開源版（AGPL / GPL）通常**無此限制**，但 **Odoo Enterprise / SAP B1 試用版 / 任何商業版**仍適用本警告。請務必確認您用的是**哪個版本**。

### Q8：我能不能用 erpilot 同步完資料後，就停用 connector？
**A**：技術上可以——一次性遷移完就斷線，後續不再連線。但「**遷移期間的存取**」本身就需要授權。請依 §2 流程取得書面授權後再做一次性遷移。

---

## 5. 給 erpilot 顧問 / 經銷商的提醒

在 demo / 推銷 erpilot 的「外部 DB connector」功能時：

✅ **可以講**：
- 「我們的 Schema Mapping AI 能自動接您的 ERP 資料」
- 「技術上 2 分鐘可連上鼎新 / 正航 SQL Server」
- 「對話式 ERP 可以讀您舊系統的歷史資料」

❌ **絕對不能講**：
- 「您的鼎新授權不用管，我們繞過去」
- 「廠商不會發現」
- 「沒事啦大家都這樣連」

⚠️ **必須附帶提醒**：
- 「但請務必先和您的原 ERP 廠商書面確認授權範圍」
- 「erpilot 不負責原 ERP 的授權合規」

---

## 6. 相關文件

| 想了解 | 看哪裡 |
|---|---|
| **技術設計（如何接）** | [`EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md`](./EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md) |
| **使用者操作手冊** | [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) |
| **業務 demo 一頁紙** | [`SALES_KILLER_MOMENTS_ZH.md`](./SALES_KILLER_MOMENTS_ZH.md) |
| **erpilot 雙授權說明** | [`COMMERCIAL_LICENSING_FAQ_ZH.md`](./COMMERCIAL_LICENSING_FAQ_ZH.md) |
| **英文版本通知** | [`EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md) |

---

**最後更新**：2026-05-19（v3.25.4 — 補第三方 ERP 授權合規通知）
**法律性質**：本文件**僅為合規提醒**，不構成法律意見。具體授權判定請諮詢您的法律顧問與原 ERP 廠商。
**版本**：1.0

# 第三輪小白卡關修補法律與合規警告（v3.39）

> **本檔性質**：LOGO 上傳、刪除三件套、批次列印、分頁、digest 觸發、slot-filling 三次 fallback、開機自啟之**合規提醒**，**不構成法律意見**。
> 累積適用於 v3.25.10 → v3.38 全部 §6 聲明。
>
> **English version**: [`POLISH_V339_LEGAL_NOTICE_EN.md`](./POLISH_V339_LEGAL_NOTICE_EN.md)

---

## ⚠️ 重要：v3.39 修補 v3.38 後再盤點之 8 條硬傷

v3.39 涉及：
- **PDF 列印公司 LOGO**（K1）— 上傳之圖檔嵌入所有對外 PDF
- **客戶 / 供應商 / 料件 刪除**（K2）— 不可逆操作，但有預檢查
- **批次列印 ZIP**（K7）— 一次最多 50 張 PDF 打包下載
- **LLM 工具分頁**（K3）— 1000 筆也不爆 token
- **手動觸發 daily digest**（K6）— 排程改由 OS cron / Task Scheduler 承接
- **Slot-filling 3 次 fallback**（K4）— 連續失敗轉表單頁
- **後端離線時的具體指引**（K5）— Login 顯示「請開 Docker Desktop」
- **Docker 容器自啟**（K8）— compose 各服務加 `restart: unless-stopped`

---

## 1. PDF LOGO 嵌入（K1）

### 1.1 著作權邊界

- 客戶上傳之 LOGO 應為**公司擁有著作權**之圖檔
- 使用**他人 LOGO**（含品牌標誌、設計師作品未經授權）可能違反《著作權法》§91
- Ouvoca **不**驗證 LOGO 之著作權歸屬

### 1.2 顯示限制

- LOGO 寬 4cm × 高 1.5cm 上限（保持 PDF 整潔）
- 檔案 ≤ 500 KB（避免 PDF 過大）
- 僅接受 PNG / JPG（image/* MIME type）

### 1.3 對外 PDF 法律效力

- LOGO 出現在報價單 / 採購單 / 銷售單 / 出貨單頂部
- 對外發送之 PDF 含 LOGO 後，**第三方可能據此認定為貴司正式文件**
- 客戶應建立內控：**只有經授權之 LOGO 可上傳**

---

## 2. 客戶 / 供應商 / 料件 刪除（K2）

### 2.1 不可逆 + 預檢查

刪除為**永久操作**。v3.38 之 `undo_last_admin_change` **不涵蓋**刪除。

預檢查：
- **客戶**：有任何 SalesOrder 引用 → 拒絕（改用 is_active=false 停用）
- **供應商**：有任何 PurchaseOrder 引用 → 拒絕
- **料件**：有任何 BOMItem / PurchaseOrderItem / InventoryTransaction → 拒絕

### 2.2 ConfirmCard TTL 10 分鐘

- 刪除類給 10 分鐘思考時間（比一般 30 分鐘更短，**強制當下決定**）
- 過期後須重新呼叫工具

### 2.3 法定保存義務

刪除前請確認：
- 商業會計法 §38：交易憑證保存 5 年 — 客戶 / 供應商主檔關聯的單據**不可一併刪**
- 個資法：客戶之個資若用於合約履行期間，**不可任意刪除**
- 若需「忘記權」（GDPR-equivalent）— 應使用「匿名化」而非刪除

### 2.4 Ouvoca 之責任

- Ouvoca 已預檢查**業務關聯**並阻擋刪除
- Ouvoca **不**檢查**法定保存期**或**契約義務**
- 客戶須自行確認**法律允許刪除**後再執行

---

## 3. 批次列印 ZIP（K7）

### 3.1 限制

- 一次最多 **50 張**（避免後端 OOM）
- 僅支援 SO / PO / Quotation
- 失敗的單號會列在回傳之 `failed_list`

### 3.2 ZIP 內容之保管

- ZIP 內含**完整對外 PDF**（同 v3.36 §2 規範）
- 客戶應加密儲存、不外流
- 列印後**及時刪除本機 ZIP 檔**

---

## 4. LLM 工具分頁（K3）

### 4.1 設計

- `list_customers_paginated` 接受 `page` + `page_size`（最大 50）
- 回傳 `total` / `total_pages` / `items`
- 提示「下一頁」自然語言

### 4.2 風險

- 分頁查詢仍可能被串接成**完整資料下載**（呼叫所有頁）
- 客戶應於企業 SSO / API gateway 層**監控異常下載行為**

---

## 5. Daily Digest 觸發（K6）

### 5.1 排程

- v3.39 提供**手動觸發**：`trigger_daily_digest_now`
- **自動排程**請由 OS cron / Windows Task Scheduler / docker-compose-restart 接管
- 範例（Linux）：`0 8 * * * curl -X POST http://localhost:8000/api/email-digest/send -H "Authorization: Bearer $TOKEN"`

### 5.2 寄出之 Email 法律邊界

- Email 內容含**業務數據**（KPI / 應收 / 待簽核）
- 客戶須**確認收件人**為授權人員（不要寄到員工私人信箱）
- 寄送行為應**留 audit log**（v3.x 路線圖）

---

## 6. Slot-filling 3 次 Fallback（K4）

### 6.1 行為

連續同一 tool 缺欄位 3 次 → 系統回 `retry_exceeded=true` + 建議「改用表單頁」。

### 6.2 限制

- Counter 為 **in-memory**（後端重啟清空）
- Per-user × per-tool 隔離（一人在 A tool 失敗，不影響 B tool）
- 成功取到欄位後自動 reset

### 6.3 客戶責任

- 若連續 3 次仍失敗，**LLM 之回答品質可能下降** → 應**自行檢查問句清晰度**
- 多次失敗可能反映**模型偏差**或**訓練資料缺口** → 客戶可向 Ouvoca 回報

---

## 7. 後端離線指引（K5）

### 7.1 訊息內容

Login 頁面連不到後端時，顯示：
- 「Docker Desktop 在跑嗎？」
- 「docker compose ps 檢查容器」
- 「防火牆 port 8000」

### 7.2 免責

- 指引**僅為一般檢查清單**
- 客戶之**特定環境**（公司防火牆、VPN、proxy）需 IT 配合
- Ouvoca **不**遠端診斷客戶之網路問題

---

## 8. Docker 容器自啟（K8）

### 8.1 配置

`docker-compose.yml` 各服務加 `restart: unless-stopped`：
- Docker 啟動時自動拉起 Ouvoca 容器
- 即使容器 crash 也會自動重啟（除非使用者明確 `docker compose stop`）

### 8.2 配套要求

- 客戶須於 **Docker Desktop 設定**勾「Start when log in」
- Ouvoca **不**註冊 Windows Service（避免與 Docker Desktop 衝突）
- 老闆關機重開後：先開 Docker Desktop → Ouvoca 自動跟上

### 8.3 風險

- 自動重啟可能**遮蔽**真正的崩潰原因（log 在 `docker compose logs backend`）
- 客戶 IT 應**定期檢視** log（v3.x 路線圖：log rotation）

---

## 9. 免責條款（累積適用 v3.25.10 → v3.39）

於適用法律所允許之最大範圍內：

**1. LOGO 上傳**
Ouvoca **不**驗證客戶上傳之 LOGO 之**著作權歸屬**；客戶須**自行確認**有合法使用權；因 LOGO 侵權所衍生之爭議 Ouvoca **不承擔責任**。

**2. 刪除三件套**
Ouvoca 已預檢查業務關聯；客戶須**自行確認**法定保存期、契約義務、GDPR 等個資法規之適用；Ouvoca 對因刪除導致**無法回溯**之資料、合約爭議、法定查核失敗**不承擔責任**。

**3. 批次列印**
ZIP 含完整商業機密；客戶須妥善保管；Ouvoca 對 ZIP 外流之衍生爭議**不承擔責任**。

**4. 分頁**
分頁工具不**取代**正式資料匯出之合規流程；客戶須於企業 SSO / Gateway 層自行監控異常下載。

**5. Daily Digest**
手動觸發為**便利性功能**；自動排程之**設定、寄送、收件人控管**由客戶自行配置；Ouvoca 對誤寄、漏寄、寄錯人**不承擔責任**。

**6. Slot-filling 3 次 Fallback**
連續 3 次失敗為**啟發式建議**；不**取代**完整對話品質檢視；客戶應依據實際 UX 結果調整。

**7. 後端離線指引**
僅為一般檢查清單；Ouvoca **不**負責客戶之網路 / 防火牆 / VPN 問題之解決。

**8. Docker 自啟**
依 docker-compose 之 `restart: unless-stopped` 機制；客戶須**配合**設定 Docker Desktop 開機自啟；Ouvoca **不**註冊 Windows Service。

---

## 10. 客戶導入前 Checklist（v3.39 補強）

### 10.1 LOGO 使用
- [ ] LOGO 為公司**擁有著作權**之圖檔（或已取得授權）
- [ ] LOGO 已縮至 4cm × 1.5cm 範圍清楚可讀
- [ ] 已試印一份 PDF 確認 LOGO 顯示無誤

### 10.2 刪除政策
- [ ] 已建立公司「資料刪除」**內控流程**（誰可刪、刪前需誰簽核）
- [ ] 已確認**法定保存期**未過，可以安全刪除
- [ ] 已對員工說明：**有訂單關聯的客戶不能刪，改用「停用」**

### 10.3 批次列印
- [ ] 列印後**及時刪除**本機 ZIP 檔
- [ ] 批次列印 audit log 已啟用（後續查誰列印了什麼）

### 10.4 開機自啟
- [ ] Docker Desktop 已勾「Start when log in」
- [ ] 已測試「電腦重開機 → Ouvoca 自動可用」流程

### 10.5 與既有 checklist 累積
- [ ] 已完成 v3.25.10 → v3.38 之**全部** checklist

---

**版本**：v3.39（2026-05-21）
**作者**：Ouvoca 法務團隊（內部）
**對應程式**：
- `backend/app/agents/domains/polish_v339_tools.py`（7 LLM tools）
- `backend/app/services/print_service.py`（LOGO 渲染）
- `backend/app/agents/engine.py`（slot-filling 3-strike fallback）
- `frontend-desktop/src/pages/Login.tsx`（後端離線指引）
- `docker-compose.yml`（restart: unless-stopped）
- `install.bat`（K8 Docker 自啟說明）

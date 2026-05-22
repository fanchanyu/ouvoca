# 進銷存模組法律與責任聲明（v3.32 / v3.33）

> **本檔性質**：合規**提醒**用途，**不構成法律意見**。本文件累積適用於 v3.25.10 → v3.33 全部 §6 聲明。
>
> **English version**: [`INVENTORY_SALES_LEGAL_NOTICE_EN.md`](./INVENTORY_SALES_LEGAL_NOTICE_EN.md)

---

## 1. 報價單 (Quotation) 法律性質

### 1.1 報價之契約地位
本系統產生之報價單**僅為要約之邀請（invitation to treat）**，**非要約**本身。客戶之回覆「接受」**亦非自動成立契約**，仍須貴司確認後始生效。

具體實務建議：
- 寄出報價前由業務主管覆核金額、條款、付款方式
- 客戶接受後仍須**書面確認**（如簽回報價單或對帳單）後再轉訂單
- 報價有效期（valid_until）過期後若客戶仍接受，建議重新報價而非沿用

### 1.2 報價變動之風險
- **clone_quotation**：複製舊報價為新版本，但**價格 / 數量 / 條款可能因時更新**，業務應檢視
- **update_quotation_status**：標為「accepted」**不等同**客戶已書面確認；建議搭配客戶簽收
- **cancel_quotation**：作廢後**不可逆**，需新建報價取代

### 1.3 反壟斷 / 公平交易合規
不同客戶之差別定價可能涉及：
- 台灣公平交易法 §22（差別取價之合理理由）
- 美國 Sherman Act §1 / Robinson-Patman Act
- 歐盟競爭法 Art. 102

`explore_pricing_curve_tool` 之 what-if 結果**不構成定價策略法律建議**，使用前應由法務顧問審視。

---

## 2. 銷售單 (Sales Order) 法律性質

### 2.1 SO 之契約效力
SO 創建後即為**對客戶之交付承諾**。本系統之 hard-write tools 影響：
- **create_sales_order_with_confirm** — 承諾成立
- **update_sales_order_item / delivery** — 契約變更（建議客戶書面同意）
- **add / remove sales_order_item** — 新增 / 減少品項（同上）
- **cancel_sales_order** — 解除契約，可能涉及違約金

### 2.2 ship_sales_order 之風險
出貨即觸發：
- 庫存扣減（影響成本帳）
- 應收帳款入帳（影響財報）
- 客戶交付承諾（影響服務水準）

**ConfirmCard 為法律確認點**：使用者按確認前應檢視具體 slot 值。

---

## 3. 採購單 (Purchase Order) 法律性質

### 3.1 PO 之契約效力
PO 經 approved / sent 後為**對供應商之契約**：
- **cancel_purchase_order** — 可能涉及供應商違約金（若已下生產）
- **update_purchase_order_item** — 修改數量 / 單價需供應商同意
- **update_purchase_order_delivery** — 改交期需通知供應商
- **add / remove purchase_order_item** — 僅限 draft 狀態（避免契約變更爭議）

### 3.2 收貨入帳之合規責任
- **receive_purchase_order** 觸發應付帳款入帳
- 收貨數量 / 品質判定**屬倉管職權**，AI 不替代
- 短缺 / 損壞應依與供應商之合約處理（不由 Ouvoca 自動扣款）

---

## 4. 庫存盤點 (StockCount) 法律性質

### 4.1 盤點作為審計依據
盤點調整影響：
- **成本會計**（盤盈轉收入、盤虧轉成本）
- **稅務申報**（存貨變動屬營業成本）
- **內控合規**（SOX / ISO 9001 / GMP 等規範要求定期盤點 + 主管覆核）

### 4.2 盤點責任分工
本系統設計為：
- 倉管：執行盤點 + key in 實盤數
- 主管：覆核差異 + 套用調整
- 會計師：依盤點結果調整帳目

**Ouvoca 之 ConfirmCard 不取代會計師覆核**。對外財報請依適用會計準則 + CPA 審視。

### 4.3 盤點原因分類
`variance_reason` 之分類僅供內部分析，**不構成**：
- 對員工失誤之認定（damaged/lost 不等同失職）
- 對供應商品質之指控（count_error 可能源自任何環節）
- 對保險理賠之證據（需另行專業評估）

---

## 5. 採購建議 (Reorder Suggestion) 法律性質

### 5.1 建議性質
**reorder_suggestion_tool** 與 **smart_reorder_with_lead_time_tool** 之輸出**僅為演算法建議**，不構成：
- 對供應商之自動下單（必走 create_purchase_order_with_confirm）
- 對價格 / 交期之承諾
- 對未來需求之預測（請搭配 demand_forecasting tool）

### 5.2 演算法限制
- `smart_reorder` 之 daily_burn 推估**保守**，若無歷史銷售可能低估
- `lead_time` 為設定值，**不反映**供應商實際近期績效
- `safety_stock` 為固定值，**未動態調整**因服務水準目標變動

重大採購（如年度大宗料）必須由採購主管 + 財務覆核。

---

## 6. LLM 互動之風險

### 6.1 抽 slot 錯誤
使用者說「PO-001 改成 200 個」LLM 可能：
- 抽錯 PO 號（如 PO-002）
- 抽錯數量（如把「200」當「2000」）
- 抽錯料件（若 PO 多行）

**ConfirmCard 為防線**：使用者按確認前須檢視 slot 值。

### 6.2 LLM 翻譯（rendering）失準
read tools 之 `summary` 為 LLM 翻譯，可能：
- 簡化過度（如把「差 5 個破損 + 5 個遺失」說成「差 10 個」）
- 編造業務原因（hallucination）

**建議**：關鍵決策時檢視 `raw` 結構化資料。

---

## 7. 不擔保條款

於適用法律所允許之最大範圍內（**to the maximum extent permitted by applicable law**），Ouvoca 對下列事項不承擔責任：

1. 因 LLM 抽 slot 錯誤誤發 PO/SO/盤點所衍生之契約 / 財務 / 稅務後果
2. 因 LLM 翻譯失準導致之錯誤業務判斷
3. 因採購建議（含 smart_reorder）所衍生之過量採購 / 缺料停線
4. 因盤點調整所衍生之財報不實 / 稅務申報問題
5. 因報價單錯誤 / 變更所衍生之客戶爭議
6. 因 PO/SO 修改所衍生之供應商 / 客戶契約違約
7. 第三方（客戶、供應商、業務、倉管）依本系統採取行動所衍生之合約 / 勞動 / 競爭法爭議

---

## 8. 累積適用前置文件之聲明

本版本疊加於 v3.25.10 → v3.32，**所有前置 design docs §6 之聲明累積適用**：

| 前置版本 | 累積聲明重點 |
|---|---|
| v3.25.10 §6 | MRP 為規劃建議，不構成 PO；確定性假設 |
| v3.26 §6 | CLSP NP-hard 啟發法非最佳；capacity 輸入準確性責任 |
| v3.27 §6 | Provenance ≠ 法律因果；TOC 啟發；OAT 不抓 interaction |
| v3.28 §6 | TA ≠ GAAP/IFRS；反壟斷警告；DBR 經驗值 |
| v3.29 §6 | 預測不保證；不可預見事件；LLM 業務 hallucination |
| v3.30 §6 | LLM slot 抽錯風險；翻譯 hallucination；RBAC × LLM |
| v3.31 §6 | hard-write 5 大客戶責任點；ConfirmCard 為法律確認點 |
| v3.32 §6 | 報價轉 SO 不可逆；盤點影響成本；契約爭議警告 |

---

## 9. 文化提醒：LLM 不取代專業

Ouvoca 之承諾：**「自然語言取代教育訓練」**，**不是**「**自然語言取代專業判斷**」。

| AI 可以 | 仍需專業判斷 |
|---|---|
| 快速建單 / 改單 / 查詢 | 重大金額決策 |
| 整合多源資料給人話 | 法律 / 稅務 / 反壟斷合規 |
| 計算 / 排序 / 建議 | 客戶關係維繫 |
| 24/7 待命 | 倫理 / 文化判斷 |

最終決策應由：
- 業務 / 採購 / 倉管 / 廠長 — 依其專業
- 主管 / 財務 / 法務 — 依其權限
- 老闆 — 依其角色

**共同承擔。**

---

**最後更新**：2026-05-21（v3.33）
**版本**：1.0
**English**：[`INVENTORY_SALES_LEGAL_NOTICE_EN.md`](./INVENTORY_SALES_LEGAL_NOTICE_EN.md)

# Phase 0 種子套件細項規格（Turnkey Seed Package Spec）

> 目標：「雙擊安裝 → 90 分鐘內，用預置的科目表、流程、角色、表單，開出第一張真實報價單 / PO / WO / 出貨單 / 傳票，金流、稅務、稽核、備份全通」。
> 本文件是「不寫 code 的預置內容」之完整規格，供工程師直接實作（不靠顧問設定）。
> 前置閱讀：`docs/GAP_ANALYSIS.md`、`docs/ROADMAP.md`。

---

## 0. 交付總覽

| 套件 | 內容 | 新檔案 / 修改 | 對應缺口 |
|---|---|---|---|
| P0-1 | TW 會計科目表種子（~110 科目 + 報表對應） | 新增 `backend/scripts/seed_accounts.py`；修改 `backend/scripts/seed.py` | 三大報表、AP/AR 科目 |
| P0-2 | 角色 × 權限矩陣（10 角色 × 95+ 權限碼，含 row-scope） | 修改 `backend/scripts/seed_permissions.py` | 開箱即安全 |
| P0-3 | 家規預設集（20 條，現有 3 條擴充） | 修改 `backend/app/services/policy_engine.py` | 內控開箱即用 |
| P0-4 | 表單範本 12 張（PDF + 標籤） | 修改 `backend/app/services/print_service.py` | 表單缺口 |
| P0-5 | 行業種子資料 ×2（機械加工 / 電子組裝，上線規模）+ CSV 匯入範本 | 修改 `backend/scripts/seed_industries.py`；新增 `backend/data/templates/*.csv` | 學習成本歸零 |
| P0-6 | 系統組態預設（幣別/稅率/付款條件/時區/備份參數） | 新增 `backend/app/services/system_defaults.py`；修改 `.env.example` | 開機即正確 |

**驗收總標準（每套件）**：全新 SQLite DB → `python -m scripts.seed` → 下述各套件檢查點全綠 → `pytest` 全數通過（既有 701 + 新增）。

---

## 1. P0-1 TW 會計科目表種子

### 1.1 設計原則

- **程式碼相容性**：現有硬編碼科目必須保留編號（v3.55 sales.py:110-112、business_completion_tools.py:354/357/444/447）：
  - `1100` = 現金及銀行存款（收付款 DR/CR 用）
  - `1200` = 應收帳款
  - `2100` = 應付帳款
  - `2200` = 銷項稅額
  - `4100` = 銷貨收入
- **編碼規則**：1xxx 資產 / 2xxx 負債 / 3xxx 權益 / 4xxx 營業收入 / 5xxx 營業成本 / 6xxx 營業費用 / 7xxx 業外收支 / 9xxx 所得稅；末位 0 = 母科目，1-9 = 明細。
- **不可刪**：`is_system=True` 標記硬編碼五碼，UI 禁止刪除/改號（只能停用）。

### 1.2 科目表（完整清單）

| code | name_zh | account_type | is_debit_normal | parent | fs_line |
|---|---|---|---|---|---|
| 1100 | 現金及銀行存款 | asset | true | — | 資產負債表-流動資產 |
| 1101 | 庫存現金 | asset | true | 1100 | 資產負債表-流動資產 |
| 1102 | 銀行存款 | asset | true | 1100 | 資產負債表-流動資產 |
| 1103 | 零用金 | asset | true | 1100 | 資產負債表-流動資產 |
| 1110 | 應收票據 | asset | true | — | 資產負債表-流動資產 |
| 1200 | 應收帳款 | asset | true | — | 資產負債表-流動資產 |
| 1210 | 備抵呆帳-應收帳款 | asset | false | 1200 | 資產負債表-流動資產(減項) |
| 1250 | 其他應收款 | asset | true | — | 資產負債表-流動資產 |
| 1300 | 存貨 | asset | true | — | 資產負債表-流動資產 |
| 1310 | 原料 | asset | true | 1300 | 資產負債表-流動資產 |
| 1320 | 物料 | asset | true | 1300 | 資產負債表-流動資產 |
| 1330 | 在製品 | asset | true | 1300 | 資產負債表-流動資產 |
| 1340 | 製成品 | asset | true | 1300 | 資產負債表-流動資產 |
| 1350 | 商品存貨 | asset | true | 1300 | 資產負債表-流動資產 |
| 1400 | 預付款項 | asset | true | — | 資產負債表-流動資產 |
| 1410 | 進項稅額 | asset | true | 1400 | 資產負債表-流動資產 |
| 1420 | 預付費用 | asset | true | 1400 | 資產負債表-流動資產 |
| 1430 | 預付貨款 | asset | true | 1400 | 資產負債表-流動資產 |
| 1500 | 其他流動資產 | asset | true | — | 資產負債表-流動資產 |
| 1600 | 不動產、廠房及設備 | asset | true | — | 資產負債表-非流動資產 |
| 1610 | 土地 | asset | true | 1600 | 資產負債表-非流動資產 |
| 1620 | 房屋及建築 | asset | true | 1600 | 資產負債表-非流動資產 |
| 1621 | 累計折舊-房屋及建築 | asset | false | 1620 | 資產負債表-非流動資產(減項) |
| 1630 | 機器設備 | asset | true | 1600 | 資產負債表-非流動資產 |
| 1631 | 累計折舊-機器設備 | asset | false | 1630 | 資產負債表-非流動資產(減項) |
| 1640 | 運輸設備 | asset | true | 1600 | 資產負債表-非流動資產 |
| 1641 | 累計折舊-運輸設備 | asset | false | 1640 | 資產負債表-非流動資產(減項) |
| 1650 | 辦公設備 | asset | true | 1600 | 資產負債表-非流動資產 |
| 1651 | 累計折舊-辦公設備 | asset | false | 1650 | 資產負債表-非流動資產(減項) |
| 1700 | 無形資產 | asset | true | — | 資產負債表-非流動資產 |
| 1800 | 其他非流動資產 | asset | true | — | 資產負債表-非流動資產 |
| 2100 | 應付帳款 | liability | false | — | 資產負債表-流動負債 |
| 2200 | 銷項稅額 | liability | false | — | 資產負債表-流動負債 |
| 2210 | 應付票據 | liability | false | — | 資產負債表-流動負債 |
| 2220 | 應付費用 | liability | false | — | 資產負債表-流動負債 |
| 2230 | 應付薪資及獎金 | liability | false | — | 資產負債表-流動負債 |
| 2240 | 應付所得稅 | liability | false | — | 資產負債表-流動負債 |
| 2250 | 預收款項 | liability | false | — | 資產負債表-流動負債 |
| 2260 | 其他應付款 | liability | false | — | 資產負債表-流動負債 |
| 2300 | 短期借款 | liability | false | — | 資產負債表-流動負債 |
| 2400 | 長期借款 | liability | false | — | 資產負債表-非流動負債 |
| 2500 | 其他非流動負債 | liability | false | — | 資產負債表-非流動負債 |
| 3100 | 股本 | equity | false | — | 資產負債表-權益 |
| 3200 | 資本公積 | equity | false | — | 資產負債表-權益 |
| 3300 | 保留盈餘 | equity | false | — | 資產負債表-權益 |
| 3310 | 法定盈餘公積 | equity | false | 3300 | 資產負債表-權益 |
| 3320 | 特別盈餘公積 | equity | false | 3300 | 資產負債表-權益 |
| 3330 | 未分配盈餘 | equity | false | 3300 | 資產負債表-權益 |
| 3400 | 本期損益 | equity | false | — | 資產負債表-權益(結帳科目) |
| 4100 | 銷貨收入 | revenue | false | — | 損益表-營業收入 |
| 4110 | 銷貨退回及折讓 | revenue | true | 4100 | 損益表-營業收入(減項) |
| 4200 | 加工收入 | revenue | false | — | 損益表-營業收入 |
| 4300 | 其他營業收入 | revenue | false | — | 損益表-營業收入 |
| 5100 | 銷貨成本 | cost | true | — | 損益表-營業成本 |
| 5110 | 原料耗用 | cost | true | 5100 | 損益表-營業成本 |
| 5120 | 直接人工 | cost | true | 5100 | 損益表-營業成本 |
| 5130 | 製造費用 | cost | true | 5100 | 損益表-營業成本 |
| 5200 | 進貨成本 | cost | true | — | 損益表-營業成本 |
| 5300 | 進貨退回及折讓 | cost | false | 5200 | 損益表-營業成本(減項) |
| 6100 | 薪資支出 | expense | true | — | 損益表-營業費用 |
| 6110 | 勞健保費 | expense | true | — | 損益表-營業費用 |
| 6120 | 退休金提撥 | expense | true | — | 損益表-營業費用 |
| 6130 | 伙食費 | expense | true | — | 損益表-營業費用 |
| 6200 | 租金支出 | expense | true | — | 損益表-營業費用 |
| 6210 | 文具印刷費 | expense | true | — | 損益表-營業費用 |
| 6220 | 郵電費 | expense | true | — | 損益表-營業費用 |
| 6230 | 水電瓦斯費 | expense | true | — | 損益表-營業費用 |
| 6240 | 燃料費 | expense | true | — | 損益表-營業費用 |
| 6250 | 運費 | expense | true | — | 損益表-營業費用 |
| 6260 | 廣告費 | expense | true | — | 損益表-營業費用 |
| 6270 | 交際費 | expense | true | — | 損益表-營業費用 |
| 6280 | 差旅費 | expense | true | — | 損益表-營業費用 |
| 6290 | 修繕費 | expense | true | — | 損益表-營業費用 |
| 6300 | 稅捐 | expense | true | — | 損益表-營業費用 |
| 6310 | 折舊費用 | expense | true | — | 損益表-營業費用 |
| 6320 | 各項攤提 | expense | true | — | 損益表-營業費用 |
| 6330 | 呆帳損失 | expense | true | — | 損益表-營業費用 |
| 6400 | 其他營業費用 | expense | true | — | 損益表-營業費用 |
| 7100 | 利息收入 | other_income | false | — | 損益表-業外收入 |
| 7200 | 租金收入 | other_income | false | — | 損益表-業外收入 |
| 7300 | 兌換利益 | other_income | false | — | 損益表-業外收入 |
| 7400 | 其他收入 | other_income | false | — | 損益表-業外收入 |
| 7500 | 利息費用 | other_expense | true | — | 損益表-業外支出 |
| 7600 | 兌換損失 | other_expense | true | — | 損益表-業外支出 |
| 7700 | 其他損失 | other_expense | true | — | 損益表-業外支出 |
| 9100 | 所得稅費用 | tax | true | — | 損益表-所得稅 |

> 共 79 個科目。實作時可依 `is_system` 保護五個硬編碼碼，其餘允許客戶新增/停用。

### 1.3 報表對應（`fs_line` 即三大報表 mapping）

- 損益表公式：`營業收入(4xxx 減 4110) − 營業成本(5xxx 減 5300) = 營業毛利；− 營業費用(6xxx) = 營業利益；± 業外(7xxx) = 稅前淨利；− 所得稅(9xxx) = 本期淨利`
- 資產負債表公式：`資產(1xxx) = 負債(2xxx) + 權益(3xxx)`，驗收時強制平衡檢查
- **Phase 0 只做科目 + mapping 資料**；報表產生器屬 Phase 1（`services/fs_statements.py`），但 seed 的 `fs_line` 欄位現在就要填好，Phase 1 直接吃。

### 1.4 檢查點

```
python -m scripts.seed_accounts
→ Account 數 ≥ 79、五硬編碼碼存在且 is_system=True
→ 每科目 fs_line 非空、借貸方向正確（資產/成本/費用=debit；負債/權益/收入=credit）
→ 測試：tests/smoke/test_seed_accounts.py
```

---

## 2. P0-2 角色 × 權限矩陣

### 2.1 角色定義（10 個，`seed_permissions.py` 擴充）

| 角色 code | name_zh | 說明 | 特殊設定 |
|---|---|---|---|
| super_admin | 系統管理員 | 全部權限 + 系統設定 | is_superuser；僅 IT |
| boss | 老闆 | 唯讀全覽 + 報表 + 審批 | 不能建單/改單（防誤操作），可看成本 |
| sales_manager | 業務主管 | 業務域全權 + 審批 | 可看客戶毛利 |
| sales_rep | 業務 | 客戶/報價/SO 讀寫，行級=own | **不可看 unit_cost / credit_limit**（v3.54 機制） |
| purchaser | 採購 | 供應商/PO 讀寫 + 收貨 | 不可看財務 |
| plant_manager | 廠長 | 生產/工單/派工/庫存全權 + 審批 | 可看成本、可覆寫家規 |
| warehouse | 倉管 | 庫存/收發料/盤點/倉儲 | 不可看成本 |
| inspector | 品保 | 檢驗/不良/NCR/CAPA | — |
| accountant | 會計 | 傳票/AR/AP/稅務/報表 + 成本 | 不可操作生產 |
| operator | 作業員 | 派工報工（自己）+ 檢視自己工單 | 最小權限 |

### 2.2 權限分配矩陣（模組 × 角色）

格式：`R=read/list, C=create, U=update, A=approve/confirm, D=delete, X=全權, —=無`；行級 scope 另標 `(own)`。

| 權限碼（模組） | super_admin | boss | sales_manager | sales_rep | purchaser | plant_manager | warehouse | inspector | accountant | operator |
|---|---|---|---|---|---|---|---|---|---|---|
| inventory.* (part/transaction) | X | R | R | R | R | X | X | R | R | — |
| inventory.inventory.adjust | X | — | — | — | — | A | U | — | U | — |
| purchase.supplier.* | X | R | — | — | X | R | R | — | R | — |
| purchase.order.* | X | R | R | — | X | R(own) | R | — | R | — |
| purchase.order.approve | X | A | — | — | A | A | — | — | — | — |
| purchase.order.receive | X | — | — | — | A | A | A | — | — | — |
| production.product.* | X | R | R | R | R | X | R | R | R | — |
| production.bom.* | X | R | — | — | R | X | — | R | R | — |
| production.work_order.* | X | R | R | R | R | X | R(own) | R | R | R(own) |
| production.work_order.release | X | — | — | — | — | A | — | — | — | — |
| production.dispatch.create | X | — | — | — | — | A | A | — | — | U |
| production.work_center.* | X | R | — | — | R | X | R | — | — | — |
| sales.customer.* | X | R | X | X(own) | R | R | R | R | R | — |
| sales.order.* | X | R | X | X(own) | R | R | R | R | R | — |
| sales.order.ship | X | — | A | U | — | A | A | — | — | — |
| sales.quotation.* | X | R | X | X(own) | — | R | — | — | R | — |
| quality.inspection.* | X | R | R | R | R | R | R | X | R | R |
| quality.ncr/capa.* | X | R | R | R | R | R | R | X | R | R |
| mps_mrp.* | X | R | R | R | R | X | R | — | R | — |
| warehouse.* (zone/bin/pick/cycle) | X | R | — | — | — | R | X | — | R | — |
| accounting.journal.* | X | R | R | — | — | — | — | — | X | — |
| accounting.ar/ap.* | X | R | R | R | R | R | — | — | X | — |
| accounting.payment/receipt.record | X | — | — | — | A | — | — | — | X | — |
| accounting.month_close.* | X | — | — | — | — | — | — | — | A | — |
| tax.einvoice.* | X | R | R | R | R | — | — | — | X | — |
| tax.tax_id.validate | X | — | — | U | U | — | — | — | U | — |
| tax.report.read | X | R | R | — | — | — | — | — | X | — |
| approval.request.* | X | A | A | U | U | A | — | U | A | U |
| analytics.view / dashboard.read | X | X | R | R | R | R | R | R | R | R |
| email_digest (analytics.view) | X | A | — | — | — | — | — | — | — | — |
| system.config.update | X | — | — | — | — | — | — | — | — | — |
| user.profile.* | X | — | — | — | — | — | — | — | — | — |
| external_db.* | X | — | — | — | — | — | — | — | — | — |
| ai.agent.use | X | X | X | X | X | X | X | X | X | X |

### 2.3 行級過濾（RowFilter）與敏感欄位

| 資源 | scope | 規則 |
|---|---|---|
| sales.customer / sales.order | own | 業務只看到自己負責客戶（sales_rep） |
| production.work_order | department | 作業員只看到自己部門工單 |
| 敏感欄位 | — | `unit_cost`、`credit_limit`、毛利率 對非 `accountant`/`boss`/`plant_manager`/`super_admin` 一律 strip（沿用 v3.54 機制） |

### 2.4 檢查點

```
python -m scripts.seed_permissions
→ 每個角色都有權限（無空角色）、每個權限碼至少被一個角色引用（無孤兒）
→ 矩陣覆蓋度測試：tests/smoke/test_role_matrix.py（定義上表為 fixture，逐一 assert）
→ 驗證過 sample user：sales_rep 呼叫 /api/agents/exec/create_purchase_order 必須 403
```

---

## 3. P0-3 家規預設集（20 條）

### 3.1 現狀

`policy_engine.py DEFAULT_RULES` 只有 3 條：WO 需 BOM、PO>10 萬需審、PO ≥1 項目。

### 3.2 新增 17 條（含 6 個新 condition type 需實作）

| # | 名稱 | trigger | condition_type | condition_params | action | message | override_role | priority |
|---|---|---|---|---|---|---|---|---|
| 4 | SO 折扣 > 5% 需主管審 | so.create | field_compare | {field: discount_rate, op: gt, value: 5} | require_approval | 折扣超過 5% 需主管核准 | manager | 40 |
| 5 | 報價單折扣 > 10% 警告 | quotation.create | field_compare | {field: discount_rate, op: gt, value: 10} | warn | 折扣超過 10%，請確認利潤 | manager | 30 |
| 6 | SO 金額不得超過客戶信用額度 | so.create | **credit_check**（新） | {} | block | 超過客戶信用額度 | manager | 90 |
| 7 | 出貨單需 SO 已核准 | dn.create | **status_required**（新） | {entity: so, status: [approved]} | block | 訂單尚未核准不可出貨 | manager | 90 |
| 8 | B2B 出貨需客戶統編 | dn.create | **tax_id_required**（新） | {} | block | B2B 客戶未填統編無法開發票 | manager | 80 |
| 9 | 庫存調整需主管覆核 | inventory.adjust | always | {} | require_approval | 庫存調整（盈虧）需主管覆核 | manager | 60 |
| 10 | 刪除主檔（料件/客戶/供應商）需雙人 | *.delete | always | {} | require_approval | 刪除主檔需主管核准 | manager | 80 |
| 11 | 盤點差異 > 5% 需主管 | inventory.count.adjust | field_compare | {field: variance_pct, op: gt, value: 5} | require_approval | 盤點差異超過 5% | manager | 60 |
| 12 | 單價異動 > 20% 需主管 | supplier_price.create | field_compare | {field: price_change_pct, op: gt, value: 20} | require_approval | 進貨單價漲幅超過 20% | manager | 50 |
| 13 | 緊急採購（交期 < 3 工作天）警告 | po.create | **leadtime_check**（新） | {min_days: 3} | warn | 交期過短，確認供應商可否承諾 | — | 20 |
| 14 | 檢驗不合格自動開 NCR | inspection.complete | **inspection_fail**（新） | {} | warn | 已自動建立 NCR | inspector | 70 |
| 15 | WO 完工前需檢驗通過 | wo.complete | **inspection_done**（新） | {} | block | 完工前須完成檢驗 | manager | 80 |
| 16 | 付款/收款單需有來源單據 | payment.record | count_check | {field: source_refs, op: gte, value: 1} | block | 收付款需連結來源單據 | accountant | 60 |
| 17 | 月結後禁止改傳票 | journal.post | **period_closed**（新） | {} | block | 已結帳期間不可新增傳票 | accountant | 100 |
| 18 | 低於安全庫存警告 | inventory.read | **below_safety**（新） | {} | warn | 低於安全庫存，建議採購 | — | 10 |
| 19 | 新客戶信用額度預設 0 警告 | customer.create | field_compare | {field: credit_limit, op: eq, value: 0} | warn | 新客戶信用額度為 0，收款風險請確認 | — | 15 |
| 20 | 應收逾期 > 60 天警示 | ar.read | **aging_over**（新） | {days: 60} | warn | 有應收帳款逾期超過 60 天 | boss | 25 |

> 標「（新）」的 condition type 需在 `policy_engine.py` 以 `register_condition()` 實作（沿用現有 pluggable 機制，0.5 天）。
> 原有 3 條保留不動（idempotent 安裝，tenant="HQ"）。

### 3.3 檢查點

```
python -m scripts.seed → PolicyRule 數 = 20（HQ tenant）
測試：tests/smoke/test_house_rules_seed.py
  - PO 12 萬 → 出 ConfirmCard/審批流
  - SO 折扣 8% → 需主管
  - 庫存調整 → 需覆核
  - 月結後建傳票 → 擋下
```

---

## 4. P0-4 表單範本 12 張

### 4.1 現狀

`print_service.py` 已有：報價單 / 採購訂單 / 銷售訂單 / 出貨單 / 電子發票（5 張）。

### 4.2 範本清單與規格

| # | 範本 | 資料來源表 | 狀態 | 版型欄位（A4 或標籤） | 簽核欄位 | 備註 |
|---|---|---|---|---|---|---|
| 1 | 報價單 | Quotation | ✅ 強化 | 既有 + 加公司 LOGO、品項表、稅額、總計、有效期限、客戶簽回欄 | 客戶簽回欄 | 現有版強化 |
| 2 | 銷售訂單 | SalesOrder | ✅ 強化 | 既有 + 交期承諾欄、內部審核欄 | 業務/主管簽核 | |
| 3 | 出貨單 | DeliveryNote | ✅ 強化 | 既有 + 貨運單號、收貨人簽收欄 | 簽收欄 | |
| 4 | 電子發票 | EInvoiceRecord | ✅ | 既有 | — | |
| 5 | 採購訂單 | PurchaseOrder | ✅ 強化 | 既有 + 交期、付款條件、供應商簽回欄 | 供應商簽回 | |
| 6 | 請購單 | **需新模型** PurchaseRequisition | ❌ 新 | 品項/需求日期/用途/預算科目、主管核准欄 | 需求者/主管 | 模型 Phase 1；範本先行規格化 |
| 7 | 收料單 GRN | **需新模型** GoodsReceiptNote | ❌ 新 | PO 對應、實收量、檢驗結果、儲位 | 倉管/品保 | 模型 Phase 1 |
| 8 | 領料單 | **需新模型** MaterialIssue | ❌ 新 | WO 對應、料號/數量、批號、領料人 | 領料/發料 | 模型 Phase 2 |
| 9 | 檢驗報告 | InspectionOrder/Result | ❌ 新（模型已有） | 檢驗項目、量測值、判定、不良數、抽樣數 | 品保簽核 | **可立即做** |
| 10 | 盤點表 | StockCount/StockCountItem | ❌ 新（模型已有） | 儲位、帳面數、實盤數、差異、盤點人 | 盤點人/主管 | **可立即做** |
| 11 | 料件標籤 | Part | ❌ 新（模型已有） | 60×40mm：料號條碼(Code128)、料名、單位、安全庫存 | — | 熱感應紙 |
| 12 | RMA 退貨單 | **需新模型** Rma/ReturnOrder | ❌ 新 | 原 SO/DN 對應、退貨原因、處理方式(換/修/退錢) | 業務/主管 | 模型 Phase 2 |

### 4.3 通用規格（所有範本）

- 公司資訊（LOGO、名稱、統編、地址、電話）從 FactoryConfig/公司設定讀取（v3.39 已支援 LOGO）
- 單號、日期（Asia/Taipei）、幣別、稅別（應稅/免稅/零稅率）
- 每張單下方印：列印時間、列印者、系統單號 QR（稽核用）
- 檔案：`print_service.py` 各加一個 `generate_xxx_pdf()`，註冊進 `print_export` router 的 doc_type 白名單
- **可立即做**（模型已有）：9、10、11 → 本 Phase 完成
- **需模型**（6、7、8、12）：本 Phase 先寫版型規格 + Pytest 佔位測試，模型落地後接上

### 4.4 檢查點

```
POST /api/print/xxx（5 既有 + 檢驗報告 + 盤點表 + 料件標籤）
→ 8 張 PDF 可下載、中文正常、含公司資料與簽核欄
測試：tests/smoke/test_pdf_templates.py（逐張 assert 內容關鍵字）
```

---

## 5. P0-5 行業種子資料 ×2 + CSV 匯入範本

### 5.1 現狀

`seed_industries.py` 有 5 個 demo 級行業（metal/plastic/pcb/food/textile），每業 8-12 料件、2-3 成品、1-2 機台、3-5 客戶/供應商。**規模不足以上線，且無 BOM 匯入範本**。

### 5.2 目標規模（機械加工 metal、電子組裝 electronic 兩業「上線啟始包」）

| 項目 | 機械加工 | 電子組裝 |
|---|---|---|
| 料件 Part | 40（原料 15 / 半成品 10 / 成品 8 / 耗材 7） | 45（電子料 20 / 機構件 10 / 半成品 8 / 成品 7） |
| 成品 Product + BOM | 8（2 階 BOM，每張 5-12 項） | 8（3 階 BOM，每張 8-25 項） |
| Routing（製程） | 8 張，每張 4-8 工序 | 8 張，每張 6-12 工序（含 SMT/插件/測試） |
| WorkCenter | 6（CNC 車/銑、研磨、拋光、品檢、包裝） | 8（SMT、插件、波焊、測試、組裝、品檢、包裝） |
| 客戶 | 5（含 1 家出口、1 家電子廠） | 5 |
| 供應商 | 5（鋼材/螺絲/刀具/包材/加工） | 6（IC/PCB/電阻電容/機構/線材/包材） |
| 單價表 | SupplierPrice 每料 1-3 家 | 同左 |
| 安全庫存/前置天數/單位成本 | 全料件填滿 | 同左 |
| 示範單據 | 各 1：報價單→SO→WO（含 Routing）→出貨；PO→收貨 | 同左 |

### 5.3 CSV 匯入範本（`backend/data/templates/`，欄位對應實際 model）

| 檔名 | 對應表 | 欄位（檔頭） |
|---|---|---|
| parts_import.csv | Part | part_no, name_zh, name_en, category(unit 選項), unit, min_stock, max_stock, safety_stock, lead_time_days, unit_cost, unit_price, is_active |
| customers_import.csv | Customer | code, name, tax_id, grade, contact_person, contact_email, contact_phone, address, payment_terms, credit_limit, is_active |
| suppliers_import.csv | Supplier | code, name, tax_id, contact_person, contact_phone, email, address, payment_terms, lead_time_days, is_active |
| bom_import.csv | Product+BOMItem | product_no, product_name, component_no, component_name, qty_per_unit, scrap_rate, sequence_no, is_active |
| routings_import.csv | Routing+RoutingStep | product_no, routing_no, seq, op_name, work_center_code, setup_time_min, run_time_min_per_unit, is_critical |

> 匯入器沿用 `app/integrations/connectors/csv_connector.py`（已存在）+ 出 ConfirmCard（migrate 前確認筆數，走 G-509 模式）。

### 5.4 檢查點

```
python -m scripts.seed_industries metal → 檢查數量 ≥ 目標規模、BOM 完整性（無孤兒料號）、Routing 全工序有機台
測試：tests/smoke/test_industry_seed.py（完整性 assert + 跑一次 MRP 不炸）
```

---

## 6. P0-6 系統組態預設

### 6.1 FactoryConfig / 公司設定預設（`system_defaults.py`，seed 時寫入，UI 可改）

| key | 預設值 | 說明 |
|---|---|---|
| company.name / tax_id / address / phone / logo_path | 空（安裝精靈引導填） | 沿用 v3.37 OnboardingWizard |
| currency | TWD | 幣別（多幣別 Phase 後） |
| vat_rate | 5% | 銷項稅率 |
| tax_type | 應稅 | 應稅/免稅/零稅率 |
| timezone | Asia/Taipei | 沿用 v3.54 |
| workweek | 一~五；國定假日併入 TaiwanWorkdays（v3.42 已有） | |
| payment_terms_default | 月結 30 天 | SO/PO 預設 |
| credit_check_enabled | true | 連結家規 #6 |
| inventory_cost_method | weighted_average | 加權平均（FIFO Phase D） |
| invoice_batch | 電子發票預設開立（B2B） | 沿用 v3.55 |
| backup.enabled | true | 每日 03:00 自動備份至 `backups/` |
| backup.retention_days | 30 | |
| ai.daily_limit_per_user | 200 | 沿用 v3.42 |
| llm.provider / model | deepseek / deepseek-chat | 沿用 config.py |

### 6.2 `.env.example` 補充

```
TZ=Asia/Taipei
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
CURRENCY=TWD
VAT_RATE=0.05
DEFAULT_PAYMENT_TERMS=net30
```

### 6.3 檢查點

```
seed 後 GET /api/settings → 預設值全部出現且可覆寫
測試：tests/smoke/test_system_defaults.py
```

---

## 7. 實作計畫（檔案與工時）

| # | 任務 | 檔案 | 工時 | 依賴 |
|---|---|---|---|---|
| 1 | 科目表 seed | `scripts/seed_accounts.py`（新）+ `scripts/seed.py` 串接 | 1d | — |
| 2 | 報表對應欄位 | `models/accounting.py` Account 加 `fs_line`（migration v006） | 0.5d | 1 |
| 3 | 角色矩陣 | `scripts/seed_permissions.py` 擴充 + RowFilter 種子 | 1d | — |
| 4 | 家規 17 條 + 6 condition | `services/policy_engine.py` | 1d | — |
| 5 | PDF 3 張新（檢驗/盤點/標籤）+ 5 張強化 | `services/print_service.py`、`api/print_export.py` | 2d | — |
| 6 | 4 張需模型範本的版型規格文件 | `docs/FORM_TEMPLATES.md`（新） | 0.5d | — |
| 7 | 行業種子上線規模 ×2 | `scripts/seed_industries.py` 擴充 | 2d | 1 |
| 8 | CSV 匯入範本 5 支 | `backend/data/templates/*.csv` + 匯入工具串 CSV connector | 1.5d | — |
| 9 | 系統組態預設 | `services/system_defaults.py`（新）+ `.env.example` | 1d | — |
| 10 | 測試（5 支 smoke） | `tests/smoke/test_seed_accounts.py`、`test_role_matrix.py`、`test_house_rules_seed.py`、`test_pdf_templates.py`、`test_industry_seed.py`、`test_system_defaults.py` | 2d | 1-9 |
| — | **合計** | | **~12.5 工作天** | |

### 里程碑

```
M1（3d）：科目表 + 角色矩陣 + 系統組態 → 全新安裝即有安全帳號體系
M2（4d）：家規 20 條 + 報表對應 → 內控開箱即用
M3（4d）：PDF 8 張 + 行業種子 ×2 + CSV 範本 → 上線啟動包
M4（2d）：測試全綠 + 90 分鐘驗收劇本跑通
```

---

## 8. 90 分鐘開機即用驗收劇本（金標準）

```
全新環境：python -m scripts.seed（含 seed_accounts / seed_permissions / seed_industries metal）
0:00  登入 admin → 跑安裝精靈（公司資料）
0:10  業務登入（sales_rep 帳號）→ Chat「幫長江精密報價 500 個 M6 螺絲」
      → ConfirmCard → 確認 → 報價單產生（含 PDF 下載）
0:30  業務轉 SO（折扣 3%）→ 主管審批 → 自動轉 WO（含 Routing）+ MRP 檢查
0:50  倉管收料（PO）→ 入庫 → 庫存 +500
1:10  出貨 → 自動開電子發票 + 傳票（DR1200/CR4100/CR2200）+ AR
1:25  會計看損益表區段（本期營收/成本/毛利）→ 資料一致
1:30  ✅ 完成 — 全程 70% 以上操作可「用講的」完成
```

---

## 9. 明確不屬於 Phase 0（後續 Phase 承接）

| 項目 | 承接 Phase |
|---|---|
| AP/AR 明細帳、付款排程、3-Way Match、現金流 | Phase 1 |
| 損益表/資產負債表/401-405 產生器 | Phase 1 |
| 領退料、批號追溯、WO 成本彙總 | Phase 2 |
| 請購/RFQ、RMA、狀態機、單據編號服務 | Phase 3 |
| 排程備份/還原 UI、Chat 管線 RBAC 補洞、MESH TLS | Phase 4 |

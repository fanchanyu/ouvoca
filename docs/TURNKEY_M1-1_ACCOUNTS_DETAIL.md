# M1-1 詳細規劃：migration v006 + seed_accounts

> 前置：`docs/TURNKEY_M1_PLAN.md`（M1 總規劃）、`docs/TURNKEY_PHASE0_SEED_SPEC.md` §1
> 本檔把 M1-1 展開到「可直接照抄實作」的粒度：migration 完整程式碼、86 科目定稿資料表、seed 演算法、API 保護、測試清單。
> **M1-0 審計工具已實作並實測**（`backend/scripts/audit_permission_codes.py`），本檔 §2 收錄實測得出的補碼清單作為 M1-0.2 的定稿工作項。

---

## 1. 目標與範圍

| 項 | 內容 |
|---|---|
| 目的 | 全新安裝即有完整 TW 會計科目表（含報表對應），且既有安裝可無痛升級（alembic v006） |
| 產出 | ① `app/services/fs_defs.py`（fs_line 常數，Phase 1 報表直接引用）② Account model +2 欄 ③ SystemSetting model ④ `alembic/versions/v006_*.py` ⑤ `scripts/seed_accounts.py` ⑥ accounting API 保護 ⑦ `tests/smoke/test_seed_accounts.py` |
| 工時 | **2.0d**（fs_defs 0.1 + model/migration 0.5 + seed 0.7 + API 0.2 + 測試 0.5） |

---

## 2. M1-0 實測結果 → 補碼定稿清單（M1-0.2 工作項）

審計工具實測（160 引用 vs 137 seed）：**MISSING 60 個碼**。分類處置：

### 2.1 新增 canonical 碼（直接進 `seed_permissions.py`，module/resource/action 齊全）

| code | module | resource | action | name_zh | sensitive | risk |
|---|---|---|---|---|---|---|
| approval.request.read / approve / reject | approval | approval.request | read/approve/reject | 查詢/核准/退回 審批單 | True | high |
| tax.einvoice.issue / read / void | tax | tax.einvoice | issue/read/void | 開立/查詢/作廢 電子發票 | True | high |
| tax.tax_id.validate | tax | tax.tax_id | validate | 驗證統編 | False | low |
| tax.report.read | tax | tax.report | read | 查詢稅務報表 | False | medium |
| accounting.ap.read | accounting | accounting.ap | read | 查詢應付帳款 | False | medium |
| accounting.month_close.read | accounting | accounting.month_close | read | 查詢月結狀態 | False | medium |
| accounting.payment.record | accounting | accounting.payment | record | 記錄付款 | True | high |
| accounting.receipt.record | accounting | accounting.receipt | record | 記錄收款 | True | high |
| audit.log.read | audit | audit.log | read | 查詢稽核日誌 | True | high |
| chat.history.read | chat | chat.history | read | 查詢對話紀錄 | False | low |
| dashboard.read | dashboard | dashboard | read | 檢視儀表板 | False | low |
| crm.lead.list | crm | crm.lead | list | 列出潛在客戶 | False | low |
| crm.opportunity.list | crm | crm.opportunity | list | 列出商機 | False | low |
| crm.event.list | crm | crm.event | list | 列出客戶事件 | False | low |
| inventory.count.create / record / adjust / cancel / read | inventory | inventory.count | * | 盤點五操作 | adjust/cancel True | high |
| mps_mrp.master.create / read | mps_mrp | mps_mrp.master | create/read | MPS/MRP 主檔 | False | medium |
| mps_mrp.mps.list / mrp.list | mps_mrp | mps_mrp.mps / mps_mrp.mrp | list | 列表查詢 | False | low |
| permission.role.read / assign | permission | permission.role | read/assign | 角色權限查詢/指派 | assign True | critical |
| production.bom.delete | production | production.bom | delete | 刪除 BOM | True | high |
| production.work_order.cancel | production | production.work_order | cancel | 取消工單 | False | medium |
| purchase.order.cancel | purchase | purchase.order | cancel | 取消採購單 | False | medium |
| purchase.price.read | purchase | purchase.price | read | 查詢進貨單價 | False | low |
| quality.capa.list | quality | quality.capa | list | 列出 CAPA | False | low |
| quality.ncr.create / read | quality | quality.ncr | create/read | 不良紀錄 | False | medium |
| sales.order.cancel | sales | sales.order | cancel | 取消銷售訂單 | False | medium |
| sales.quotation.create / read / update / send / cancel | sales | sales.quotation | * | 報價單五操作 | False | medium |
| system.health.read | system | system.health | read | 系統健康檢查 | False | low |
| user.profile.read | user | user.profile | read | 個人資料查詢 | False | medium |
| warehouse.cycle_count.list | warehouse | warehouse.cycle_count | list | 列出循環盤點 | False | low |
| warehouse.pick.list / read | warehouse | warehouse.pick | list/read | 揀貨查詢 | False | low |

> 共 **37 個新碼**。alias 檔已更新（`data/permission_alias.json`）：
> `production.wo.* ↔ production.work_order.*`、`production.workcenter.list ↔ production.work_center.list`、`sales.so.update ↔ sales.order.update`、`crm.customer.read ↔ sales.customer.read`、`tax.einvoice.* ↔ accounting.einvoice.*`（legacy 為 cancel，非 void）。
>
> ⚠️ **2026-08-04 實作修正**：實測補碼定稿為 **61 個新碼**（137 → 198）。
> 除本表 37 個外，另含：① 審計實測額外抓出的引用碼 `crm.customer.read`、`production.wo.read/update`、`production.workcenter.list`、`sales.so.update`（共 5 個，皆為 alias 組的變體側）；② `purchase.po.create/approve/read`（3 個）；③ 並行開發新增的 v3.60 Phase B1 金流碼（`accounting.bank.*`、`accounting.payment.read/create`、`accounting.receipt.create`、`accounting.ap.read`，共 6 個，由另一工作流加入 EXTRA_PERMISSIONS）；④ `accounting.account.delete`（M1-1.4 API 需要，1 個）；⑤ `dashboard.read`（2 段別名，1 個）。驗證結果：`audit_permission_codes` MISSING=0 / exit 0。

### 2.2 驗收（M1-0.3）

```
python -m scripts.seed_permissions → python -m scripts.audit_permission_codes
→ MISSING = 0（exit 0）；ORPHAN 僅警告
```

---

## 3. `app/services/fs_defs.py`（新，0.1d）

```python
"""三大報表行定義（fs_line 值域的唯一真相來源）。

seed_accounts 與 Phase 1 報表產生器（fs_statements.py）共用，
防止科目 seed 與報表產生器對不上。
"""
# fs_line 允許值（白名單）
FS_LINES = (
    "bs_current_asset",       # 資產負債表-流動資產
    "bs_noncurrent_asset",    # 資產負債表-非流動資產
    "bs_current_liability",   # 資產負債表-流動負債
    "bs_noncurrent_liability",# 資產負債表-非流動負債
    "bs_equity",              # 資產負債表-權益
    "is_revenue",             # 損益表-營業收入
    "is_cost",                # 損益表-營業成本
    "is_expense",             # 損益表-營業費用
    "is_other_income",        # 損益表-業外收入
    "is_other_expense",       # 損益表-業外支出
    "is_tax",                 # 損益表-所得稅
)

# 中文標籤（Phase 1 報表印行用）
FS_LINE_LABELS = {
    "bs_current_asset": "流動資產",
    "bs_noncurrent_asset": "非流動資產",
    "bs_current_liability": "流動負債",
    "bs_noncurrent_liability": "非流動負債",
    "bs_equity": "權益",
    "is_revenue": "營業收入",
    "is_cost": "營業成本",
    "is_expense": "營業費用",
    "is_other_income": "業外收入",
    "is_other_expense": "業外支出",
    "is_tax": "所得稅費用",
}
```

---

## 4. Model 變更

### 4.1 `app/models/accounting.py` — Account +2 欄

```python
class Account(Base):
    ...
    code = Column(String(20), unique=True, nullable=False)
    ...
    # v006 (M1-1)：三大報表行對應 + 系統內建保護
    fs_line = Column(String(80))                        # fs_defs.FS_LINES 白名單值
    is_system = Column(Boolean, default=False)          # True = 系統內建（五硬編碼）
```

### 4.2 `app/models/system_setting.py`（新）

```python
"""SystemSetting — 系統組態 key-value（M1-3 使用，v006 一起落地）。"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON, Boolean, DateTime
from app.core.base import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(80), primary_key=True)
    value = Column(JSON, nullable=False)
    group = Column(String(40), default="general")   # general/company/finance/backup/ai
    description = Column(String(200))
    is_system = Column(Boolean, default=False)
    updated_by = Column(String(36))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 4.3 `app/models/__init__.py` 追加

```python
from app.models.system_setting import SystemSetting  # v006 (M1)
```

---

## 5. Migration v006（`alembic/versions/v006_accounts_fs_and_settings.py`）

> 樣式對齊 v004/v005（顯式 `op.create_table` + SQLite `batch_alter_table`）。
> 全新安裝走 `init_db()`（create_all 依 model 建出全部含新欄位）；v006 只服務**既有安裝升級**（v3.55 → v3.56）。

```python
"""M1-1 — accounts 加 fs_line/is_system + system_settings 表。

  - Account.fs_line      : 三大報表行對應（fs_defs.FS_LINES）
  - Account.is_system    : 系統內建科目保護（硬編碼五碼 1100/1200/2100/2200/4100）
  - system_settings 表   : 系統組態 key-value（M1-3）

Revision ID: 006_accounts_fs_and_settings
Revises: 005_delivery_notes
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "006_accounts_fs_and_settings"
down_revision: Union[str, None] = "005_delivery_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) system_settings 表（新表，顯式建立）
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("group", sa.String(40), server_default="general"),
        sa.Column("description", sa.String(200)),
        sa.Column("is_system", sa.Boolean(), server_default="0"),
        sa.Column("updated_by", sa.String(36)),
        sa.Column("updated_at", sa.DateTime()),
    )

    # 2) accounts 加欄位（SQLite 需 batch）
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(sa.Column("fs_line", sa.String(80)))
        batch_op.add_column(sa.Column("is_system", sa.Boolean(), server_default="0"))

    # 3) 硬編碼五碼回填保護（既有安裝）
    op.execute(
        "UPDATE accounts SET is_system = 1 "
        "WHERE code IN ('1100', '1200', '2100', '2200', '4100')"
    )

    # 4) 報表查詢索引（Phase 1 三大報表用）
    op.create_index("ix_accounts_fs_line", "accounts", ["fs_line"])


def downgrade() -> None:
    op.drop_index("ix_accounts_fs_line", table_name="accounts")
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("is_system")
        batch_op.drop_column("fs_line")
    op.drop_table("system_settings")
```

> ⚠️ 註記（承接 v001 `create_all` 設計）：migration 只在「既有 DB 升級」執行；
> 全新安裝由 `init_db()` 依 model 直接建 schema，兩軌欄位必然一致（model 是唯一真相來源）。

---

## 6. `scripts/seed_accounts.py` 完整設計（0.7d）

### 6.1 資料結構（86 科目定稿）

欄位：`code | name_zh | account_type | is_debit_normal | parent_code | fs_line | is_system`

| code | name_zh | account_type | debit | parent | fs_line | sys |
|---|---|---|---|---|---|---|
| 1100 | 現金及銀行存款 | asset | T | — | bs_current_asset | ★ |
| 1101 | 庫存現金 | asset | T | 1100 | bs_current_asset | |
| 1102 | 銀行存款 | asset | T | 1100 | bs_current_asset | |
| 1103 | 零用金 | asset | T | 1100 | bs_current_asset | |
| 1110 | 應收票據 | asset | T | — | bs_current_asset | |
| 1200 | 應收帳款 | asset | T | — | bs_current_asset | ★ |
| 1210 | 備抵呆帳-應收帳款 | asset | F | 1200 | bs_current_asset | |
| 1250 | 其他應收款 | asset | T | — | bs_current_asset | |
| 1300 | 存貨 | asset | T | — | bs_current_asset | |
| 1310 | 原料 | asset | T | 1300 | bs_current_asset | |
| 1320 | 物料 | asset | T | 1300 | bs_current_asset | |
| 1330 | 在製品 | asset | T | 1300 | bs_current_asset | |
| 1340 | 製成品 | asset | T | 1300 | bs_current_asset | |
| 1350 | 商品存貨 | asset | T | 1300 | bs_current_asset | |
| 1400 | 預付款項 | asset | T | — | bs_current_asset | |
| 1410 | 進項稅額 | asset | T | 1400 | bs_current_asset | |
| 1420 | 預付費用 | asset | T | 1400 | bs_current_asset | |
| 1430 | 預付貨款 | asset | T | 1400 | bs_current_asset | |
| 1500 | 其他流動資產 | asset | T | — | bs_current_asset | |
| 1600 | 不動產、廠房及設備 | asset | T | — | bs_noncurrent_asset | |
| 1610 | 土地 | asset | T | 1600 | bs_noncurrent_asset | |
| 1620 | 房屋及建築 | asset | T | 1600 | bs_noncurrent_asset | |
| 1621 | 累計折舊-房屋及建築 | asset | F | 1620 | bs_noncurrent_asset | |
| 1630 | 機器設備 | asset | T | 1600 | bs_noncurrent_asset | |
| 1631 | 累計折舊-機器設備 | asset | F | 1630 | bs_noncurrent_asset | |
| 1640 | 運輸設備 | asset | T | 1600 | bs_noncurrent_asset | |
| 1641 | 累計折舊-運輸設備 | asset | F | 1640 | bs_noncurrent_asset | |
| 1650 | 辦公設備 | asset | T | 1600 | bs_noncurrent_asset | |
| 1651 | 累計折舊-辦公設備 | asset | F | 1650 | bs_noncurrent_asset | |
| 1700 | 無形資產 | asset | T | — | bs_noncurrent_asset | |
| 1800 | 其他非流動資產 | asset | T | — | bs_noncurrent_asset | |
| 2100 | 應付帳款 | liability | F | — | bs_current_liability | ★ |
| 2200 | 銷項稅額 | liability | F | — | bs_current_liability | ★ |
| 2210 | 應付票據 | liability | F | — | bs_current_liability | |
| 2220 | 應付費用 | liability | F | — | bs_current_liability | |
| 2230 | 應付薪資及獎金 | liability | F | — | bs_current_liability | |
| 2240 | 應付所得稅 | liability | F | — | bs_current_liability | |
| 2250 | 預收款項 | liability | F | — | bs_current_liability | |
| 2260 | 其他應付款 | liability | F | — | bs_current_liability | |
| 2300 | 短期借款 | liability | F | — | bs_current_liability | |
| 2400 | 長期借款 | liability | F | — | bs_noncurrent_liability | |
| 2500 | 其他非流動負債 | liability | F | — | bs_noncurrent_liability | |
| 3100 | 股本 | equity | F | — | bs_equity | |
| 3200 | 資本公積 | equity | F | — | bs_equity | |
| 3300 | 保留盈餘 | equity | F | — | bs_equity | |
| 3310 | 法定盈餘公積 | equity | F | 3300 | bs_equity | |
| 3320 | 特別盈餘公積 | equity | F | 3300 | bs_equity | |
| 3330 | 未分配盈餘 | equity | F | 3300 | bs_equity | |
| 3400 | 本期損益 | equity | F | — | bs_equity | |
| 4100 | 銷貨收入 | revenue | F | — | is_revenue | ★ |
| 4110 | 銷貨退回及折讓 | revenue | T | 4100 | is_revenue | |
| 4200 | 加工收入 | revenue | F | — | is_revenue | |
| 4300 | 其他營業收入 | revenue | F | — | is_revenue | |
| 5100 | 銷貨成本 | cost | T | — | is_cost | |
| 5110 | 原料耗用 | cost | T | 5100 | is_cost | |
| 5120 | 直接人工 | cost | T | 5100 | is_cost | |
| 5130 | 製造費用 | cost | T | 5100 | is_cost | |
| 5200 | 進貨成本 | cost | T | — | is_cost | |
| 5300 | 進貨退回及折讓 | cost | F | 5200 | is_cost | |
| 6100 | 薪資支出 | expense | T | — | is_expense | |
| 6110 | 勞健保費 | expense | T | — | is_expense | |
| 6120 | 退休金提撥 | expense | T | — | is_expense | |
| 6130 | 伙食費 | expense | T | — | is_expense | |
| 6200 | 租金支出 | expense | T | — | is_expense | |
| 6210 | 文具印刷費 | expense | T | — | is_expense | |
| 6220 | 郵電費 | expense | T | — | is_expense | |
| 6230 | 水電瓦斯費 | expense | T | — | is_expense | |
| 6240 | 燃料費 | expense | T | — | is_expense | |
| 6250 | 運費 | expense | T | — | is_expense | |
| 6260 | 廣告費 | expense | T | — | is_expense | |
| 6270 | 交際費 | expense | T | — | is_expense | |
| 6280 | 差旅費 | expense | T | — | is_expense | |
| 6290 | 修繕費 | expense | T | — | is_expense | |
| 6300 | 稅捐 | expense | T | — | is_expense | |
| 6310 | 折舊費用 | expense | T | — | is_expense | |
| 6320 | 各項攤提 | expense | T | — | is_expense | |
| 6330 | 呆帳損失 | expense | T | — | is_expense | |
| 6400 | 其他營業費用 | expense | T | — | is_expense | |
| 7100 | 利息收入 | other_income | F | — | is_other_income | |
| 7200 | 租金收入 | other_income | F | — | is_other_income | |
| 7300 | 兌換利益 | other_income | F | — | is_other_income | |
| 7400 | 其他收入 | other_income | F | — | is_other_income | |
| 7500 | 利息費用 | other_expense | T | — | is_other_expense | |
| 7600 | 兌換損失 | other_expense | T | — | is_other_expense | |
| 7700 | 其他損失 | other_expense | T | — | is_other_expense | |
| 9100 | 所得稅費用 | tax | T | — | is_tax | |

> 共 **86 科**（原 spec 估 ~79，定稿 86）。★ = 硬編碼五碼（1100/1200/2100/2200/4100），`is_system=True`。
> `4110`/`5300` 為抵減科目（銷退折讓/進退折讓），借貸方向反轉但 account_type 不變。

### 6.2 seed 演算法

```python
# scripts/seed_accounts.py
ACCOUNTS: list[dict] = [ {...86 筆如上表...} ]
SYSTEM_CODES = {"1100", "1200", "2100", "2200", "4100"}

async def seed_accounts(dry_run: bool = False) -> int:
    await init_db()
    async with AsyncSessionLocal() as db:
        # Pass 1：UPSERT by code（先讀出既有全量 map，避免 N+1）
        existing = {a.code: a for a in (await db.execute(select(Account))).scalars()}
        for spec in ACCOUNTS:
            row = existing.get(spec["code"])
            if row is None:
                db.add(Account(id=str(uuid.uuid4()), **spec))
            else:
                # 更新非保護欄位；is_system 永不降級（True 維持 True）
                for f in ("name", "account_type", "is_debit_normal", "fs_line"):
                    setattr(row, f, spec[f])
                if spec["is_system"]:
                    row.is_system = True
        # Pass 2：parent_id 解析（parent_code → id）
        # Pass 3：驗證（任一失敗 → rollback + print + return 1）
        #   - fs_line ∈ fs_defs.FS_LINES
        #   - 借貸方向：asset/cost/expense/other_expense/tax 必須 debit_normal；
        #     liability/equity/revenue/other_income 必須 credit_normal
        #   - parent_code 有指定者必須存在
        #   - 硬編碼五碼 name/type/fs_line 與 seed 一致（防漂移）
        await db.commit()
        return 0

if __name__ == "__main__":  # 支援 --dry-run / --json
    ...
```

### 6.3 `seed.py` 串接

```python
# scripts/seed.py 內（順序不可顛倒）
await seed_permissions()            # 既有
from scripts.seed_accounts import seed_accounts
await seed_accounts()               # 新：科目表（依賴 fs_defs 與 Account model）
# （M1-3 的 seed_system_settings 在此之後）
```

---

## 7. API 保護（`app/api/accounting.py` + `services/accounting.py`）

| 端點 | 修改 |
|---|---|
| `POST /accounts` | 不變（新科目一律 is_system=False；fs_line 可空白 → 驗證白名單） |
| `GET /accounts` | 不變（AccountResponse 需加 fs_line/is_system 欄位輸出） |
| 新增 `PUT /accounts/{code}` | `accounting.account.update`；**is_system=True 時禁止改 code**（BusinessRuleError 403） |
| 新增 `DELETE /accounts/{code}` | `accounting.account.delete`（新權限碼，加入 §2.1 清單）；is_system 一律 403 |

- `services/accounting.py` 的 `create_account` 加 `fs_line` 白名單驗證（引用 `fs_defs`）
- `schemas/accounting.py` `AccountCreate/AccountResponse` 加 `fs_line`/`is_system`

---

## 8. 測試清單（`tests/smoke/test_seed_accounts.py`）

```python
def test_seed_account_count()        # == 86；五硬編碼 is_system=True
def test_hardcoded_codes_present()   # 1100/1200/2100/2200/4100 存在且名稱正確
def test_fs_line_whitelist()         # 全部 fs_line ∈ fs_defs.FS_LINES 且非空
def test_debit_credit_direction()    # 依 account_type 驗證 is_debit_normal
def test_parent_resolution()         # 無懸空 parent；parent 已建立（id 非空）
def test_seed_idempotent()           # 跑兩次筆數不變、fs_line 不變
def test_system_account_code_protected()  # PUT 改 1100 的 code → 403
def test_system_account_deletable()       # DELETE 1100 → 403；DELETE 自訂科 → 200
def test_alias_audit_gate()               # 審計工具 MISSING == 0（M1-0.3 複驗）
```

---

## 9. WBS（M1-1 內任務）與驗收

| # | 任務 | 檔案 | 依賴 | 工時 |
|---|---|---|---|---|
| M1-1.0 | fs_defs.py 常數 | `app/services/fs_defs.py` | — | 0.1d |
| M1-1.1 | Account +2 欄、SystemSetting model、models/__init__ | `app/models/*` | — | 0.2d |
| M1-1.2 | migration v006（§5 完整內容） | `alembic/versions/v006_*.py` | 1.1 | 0.3d |
| M1-1.3 | seed_accounts.py（86 科 + 驗證） | `scripts/seed_accounts.py` | 1.0, 1.1 | 0.7d |
| M1-1.4 | accounting API 保護 + schema | `app/api/accounting.py`、`app/services/accounting.py`、`app/schemas/accounting.py` | 1.3 | 0.2d |
| M1-1.5 | 測試 9 支 | `tests/smoke/test_seed_accounts.py` | 1.2-1.4 | 0.5d |
| M1-0.2 | 37 個補碼（§2.1）+ alias 檔定稿 | `scripts/seed_permissions.py`、`data/permission_alias.json` | — | 0.5d |

**驗收（全新軌）**：
```
python -m scripts.seed
→ Account = 86；五碼 is_system；fs_line 全填
→ python -m scripts.audit_permission_codes → MISSING = 0
→ pytest tests/smoke/test_seed_accounts.py → 9 綠
```
**驗收（升級軌）**：v3.55 DB（含既有科目）→ `alembic upgrade head`（v006 無錯）→ `seed_accounts` 補 86 科、is_system 回填、既有自訂科不動。

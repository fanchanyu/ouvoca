# M1-1.3 詳細規劃：seed_accounts.py 實作規格

> 前置：`docs/TURNKEY_M1-1_ACCOUNTS_DETAIL.md`（§4 model、§5 migration v006、§6.1 的 **86 科目定稿資料表**、§6.2 演算法概要）
> 本檔把 seed_accounts.py 展開到「函式級」規格：資料格式、UPSERT 逐欄語義、parent 解析、驗證矩陣、錯誤處理、CLI、冪等保證、測試對照。86 科資料不重複貼，以父文件 §6.1 為準。

---

## 1. 檔案與依賴

| 項目 | 內容 |
|---|---|
| 路徑 | `backend/scripts/seed_accounts.py`（新） |
| 依賴 | `app.database.{AsyncSessionLocal, init_db}`、`app.models.accounting.Account`、`app.services.fs_defs`（M1-1.0 產出）、`app.core.exceptions.BusinessRuleError` 不直接用（seed 腳本自帶錯誤輸出） |
| 呼叫方 | `scripts/seed.py`（串接）、CLI 手動跑 |
| 工時 | 0.7d |

---

## 2. 資料結構（`ACCOUNTS`）

### 2.1 格式

```python
# 86 筆，內容 = 父文件 §6.1 表格逐列轉換（★ = is_system=True）
ACCOUNTS: list[dict] = [
    {"code": "1100", "name": "現金及銀行存款", "account_type": "asset",
     "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset",
     "is_system": True},
    {"code": "1101", "name": "庫存現金", "account_type": "asset",
     "is_debit_normal": True, "parent_code": "1100", "fs_line": "bs_current_asset",
     "is_system": False},
    ...
]

# 硬編碼五碼（程式碼層面被 services/sales.py 等引用的科目）
SYSTEM_CODES: frozenset[str] = frozenset({"1100", "1200", "2100", "2200", "4100"})
```

### 2.2 與現有程式碼的一致性保證（寫進 seed 驗證）

| 硬編碼碼 | 引用處（現況） | seed 要求 |
|---|---|---|
| 1100 現金及銀行存款 | `business_completion_tools.py:357/444`（收付款 DR/CR） | name 必須含「現金」 |
| 1200 應收帳款 | `sales.py:110`、`business_completion_tools.py:447` | name = 應收帳款 |
| 2100 應付帳款 | `business_completion_tools.py:354` | name = 應付帳款 |
| 2200 銷項稅額 | `sales.py:112`（O2C 自動傳票 CR） | name 必須含「銷項稅額」 |
| 4100 銷貨收入 | `sales.py:111` | name = 銷貨收入 |

> 驗證規則：若 DB 已有這些 code 但 name 與 seed 不符 → **僅警告**（既有客製改名不強制覆寫），
> 但 `is_system=True` 強制補上（保護編號，不鎖名稱）。

---

## 3. 函式規格

```python
async def seed_accounts(dry_run: bool = False) -> int
```

### 3.1 流程（3 pass + commit）

```
Pass 0  預檢（同步、純資料）：ACCOUNTS 內部一致性
        - code 無重複；SYSTEM_CODES ⊆ ACCOUNTS code
        - parent_code 必須存在於 ACCOUNTS（自己除外）
        - fs_line ∈ fs_defs.FS_LINES；account_type 合法
        - 借貸方向規則：asset/cost/expense/other_expense/tax → debit；
          liability/equity/revenue/other_income → credit
        → 任一失敗：print + return 2（不碰 DB）

Pass 1  UPSERT by code（async，單一 session）
        existing = {a.code: a for a in select(Account)}
        for spec in ACCOUNTS:
            row = existing.get(spec["code"])
            if row is None:  db.add(Account(id=uuid4, **spec)); created += 1
            else:
                updated_fields = 0
                for f in ("name", "account_type", "is_debit_normal", "fs_line"):
                    if getattr(row, f) != spec[f]:
                        setattr(row, f, spec[f]); updated_fields += 1
                if spec["is_system"] and not row.is_system:
                    row.is_system = True; updated_fields += 1
                # is_system 永不降級：spec 為 False 時不動既有 True
                if updated_fields: updated += 1

Pass 2  parent_id 解析（須在 flush 後）
        parent_map = {a.code: a.id for a in select(Account)}
        for spec in ACCOUNTS:
            row = existing[spec["code"]]（或剛新增物件）
            if spec["parent_code"]:
                row.parent_id = parent_map[spec["parent_code"]]
        # 懸空 parent 不可能（Pass 0 已擋），但仍 assert 防護

Pass 3  驗證（任一失敗 → rollback + return 1）
        - 全部 Account 的 fs_line ∈ 白名單（含既有客製科目：非空即檢查，
          空值允許（客製科目可無報表對應），但 seed 的 86 科必須非空）
        - 五硬編碼存在且 is_system=True
        - 借貸方向抽驗（同 Pass 0 規則）

Commit / rollback：
        dry_run=False → await db.commit()
        dry_run=True  → await db.rollback()（只印計畫動作，不寫入）
```

### 3.2 回傳值與 exit code

| 值 | 意義 | CLI 行為 |
|---|---|---|
| 0 | 成功（含 0 變更） | exit 0 |
| 1 | Pass 3 驗證失敗（已 rollback） | exit 1 |
| 2 | Pass 0 預檢失敗（未碰 DB） | exit 2 |

### 3.3 輸出

```
✓ seed_accounts: 86 defined (86 created / 0 updated / 0 skipped)
  hardcoded: 1100/1200/2100/2200/4100 all is_system=True
  validation: fs_line 86/86, direction 86/86, parent 86/86
```
`--dry-run` 時每筆動作列出：`[DRY] +1100 現金及銀行存款` / `[DRY] ~4100 name: 銷貨收入→銷貨收入`。

### 3.4 CLI

```python
if __name__ == "__main__":
    asyncio.run(seed_accounts(dry_run="--dry-run" in sys.argv))
```

---

## 4. 冪等保證（升級重跑安全性）

| 情境 | 行為 |
|---|---|
| 全新跑第 1 次 | 86 科全建 |
| 重跑第 2 次 | created=0, updated=0（除非有人改了 name/fs_line → 被 sync 回 seed 值） |
| 客戶改過科目名稱（is_system=False 或 True） | **會被 seed 覆寫回 seed 值** — 這是設計選擇（seed 為系統科目唯一真相），文件明示；客製科目請加新 code，勿改內建名稱 |
| 客戶新增自訂科目（code 不在 ACCOUNTS） | 完全不受影響（seed 只掃 86 個定義 code） |
| DB 已有 1100 且 is_system=False（舊版沒保護） | seed 強制補 is_system=True |
| 並行 v3.60 工作流加入金流碼 | 無衝突（seed 不碰權限表） |

---

## 5. 錯誤情境表

| # | 情境 | 層 | 行為 |
|---|---|---|---|
| 1 | ACCOUNTS 內 code 重複 | Pass 0 | return 2 + 列出重複碼 |
| 2 | parent_code 指向不存在科目 | Pass 0 | return 2 + 列出懸空 |
| 3 | fs_line 非白名單值 | Pass 0 | return 2 |
| 4 | 借貸方向與 account_type 衝突 | Pass 0 | return 2 |
| 5 | 硬編碼五碼被 ACCOUNTS 漏定義 | Pass 0 | return 2（防程式碼與 seed 漂移） |
| 6 | DB 連線失敗 | 任意 | 拋出（沿用 seed.py 既有風格，含明確訊息） |
| 7 | 既有科目 parent 指向已被刪的科目 | Pass 3 | 警告 + 不 rollback（非 seed 造成，僅提示） |
| 8 | 客戶把 1100 改成負債類 | Pass 3 | return 1 + rollback（硬編碼科目方向漂移 = 傳票全錯） |

---

## 6. 測試對照（`tests/smoke/test_seed_accounts.py` 9 支）

| 測試 | 對應規格 | 關鍵 assert |
|---|---|---|
| test_seed_account_count | §3.1 | `len(ACCOUNTS) == 86`、DB 數 = 86 |
| test_hardcoded_codes_present | §2.2 | 五碼存在、`is_system=True`、name 正確 |
| test_fs_line_whitelist | §3.1 Pass 0/3 | 86 科 fs_line ∈ FS_LINES 且非空 |
| test_debit_credit_direction | §3.1 | asset/cost/expense → debit；liability/equity/revenue → credit |
| test_parent_resolution | §3.1 Pass 2 | 所有有 parent_code 的科目 parent_id 非空且指向正確 code |
| test_seed_idempotent | §4 | 跑兩次：created=0、updated=0、fs_line 不變 |
| test_system_account_code_protected | M1-1.4 API | `PUT /api/accounting/accounts/1100` 改 code → 403 |
| test_system_account_deletable | M1-1.4 API | `DELETE 1100` → 403；自訂科 → 200 |
| test_alias_audit_gate | M1-0.3 | 審計工具 MISSING=0（合併 CI 跑） |

---

## 7. seed.py 串接（`scripts/seed.py` 修改點）

```python
# 順序：RBAC → 科目表 → 系統組態 → 既有資料
await seed_permissions()                  # 既有（含 M1-0.2 補碼）
from scripts.seed_accounts import seed_accounts
rc = await seed_accounts()                # 新增；rc!=0 時中止後續 seed（失敗快停）
if rc:
    raise SystemExit(rc)
# （M1-3 的 seed_system_settings() 於此之後插入）
```

---

## 8. 驗收

```
全新軌：
  python -m scripts.seed
  → ✓ seed_accounts: 86 defined (86 created / 0 updated)
  → python -m scripts.audit_permission_codes → exit 0
  → pytest tests/smoke/test_seed_accounts.py → 9 綠

升級軌（v3.55 DB）：
  alembic upgrade head（v006：欄位 + is_system 回填）
  → python -m scripts.seed_accounts
  → created=86 或更新既有；客戶自訂科目不動；五碼 is_system=True
  → 重跑第 2 次 → created=0, updated=0（冪等）
```

## 9. 風險與對策

| 風險 | 對策 |
|---|---|
| 86 科資料表人工鍵入筆誤（parent/方向/fs_line） | Pass 0 預檢把大部分錯誤擋在寫入前；測試逐科斷言 |
| seed 覆寫客戶改名的內建科目 | 文件明示 + 只 sync 4 個資料欄位；未來若客戶要求鎖定可加 `is_locked_by_customer` 欄位（Phase E） |
| 與 v3.60 並行工作流改動同檔 | seed_accounts 是全新檔，不與他人共檔；ACCOUNTS 資料獨立於權限 seed |
| fs_defs 白名單日後擴充 | 新 fs_line 值必須先加進 fs_defs.FS_LINES（測試 test_fs_line_whitelist 強制） |

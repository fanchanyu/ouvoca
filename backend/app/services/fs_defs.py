"""三大報表行定義（fs_line 值域的唯一真相來源）。

seed_accounts 與 Phase 1 報表產生器（fs_statements.py）共用，
防止科目 seed 與報表產生器對不上。

規格：docs/TURNKEY_M1-1_ACCOUNTS_DETAIL.md §3
"""

# fs_line 允許值（白名單）
FS_LINES: tuple[str, ...] = (
    "bs_current_asset",        # 資產負債表-流動資產
    "bs_noncurrent_asset",     # 資產負債表-非流動資產
    "bs_current_liability",    # 資產負債表-流動負債
    "bs_noncurrent_liability", # 資產負債表-非流動負債
    "bs_equity",               # 資產負債表-權益
    "is_revenue",              # 損益表-營業收入
    "is_cost",                 # 損益表-營業成本
    "is_expense",              # 損益表-營業費用
    "is_other_income",         # 損益表-業外收入
    "is_other_expense",        # 損益表-業外支出
    "is_tax",                  # 損益表-所得稅
)

# 中文標籤（Phase 1 報表印行用）
FS_LINE_LABELS: dict[str, str] = {
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

# 科目類別（Account.account_type 允許值）
ACCOUNT_TYPES: tuple[str, ...] = (
    "asset", "liability", "equity",
    "revenue", "cost", "expense",
    "other_income", "other_expense", "tax",
)

# 借貸方向規則：debit normal（is_debit_normal=True）的類別
DEBIT_NORMAL_TYPES: frozenset[str] = frozenset({
    "asset", "cost", "expense", "other_expense", "tax",
})

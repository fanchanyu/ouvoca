"""M1-1.3 seed_accounts — TW 會計科目表種子（86 科）。

規格：docs/TURNKEY_M1-1_ACCOUNTS_DETAIL.md §6、docs/TURNKEY_M1-1_3_SEEDACCOUNTS_DETAIL.md

設計：
  - Pass 0 同步預檢（資料檔內部一致性）→ 失敗 return 2（不碰 DB）
  - Pass 1 UPSERT by code（不刪除既有；is_system 永不降級）
  - Pass 2 parent_id 解析
  - Pass 3 驗證（fs_line 白名單 / 五硬編碼保護 / 借貸方向）→ 失敗 rollback return 1
  - --dry-run：只印計畫動作不寫入
  - 輸出強制 UTF-8（Windows cp950 console 相容）

Usage:
    python -m scripts.seed_accounts            # 正常執行
    python -m scripts.seed_accounts --dry-run  # 預演
    # 或由 scripts.seed 呼叫 seed_accounts()
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models.accounting import Account
from app.services import fs_defs

# 硬編碼五碼：程式碼層面被 services/sales.py / agents/domains/business_completion_tools.py
# 引用的科目（1100 收付款現金、1200 AR、2100 AP、2200 銷項稅額、4100 銷貨收入）。
SYSTEM_CODES: frozenset[str] = frozenset({"1100", "1200", "2100", "2200", "4100"})

# 抵減科目（contra）：借貸方向與其 account_type 常態相反
#   - 備抵呆帳 / 累計折舊（asset 但貸方方向）
#   - 銷貨退回及折讓（revenue 但借方方向）
#   - 進貨退回及折讓（cost 但貸方方向）
CONTRA_CODES: frozenset[str] = frozenset({"1210", "1621", "1631", "1641", "1651", "4110", "5300"})

# ────────────────────────────────────────────────────────────
# 86 科定稿（code, name, account_type, is_debit_normal, parent_code, fs_line, is_system）
# 硬編碼五碼 is_system=True（★）
# ────────────────────────────────────────────────────────────
ACCOUNTS: list[dict] = [
    # --- 資產：流動資產 ---
    {"code": "1100", "name": "現金及銀行存款", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset", "is_system": True},
    {"code": "1101", "name": "庫存現金", "account_type": "asset", "is_debit_normal": True, "parent_code": "1100", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1102", "name": "銀行存款", "account_type": "asset", "is_debit_normal": True, "parent_code": "1100", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1103", "name": "零用金", "account_type": "asset", "is_debit_normal": True, "parent_code": "1100", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1110", "name": "應收票據", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1200", "name": "應收帳款", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset", "is_system": True},
    {"code": "1210", "name": "備抵呆帳-應收帳款", "account_type": "asset", "is_debit_normal": False, "parent_code": "1200", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1250", "name": "其他應收款", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1300", "name": "存貨", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1310", "name": "原料", "account_type": "asset", "is_debit_normal": True, "parent_code": "1300", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1320", "name": "物料", "account_type": "asset", "is_debit_normal": True, "parent_code": "1300", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1330", "name": "在製品", "account_type": "asset", "is_debit_normal": True, "parent_code": "1300", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1340", "name": "製成品", "account_type": "asset", "is_debit_normal": True, "parent_code": "1300", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1350", "name": "商品存貨", "account_type": "asset", "is_debit_normal": True, "parent_code": "1300", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1400", "name": "預付款項", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1410", "name": "進項稅額", "account_type": "asset", "is_debit_normal": True, "parent_code": "1400", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1420", "name": "預付費用", "account_type": "asset", "is_debit_normal": True, "parent_code": "1400", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1430", "name": "預付貨款", "account_type": "asset", "is_debit_normal": True, "parent_code": "1400", "fs_line": "bs_current_asset", "is_system": False},
    {"code": "1500", "name": "其他流動資產", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset", "is_system": False},
    # --- 資產：非流動資產 ---
    {"code": "1600", "name": "不動產、廠房及設備", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1610", "name": "土地", "account_type": "asset", "is_debit_normal": True, "parent_code": "1600", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1620", "name": "房屋及建築", "account_type": "asset", "is_debit_normal": True, "parent_code": "1600", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1621", "name": "累計折舊-房屋及建築", "account_type": "asset", "is_debit_normal": False, "parent_code": "1620", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1630", "name": "機器設備", "account_type": "asset", "is_debit_normal": True, "parent_code": "1600", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1631", "name": "累計折舊-機器設備", "account_type": "asset", "is_debit_normal": False, "parent_code": "1630", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1640", "name": "運輸設備", "account_type": "asset", "is_debit_normal": True, "parent_code": "1600", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1641", "name": "累計折舊-運輸設備", "account_type": "asset", "is_debit_normal": False, "parent_code": "1640", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1650", "name": "辦公設備", "account_type": "asset", "is_debit_normal": True, "parent_code": "1600", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1651", "name": "累計折舊-辦公設備", "account_type": "asset", "is_debit_normal": False, "parent_code": "1650", "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1700", "name": "無形資產", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_noncurrent_asset", "is_system": False},
    {"code": "1800", "name": "其他非流動資產", "account_type": "asset", "is_debit_normal": True, "parent_code": None, "fs_line": "bs_noncurrent_asset", "is_system": False},
    # --- 負債：流動負債 ---
    {"code": "2100", "name": "應付帳款", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": True},
    {"code": "2200", "name": "銷項稅額", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": True},
    {"code": "2210", "name": "應付票據", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": False},
    {"code": "2220", "name": "應付費用", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": False},
    {"code": "2230", "name": "應付薪資及獎金", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": False},
    {"code": "2240", "name": "應付所得稅", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": False},
    {"code": "2250", "name": "預收款項", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": False},
    {"code": "2260", "name": "其他應付款", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": False},
    {"code": "2300", "name": "短期借款", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_current_liability", "is_system": False},
    # --- 負債：非流動負債 ---
    {"code": "2400", "name": "長期借款", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_noncurrent_liability", "is_system": False},
    {"code": "2500", "name": "其他非流動負債", "account_type": "liability", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_noncurrent_liability", "is_system": False},
    # --- 權益 ---
    {"code": "3100", "name": "股本", "account_type": "equity", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_equity", "is_system": False},
    {"code": "3200", "name": "資本公積", "account_type": "equity", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_equity", "is_system": False},
    {"code": "3300", "name": "保留盈餘", "account_type": "equity", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_equity", "is_system": False},
    {"code": "3310", "name": "法定盈餘公積", "account_type": "equity", "is_debit_normal": False, "parent_code": "3300", "fs_line": "bs_equity", "is_system": False},
    {"code": "3320", "name": "特別盈餘公積", "account_type": "equity", "is_debit_normal": False, "parent_code": "3300", "fs_line": "bs_equity", "is_system": False},
    {"code": "3330", "name": "未分配盈餘", "account_type": "equity", "is_debit_normal": False, "parent_code": "3300", "fs_line": "bs_equity", "is_system": False},
    {"code": "3400", "name": "本期損益", "account_type": "equity", "is_debit_normal": False, "parent_code": None, "fs_line": "bs_equity", "is_system": False},
    # --- 營業收入 ---
    {"code": "4100", "name": "銷貨收入", "account_type": "revenue", "is_debit_normal": False, "parent_code": None, "fs_line": "is_revenue", "is_system": True},
    {"code": "4110", "name": "銷貨退回及折讓", "account_type": "revenue", "is_debit_normal": True, "parent_code": "4100", "fs_line": "is_revenue", "is_system": False},
    {"code": "4200", "name": "加工收入", "account_type": "revenue", "is_debit_normal": False, "parent_code": None, "fs_line": "is_revenue", "is_system": False},
    {"code": "4300", "name": "其他營業收入", "account_type": "revenue", "is_debit_normal": False, "parent_code": None, "fs_line": "is_revenue", "is_system": False},
    # --- 營業成本 ---
    {"code": "5100", "name": "銷貨成本", "account_type": "cost", "is_debit_normal": True, "parent_code": None, "fs_line": "is_cost", "is_system": False},
    {"code": "5110", "name": "原料耗用", "account_type": "cost", "is_debit_normal": True, "parent_code": "5100", "fs_line": "is_cost", "is_system": False},
    {"code": "5120", "name": "直接人工", "account_type": "cost", "is_debit_normal": True, "parent_code": "5100", "fs_line": "is_cost", "is_system": False},
    {"code": "5130", "name": "製造費用", "account_type": "cost", "is_debit_normal": True, "parent_code": "5100", "fs_line": "is_cost", "is_system": False},
    {"code": "5200", "name": "進貨成本", "account_type": "cost", "is_debit_normal": True, "parent_code": None, "fs_line": "is_cost", "is_system": False},
    {"code": "5300", "name": "進貨退回及折讓", "account_type": "cost", "is_debit_normal": False, "parent_code": "5200", "fs_line": "is_cost", "is_system": False},
    # --- 營業費用 ---
    {"code": "6100", "name": "薪資支出", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6110", "name": "勞健保費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6120", "name": "退休金提撥", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6130", "name": "伙食費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6200", "name": "租金支出", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6210", "name": "文具印刷費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6220", "name": "郵電費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6230", "name": "水電瓦斯費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6240", "name": "燃料費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6250", "name": "運費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6260", "name": "廣告費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6270", "name": "交際費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6280", "name": "差旅費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6290", "name": "修繕費", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6300", "name": "稅捐", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6310", "name": "折舊費用", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6320", "name": "各項攤提", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6330", "name": "呆帳損失", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    {"code": "6400", "name": "其他營業費用", "account_type": "expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_expense", "is_system": False},
    # --- 業外收入及支出 ---
    {"code": "7100", "name": "利息收入", "account_type": "other_income", "is_debit_normal": False, "parent_code": None, "fs_line": "is_other_income", "is_system": False},
    {"code": "7200", "name": "租金收入", "account_type": "other_income", "is_debit_normal": False, "parent_code": None, "fs_line": "is_other_income", "is_system": False},
    {"code": "7300", "name": "兌換利益", "account_type": "other_income", "is_debit_normal": False, "parent_code": None, "fs_line": "is_other_income", "is_system": False},
    {"code": "7400", "name": "其他收入", "account_type": "other_income", "is_debit_normal": False, "parent_code": None, "fs_line": "is_other_income", "is_system": False},
    {"code": "7500", "name": "利息費用", "account_type": "other_expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_other_expense", "is_system": False},
    {"code": "7600", "name": "兌換損失", "account_type": "other_expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_other_expense", "is_system": False},
    {"code": "7700", "name": "其他損失", "account_type": "other_expense", "is_debit_normal": True, "parent_code": None, "fs_line": "is_other_expense", "is_system": False},
    # --- 所得稅 ---
    {"code": "9100", "name": "所得稅費用", "account_type": "tax", "is_debit_normal": True, "parent_code": None, "fs_line": "is_tax", "is_system": False},
]


# ────────────────────────────────────────────────────────────
# Pass 0：同步預檢（純資料，不碰 DB）
# ────────────────────────────────────────────────────────────

def _precheck() -> list[str]:
    """回錯誤清單；空 = 通過。"""
    errors: list[str] = []
    codes = [a["code"] for a in ACCOUNTS]

    if len(set(codes)) != len(codes):
        dup = sorted({c for c in codes if codes.count(c) > 1})
        errors.append(f"ACCOUNTS 內 code 重複: {', '.join(dup)}")

    missing_sys = sorted(SYSTEM_CODES - set(codes))
    if missing_sys:
        errors.append(f"硬編碼五碼未定義: {', '.join(missing_sys)}")

    by_code = {a["code"]: a for a in ACCOUNTS}
    for a in ACCOUNTS:
        c = a["code"]
        if a["account_type"] not in fs_defs.ACCOUNT_TYPES:
            errors.append(f"{c} account_type 非法: {a['account_type']}")
        if a["fs_line"] not in fs_defs.FS_LINES:
            errors.append(f"{c} fs_line 非白名單: {a['fs_line']}")
        pc = a["parent_code"]
        if pc is not None and pc not in by_code:
            errors.append(f"{c} parent_code 懸空: {pc}")
        if c in CONTRA_CODES:
            continue  # 抵減科目借貸方向例外（資料表已人工校驗）
        expect_debit = a["account_type"] in fs_defs.DEBIT_NORMAL_TYPES
        if a["is_debit_normal"] != expect_debit:
            errors.append(f"{c} 借貸方向錯誤 ({a['account_type']} 應 debit_normal={expect_debit})")
    return errors


# ────────────────────────────────────────────────────────────
# Pass 1-3：DB 寫入 + 驗證
# ────────────────────────────────────────────────────────────

async def _upsert_accounts(db, dry_run: bool) -> tuple[int, int, list[dict]]:
    """Pass 1 + Pass 2。回 (created, updated, parent_missing)。"""
    existing = {
        row.code: row for row in (await db.execute(select(Account))).scalars().all()
    }
    created = 0
    updated = 0

    for spec in ACCOUNTS:
        row = existing.get(spec["code"])
        if row is None:
            data = {k: v for k, v in spec.items() if k != "parent_code"}
            db.add(Account(id=str(uuid.uuid4()), **data))
            created += 1
            if dry_run:
                print(f"  [DRY] +{spec['code']} {spec['name']}")
            continue
        changed = False
        for f in ("name", "account_type", "is_debit_normal", "fs_line"):
            if getattr(row, f) != spec[f]:
                setattr(row, f, spec[f])
                changed = True
        if spec["is_system"] and not row.is_system:
            row.is_system = True
            changed = True
        if changed:
            updated += 1
            if dry_run:
                print(f"  [DRY] ~{spec['code']} {spec['name']}")

    await db.flush()

    # Pass 2：parent_id 解析（單次查詢，避免 N+1）
    code_to_row = {
        r.code: r for r in (await db.execute(select(Account))).scalars().all()
    }
    parent_map = {r.code: r.id for r in code_to_row.values()}
    parent_missing: list[str] = []
    for spec in ACCOUNTS:
        pc = spec["parent_code"]
        if pc is None:
            continue
        row = code_to_row.get(spec["code"])
        pid = parent_map.get(pc)
        if row is None or pid is None:
            parent_missing.append(f"{spec['code']}->{pc}")
            continue
        if row.parent_id != pid:
            row.parent_id = pid

    return created, updated, parent_missing


async def _validate_db(db) -> list[str]:
    """Pass 3：DB 狀態驗證。回錯誤清單；空 = 通過。"""
    errors: list[str] = []
    rows = (await db.execute(select(Account))).scalars().all()
    by_code = {r.code: r for r in rows}
    seed_codes = {a["code"] for a in ACCOUNTS}

    for code in sorted(SYSTEM_CODES):
        row = by_code.get(code)
        if row is None:
            errors.append(f"硬編碼科目 {code} 不存在")
        elif not row.is_system:
            errors.append(f"硬編碼科目 {code} is_system=False（保護失效）")

    for row in rows:
        if row.fs_line is not None and row.fs_line not in fs_defs.FS_LINES:
            errors.append(f"{row.code} fs_line 非白名單: {row.fs_line}")
        # 方向檢查只限 seed 的 86 科（客製科目由 API 層把關，不在此擋）
        if row.code not in seed_codes or row.code in CONTRA_CODES:
            continue
        if row.account_type in fs_defs.DEBIT_NORMAL_TYPES and not row.is_debit_normal:
            errors.append(f"{row.code} 借貸方向錯誤（{row.account_type} 應 debit_normal）")
        if row.account_type in (set(fs_defs.ACCOUNT_TYPES) - fs_defs.DEBIT_NORMAL_TYPES) and row.is_debit_normal:
            errors.append(f"{row.code} 借貸方向錯誤（{row.account_type} 應 credit_normal）")
    return errors


async def seed_accounts(dry_run: bool = False) -> int:
    """執行科目 seed。回傳 exit code：0 成功 / 1 Pass 3 失敗（已 rollback）/ 2 Pass 0 失敗（未碰 DB）。"""
    pre_errors = _precheck()
    if pre_errors:
        print("✗ seed_accounts 預檢失敗（未碰 DB）:")
        for e in pre_errors:
            print(f"  - {e}")
        return 2

    await init_db()
    async with AsyncSessionLocal() as db:
        created, updated, parent_missing = await _upsert_accounts(db, dry_run)
        errors = await _validate_db(db)
        if parent_missing:
            errors.append(f"parent 解析失敗: {', '.join(parent_missing)}")
        if errors:
            await db.rollback()
            print("✗ seed_accounts 驗證失敗（已 rollback）:")
            for e in errors:
                print(f"  - {e}")
            return 1

        if dry_run:
            await db.rollback()
            print(f"[DRY] seed_accounts: {len(ACCOUNTS)} defined "
                  f"({created} created / {updated} updated) — 未寫入")
            return 0

        await db.commit()
        print(f"✓ seed_accounts: {len(ACCOUNTS)} defined ({created} created / {updated} updated)")
        print(f"  hardcoded: {', '.join(sorted(SYSTEM_CODES))} all is_system=True")
        return 0


if __name__ == "__main__":
    asyncio.run(seed_accounts(dry_run="--dry-run" in sys.argv))

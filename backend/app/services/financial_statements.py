"""三大報表產生器（M2-1）— 試算表 / 損益表 / 資產負債表。

資料來源：已過帳（status='posted'）傳票的 JournalLine。
科目分組走 Account.fs_line（值域 app.services.fs_defs.FS_LINES）。

規則：
  - 試算表：每科目 debit/credit 加總 + 期末餘額（借餘=debit-credit，貸餘反之）
  - 損益表：收入 - 成本 - 費用 ± 業外 ± 稅 = 本期淨利
  - 資產負債表：資產 = 負債 + 權益（權益含本期淨利）
"""
from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Account, JournalEntry, JournalLine


async def _posted_balances(
    db: AsyncSession,
    period: str | None = None,
    *,
    cumulative: bool = False,
) -> list[dict]:
    """取得已過帳傳票的每科目 debit/credit 總和。

    健檢 #15：資產負債表是「截至期末的累計餘額」—
    用 entry_date < 次月初 過濾而非 period == period（後者只反映當期異動）。
    """
    q = (
        select(
            Account.code,
            Account.name,
            Account.account_type,
            Account.fs_line,
            Account.is_debit_normal,
            func.coalesce(func.sum(JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(JournalEntry.status == "posted")
        .group_by(
            Account.code, Account.name, Account.account_type,
            Account.fs_line, Account.is_debit_normal,
        )
    )
    if period and cumulative:
        y, m = (int(x) for x in period.split("-"))
        if m == 12:
            end = date(y + 1, 1, 1)
        else:
            end = date(y, m + 1, 1)
        from datetime import datetime as _dt
        q = q.where(JournalEntry.entry_date < _dt(end.year, end.month, end.day))
    elif period:
        q = q.where(JournalEntry.period == period)
    rows = (await db.execute(q)).all()
    out = []
    for code, name, atype, fs_line, debit_normal, total_debit, total_credit in rows:
        total_debit = float(total_debit or 0)
        total_credit = float(total_credit or 0)
        balance = total_debit - total_credit
        if debit_normal is False:  # 貸方常態（liability/equity/revenue）
            balance = total_credit - total_debit
        out.append({
            "code": code,
            "name": name,
            "account_type": atype,
            "fs_line": fs_line,
            "is_debit_normal": bool(debit_normal),
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "balance": round(balance, 2),  # 期末餘額（常態方向為正）
        })
    return out


async def trial_balance(db: AsyncSession, period: str | None = None) -> dict:
    """試算表：每科目借/貸 + 餘額；總借 = 總貸。"""
    rows = await _posted_balances(db, period)
    total_debit = round(sum(r["total_debit"] for r in rows), 2)
    total_credit = round(sum(r["total_credit"] for r in rows), 2)
    return {
        "period": period or "all",
        "generated_at": datetime.utcnow().isoformat(),
        "balanced": abs(total_debit - total_credit) < 0.01,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "accounts": sorted(rows, key=lambda r: r["code"]),
    }


async def income_statement(db: AsyncSession, period: str | None = None) -> dict:
    """損益表：營業收入/成本/費用/業外/稅 → 本期淨利。"""
    rows = await _posted_balances(db, period)
    section_lines = {
        "is_revenue": [],
        "is_cost": [],
        "is_expense": [],
        "is_other_income": [],
        "is_other_expense": [],
        "is_tax": [],
    }
    for r in rows:
        if r["fs_line"] in section_lines:
            section_lines[r["fs_line"]].append(r)

    revenue = round(sum(r["balance"] for r in section_lines["is_revenue"]), 2)
    cost = round(sum(r["balance"] for r in section_lines["is_cost"]), 2)
    expense = round(sum(r["balance"] for r in section_lines["is_expense"]), 2)
    other_income = round(sum(r["balance"] for r in section_lines["is_other_income"]), 2)
    other_expense = round(sum(r["balance"] for r in section_lines["is_other_expense"]), 2)
    tax = round(sum(r["balance"] for r in section_lines["is_tax"]), 2)
    gross_profit = round(revenue - cost, 2)
    operating_income = round(gross_profit - expense, 2)
    net_income = round(operating_income + other_income - other_expense - tax, 2)

    return {
        "period": period or "all",
        "generated_at": datetime.utcnow().isoformat(),
        "revenue": revenue,
        "cost": cost,
        "gross_profit": gross_profit,
        "expense": expense,
        "operating_income": operating_income,
        "other_income": other_income,
        "other_expense": other_expense,
        "tax": tax,
        "net_income": net_income,
        "sections": {
            key: [
                {"code": r["code"], "name": r["name"], "balance": r["balance"]}
                for r in rows_list
            ]
            for key, rows_list in section_lines.items()
        },
    }


async def balance_sheet(db: AsyncSession, period: str | None = None) -> dict:
    """資產負債表：資產 = 負債 + 權益（權益含本期淨利）。"""
    rows = await _posted_balances(db, period, cumulative=True)
    section_lines = {
        "bs_current_asset": [],
        "bs_noncurrent_asset": [],
        "bs_current_liability": [],
        "bs_noncurrent_liability": [],
        "bs_equity": [],
    }
    for r in rows:
        if r["fs_line"] in section_lines:
            section_lines[r["fs_line"]].append(r)

    current_asset = round(sum(r["balance"] for r in section_lines["bs_current_asset"]), 2)
    noncurrent_asset = round(sum(r["balance"] for r in section_lines["bs_noncurrent_asset"]), 2)
    current_liability = round(sum(r["balance"] for r in section_lines["bs_current_liability"]), 2)
    noncurrent_liability = round(sum(r["balance"] for r in section_lines["bs_noncurrent_liability"]), 2)
    equity = round(sum(r["balance"] for r in section_lines["bs_equity"]), 2)

    total_asset = round(current_asset + noncurrent_asset, 2)
    total_liability = round(current_liability + noncurrent_liability, 2)
    # 本期淨利歸入權益（未結轉 retained earnings）
    net_income = (await income_statement(db, period))["net_income"]
    total_equity = round(equity + net_income, 2)
    balanced = abs(total_asset - (total_liability + total_equity)) < 0.01

    return {
        "period": period or "all",
        "generated_at": datetime.utcnow().isoformat(),
        "current_asset": current_asset,
        "noncurrent_asset": noncurrent_asset,
        "total_asset": total_asset,
        "current_liability": current_liability,
        "noncurrent_liability": noncurrent_liability,
        "total_liability": total_liability,
        "equity": equity,
        "net_income": net_income,
        "total_equity": total_equity,
        "balanced": balanced,
        "sections": {
            key: [
                {"code": r["code"], "name": r["name"], "balance": r["balance"]}
                for r in rows_list
            ]
            for key, rows_list in section_lines.items()
        },
    }

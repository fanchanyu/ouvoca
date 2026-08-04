"""固定資產 + 折舊（M2-5）— 直線法。

每月折舊 = (成本 - 殘值) / 耐用月數。
折舊傳票：DR 折舊費用（預設 6310）/ CR 累計折舊（依類別對應科目）。
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.finance import FixedAsset

# 類別 → 累計折舊科目（對齊 seed_accounts 86 科）
_ACCUM_ACCOUNT_BY_CATEGORY = {
    "machinery": "1631",      # 累計折舊-機器設備
    "building": "1621",       # 累計折舊-房屋及建築
    "vehicle": "1641",        # 累計折舊-運輸設備
    "furniture": "1651",      # 累計折舊-辦公設備
}
DEFAULT_EXPENSE_ACCOUNT = "6310"  # 折舊費用


def _monthly_depreciation(cost: float, salvage: float, months: int) -> float:
    if months <= 0:
        raise BusinessRuleError("耐用月數必須大於 0")
    depreciable = max(cost - salvage, 0)
    return round(depreciable / months, 2)


async def create_fixed_asset(db: AsyncSession, data: dict, user: dict | None = None) -> FixedAsset:
    cost = float(data["cost"])
    salvage = float(data.get("salvage_value", 0) or 0)
    months = int(data["useful_life_months"])
    if cost <= 0:
        raise BusinessRuleError("取得成本必須大於 0")
    asset = FixedAsset(
        code=data.get("code") or f"FA-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        name=data["name"],
        category=data.get("category", "machinery"),
        cost=cost,
        salvage_value=salvage,
        useful_life_months=months,
        acquisition_date=data.get("acquisition_date") or datetime.now(UTC).replace(tzinfo=None),
        depreciation_method=data.get("depreciation_method", "straight_line"),
        monthly_depreciation=_monthly_depreciation(cost, salvage, months),
        status="active",
        remark=data.get("remark"),
        created_by=(user or {}).get("employee_id"),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def post_monthly_depreciation(
    db: AsyncSession,
    asset_id: str,
    period: str,
    user: dict | None = None,
    *,
    expense_account: str = DEFAULT_EXPENSE_ACCOUNT,
    accum_account: str | None = None,
) -> FixedAsset:
    """過帳一個月的折舊傳票（DR 折舊費用 / CR 累計折舊）。"""
    asset = (await db.execute(
        select(FixedAsset).where(FixedAsset.id == asset_id)
    )).scalar_one_or_none()
    if asset is None:
        raise NotFoundError("固定資產不存在", asset_id=asset_id)
    if asset.status in ("fully_depreciated", "disposed"):
        raise BusinessRuleError(f"資產狀態 {asset.status!r} 不可再提折舊")
    if asset.monthly_depreciation <= 0:
        raise BusinessRuleError("月折舊額為 0（可能已提滿）")

    # 健檢 #12：冪等防呆 — 同期間同資產不得重複提列折舊
    from app.models.accounting import JournalEntry
    dup = (await db.execute(
        select(JournalEntry).where(
            JournalEntry.source_type == "fixed_asset_depreciation",
            JournalEntry.source_id == asset.id,
            JournalEntry.period == period,
        )
    )).scalar_one_or_none()
    if dup is not None:
        raise BusinessRuleError(
            f"資產 {asset.code} 已於 {period} 提列折舊（傳票 {dup.entry_no}），請勿重複",
            asset_id=asset.id, period=period,
        )

    accum = accum_account or _ACCUM_ACCOUNT_BY_CATEGORY.get(
        asset.category or "machinery", "1631"
    )
    # 不可超過可折舊上限
    depreciable = round(asset.cost - asset.salvage_value, 2)
    if asset.accumulated_depreciation + asset.monthly_depreciation > depreciable:
        amount = round(depreciable - asset.accumulated_depreciation, 2)
    else:
        amount = asset.monthly_depreciation
    if amount <= 0:
        raise BusinessRuleError("已提滿折舊")

    # 建立並過帳傳票（DR 折舊費用 / CR 累計折舊）
    from app.core.exceptions import NotFoundError as _NF
    from app.models.accounting import Account
    from app.services.accounting import create_journal_entry

    exp_acc = (await db.execute(
        select(Account).where(Account.code == expense_account)
    )).scalar_one_or_none()
    acc_acc = (await db.execute(
        select(Account).where(Account.code == accum)
    )).scalar_one_or_none()
    if exp_acc is None or acc_acc is None:
        raise _NF("折舊科目不存在（請先 seed_accounts）",
                  expense_account=expense_account, accum_account=accum)

    je = await create_journal_entry(db, {
        "period": period,
        "description": f"折舊 {asset.code} {asset.name} {period}",
        "source_type": "fixed_asset_depreciation",
        "source_id": asset.id,
        "lines": [
            {"account_id": exp_acc.id, "debit": amount, "credit": 0,
             "description": f"{asset.code} 月折舊"},
            {"account_id": acc_acc.id, "debit": 0, "credit": amount,
             "description": f"{asset.code} 累計折舊"},
        ],
    }, user=user)
    from app.services.accounting import post_journal
    await post_journal(db, je.id, user or {})

    asset.accumulated_depreciation = round(asset.accumulated_depreciation + amount, 2)
    if asset.accumulated_depreciation >= depreciable - 0.005:
        asset.status = "fully_depreciated"
    asset.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(asset)
    return asset


async def list_fixed_assets(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    q = select(FixedAsset).order_by(FixedAsset.code).limit(limit)
    if status:
        q = q.where(FixedAsset.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": r.id, "code": r.code, "name": r.name, "category": r.category,
            "cost": r.cost, "salvage_value": r.salvage_value,
            "useful_life_months": r.useful_life_months,
            "acquisition_date": r.acquisition_date.isoformat() if r.acquisition_date else None,
            "monthly_depreciation": r.monthly_depreciation,
            "accumulated_depreciation": r.accumulated_depreciation,
            "net_book_value": round(r.cost - (r.accumulated_depreciation or 0), 2),
            "status": r.status,
        }
        for r in rows
    ]

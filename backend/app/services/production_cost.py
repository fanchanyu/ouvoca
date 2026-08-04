"""WO 成本彙總 + 銷貨成本結轉（M2-6，財務閉環最後一塊）。

WO 成本（三要素）：
  - 材料成本：BOM 展開 × 數量 × Part.unit_cost
  - 人工成本：Σ(工序 setup + run_time×完工數) × WorkCenter.hourly_rate
  - 製造費用：人工 × overhead_rate（預設 0.3，可傳參覆蓋）

銷貨成本結轉（月結）：
  期間內出貨單（DeliveryNote）明細 × Part.unit_cost
  → 傳票 DR 5100 銷貨成本 / CR 1340 製成品
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.production import ProductionOrder, Operation, DispatchLog, WorkCenter
from app.models.product import Product, BOMItem
from app.models.inventory import Part
from app.models.delivery import DeliveryNote, DeliveryNoteItem
from app.models.accounting import Account


COGS_ACCOUNT = "5100"       # 銷貨成本
FINISHED_GOODS_ACCOUNT = "1340"  # 製成品
DEFAULT_OVERHEAD_RATE = 0.3


async def _bom_material_cost(db: AsyncSession, product_id: str, qty: float) -> list[dict]:
    """BOM 展開（單階，多階遞迴）材料成本。"""
    rows = (await db.execute(
        select(BOMItem, Part.unit_cost, Part.part_no)
        .join(Part, Part.id == BOMItem.part_id)
        .where(BOMItem.product_id == product_id, BOMItem.is_active == True)  # noqa: E712
    )).all()
    lines = []
    for bom, unit_cost, part_no in rows:
        cost = round(float(bom.qty_per or 0) * float(unit_cost or 0) * qty, 2)
        lines.append({
            "part_id": bom.part_id,
            "part_no": part_no,
            "qty_per": bom.qty_per,
            "unit_cost": float(unit_cost or 0),
            "extended_qty": round(float(bom.qty_per or 0) * qty, 4),
            "cost": cost,
        })
    return lines


async def _labor_cost(db: AsyncSession, wo_id: str, qty: float) -> list[dict]:
    """人工成本：各工序（已完工數）時間 × 工作中心時薪。"""
    ops = (await db.execute(
        select(Operation).where(Operation.production_order_id == wo_id)
    )).scalars().all()
    # N+1 修復：一次撈出所有工作中心，取代逐工序查詢
    wc_ids = {op.work_center_id for op in ops}
    wcs: dict[str, WorkCenter] = {}
    if wc_ids:
        wcs = {
            wc.id: wc for wc in (await db.execute(
                select(WorkCenter).where(WorkCenter.id.in_(wc_ids))
            )).scalars().all()
        }
    lines = []
    for op in ops:
        wc = wcs.get(op.work_center_id)
        rate = float(wc.hourly_rate if wc else 0)
        hours = float(op.setup_time or 0) + float(op.run_time_per_unit or 0) * float(op.completed_qty or 0)
        lines.append({
            "op_no": op.op_no,
            "op_name": op.op_name,
            "work_center": wc.code if wc else None,
            "hours": round(hours, 4),
            "hourly_rate": rate,
            "cost": round(hours * rate, 2),
        })
    return lines


async def aggregate_wo_cost(
    db: AsyncSession,
    wo_id: str,
    *,
    overhead_rate: float = DEFAULT_OVERHEAD_RATE,
) -> dict:
    """彙總單張工單成本（材料 + 人工 + 製造費用）。"""
    wo = (await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.operations))
        .where(ProductionOrder.id == wo_id)
    )).scalar_one_or_none()
    if wo is None:
        raise NotFoundError("工單不存在", wo_id=wo_id)

    qty = float(wo.completed_qty or 0) or float(wo.ordered_qty or 0)
    material_lines = await _bom_material_cost(db, wo.product_id, qty)
    labor_lines = await _labor_cost(db, wo.id, qty)

    material = round(sum(l["cost"] for l in material_lines), 2)
    labor = round(sum(l["cost"] for l in labor_lines), 2)
    overhead = round(labor * overhead_rate, 2)
    total = round(material + labor + overhead, 2)

    return {
        "wo_id": wo.id,
        "wo_no": wo.wo_no,
        "product_id": wo.product_id,
        "status": wo.status,
        "ordered_qty": wo.ordered_qty,
        "completed_qty": wo.completed_qty,
        "cost_qty_basis": qty,
        "material_cost": material,
        "labor_cost": labor,
        "overhead_cost": overhead,
        "overhead_rate": overhead_rate,
        "total_cost": total,
        "unit_cost": round(total / qty, 2) if qty else 0,
        "material_lines": material_lines,
        "labor_lines": labor_lines,
    }


async def settle_cogs(
    db: AsyncSession,
    period: str,
    user: Optional[dict] = None,
) -> dict:
    """月結銷貨成本：期間內出貨明細 × Part.unit_cost → DR 5100 / CR 1340。"""
    # 健檢 #12：冪等防呆 — 同期間不得重複結轉
    from app.models.accounting import JournalEntry
    existing = (await db.execute(
        select(JournalEntry).where(
            JournalEntry.source_type == "cogs_settlement",
            JournalEntry.period == period,
        )
    )).scalar_one_or_none()
    if existing is not None:
        raise BusinessRuleError(
            f"期間 {period} 已結轉銷貨成本（傳票 {existing.entry_no}），請勿重複",
            period=period,
        )

    # 期間內已出貨的 DN items
    from sqlalchemy import extract
    year, month = (int(x) for x in period.split("-")) if "-" in period else (int(period[:4]), int(period[4:6]))
    rows = (await db.execute(
        select(DeliveryNoteItem, Part.unit_cost, Part.part_no)
        .join(DeliveryNote, DeliveryNote.id == DeliveryNoteItem.dn_id)
        .join(Part, Part.id == DeliveryNoteItem.part_id)
        .where(
            extract("year", DeliveryNote.ship_date) == year,
            extract("month", DeliveryNote.ship_date) == month,
        )
    )).all()

    if not rows:
        return {
            "period": period,
            "settled": False,
            "reason": "期間內沒有出貨紀錄",
            "total_cogs": 0,
            "lines": [],
        }

    # 依料件彙總
    by_part: dict[str, dict] = {}
    for item, unit_cost, part_no in rows:
        key = str(item.part_id)
        entry = by_part.setdefault(key, {
            "part_id": key, "part_no": part_no, "qty": 0.0, "unit_cost": float(unit_cost or 0), "cogs": 0.0,
        })
        entry["qty"] = round(entry["qty"] + float(item.qty_shipped or 0), 4)
        entry["cogs"] = round(entry["qty"] * entry["unit_cost"], 2)

    total_cogs = round(sum(e["cogs"] for e in by_part.values()), 2)
    if total_cogs <= 0:
        return {"period": period, "settled": False,
                "reason": "出貨品項無成本（unit_cost 皆為 0）", "total_cogs": 0, "lines": list(by_part.values())}

    # 科目查詢
    cogs_acc = (await db.execute(
        select(Account).where(Account.code == COGS_ACCOUNT)
    )).scalar_one_or_none()
    fg_acc = (await db.execute(
        select(Account).where(Account.code == FINISHED_GOODS_ACCOUNT)
    )).scalar_one_or_none()
    if cogs_acc is None or fg_acc is None:
        raise BusinessRuleError(
            f"科目 {COGS_ACCOUNT}/{FINISHED_GOODS_ACCOUNT} 不存在，請先執行 seed_accounts"
        )

    from app.services.accounting import create_journal_entry, post_journal
    je = await create_journal_entry(db, {
        "period": period,
        "description": f"銷貨成本結轉 {period}",
        "source_type": "cogs_settlement",
        "source_id": period,
        "lines": [
            {"account_id": cogs_acc.id, "debit": total_cogs, "credit": 0,
             "description": f"{period} 銷貨成本"},
            {"account_id": fg_acc.id, "debit": 0, "credit": total_cogs,
             "description": f"{period} 製成品出庫"},
        ],
    }, user=user)
    await post_journal(db, je.id, user or {})

    return {
        "period": period,
        "settled": True,
        "total_cogs": total_cogs,
        "journal_entry_id": je.id,
        "lines": list(by_part.values()),
    }

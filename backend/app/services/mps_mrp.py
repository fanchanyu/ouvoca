"""MPS/MRP service — master scheduling and material requirement planning.

MRP algorithm:
1. Load all MPS entries → planned_production per product per period.
2. For each product, explode BOM **recursively (multi-level)** via
   explode_bom_recursive() — handles 2+ 階 sub-assembly products as
   parts (by part_no == product_no convention).
   Cycle protection: visited set 阻止 A→B→A 無窮遞迴。
3. Net = gross - on_hand - scheduled_receipts (we treat current inventory as period 0 on-hand).
4. If net > 0 → planned_order_release in (period - part.lead_time_days).

v3.25.9：升級單階 → 多階遞迴爆破。
"""
import uuid
from collections import defaultdict
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.mps_mrp import MpsMaster, MpsEntry, TimeFence, MrpMaster, MrpItem
from app.models.product import BOMItem
from app.models.inventory import Part, Inventory
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


# -------- MPS --------

async def create_mps(db: AsyncSession, data: dict, user: Optional[dict] = None) -> MpsMaster:
    mps = MpsMaster(id=str(uuid.uuid4()), created_by=(user or {}).get("employee_id"), **data)
    db.add(mps)
    await db.commit()
    await db.refresh(mps)
    return mps


async def add_mps_entry(db: AsyncSession, data: dict) -> MpsEntry:
    e = MpsEntry(id=str(uuid.uuid4()), **data)
    # PAB = projected on hand (simplified)
    e.projected_on_hand = e.planned_production - e.actual_demand
    e.available_to_promise = max(0, e.planned_production - e.actual_demand)
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return e


async def list_mps(db: AsyncSession) -> List[MpsMaster]:
    return list((await db.execute(
        select(MpsMaster).order_by(MpsMaster.created_at.desc())
    )).scalars().all())


async def get_mps(db: AsyncSession, mps_id: str) -> Optional[MpsMaster]:
    return (await db.execute(
        select(MpsMaster).options(selectinload(MpsMaster.entries)).where(MpsMaster.id == mps_id)
    )).scalar_one_or_none()


# -------- MRP --------

async def run_mrp(db: AsyncSession, mps_id: str, user: Optional[dict] = None) -> MrpMaster:
    """Generate MRP items from MPS by exploding BOM."""
    mps = await get_mps(db, mps_id)
    if not mps:
        raise NotFoundError("MPS 不存在", mps_id=mps_id)
    if not mps.entries:
        raise BusinessRuleError("MPS 沒有需求項目，無法執行 MRP")

    mrp = MrpMaster(
        id=str(uuid.uuid4()),
        mps_master_id=mps.id,
        mrp_name=f"MRP-{mps.mps_name}-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}",
        status="generated",
        generated_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(mrp)

    # gross requirement bucket: { (part_id, period) -> qty }
    # 同時記錄每個 part 出現時的最深 level（用於 MrpItem.bom_level）
    gross: dict[tuple[str, str], float] = defaultdict(float)
    deepest_level: dict[str, int] = {}

    # v3.25.9：多階遞迴爆破，自動處理半成品（part_no == product_no 對應的 sub-assembly）
    from app.services.production import explode_bom_recursive

    for entry in mps.entries:
        explosion = await explode_bom_recursive(
            db, entry.product_id, qty=float(entry.planned_production)
        )
        for item in explosion:
            gross[(item["part_id"], entry.period)] += item["qty"]
            # 取最深的 level（同 part 可能在多個分支出現）
            deepest_level[item["part_id"]] = max(
                deepest_level.get(item["part_id"], 1), item["level"]
            )

    for (part_id, period), gross_qty in gross.items():
        # on-hand snapshot
        inv = (await db.execute(
            select(Inventory).where(Inventory.part_id == part_id)
        )).scalar_one_or_none()
        on_hand = inv.qty_available if inv else 0
        net = max(0.0, gross_qty - on_hand)
        part = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()

        item = MrpItem(
            id=str(uuid.uuid4()),
            mrp_master_id=mrp.id,
            part_id=part_id,
            bom_level=deepest_level.get(part_id, 1),
            order_type="buy" if (part and part.category == "raw_material") else "make",
            period=period,
            gross_requirement=gross_qty,
            scheduled_receipts=0,
            projected_on_hand=on_hand,
            net_requirement=net,
            planned_order_release=net,
            planned_order_receipt=net,
        )
        db.add(item)

    await db.commit()
    await db.refresh(mrp)
    await EventBus.emit(DomainEvent(
        name="mrp.generated", domain="mps_mrp",
        entity_type="MrpMaster", entity_id=mrp.id,
        data={"mps_id": mps.id, "item_count": len(gross)},
    ))
    return mrp


async def list_mrp(db: AsyncSession) -> List[MrpMaster]:
    return list((await db.execute(
        select(MrpMaster).order_by(MrpMaster.created_at.desc())
    )).scalars().all())


async def get_mrp(db: AsyncSession, mrp_id: str) -> Optional[MrpMaster]:
    return (await db.execute(
        select(MrpMaster).options(selectinload(MrpMaster.items)).where(MrpMaster.id == mrp_id)
    )).scalar_one_or_none()

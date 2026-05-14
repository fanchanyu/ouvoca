"""Warehouse service — Zone / Bin / PickTask / CycleCount."""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import WarehouseZone, BinLocation, PickTask, CycleCount
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError


async def create_zone(db: AsyncSession, data: dict) -> WarehouseZone:
    z = WarehouseZone(id=str(uuid.uuid4()), **data)
    db.add(z)
    await db.commit()
    await db.refresh(z)
    return z


async def list_zones(db: AsyncSession) -> List[WarehouseZone]:
    return list((await db.execute(select(WarehouseZone).order_by(WarehouseZone.code))).scalars().all())


async def create_bin(db: AsyncSession, data: dict) -> BinLocation:
    b = BinLocation(id=str(uuid.uuid4()), **data)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def list_bins(db: AsyncSession, zone_id: Optional[str] = None) -> List[BinLocation]:
    q = select(BinLocation)
    if zone_id:
        q = q.where(BinLocation.zone_id == zone_id)
    return list((await db.execute(q.order_by(BinLocation.bin_code))).scalars().all())


async def create_pick_task(db: AsyncSession, data: dict, user: Optional[dict] = None) -> PickTask:
    task = PickTask(
        id=str(uuid.uuid4()),
        pick_no=f"PICK-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        assigned_to=(user or {}).get("employee_id"),
        **data,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await EventBus.emit(DomainEvent(
        name="pick.created", domain="warehouse",
        entity_type="PickTask", entity_id=task.id,
        data={"pick_no": task.pick_no, "part_id": task.part_id, "qty": task.qty_to_pick},
    ))
    return task


async def complete_pick(db: AsyncSession, pick_id: str, picked_qty: float, user: dict) -> PickTask:
    task = (await db.execute(select(PickTask).where(PickTask.id == pick_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("揀貨任務不存在", pick_id=pick_id)
    task.qty_picked = picked_qty
    task.status = "completed" if picked_qty >= task.qty_to_pick else "partial"
    task.completed_at = datetime.utcnow()
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="pick.completed", domain="warehouse",
        entity_type="PickTask", entity_id=task.id,
        data={"pick_no": task.pick_no, "qty": picked_qty},
    ))
    return task


async def list_pick_tasks(db: AsyncSession, status: Optional[str] = None,
                          skip: int = 0, limit: int = 100) -> List[PickTask]:
    q = select(PickTask)
    if status:
        q = q.where(PickTask.status == status)
    return list((await db.execute(q.offset(skip).limit(limit).order_by(PickTask.created_at.desc()))).scalars().all())


async def create_cycle_count(db: AsyncSession, data: dict, user: Optional[dict] = None) -> CycleCount:
    cc = CycleCount(
        id=str(uuid.uuid4()),
        count_no=f"CC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        counted_by=(user or {}).get("employee_id"),
        **data,
    )
    cc.variance = (cc.counted_qty or 0) - (cc.system_qty or 0)
    db.add(cc)
    await db.commit()
    await db.refresh(cc)
    await EventBus.emit(DomainEvent(
        name="cycle_count.created", domain="warehouse",
        entity_type="CycleCount", entity_id=cc.id,
        data={"count_no": cc.count_no, "variance": cc.variance},
    ))
    return cc

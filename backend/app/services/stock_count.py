"""StockCount service (v3.32 進銷存深化).

月底盤點流程：
  1. snapshot_stock_count — 建單時自動 snapshot 現有 inventory 為 book_qty
  2. record_counted_qty — 倉管 key in 實盤數，自動計算 variance
  3. apply_count_adjustments — 主管確認後產生 inventory_transaction 對沖差異
"""
import uuid
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.stock_count import StockCount, StockCountItem
from app.models.inventory import Part, Inventory
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


async def create_stock_count(
    db: AsyncSession,
    part_ids: Optional[List[str]] = None,
    scope: str = "partial",
    notes: str = "",
    user: Optional[dict] = None,
) -> StockCount:
    """建立盤點單。若 part_ids 未指定且 scope='full'，盤所有 active parts。"""
    sc = StockCount(
        id=str(uuid.uuid4()),
        count_no=f"SC-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
        count_date=datetime.now(UTC).replace(tzinfo=None),
        scope=scope,
        status="draft",
        notes=notes,
        created_by=(user or {}).get("employee_id"),
    )
    db.add(sc)
    await db.flush()

    # Snapshot 帳上數量為 book_qty
    if part_ids:
        parts_q = select(Part).where(Part.id.in_(part_ids), Part.is_active == True)
    else:
        parts_q = select(Part).where(Part.is_active == True)
    parts = (await db.execute(parts_q)).scalars().all()

    inv_map = {
        i.part_id: i.qty_available for i in (await db.execute(select(Inventory))).scalars().all()
    }

    for idx, part in enumerate(parts):
        db.add(StockCountItem(
            id=str(uuid.uuid4()), count_id=sc.id,
            sequence_no=(idx + 1) * 10,
            part_id=part.id,
            book_qty=inv_map.get(part.id, 0),
            counted_qty=None,  # 待 key in
            variance=0,
        ))

    sc.status = "counting"
    await db.commit()
    await db.refresh(sc)
    await EventBus.emit(DomainEvent(
        name="stock_count.created", domain="inventory",
        entity_type="StockCount", entity_id=sc.id,
        data={"count_no": sc.count_no, "items_count": len(parts), "scope": scope},
    ))
    return sc


async def record_counted_qty(
    db: AsyncSession,
    count_item_id: str,
    counted_qty: float,
    variance_reason: str = "",
    notes: str = "",
    user: Optional[dict] = None,
) -> StockCountItem:
    item = (await db.execute(
        select(StockCountItem).where(StockCountItem.id == count_item_id)
    )).scalar_one_or_none()
    if not item:
        raise NotFoundError("盤點單行不存在", count_item_id=count_item_id)

    item.counted_qty = counted_qty
    item.variance = counted_qty - (item.book_qty or 0)
    item.variance_reason = variance_reason
    item.notes = notes
    item.counted_by = (user or {}).get("employee_id")
    item.counted_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(item)
    return item


async def get_stock_count(db: AsyncSession, count_id: str) -> Optional[StockCount]:
    return (await db.execute(
        select(StockCount).options(selectinload(StockCount.items))
        .where(StockCount.id == count_id)
    )).scalar_one_or_none()


async def list_stock_counts(
    db: AsyncSession, status: Optional[str] = None, limit: int = 50,
) -> List[StockCount]:
    q = select(StockCount)
    if status:
        q = q.where(StockCount.status == status)
    q = q.order_by(StockCount.count_date.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def apply_count_adjustments(
    db: AsyncSession, count_id: str, user: Optional[dict] = None,
) -> dict:
    """主管確認後執行：產生 inventory_transaction 對沖差異 → 帳目同步。"""
    from app.services.inventory import add_inventory_transaction

    sc = await get_stock_count(db, count_id)
    if not sc:
        raise NotFoundError("盤點單不存在", count_id=count_id)
    if sc.status not in ("counting", "reviewed"):
        raise BusinessRuleError(f"盤點單狀態 {sc.status!r} 無法套用調整")

    # Only items with counted_qty set + variance != 0 need adjustment
    adjustments = [
        it for it in sc.items
        if it.counted_qty is not None and abs(it.variance or 0) > 0.001
    ]

    inbound_count = 0
    outbound_count = 0
    for it in adjustments:
        if it.variance > 0:
            tx_type = "inbound"
            qty = it.variance
            inbound_count += 1
        else:
            tx_type = "outbound"
            qty = -it.variance
            outbound_count += 1
        await add_inventory_transaction(db, {
            "part_id": it.part_id,
            "transaction_type": tx_type,
            "qty": qty,
            "reference_type": "stock_count",
            "reference_id": sc.id,
            "remark": f"盤點調整 {sc.count_no} 行 {it.id[:8]}：{it.variance_reason or '盤盈/盤虧'}",
        }, user=user)

    sc.status = "adjusted"
    sc.reviewed_by = (user or {}).get("employee_id")
    sc.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="stock_count.adjusted", domain="inventory",
        entity_type="StockCount", entity_id=sc.id,
        data={"count_no": sc.count_no, "adjustments": len(adjustments),
              "inbound": inbound_count, "outbound": outbound_count},
    ))
    return {
        "count_no": sc.count_no,
        "adjustments_applied": len(adjustments),
        "inbound_items": inbound_count,
        "outbound_items": outbound_count,
        "message": f"✅ 盤點 {sc.count_no} 已調整 {len(adjustments)} 項",
    }

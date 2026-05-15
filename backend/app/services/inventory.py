"""Inventory service — Part/Inventory/InventoryTransaction/Transfer business logic.

Emits domain events on every state-changing operation so the event engine
can apply constraints, send notifications and broadcast SSE.
"""
import uuid
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.inventory import Part, Inventory, InventoryTransaction, InventoryTransfer
from app.events import EventBus, DomainEvent
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging import get_logger

log = get_logger(__name__)

# -------- Part --------

async def get_part(db: AsyncSession, part_id: str) -> Optional[Part]:
    result = await db.execute(select(Part).where(Part.id == part_id))
    return result.scalar_one_or_none()


async def get_part_by_no(db: AsyncSession, part_no: str) -> Optional[Part]:
    result = await db.execute(select(Part).where(Part.part_no == part_no))
    return result.scalar_one_or_none()


async def list_parts(db: AsyncSession, skip: int = 0, limit: int = 100, category: Optional[str] = None) -> List[Part]:
    query = select(Part)
    if category:
        query = query.where(Part.category == category)
    query = query.offset(skip).limit(limit).order_by(Part.part_no)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_part(db: AsyncSession, data: dict) -> Part:
    part = Part(id=str(uuid.uuid4()), **data)
    db.add(part)
    inv = Inventory(id=str(uuid.uuid4()), part_id=part.id)
    db.add(inv)
    await db.commit()
    await db.refresh(part)
    await EventBus.emit(DomainEvent(
        name="part.created", domain="inventory",
        entity_type="Part", entity_id=part.id,
        data={"part_no": part.part_no, "name": part.name},
    ))
    return part


# -------- Inventory --------

async def get_inventory(db: AsyncSession, part_id: str) -> Optional[Inventory]:
    result = await db.execute(
        select(Inventory).options(joinedload(Inventory.part)).where(Inventory.part_id == part_id)
    )
    return result.scalar_one_or_none()


async def list_inventory_below_safety(db: AsyncSession, limit: int = 100):
    """Return inventory rows where qty_available < part.safety_stock."""
    result = await db.execute(
        select(Inventory, Part)
        .join(Part, Inventory.part_id == Part.id)
        .where(Inventory.qty_available < Part.safety_stock)
        .where(Part.safety_stock > 0)
        .limit(limit)
    )
    return [(inv, p) for inv, p in result.all()]


# -------- Transactions --------

VALID_INBOUND = {"inbound", "receipt", "return_to_stock", "adjustment_in"}
VALID_OUTBOUND = {"outbound", "issue", "consumption", "adjustment_out"}
VALID_ALLOCATION = {"allocate", "deallocate"}
ALL_VALID_TXN_TYPES = VALID_INBOUND | VALID_OUTBOUND | VALID_ALLOCATION


async def add_inventory_transaction(db: AsyncSession, data: dict, user: Optional[dict] = None) -> InventoryTransaction:
    part_id = data["part_id"]
    qty = float(data["qty"])
    txn_type = data["transaction_type"]

    if qty <= 0:
        raise BusinessRuleError("數量必須大於 0", qty=qty)

    # 防呆：拒絕未知的 transaction_type，避免靜默不更新庫存
    # (早期 bug: type='in'/'out' 不報錯但不改庫存 → 沉默資料毀損)
    if txn_type not in ALL_VALID_TXN_TYPES:
        raise BusinessRuleError(
            f"無效的 transaction_type: {txn_type!r}。"
            f"合法值：{sorted(ALL_VALID_TXN_TYPES)}",
            transaction_type=txn_type,
        )

    inv_q = await db.execute(select(Inventory).where(Inventory.part_id == part_id))
    inv = inv_q.scalar_one_or_none()
    if not inv:
        raise NotFoundError(f"零件 {part_id} 沒有庫存記錄", part_id=part_id)

    # Outbound: check available qty
    if txn_type in VALID_OUTBOUND and inv.qty_available < qty:
        raise BusinessRuleError(
            "庫存不足",
            part_id=part_id, requested=qty, available=inv.qty_available,
        )

    txn = InventoryTransaction(
        id=str(uuid.uuid4()),
        operator_id=(user or {}).get("employee_id") if user else None,
        **data,
    )
    db.add(txn)

    if txn_type in VALID_INBOUND:
        inv.qty_on_hand += qty
    elif txn_type in VALID_OUTBOUND:
        inv.qty_on_hand -= qty
        inv.qty_allocated = max(0.0, inv.qty_allocated - qty)
    elif txn_type == "allocate":
        inv.qty_allocated += qty
    elif txn_type == "deallocate":
        inv.qty_allocated = max(0.0, inv.qty_allocated - qty)
    inv.qty_available = inv.qty_on_hand - inv.qty_allocated
    inv.updated_at = datetime.now(UTC).replace(tzinfo=None)

    await db.commit()
    await db.refresh(txn)

    await EventBus.emit(DomainEvent(
        name="inventory.changed", domain="inventory",
        entity_type="InventoryTransaction", entity_id=txn.id,
        data={"part_id": part_id, "qty": qty, "type": txn_type,
              "qty_on_hand": inv.qty_on_hand, "qty_available": inv.qty_available},
    ))

    # Check safety stock breach
    part = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()
    if part and part.safety_stock > 0 and inv.qty_available < part.safety_stock:
        await EventBus.emit(DomainEvent(
            name="stock.below_safety", domain="inventory",
            entity_type="Part", entity_id=part_id,
            data={"part_no": part.part_no, "qty_available": inv.qty_available,
                  "safety_stock": part.safety_stock},
        ))

    return txn


# -------- Transfers --------

async def create_transfer(db: AsyncSession, data: dict, user: Optional[dict] = None) -> InventoryTransfer:
    transfer = InventoryTransfer(
        id=str(uuid.uuid4()),
        transfer_no=f"TRF-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        requested_by=(user or {}).get("employee_id") if user else None,
        **{k: v for k, v in data.items() if k != "requested_by"},
    )
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    await EventBus.emit(DomainEvent(
        name="transfer.requested", domain="inventory",
        entity_type="InventoryTransfer", entity_id=transfer.id,
        data={"transfer_no": transfer.transfer_no, "part_id": transfer.part_id, "qty": transfer.qty},
    ))
    return transfer

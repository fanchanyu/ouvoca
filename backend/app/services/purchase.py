"""Purchase service — Supplier / PO / PO-receipt business logic."""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.purchase import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    SupplierPrice, SupplierEvaluation,
)
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


# -------- Supplier --------

async def create_supplier(db: AsyncSession, data: dict) -> Supplier:
    s = Supplier(id=str(uuid.uuid4()), **data)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def list_suppliers(db: AsyncSession, skip: int = 0, limit: int = 100,
                         tier: Optional[str] = None, keyword: Optional[str] = None) -> List[Supplier]:
    q = select(Supplier)
    if tier:
        q = q.where(Supplier.tier == tier)
    if keyword:
        like = f"%{keyword}%"
        q = q.where((Supplier.name.like(like)) | (Supplier.code.like(like)))
    q = q.offset(skip).limit(limit).order_by(Supplier.code)
    return list((await db.execute(q)).scalars().all())


async def get_supplier(db: AsyncSession, supplier_id: str) -> Optional[Supplier]:
    return (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()


# -------- Purchase Order --------

async def create_purchase_order(db: AsyncSession, data: dict, user: Optional[dict] = None) -> PurchaseOrder:
    items_data = data.pop("items", [])
    if not items_data:
        raise BusinessRuleError("採購單必須至少包含 1 個項目")

    po = PurchaseOrder(
        id=str(uuid.uuid4()),
        po_no=f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        created_by=(user or {}).get("employee_id"),
        **data,
    )
    db.add(po)
    total = 0.0
    for i, item in enumerate(items_data):
        line_total = float(item.get("ordered_qty", 0)) * float(item.get("unit_price", 0))
        poi = PurchaseOrderItem(
            id=str(uuid.uuid4()),
            po_id=po.id,
            line_no=i + 1,
            line_total=line_total,
            **item,
        )
        db.add(poi)
        total += line_total
    po.total_amount = total
    await db.commit()
    # 預載 supplier + items 關聯，避免 PurchaseOrderResponse 觸發 async lazy-load
    # (MissingGreenlet error — 由 smoke test 抓到)
    await db.refresh(po, attribute_names=["supplier", "items"])
    await EventBus.emit(DomainEvent(
        name="po.created", domain="purchase",
        entity_type="PurchaseOrder", entity_id=po.id,
        data={"po_no": po.po_no, "supplier_id": po.supplier_id, "total": total},
    ))
    return po


async def get_purchase_order(db: AsyncSession, po_id: str) -> Optional[PurchaseOrder]:
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items), joinedload(PurchaseOrder.supplier))
        .where(PurchaseOrder.id == po_id)
    )
    return result.unique().scalar_one_or_none()


async def list_purchase_orders(db: AsyncSession, status: Optional[str] = None,
                               skip: int = 0, limit: int = 100) -> List[PurchaseOrder]:
    q = select(PurchaseOrder).options(joinedload(PurchaseOrder.supplier))
    if status:
        q = q.where(PurchaseOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(PurchaseOrder.created_at.desc())
    return list((await db.execute(q)).unique().scalars().all())


async def approve_purchase_order(db: AsyncSession, po_id: str, user: dict) -> PurchaseOrder:
    po = await get_purchase_order(db, po_id)
    if not po:
        raise NotFoundError("採購單不存在", po_id=po_id)
    if po.status not in ("draft", "pending"):
        raise BusinessRuleError(f"狀態 '{po.status}' 不可審核", po_id=po_id, current_status=po.status)
    po.status = "approved"
    po.approved_by = user.get("employee_id")
    await db.commit()
    await db.refresh(po, attribute_names=["supplier"])
    await EventBus.emit(DomainEvent(
        name="po.approved", domain="purchase",
        entity_type="PurchaseOrder", entity_id=po.id,
        data={"po_no": po.po_no, "approved_by": po.approved_by},
    ))
    return po


async def receive_purchase_order(db: AsyncSession, po_id: str,
                                 receipts: list[dict], user: dict) -> PurchaseOrder:
    """Receive goods for a PO.
    `receipts` = [{"item_id": str, "received_qty": float}].
    Creates inventory inbound transactions and updates PO line + status.
    """
    from app.services.inventory import add_inventory_transaction

    po = await get_purchase_order(db, po_id)
    if not po:
        raise NotFoundError("採購單不存在", po_id=po_id)
    if po.status not in ("approved", "sent", "partial_received"):
        raise BusinessRuleError(f"狀態 '{po.status}' 不可收貨", po_id=po_id)

    items_by_id = {it.id: it for it in po.items}
    all_received = True
    for r in receipts:
        item = items_by_id.get(r["item_id"])
        if not item:
            raise NotFoundError(f"PO 項目不存在: {r['item_id']}")
        rec_qty = float(r["received_qty"])
        if rec_qty <= 0:
            continue
        item.received_qty += rec_qty
        item.received_date = datetime.utcnow()
        # Push to inventory
        await add_inventory_transaction(db, {
            "part_id": item.part_id,
            "transaction_type": "inbound",
            "qty": rec_qty,
            "reference_type": "purchase_order",
            "reference_id": po.id,
            "remark": f"PO {po.po_no} 收貨",
        }, user=user)
        if item.received_qty < item.ordered_qty:
            all_received = False

    po.status = "received" if all_received else "partial_received"
    po.actual_delivery_date = datetime.utcnow() if all_received else po.actual_delivery_date
    await db.commit()
    await db.refresh(po, attribute_names=["supplier"])
    await EventBus.emit(DomainEvent(
        name="po.received", domain="purchase",
        entity_type="PurchaseOrder", entity_id=po.id,
        data={"po_no": po.po_no, "status": po.status},
    ))
    return po

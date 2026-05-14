"""Production service — Product / BOM / WO / Operation / Dispatch."""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, BOMItem
from app.models.production import ProductionOrder, WorkCenter, Operation, DispatchLog
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


# -------- Product --------

async def create_product(db: AsyncSession, data: dict) -> Product:
    p = Product(id=str(uuid.uuid4()), **data)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def list_products(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
    result = await db.execute(select(Product).offset(skip).limit(limit).order_by(Product.product_no))
    return list(result.scalars().all())


async def get_product(db: AsyncSession, product_id: str) -> Optional[Product]:
    return (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()


# -------- BOM --------

async def add_bom_item(db: AsyncSession, data: dict) -> BOMItem:
    item = BOMItem(id=str(uuid.uuid4()), **data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_bom_tree(db: AsyncSession, product_id: str) -> List[BOMItem]:
    result = await db.execute(
        select(BOMItem)
        .where(BOMItem.product_id == product_id, BOMItem.is_active == True)
        .order_by(BOMItem.level, BOMItem.sequence_no)
    )
    return list(result.scalars().all())


# -------- Work Order --------

async def create_production_order(db: AsyncSession, data: dict, user: Optional[dict] = None) -> ProductionOrder:
    if float(data.get("ordered_qty", 0)) <= 0:
        raise BusinessRuleError("訂單量必須大於 0")

    wo = ProductionOrder(
        id=str(uuid.uuid4()),
        wo_no=f"WO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        created_by=(user or {}).get("employee_id"),
        **data,
    )
    db.add(wo)
    await db.commit()
    await db.refresh(wo)
    await EventBus.emit(DomainEvent(
        name="wo.created", domain="production",
        entity_type="ProductionOrder", entity_id=wo.id,
        data={"wo_no": wo.wo_no, "product_id": wo.product_id, "qty": wo.ordered_qty},
    ))
    return wo


async def get_production_order(db: AsyncSession, wo_id: str) -> Optional[ProductionOrder]:
    result = await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.operations))
        .where(ProductionOrder.id == wo_id)
    )
    return result.scalar_one_or_none()


async def list_production_orders(db: AsyncSession, status: Optional[str] = None,
                                 skip: int = 0, limit: int = 100) -> List[ProductionOrder]:
    q = select(ProductionOrder)
    if status:
        q = q.where(ProductionOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(ProductionOrder.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def release_production_order(db: AsyncSession, wo_id: str, user: Optional[dict] = None) -> ProductionOrder:
    wo = (await db.execute(select(ProductionOrder).where(ProductionOrder.id == wo_id))).scalar_one_or_none()
    if not wo:
        raise NotFoundError("工單不存在", wo_id=wo_id)
    if wo.status != "draft":
        raise BusinessRuleError(f"工單狀態 '{wo.status}' 不可釋放", wo_id=wo_id)

    # Validate BOM exists
    bom = await get_bom_tree(db, wo.product_id)
    if not bom:
        raise BusinessRuleError("產品尚未維護 BOM，無法釋放工單", product_id=wo.product_id)

    wo.status = "released"
    wo.released_by = (user or {}).get("employee_id")
    wo.actual_start = datetime.utcnow()
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="wo.released", domain="production",
        entity_type="ProductionOrder", entity_id=wo.id,
        data={"wo_no": wo.wo_no, "product_id": wo.product_id, "qty": wo.ordered_qty},
    ))
    return wo


async def complete_production_order(db: AsyncSession, wo_id: str,
                                    completed_qty: float, user: Optional[dict] = None) -> ProductionOrder:
    """Mark WO completed and push finished product to inventory."""
    from app.services.inventory import add_inventory_transaction

    wo = await get_production_order(db, wo_id)
    if not wo:
        raise NotFoundError("工單不存在", wo_id=wo_id)
    if wo.status not in ("released", "in_progress"):
        raise BusinessRuleError(f"工單狀態 '{wo.status}' 不可完工")

    wo.completed_qty += completed_qty
    if wo.completed_qty >= wo.ordered_qty:
        wo.status = "completed"
        wo.actual_end = datetime.utcnow()

    # 把成品實際入庫（之前是註解 TODO 沒做 → 完工不會增加庫存的沉默 bug）
    # 約定：product.product_no == part.part_no（同編號對齊）
    from app.models.product import Product
    from app.models.inventory import Part
    prod = (await db.execute(
        select(Product).where(Product.id == wo.product_id)
    )).scalar_one_or_none()
    fg_part = None
    if prod is not None:
        fg_part = (await db.execute(
            select(Part).where(Part.part_no == prod.product_no)
        )).scalar_one_or_none()
    if fg_part is not None and completed_qty > 0:
        await add_inventory_transaction(db, {
            "part_id": fg_part.id,
            "transaction_type": "inbound",
            "qty": float(completed_qty),
            "reference_type": "work_order",
            "reference_id": wo.id,
            "remark": f"WO {wo.wo_no} 完工入庫",
        }, user=user)

    await db.commit()
    await EventBus.emit(DomainEvent(
        name="wo.completed", domain="production",
        entity_type="ProductionOrder", entity_id=wo.id,
        data={
            "wo_no": wo.wo_no, "completed_qty": completed_qty,
            "status": wo.status,
            "fg_inventory_increased": fg_part is not None,
        },
    ))
    return wo


# -------- WorkCenter / Operation / DispatchLog --------

async def create_work_center(db: AsyncSession, data: dict) -> WorkCenter:
    wc = WorkCenter(id=str(uuid.uuid4()), **data)
    db.add(wc)
    await db.commit()
    await db.refresh(wc)
    return wc


async def list_work_centers(db: AsyncSession) -> List[WorkCenter]:
    return list((await db.execute(select(WorkCenter).order_by(WorkCenter.code))).scalars().all())


async def create_operation(db: AsyncSession, data: dict) -> Operation:
    op = Operation(id=str(uuid.uuid4()), **data)
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return op


async def create_dispatch_log(db: AsyncSession, data: dict, user: Optional[dict] = None) -> DispatchLog:
    log = DispatchLog(
        id=str(uuid.uuid4()),
        operator_id=(user or {}).get("employee_id") or data.get("operator_id"),
        started_at=datetime.utcnow(),
        **{k: v for k, v in data.items() if k != "operator_id"},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    await EventBus.emit(DomainEvent(
        name="dispatch.created", domain="production",
        entity_type="DispatchLog", entity_id=log.id,
        data={"wo_id": log.production_order_id, "op_id": log.operation_id, "qty": log.dispatched_qty},
    ))
    return log

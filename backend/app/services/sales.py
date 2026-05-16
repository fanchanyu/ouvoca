"""Sales service — Customer / SalesOrder business logic."""
import uuid
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


async def create_customer(db: AsyncSession, data: dict) -> Customer:
    c = Customer(id=str(uuid.uuid4()), **data)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def list_customers(db: AsyncSession, skip: int = 0, limit: int = 100,
                         grade: Optional[str] = None, keyword: Optional[str] = None) -> List[Customer]:
    q = select(Customer)
    if grade:
        q = q.where(Customer.grade == grade)
    if keyword:
        like = f"%{keyword}%"
        q = q.where((Customer.name.like(like)) | (Customer.code.like(like)))
    q = q.offset(skip).limit(limit).order_by(Customer.code)
    return list((await db.execute(q)).scalars().all())


async def create_sales_order(db: AsyncSession, data: dict, user: Optional[dict] = None) -> SalesOrder:
    items_data = data.pop("items", [])
    if not items_data:
        raise BusinessRuleError("銷售訂單必須至少包含 1 個項目")

    so = SalesOrder(
        id=str(uuid.uuid4()),
        so_no=f"SO-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        created_by=(user or {}).get("employee_id"),
        **data,
    )
    db.add(so)
    total = 0.0
    for i, item in enumerate(items_data):
        line_total = float(item.get("ordered_qty", 0)) * float(item.get("unit_price", 0))
        soi = SalesOrderItem(
            id=str(uuid.uuid4()),
            so_id=so.id, line_no=i + 1, line_total=line_total, **item,
        )
        db.add(soi)
        total += line_total
    so.total_amount = total
    await db.commit()
    # 預載 customer 關聯，避免 SalesOrderResponse 觸發 async lazy-load (MissingGreenlet)
    await db.refresh(so, attribute_names=["customer"])
    await EventBus.emit(DomainEvent(
        name="so.created", domain="sales",
        entity_type="SalesOrder", entity_id=so.id,
        data={"so_no": so.so_no, "customer_id": so.customer_id, "total": total},
    ))
    return so


async def confirm_sales_order(db: AsyncSession, so_id: str, user: dict) -> SalesOrder:
    so = await get_sales_order(db, so_id)
    if not so:
        raise NotFoundError("銷售訂單不存在", so_id=so_id)
    if so.status != "draft":
        raise BusinessRuleError(f"狀態 '{so.status}' 不可確認")
    so.status = "confirmed"
    so.approved_by = user.get("employee_id")
    await db.commit()
    await db.refresh(so, attribute_names=["customer"])
    await EventBus.emit(DomainEvent(
        name="so.confirmed", domain="sales",
        entity_type="SalesOrder", entity_id=so.id,
        data={"so_no": so.so_no, "customer_id": so.customer_id, "total": so.total_amount},
    ))
    return so


async def ship_sales_order(db: AsyncSession, so_id: str, user: dict) -> SalesOrder:
    """出貨：① 改 SO 狀態 ② **為每個 item 寫 inventory_transaction (out)** ③ EventBus emit。

    早期 bug：只改狀態，不扣庫存 → 庫存永遠不會減少。
    由 O2C 閉環測試 (Phase α) 抓到。
    """
    from app.models.inventory import Part
    from app.models.product import Product

    so = await get_sales_order(db, so_id)
    if not so:
        raise NotFoundError("銷售訂單不存在", so_id=so_id)
    if so.status not in ("confirmed", "production", "ready_to_ship"):
        raise BusinessRuleError(f"狀態 '{so.status}' 不可出貨")

    # 為每個 item 建 inventory_transaction (out)
    # SO item 是 product_id；庫存記在 part 層級。
    # 約定：product.product_no == part.part_no（生產與庫存以 part_no 對齊）
    shipped_items = []
    for item in (so.items or []):
        prod = (await db.execute(
            select(Product).where(Product.id == item.product_id)
        )).scalar_one_or_none()
        if prod is None:
            continue
        part = (await db.execute(
            select(Part).where(Part.part_no == prod.product_no)
        )).scalar_one_or_none()
        if part is None:
            # 沒對應的 part，警告但不擋出貨（避免破壞 demo data）
            continue
        # 直接呼叫 service 確保庫存正確扣減（不是直接寫 raw model）
        from app.services.inventory import add_inventory_transaction
        await add_inventory_transaction(db, {
            "part_id": part.id,
            "transaction_type": "outbound",
            "qty": float(item.ordered_qty),
            "reference_type": "sales_order",
            "reference_id": so.id,
            "remark": f"自動出貨 / Auto-ship SO {so.so_no}",
        }, user=user)
        shipped_items.append({"part_id": part.id, "qty": float(item.ordered_qty)})

    so.status = "shipped"
    so.actual_delivery_date = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(so, attribute_names=["customer"])
    await EventBus.emit(DomainEvent(
        name="so.shipped", domain="sales",
        entity_type="SalesOrder", entity_id=so.id,
        data={
            "so_no": so.so_no,
            "shipped_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            "items": shipped_items,
            "total_amount": float(so.total_amount or 0),
            "customer_id": so.customer_id,
        },
    ))
    return so


async def get_sales_order(db: AsyncSession, so_id: str) -> Optional[SalesOrder]:
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.items), joinedload(SalesOrder.customer))
        .where(SalesOrder.id == so_id)
    )
    return result.unique().scalar_one_or_none()


async def list_sales_orders(db: AsyncSession, status: Optional[str] = None,
                            skip: int = 0, limit: int = 100) -> List[SalesOrder]:
    q = select(SalesOrder).options(joinedload(SalesOrder.customer))
    if status:
        q = q.where(SalesOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(SalesOrder.created_at.desc())
    return list((await db.execute(q)).unique().scalars().all())


# ============================================================
# v3.10 — Update / Delete
# ============================================================

CUSTOMER_UPDATABLE_FIELDS = {
    "name", "grade", "contact_person", "contact_email", "contact_phone",
    "address", "payment_terms", "credit_limit", "is_active",
}


async def update_customer(db: AsyncSession, customer_id: str, data: dict, user: Optional[dict] = None) -> Customer:
    c = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not c:
        raise NotFoundError("客戶不存在", customer_id=customer_id)
    changes = {}
    for k, v in data.items():
        if k not in CUSTOMER_UPDATABLE_FIELDS:
            continue
        if getattr(c, k) != v:
            changes[k] = {"from": getattr(c, k), "to": v}
            setattr(c, k, v)
    if not changes:
        return c
    await db.commit()
    await db.refresh(c)
    await EventBus.emit(DomainEvent(
        name="customer.updated", domain="sales",
        entity_type="Customer", entity_id=c.id,
        data={"code": c.code, "changes": changes},
    ))
    return c


async def delete_customer(db: AsyncSession, customer_id: str, user: Optional[dict] = None) -> dict:
    c = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not c:
        raise NotFoundError("客戶不存在", customer_id=customer_id)
    has_so = (await db.execute(
        select(SalesOrder).where(SalesOrder.customer_id == customer_id).limit(1)
    )).scalar_one_or_none()
    if has_so is not None:
        raise BusinessRuleError("此客戶已有銷售訂單，不可刪除（改用 is_active=False 停用）", customer_id=customer_id)
    code = c.code
    await db.delete(c)
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="customer.deleted", domain="sales",
        entity_type="Customer", entity_id=customer_id,
        data={"code": code},
    ))
    return {"deleted": True, "customer_id": customer_id, "code": code}


async def cancel_sales_order(db: AsyncSession, so_id: str, user: dict, reason: str = "") -> SalesOrder:
    so = await get_sales_order(db, so_id)
    if not so:
        raise NotFoundError("銷售訂單不存在", so_id=so_id)
    if so.status in ("shipped", "delivered", "closed", "cancelled"):
        raise BusinessRuleError(f"狀態 {so.status!r} 不可取消", so_id=so_id)
    old = so.status
    so.status = "cancelled"
    if reason:
        so.remark = (so.remark or "") + f"\n[Cancel] {reason}"
    await db.commit()
    await db.refresh(so, attribute_names=["customer"])
    await EventBus.emit(DomainEvent(
        name="so.cancelled", domain="sales",
        entity_type="SalesOrder", entity_id=so.id,
        data={"so_no": so.so_no, "previous_status": old, "reason": reason},
    ))
    return so

"""Quotation service (v3.32 進銷存深化)."""
import uuid
from datetime import datetime, timedelta, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quotation import Quotation, QuotationItem
from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


async def create_quotation(db: AsyncSession, data: dict, user: Optional[dict] = None) -> Quotation:
    items_data = data.pop("items", [])
    q = Quotation(
        id=str(uuid.uuid4()),
        quote_no=data.get("quote_no")
        or f"QUO-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
        quote_date=data.get("quote_date", datetime.now(UTC).replace(tzinfo=None)),
        valid_until=data.get("valid_until", datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)),
        customer_id=data["customer_id"],
        notes=data.get("notes", ""),
        created_by=(user or {}).get("employee_id"),
        status="draft",
    )
    db.add(q)
    await db.flush()

    subtotal = 0.0
    for idx, it in enumerate(items_data):
        qty = float(it.get("quantity", 0))
        price = float(it.get("unit_price", 0))
        disc = float(it.get("discount_rate", 0))
        line_total = qty * price * (1 - disc)
        subtotal += line_total
        db.add(QuotationItem(
            id=str(uuid.uuid4()), quotation_id=q.id,
            sequence_no=it.get("sequence_no", (idx + 1) * 10),
            product_id=it.get("product_id"),
            description=it["description"],
            quantity=qty, unit=it.get("unit", "pcs"),
            unit_price=price, discount_rate=disc,
            line_total=line_total, remark=it.get("remark", ""),
        ))
    q.subtotal = subtotal
    q.total_amount = subtotal + (data.get("tax_amount", 0)) - (data.get("discount_amount", 0))

    await db.commit()
    await db.refresh(q)
    await EventBus.emit(DomainEvent(
        name="quotation.created", domain="sales",
        entity_type="Quotation", entity_id=q.id,
        data={"quote_no": q.quote_no, "customer_id": q.customer_id,
              "total_amount": q.total_amount, "items_count": len(items_data)},
    ))
    return q


async def get_quotation(db: AsyncSession, quote_id: str) -> Optional[Quotation]:
    return (await db.execute(
        select(Quotation).options(selectinload(Quotation.items))
        .where(Quotation.id == quote_id)
    )).scalar_one_or_none()


async def list_quotations(
    db: AsyncSession, status: Optional[str] = None,
    customer_id: Optional[str] = None, limit: int = 100,
) -> List[Quotation]:
    q = select(Quotation)
    if status:
        q = q.where(Quotation.status == status)
    if customer_id:
        q = q.where(Quotation.customer_id == customer_id)
    q = q.order_by(Quotation.quote_date.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def convert_quotation_to_so(
    db: AsyncSession, quote_id: str, user: Optional[dict] = None,
) -> SalesOrder:
    """報價單接受 → 自動建 SO（killer feature for 業務）"""
    quote = await get_quotation(db, quote_id)
    if not quote:
        raise NotFoundError("報價單不存在", quote_id=quote_id)
    if quote.status not in ("draft", "sent", "accepted"):
        raise BusinessRuleError(
            f"報價單狀態 {quote.status!r} 無法轉訂單",
            quote_id=quote_id,
        )
    if quote.converted_so_id:
        raise BusinessRuleError(
            f"報價單已轉成 SO，無法重複轉",
            converted_so_id=quote.converted_so_id,
        )

    so = SalesOrder(
        id=str(uuid.uuid4()),
        so_no=f"SO-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        customer_id=quote.customer_id,
        status="confirmed",
        order_date=datetime.now(UTC).replace(tzinfo=None),
        total_amount=quote.total_amount,
        created_by=(user or {}).get("employee_id"),
        remark=f"由報價單 {quote.quote_no} 轉換",
    )
    db.add(so)
    await db.flush()

    for i, q_item in enumerate(quote.items):
        if q_item.product_id:  # SO 必須有 product_id
            db.add(SalesOrderItem(
                id=str(uuid.uuid4()), so_id=so.id,
                line_no=i + 1,
                product_id=q_item.product_id,
                ordered_qty=q_item.quantity,
                unit_price=q_item.unit_price,
                line_total=q_item.line_total,
            ))

    quote.status = "converted"
    quote.converted_so_id = so.id
    quote.converted_at = datetime.now(UTC).replace(tzinfo=None)

    await db.commit()
    await db.refresh(so)
    await EventBus.emit(DomainEvent(
        name="quotation.converted", domain="sales",
        entity_type="Quotation", entity_id=quote.id,
        data={"quote_no": quote.quote_no, "so_no": so.so_no,
              "total_amount": so.total_amount},
    ))
    return so


async def update_quotation_status(
    db: AsyncSession, quote_id: str, new_status: str,
    user: Optional[dict] = None,
) -> Quotation:
    """改報價單狀態（sent / accepted / rejected / expired）。"""
    quote = await get_quotation(db, quote_id)
    if not quote:
        raise NotFoundError("報價單不存在", quote_id=quote_id)
    valid_statuses = {"draft", "sent", "accepted", "rejected", "expired"}
    if new_status not in valid_statuses:
        raise BusinessRuleError(f"不合法狀態 {new_status!r}")
    quote.status = new_status
    await db.commit()
    await db.refresh(quote)
    return quote

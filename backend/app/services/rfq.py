"""RFQ 詢價比價（M3-3）— 詢價 → 報價 → 比價 → 決標轉 PO。"""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.rfq import RFQ, RFQItem, SupplierQuote, SupplierQuoteItem


async def _next_rfq_no(db) -> str:
    from app.services.document_numbering import next_document_no
    return await next_document_no(db, "RFQ")


async def create_rfq(db: AsyncSession, data: dict, user: Optional[dict] = None) -> RFQ:
    items_data = data.pop("items", [])
    if not items_data:
        raise BusinessRuleError("詢價單必須至少包含 1 個項目")
    rfq = RFQ(
        rfq_no=await _next_rfq_no(db),
        need_date=data.get("need_date"),
        remark=data.get("remark"),
        status="draft",
        created_by=(user or {}).get("employee_id"),
    )
    db.add(rfq)
    await db.flush()
    for i, item in enumerate(items_data, 1):
        db.add(RFQItem(rfq_id=rfq.id, part_id=item["part_id"], line_no=i,
                       qty=float(item["qty"]), need_date=item.get("need_date")))
    await db.commit()
    await db.refresh(rfq)
    return rfq


async def send_rfq(db: AsyncSession, rfq_id: str, user: Optional[dict] = None) -> RFQ:
    rfq = (await db.execute(
        select(RFQ).options(selectinload(RFQ.quotes)).where(RFQ.id == rfq_id)
    )).scalar_one_or_none()
    if rfq is None:
        raise NotFoundError("詢價單不存在", rfq_id=rfq_id)
    if rfq.status != "draft":
        raise BusinessRuleError(f"詢價單狀態 {rfq.status!r} 不可送出")
    rfq.status = "sent"
    await db.commit()
    await db.refresh(rfq)
    return rfq


async def receive_quote(db: AsyncSession, data: dict, user: Optional[dict] = None) -> SupplierQuote:
    """登錄供應商報價（含明細），自動算總金額。"""
    rfq_id = data["rfq_id"]
    rfq = (await db.execute(select(RFQ).where(RFQ.id == rfq_id))).scalar_one_or_none()
    if rfq is None:
        raise NotFoundError("詢價單不存在", rfq_id=rfq_id)
    if rfq.status != "sent":
        raise BusinessRuleError(f"詢價單狀態 {rfq.status!r} 不可收報價")

    items = data.get("items") or []
    if not items:
        raise BusinessRuleError("報價必須至少包含 1 行")
    total = round(sum(float(i.get("unit_price", 0)) * float(i.get("qty", 0)) for i in items), 2)
    quote = SupplierQuote(
        rfq_id=rfq.id,
        supplier_id=data["supplier_id"],
        quote_date=data.get("quote_date") or datetime.now(UTC).replace(tzinfo=None),
        amount=total,
        lead_time_days=int(data.get("lead_time_days", 0) or 0),
        currency=data.get("currency", "TWD"),
        status="received",
        remark=data.get("remark"),
        created_by=(user or {}).get("employee_id"),
    )
    db.add(quote)
    await db.flush()
    for i, item in enumerate(items, 1):
        db.add(SupplierQuoteItem(
            quote_id=quote.id, part_id=item["part_id"],
            qty=float(item["qty"]), unit_price=float(item.get("unit_price", 0)),
        ))
    await db.commit()
    await db.refresh(quote)
    return quote


async def compare_quotes(db: AsyncSession, rfq_id: str) -> dict:
    """比價：列出所有報價 + 每料件最低價 + 總額排序。"""
    rfq = (await db.execute(
        select(RFQ).options(
            selectinload(RFQ.items), selectinload(RFQ.quotes),
        ).where(RFQ.id == rfq_id)
    )).scalar_one_or_none()
    if rfq is None:
        raise NotFoundError("詢價單不存在", rfq_id=rfq_id)

    # N+1 修復：一次撈出所有報價明細
    quote_ids = [q.id for q in rfq.quotes]
    items_by_quote: dict[str, list[SupplierQuoteItem]] = {}
    if quote_ids:
        all_items = (await db.execute(
            select(SupplierQuoteItem).where(SupplierQuoteItem.quote_id.in_(quote_ids))
        )).scalars().all()
        for it in all_items:
            items_by_quote.setdefault(it.quote_id, []).append(it)

    quotes_out = []
    for q in rfq.quotes:
        items = items_by_quote.get(q.id, [])
        quotes_out.append({
            "quote_id": q.id,
            "supplier_id": q.supplier_id,
            "amount": q.amount,
            "lead_time_days": q.lead_time_days,
            "status": q.status,
            "items": [
                {"part_id": i.part_id, "qty": i.qty, "unit_price": i.unit_price}
                for i in items
            ],
        })
    quotes_out.sort(key=lambda x: x["amount"])

    # 每料件最低價
    best_per_part: dict[str, dict] = {}
    for q in quotes_out:
        for it in q["items"]:
            cur = best_per_part.get(it["part_id"])
            if cur is None or it["unit_price"] < cur["unit_price"]:
                best_per_part[it["part_id"]] = {
                    "part_id": it["part_id"],
                    "unit_price": it["unit_price"],
                    "supplier_id": q["supplier_id"],
                    "quote_id": q["quote_id"],
                }

    return {
        "rfq_id": rfq.id,
        "rfq_no": rfq.rfq_no,
        "status": rfq.status,
        "quotes": quotes_out,
        "best_per_part": list(best_per_part.values()),
    }


async def award_rfq(db: AsyncSession, rfq_id: str, quote_id: str,
                    user: Optional[dict] = None) -> dict:
    """決標：指定報價得標，其餘 declined；可選轉 PO。"""
    from app.services.purchase import create_purchase_order

    rfq = (await db.execute(
        select(RFQ).options(selectinload(RFQ.quotes)).where(RFQ.id == rfq_id)
    )).scalar_one_or_none()
    quote = (await db.execute(
        select(SupplierQuote).where(SupplierQuote.id == quote_id, SupplierQuote.rfq_id == rfq_id)
    )).scalar_one_or_none()
    if rfq is None or quote is None:
        raise NotFoundError("詢價單或報價不存在")
    if rfq.status != "sent":
        raise BusinessRuleError(f"詢價單狀態 {rfq.status!r} 不可決標")

    quote.status = "awarded"
    rfq.awarded_quote_id = quote.id
    rfq.status = "awarded"
    for other in rfq.quotes:
        if other.id != quote.id and other.status == "received":
            other.status = "declined"

    # 轉 PO（依得標報價明細）
    quote_items = (await db.execute(
        select(SupplierQuoteItem).where(SupplierQuoteItem.quote_id == quote.id)
    )).scalars().all()
    po = await create_purchase_order(db, {
        "supplier_id": quote.supplier_id,
        "expected_delivery_date": rfq.need_date,
        "remark": f"由 RFQ {rfq.rfq_no} 決標轉入",
        "items": [
            {"part_id": i.part_id, "ordered_qty": i.qty, "unit_price": i.unit_price}
            for i in quote_items
        ],
    }, user=user)
    rfq.converted_po_id = po.id
    await db.commit()
    return {"rfq_id": rfq.id, "quote_id": quote.id, "po_id": po.id, "po_no": po.po_no}

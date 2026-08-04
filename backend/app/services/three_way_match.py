"""3-Way Match（M2-3）— PO ↔ 收貨 ↔ 供應商發票勾稽。

每張 SupplierInvoice（含 items，可對應 po_item_id）與 PO 的
ordered_qty / received_qty / unit_price 比對，產出差異清單與狀態：
  - matched          數量與金額一致
  - qty_variance     數量不一致
  - price_variance   單價不一致（金額不一致但數量一致）
  - unmatched        未關聯 PO 或找不到對應行
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.finance import SupplierInvoice, SupplierInvoiceItem
from app.models.purchase import PurchaseOrder, PurchaseOrderItem

_EPS = 0.005


def _match_item(invoice_item, po_item: PurchaseOrderItem | None) -> dict:
    if po_item is None:
        return {
            "part_id": invoice_item.part_id,
            "invoice_qty": invoice_item.qty,
            "po_qty": None,
            "received_qty": None,
            "invoice_unit_price": invoice_item.unit_price,
            "po_unit_price": None,
            "status": "unmatched",
            "issues": ["供應商發票行未對應到 PO 行"],
        }
    qty_diff = round(invoice_item.qty - (po_item.received_qty or 0), 2)
    # 健檢殘留 #2：unit_price 與 received_qty 一樣可能為 None，必須防呆
    invoice_price = invoice_item.unit_price or 0
    po_price = po_item.unit_price or 0
    price_diff = round(invoice_price - po_price, 2)
    issues = []
    if abs(qty_diff) > _EPS:
        # 健檢 #20：received_qty 可能為 None，format 前防呆
        issues.append(f"數量差 {qty_diff:g}（發票 {invoice_item.qty:g} vs 收貨 {(po_item.received_qty or 0):g}）")
    if abs(price_diff) > _EPS:
        issues.append(f"單價差 {price_diff:g}（發票 {invoice_price:g} vs PO {po_price:g}）")
    if not issues:
        status = "matched"
    elif abs(qty_diff) > _EPS:
        status = "qty_variance"
    else:
        status = "price_variance"
    return {
        "po_item_id": po_item.id,
        "part_id": invoice_item.part_id,
        "invoice_qty": invoice_item.qty,
        "po_qty": po_item.ordered_qty,
        "received_qty": po_item.received_qty,
        "invoice_unit_price": invoice_item.unit_price,
        "po_unit_price": po_item.unit_price,
        "status": status,
        "issues": issues,
    }


async def match_supplier_invoice(db: AsyncSession, invoice_id: str) -> dict:
    """對單張供應商發票執行 3-Way Match。"""
    inv = (await db.execute(
        select(SupplierInvoice)
        .options(selectinload(SupplierInvoice.items))
        .where(SupplierInvoice.id == invoice_id)
    )).scalar_one_or_none()
    if inv is None:
        raise NotFoundError("供應商發票不存在", invoice_id=invoice_id)

    po_items: dict[str, PurchaseOrderItem] = {}
    po = None
    if inv.po_id:
        po = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == inv.po_id)
        )).scalar_one_or_none()
        if po is not None:
            po_items = {
                str(i.id): i for i in (await db.execute(
                    select(PurchaseOrderItem).where(PurchaseOrderItem.po_id == po.id)
                )).scalars().all()
            }

    line_results = []
    for item in inv.items:
        po_item = po_items.get(str(item.po_item_id)) if item.po_item_id else None
        line_results.append(_match_item(item, po_item))

    statuses = {r["status"] for r in line_results}
    if "unmatched" in statuses:
        overall = "unmatched"
    elif "qty_variance" in statuses:
        overall = "qty_variance"
    elif "price_variance" in statuses:
        overall = "price_variance"
    else:
        overall = "matched"

    inv.status = overall
    await db.commit()
    await db.refresh(inv)

    return {
        "invoice_id": inv.id,
        "invoice_no": inv.invoice_no,
        "po_no": po.po_no if po else None,
        "supplier_id": inv.supplier_id,
        "invoice_total": inv.total_amount,
        "po_total": po.total_amount if po else None,
        "status": overall,
        "lines": line_results,
    }


async def list_invoice_matches(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """列出供應商發票與其 match 狀態（不逐行重算，直接回 status）。"""
    q = select(SupplierInvoice).order_by(SupplierInvoice.invoice_date.desc()).limit(limit)
    if status:
        q = q.where(SupplierInvoice.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "invoice_no": r.invoice_no,
            "supplier_id": r.supplier_id,
            "po_id": r.po_id,
            "invoice_date": r.invoice_date.isoformat() if r.invoice_date else None,
            "total_amount": r.total_amount,
            "status": r.status,
        }
        for r in rows
    ]


async def create_supplier_invoice(
    db: AsyncSession,
    data: dict,
    user: dict | None = None,
    *,
    run_match: bool = True,
) -> SupplierInvoice:
    """建立供應商發票（含行），可選立即執行 3-Way Match。"""
    items_data = data.pop("items", [])
    if not items_data:
        raise BusinessRuleError("供應商發票必須至少包含 1 行")
    sales_amount = float(data.get("sales_amount", 0) or 0)
    tax_amount = float(data.get("tax_amount", 0) or 0)
    total_amount = float(data.get("total_amount", 0) or 0)
    if not total_amount:
        total_amount = round(sales_amount + tax_amount, 2)

    inv = SupplierInvoice(
        invoice_no=data["invoice_no"],
        supplier_id=data["supplier_id"],
        po_id=data.get("po_id"),
        invoice_date=data.get("invoice_date") or datetime.now(UTC).replace(tzinfo=None),
        due_date=data.get("due_date"),
        sales_amount=sales_amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        status="received",
        remark=data.get("remark"),
        created_by=(user or {}).get("employee_id"),
    )
    db.add(inv)
    await db.flush()

    for i, item in enumerate(items_data, 1):
        qty = float(item["qty"])
        unit_price = float(item.get("unit_price", 0))
        db.add(SupplierInvoiceItem(
            invoice_id=inv.id,
            po_item_id=item.get("po_item_id"),
            part_id=item["part_id"],
            line_no=i,
            qty=qty,
            unit_price=unit_price,
            line_total=round(qty * unit_price, 2),
        ))
    await db.commit()
    await db.refresh(inv)

    if run_match:
        await match_supplier_invoice(db, inv.id)
    return inv

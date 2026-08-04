"""批號 / 序號追溯（M3-2）— 正反向 Pegging。

正向：某批/某序號 → 被哪些單據消耗（出貨/領料/退貨）
反向：某批/某序號 → 從哪些單據進來（收料/入庫）

動向來源：InventoryTransaction（batch_no + reference_type/reference_id），
reference 對應單號用 _resolve_doc_no 解析。
"""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.traceability import BatchLot, SerialNumber
from app.models.inventory import InventoryTransaction, Part


async def _resolve_doc_no(db: AsyncSession, ref_type: str, ref_id: str) -> str | None:
    """reference_type/id → 人類可讀單號。

    健檢 #22：用 ORM select（走自動租戶過濾），不用 raw SQL —
    否則可能洩漏他租戶的單號。
    """
    table_map = {
        "purchase_order": _import_model("app.models.purchase", "PurchaseOrder"),
        "goods_receipt_note": _import_model("app.models.documents_m3", "GoodsReceiptNote"),
        "work_order": _import_model("app.models.production", "ProductionOrder"),
        "material_issue": _import_model("app.models.documents_m3", "MaterialIssue"),
        "delivery_note": _import_model("app.models.delivery", "DeliveryNote"),
        "sales_order": _import_model("app.models.crm_sales", "SalesOrder"),
        "return_note": _import_model("app.models.documents_m3", "ReturnNote"),
    }
    model = table_map.get(ref_type)
    if model is None:
        return f"{ref_type}:{ref_id}"
    row = (await db.execute(select(model).where(model.id == ref_id))).scalar_one_or_none()
    if row is None:
        return f"{ref_type}:{ref_id}"
    # 各 model 的單號欄位名
    col_name = {
        "PurchaseOrder": "po_no",
        "GoodsReceiptNote": "grn_no",
        "ProductionOrder": "wo_no",
        "MaterialIssue": "issue_no",
        "DeliveryNote": "dn_no",
        "SalesOrder": "so_no",
        "ReturnNote": "return_no",
    }[model.__name__]
    return str(getattr(row, col_name))


def _import_model(module: str, cls: str):
    """延遲 import（避免 models 初始化順序相依）。"""
    import importlib
    return getattr(importlib.import_module(module), cls)


async def assign_batch(
    db: AsyncSession,
    part_id: str,
    lot_no: str,
    qty: float = 0,
    expiry_date=None,
    user: Optional[dict] = None,
) -> BatchLot:
    """建立/更新批號主檔。"""
    if qty < 0:
        raise BusinessRuleError("批號數量不能為負")
    lot = (await db.execute(
        select(BatchLot).where(BatchLot.lot_no == lot_no, BatchLot.part_id == part_id)
    )).scalar_one_or_none()
    if lot is None:
        lot = BatchLot(lot_no=lot_no, part_id=part_id, qty=qty,
                       expiry_date=expiry_date, status="active",
                       created_by=(user or {}).get("employee_id"))
        db.add(lot)
    else:
        lot.qty = qty
        lot.expiry_date = expiry_date
    await db.commit()
    await db.refresh(lot)
    return lot


async def record_serials(
    db: AsyncSession,
    part_id: str,
    serials: list[str],
    batch_id: Optional[str] = None,
    user: Optional[dict] = None,
) -> list[SerialNumber]:
    """批量登記序號（重複序號拒絕）。"""
    created = []
    for sn in serials:
        dup = (await db.execute(
            select(SerialNumber).where(SerialNumber.serial_no == sn)
        )).scalar_one_or_none()
        if dup:
            raise BusinessRuleError(f"序號 {sn} 已存在")
        obj = SerialNumber(serial_no=sn, part_id=part_id, batch_id=batch_id,
                           status="in_stock")
        db.add(obj)
        created.append(obj)
    await db.commit()
    return created


async def trace_batch(db: AsyncSession, lot_no: str) -> dict:
    """批次追溯：批次主檔 + 正反向動向。"""
    lots = list((await db.execute(
        select(BatchLot).where(BatchLot.lot_no == lot_no)
    )).scalars().all())
    if not lots:
        raise NotFoundError(f"批號不存在：{lot_no}")
    movements = []
    for lot in lots:
        txns = (await db.execute(
            select(InventoryTransaction)
            .where(InventoryTransaction.batch_no == lot.lot_no)
            .order_by(InventoryTransaction.created_at)
        )).scalars().all()
        for t in txns:
            movements.append({
                "direction": "in" if t.transaction_type in (
                    "inbound", "adjustment_in", "return_in",
                ) else "out",
                "transaction_type": t.transaction_type,
                "qty": t.qty,
                "document_type": t.reference_type,
                "document_no": await _resolve_doc_no(db, t.reference_type or "", t.reference_id or ""),
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
    return {
        "lot_no": lot_no,
        "lots": [
            {"id": l.id, "part_id": l.part_id, "qty": l.qty,
             "expiry_date": l.expiry_date.isoformat() if l.expiry_date else None,
             "status": l.status}
            for l in lots
        ],
        "movements": movements,
        "forward_consumed_by": [m for m in movements if m["direction"] == "out"],
        "backward_received_from": [m for m in movements if m["direction"] == "in"],
    }


async def trace_serial(db: AsyncSession, serial_no: str) -> dict:
    """序號追溯：序號主檔 + 最近文件 + 批次。"""
    sn = (await db.execute(
        select(SerialNumber).where(SerialNumber.serial_no == serial_no)
    )).scalar_one_or_none()
    if sn is None:
        raise NotFoundError(f"序號不存在：{serial_no}")
    return {
        "serial_no": sn.serial_no,
        "part_id": sn.part_id,
        "status": sn.status,
        "batch_id": sn.batch_id,
        "last_document_type": sn.last_document_type,
        "last_document_no": await _resolve_doc_no(
            db, sn.last_document_type or "", sn.last_document_id or "",
        ),
        "created_at": sn.created_at.isoformat() if sn.created_at else None,
    }


async def list_batches(db: AsyncSession, part_id: Optional[str] = None,
                       limit: int = 100) -> list[dict]:
    q = select(BatchLot).order_by(BatchLot.created_at.desc()).limit(limit)
    if part_id:
        q = q.where(BatchLot.part_id == part_id)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": r.id, "lot_no": r.lot_no, "part_id": r.part_id, "qty": r.qty,
         "expiry_date": r.expiry_date.isoformat() if r.expiry_date else None,
         "status": r.status}
        for r in rows
    ]

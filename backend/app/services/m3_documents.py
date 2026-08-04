"""M3 表單工程服務 — 請購單 / 收料單 / 領料單 / 退貨單。"""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.documents_m3 import (
    GoodsReceiptNote, GoodsReceiptNoteItem,
    MaterialIssue, MaterialIssueItem,
    PurchaseRequisition, PurchaseRequisitionItem,
    ReturnNote, ReturnNoteItem,
)
from app.models.purchase import PurchaseOrder, PurchaseOrderItem
from app.models.inventory import Part
from app.models.production import ProductionOrder


async def _next_no(db, doc_type: str) -> str:
    from app.services.document_numbering import next_document_no
    return await next_document_no(db, doc_type)


# ════════════════════════════════════════════════════════════
# 請購單 PR
# ════════════════════════════════════════════════════════════

async def create_purchase_requisition(db: AsyncSession, data: dict, user: Optional[dict] = None) -> PurchaseRequisition:
    items_data = data.pop("items", [])
    if not items_data:
        raise BusinessRuleError("請購單必須至少包含 1 個項目")
    pr = PurchaseRequisition(
        pr_no=await _next_no(db, "PR"),
        requester_id=data.get("requester_id") or (user or {}).get("employee_id"),
        department_id=data.get("department_id"),
        need_date=data.get("need_date"),
        remark=data.get("remark"),
        status="draft",
        created_by=(user or {}).get("employee_id"),
    )
    db.add(pr)
    await db.flush()
    for i, item in enumerate(items_data, 1):
        db.add(PurchaseRequisitionItem(
            pr_id=pr.id, part_id=item["part_id"], line_no=i,
            qty=float(item["qty"]), need_date=item.get("need_date"),
            remark=item.get("remark"),
        ))
    await db.commit()
    await db.refresh(pr)
    return pr


async def approve_purchase_requisition(db: AsyncSession, pr_id: str, user: Optional[dict] = None) -> PurchaseRequisition:
    pr = (await db.execute(
        select(PurchaseRequisition).where(PurchaseRequisition.id == pr_id)
    )).scalar_one_or_none()
    if pr is None:
        raise NotFoundError("請購單不存在", pr_id=pr_id)
    if pr.status != "draft":
        raise BusinessRuleError(f"請購單狀態 {pr.status!r} 不可核准")
    pr.status = "approved"
    await db.commit()
    await db.refresh(pr)
    return pr


async def convert_pr_to_po(db: AsyncSession, pr_id: str, supplier_id: str,
                           user: Optional[dict] = None) -> PurchaseOrder:
    """請購單 → 採購單（PR 審核通過後轉 PO）。"""
    from app.services.purchase import create_purchase_order

    pr = (await db.execute(
        select(PurchaseRequisition).options(selectinload(PurchaseRequisition.items))
        .where(PurchaseRequisition.id == pr_id)
    )).scalar_one_or_none()
    if pr is None:
        raise NotFoundError("請購單不存在", pr_id=pr_id)
    if pr.status != "approved":
        raise BusinessRuleError(f"請購單狀態 {pr.status!r} 不可轉採購（需先核准）")
    if pr.converted_po_id:
        raise BusinessRuleError("此請購單已轉成採購單", po_id=pr.converted_po_id)

    items = (await db.execute(
        select(PurchaseRequisitionItem).where(PurchaseRequisitionItem.pr_id == pr.id)
    )).scalars().all()
    if not items:
        raise BusinessRuleError("請購單沒有項目")
    # N+1 修復：一次撈出所有料件，取代逐項查詢
    part_ids = {it.part_id for it in items}
    parts: dict[str, Part] = {}
    if part_ids:
        parts = {
            p.id: p for p in (await db.execute(
                select(Part).where(Part.id.in_(part_ids))
            )).scalars().all()
        }
    po_items = []
    for it in items:
        part = parts.get(it.part_id)
        po_items.append({
            "part_id": it.part_id,
            "ordered_qty": it.qty,
            "unit_price": part.unit_cost if part else 0,
            "expected_date": it.need_date,
        })
    po = await create_purchase_order(db, {
        "supplier_id": supplier_id,
        "expected_delivery_date": pr.need_date,
        "remark": f"由請購單 {pr.pr_no} 轉入",
        "items": po_items,
    }, user=user)
    pr.status = "converted"
    pr.converted_po_id = po.id
    await db.commit()
    return po


# ════════════════════════════════════════════════════════════
# 收料單 GRN
# ════════════════════════════════════════════════════════════

async def create_grn(db: AsyncSession, po_id: str, receipts: list[dict],
                     user: Optional[dict] = None) -> GoodsReceiptNote:
    """收料：建立 GRN + 更新 PO 收貨量 + 入庫（原子）。"""
    from app.services.inventory import add_inventory_transaction
    from app.core.status_machine import assert_transition

    po = (await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )).scalar_one_or_none()
    if po is None:
        raise NotFoundError("採購單不存在", po_id=po_id)
    # v3.67 家規：收貨需 PO 已核准
    from app.services.policy_engine import evaluate_policies
    policy = await evaluate_policies(db, "po.receive", {
        "status": po.status, "po_id": po.id, "po_no": po.po_no,
    }, user_id=(user or {}).get("employee_id"))
    if policy.blocked:
        raise BusinessRuleError(policy.message, can_override=policy.can_override)
    if po.status not in ("approved", "sent", "partial_received"):
        raise BusinessRuleError(f"採購單狀態 {po.status!r} 不可收貨")

    grn = GoodsReceiptNote(
        grn_no=await _next_no(db, "GRN"),
        po_id=po.id,
        supplier_id=po.supplier_id,
        received_at=datetime.now(UTC).replace(tzinfo=None),
        status="posted",
        created_by=(user or {}).get("employee_id"),
    )
    db.add(grn)
    await db.flush()

    items_by_id = {it.id: it for it in po.items}
    all_received = True
    for r in receipts:
        item = items_by_id.get(r["item_id"])
        if item is None:
            raise NotFoundError(f"PO 項目不存在: {r['item_id']}")
        rec_qty = float(r["received_qty"])
        if rec_qty <= 0:
            continue
        # 健檢 #11：超收防呆 — 累計收貨不可超過訂購量
        if item.received_qty + rec_qty > item.ordered_qty:
            raise BusinessRuleError(
                f"超收：PO 行 {item.id} 已收 {item.received_qty:g}，"
                f"再收 {rec_qty:g} 超過訂購量 {item.ordered_qty:g}",
                po_item_id=item.id,
            )
        item.received_qty += rec_qty
        item.received_date = datetime.now(UTC).replace(tzinfo=None)
        db.add(GoodsReceiptNoteItem(
            grn_id=grn.id, po_item_id=item.id, part_id=item.part_id,
            qty_received=rec_qty, unit_price=item.unit_price,
        ))
        await add_inventory_transaction(db, {
            "part_id": item.part_id,
            "transaction_type": "inbound",
            "qty": rec_qty,
            "reference_type": "goods_receipt_note",
            "reference_id": grn.id,
            "remark": f"GRN {grn.grn_no} 收貨（PO {po.po_no}）",
        }, user=user)
        if item.received_qty < item.ordered_qty:
            all_received = False

    target = "received" if all_received else "partial_received"
    assert_transition("PO", po.status, target, po.po_no)
    po.status = target
    po.actual_delivery_date = (
        datetime.now(UTC).replace(tzinfo=None) if all_received else po.actual_delivery_date
    )
    await db.commit()
    await db.refresh(grn)
    return grn


async def list_grns(db: AsyncSession, limit: int = 100) -> list[dict]:
    rows = (await db.execute(
        select(GoodsReceiptNote).order_by(GoodsReceiptNote.received_at.desc()).limit(limit)
    )).scalars().all()
    return [
        {"id": r.id, "grn_no": r.grn_no, "po_id": r.po_id, "supplier_id": r.supplier_id,
         "received_at": r.received_at.isoformat() if r.received_at else None,
         "status": r.status}
        for r in rows
    ]


# ════════════════════════════════════════════════════════════
# 領料單 MaterialIssue
# ════════════════════════════════════════════════════════════

async def issue_material(db: AsyncSession, wo_id: str, items: list[dict],
                         user: Optional[dict] = None) -> MaterialIssue:
    """工單領料：扣原料庫存 + 記錄領料單（成本快照）。"""
    from app.services.inventory import add_inventory_transaction

    wo = (await db.execute(
        select(ProductionOrder).where(ProductionOrder.id == wo_id)
    )).scalar_one_or_none()
    if wo is None:
        raise NotFoundError("工單不存在", wo_id=wo_id)
    if wo.status not in ("released", "in_progress"):
        raise BusinessRuleError(f"工單狀態 {wo.status!r} 不可領料")
    if not items:
        raise BusinessRuleError("領料單必須至少包含 1 個項目")

    issue = MaterialIssue(
        issue_no=await _next_no(db, "MI"),
        wo_id=wo.id,
        issued_at=datetime.now(UTC).replace(tzinfo=None),
        status="posted",
        created_by=(user or {}).get("employee_id"),
    )
    db.add(issue)
    await db.flush()

    for raw in items:
        part = (await db.execute(
            select(Part).where(Part.id == raw["part_id"])
        )).scalar_one_or_none()
        if part is None:
            raise NotFoundError(f"料件不存在: {raw['part_id']}")
        qty = float(raw["qty"])
        if qty <= 0:
            raise BusinessRuleError("領料數量必須大於 0")
        db.add(MaterialIssueItem(
            issue_id=issue.id, part_id=part.id, qty=qty,
            unit_cost=float(part.unit_cost or 0),
        ))
        await add_inventory_transaction(db, {
            "part_id": part.id,
            "transaction_type": "outbound",
            "qty": qty,
            "reference_type": "material_issue",
            "reference_id": issue.id,
            "remark": f"MI {issue.issue_no} 領料（WO {wo.wo_no}）",
        }, user=user)
    await db.commit()
    await db.refresh(issue)
    return issue


async def list_material_issues(db: AsyncSession, wo_id: Optional[str] = None,
                               limit: int = 100) -> list[dict]:
    q = select(MaterialIssue).order_by(MaterialIssue.issued_at.desc()).limit(limit)
    if wo_id:
        q = q.where(MaterialIssue.wo_id == wo_id)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": r.id, "issue_no": r.issue_no, "wo_id": r.wo_id,
         "issued_at": r.issued_at.isoformat() if r.issued_at else None, "status": r.status}
        for r in rows
    ]


# ════════════════════════════════════════════════════════════
# 退貨單 RMA
# ════════════════════════════════════════════════════════════

async def create_return_note(db: AsyncSession, data: dict, user: Optional[dict] = None) -> ReturnNote:
    items_data = data.pop("items", [])
    if not items_data:
        raise BusinessRuleError("退貨單必須至少包含 1 個項目")
    note = ReturnNote(
        return_no=await _next_no(db, "RT"),
        customer_id=data["customer_id"],
        so_id=data.get("so_id"),
        return_date=data.get("return_date") or datetime.now(UTC).replace(tzinfo=None),
        reason=data.get("reason"),
        status="draft",
        created_by=(user or {}).get("employee_id"),
    )
    db.add(note)
    await db.flush()
    for i, item in enumerate(items_data, 1):
        db.add(ReturnNoteItem(
            return_id=note.id, part_id=item["part_id"], qty=float(item["qty"]),
            unit_price=float(item.get("unit_price", 0)), reason=item.get("reason"),
        ))
    await db.commit()
    await db.refresh(note)
    return note


async def approve_return_note(db: AsyncSession, return_id: str, user: Optional[dict] = None) -> ReturnNote:
    note = (await db.execute(
        select(ReturnNote).where(ReturnNote.id == return_id)
    )).scalar_one_or_none()
    if note is None:
        raise NotFoundError("退貨單不存在", return_id=return_id)
    if note.status != "draft":
        raise BusinessRuleError(f"退貨單狀態 {note.status!r} 不可核准")
    note.status = "approved"
    await db.commit()
    await db.refresh(note)
    return note


async def process_return_note(db: AsyncSession, return_id: str,
                              user: Optional[dict] = None) -> ReturnNote:
    """退貨入庫：退回品項加回庫存。"""
    from app.services.inventory import add_inventory_transaction

    note = (await db.execute(
        select(ReturnNote).options(selectinload(ReturnNote.items))
        .where(ReturnNote.id == return_id)
    )).scalar_one_or_none()
    if note is None:
        raise NotFoundError("退貨單不存在", return_id=return_id)
    if note.status != "approved":
        raise BusinessRuleError(f"退貨單狀態 {note.status!r} 不可入庫（需先核准）")

    for item in note.items:
        await add_inventory_transaction(db, {
            "part_id": item.part_id,
            "transaction_type": "inbound",
            "qty": item.qty,
            "reference_type": "return_note",
            "reference_id": note.id,
            "remark": f"RT {note.return_no} 退貨入庫",
        }, user=user)
    note.status = "processed"
    await db.commit()
    await db.refresh(note)
    return note


async def list_return_notes(db: AsyncSession, status: Optional[str] = None,
                            limit: int = 100) -> list[dict]:
    q = select(ReturnNote).order_by(ReturnNote.return_date.desc()).limit(limit)
    if status:
        q = q.where(ReturnNote.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": r.id, "return_no": r.return_no, "customer_id": r.customer_id,
         "return_date": r.return_date.isoformat() if r.return_date else None,
         "status": r.status, "reason": r.reason}
        for r in rows
    ]

"""Purchase API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_db
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.core.security import require_permission, UserContext, apply_row_filter
from app.models.purchase import Supplier, PurchaseOrder
from app.core.exceptions import NotFoundError
from app.schemas.purchase import (
    SupplierCreate, SupplierResponse,
    PurchaseOrderCreate, PurchaseOrderResponse,
)
from app.services import purchase as svc

router = APIRouter(prefix="/api/purchase", tags=["Purchase"])


@router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier_endpoint(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.supplier.create")),
):
    s = await svc.create_supplier(db, data.model_dump())
    return SupplierResponse.model_validate(s)


@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers_endpoint(
    tier: Optional[str] = None,
    keyword: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.supplier.list")),
):
    rows = await svc.list_suppliers(db, skip, limit, tier, keyword)
    return [SupplierResponse.model_validate(s) for s in rows]


@router.post("/orders", response_model=PurchaseOrderResponse)
async def create_po_endpoint(
    data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.order.create")),
):
    po = await svc.create_purchase_order(db, data.model_dump(), user=user.raw_user)
    return PurchaseOrderResponse.model_validate(po)


@router.get("/orders", response_model=List[PurchaseOrderResponse])
async def list_po_endpoint(
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.order.list")),
):
    # 健檢：列表查詢也要 eager-load items，否則獨立 session 下
    # PurchaseOrderResponse 序列化 items 時 MissingGreenlet → HTTP 400
    q = select(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.items),
    )
    q = apply_row_filter(q, user, "purchase.order")
    if status: q = q.where(PurchaseOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(PurchaseOrder.created_at.desc())
    rows = (await db.execute(q)).unique().scalars().all()
    return [PurchaseOrderResponse.model_validate(r) for r in rows]


@router.get("/orders/{po_id}", response_model=PurchaseOrderResponse)
async def get_po_endpoint(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.order.read")),
):
    po = await svc.get_purchase_order(db, po_id)
    if not po:
        raise NotFoundError("採購單不存在", po_id=po_id)
    return PurchaseOrderResponse.model_validate(po)


@router.post("/orders/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.order.approve")),
):
    po = await svc.approve_purchase_order(db, po_id, user.raw_user)
    return PurchaseOrderResponse.model_validate(po)


class ReceiptItem(BaseModel):
    item_id: str
    received_qty: float


class ReceiveRequest(BaseModel):
    receipts: List[ReceiptItem]


@router.post("/orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_po(
    po_id: str,
    payload: ReceiveRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.order.receive")),
):
    po = await svc.receive_purchase_order(
        db, po_id, [r.model_dump() for r in payload.receipts], user.raw_user,
    )
    return PurchaseOrderResponse.model_validate(po)


# ─── v3.10 PATCH/DELETE/Cancel ────────────────────────────

from pydantic import BaseModel as _BM


class SupplierUpdate(_BM):
    name: Optional[str] = None
    tier: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: Optional[int] = None
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None


class CancelRequest(_BM):
    reason: str = ""


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier_endpoint(
    supplier_id: str,
    data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.supplier.update")),
):
    patch = data.model_dump(exclude_unset=True)
    s = await svc.update_supplier(db, supplier_id, patch, user=user.raw_user)
    return SupplierResponse.model_validate(s)


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier_endpoint(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.supplier.update")),
):
    return await svc.delete_supplier(db, supplier_id, user=user.raw_user)


@router.post("/orders/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_po_endpoint(
    po_id: str,
    data: Optional[CancelRequest] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.po.update")),
):
    po = await svc.cancel_purchase_order(
        db, po_id, user=user.raw_user, reason=(data.reason if data else ""),
    )
    return PurchaseOrderResponse.model_validate(po)


# v3.22: 單據備註
class POPatchRequest(_BM):
    remark: Optional[str] = None


@router.patch("/orders/{po_id}", response_model=PurchaseOrderResponse)
async def patch_po_endpoint(
    po_id: str,
    data: POPatchRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.po.update")),
):
    """PATCH PO（目前只支援 remark / notes）。"""
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        from fastapi import HTTPException
        raise HTTPException(404, "採購單不存在")
    if data.remark is not None:
        po.remark = data.remark
    await db.commit()
    await db.refresh(po, attribute_names=["supplier"])
    return PurchaseOrderResponse.model_validate(po)


# ═══════════════════════════════════════════════════════════
# v3.63 M3 — 請購單（PR）+ 收料單（GRN）
# ═══════════════════════════════════════════════════════════

@router.post("/requisitions")
async def create_pr_endpoint(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.pr.create")),
):
    from app.services.m3_documents import create_purchase_requisition
    pr = await create_purchase_requisition(db, data, {"employee_id": user.employee_id})
    return {"id": pr.id, "pr_no": pr.pr_no, "status": pr.status}


@router.post("/requisitions/{pr_id}/approve")
async def approve_pr_endpoint(
    pr_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.pr.approve")),
):
    from app.services.m3_documents import approve_purchase_requisition
    pr = await approve_purchase_requisition(db, pr_id)
    return {"id": pr.id, "pr_no": pr.pr_no, "status": pr.status}


@router.post("/requisitions/{pr_id}/convert")
async def convert_pr_endpoint(
    pr_id: str,
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.pr.convert")),
):
    from app.services.m3_documents import convert_pr_to_po
    po = await convert_pr_to_po(db, pr_id, supplier_id, {"employee_id": user.employee_id})
    return {"po_id": po.id, "po_no": po.po_no, "status": po.status}


@router.post("/grns")
async def create_grn_endpoint(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.grn.create")),
):
    from app.services.m3_documents import create_grn
    grn = await create_grn(
        db, data["po_id"], data.get("receipts", []),
        {"employee_id": user.employee_id},
    )
    return {"id": grn.id, "grn_no": grn.grn_no, "status": grn.status}


@router.get("/grns")
async def list_grns_endpoint(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.grn.read")),
):
    from app.services.m3_documents import list_grns
    return await list_grns(db)


# ─── v3.64 RFQ 詢價比價 ─────────────────────────────────────

@router.post("/rfqs")
async def create_rfq_endpoint(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.rfq.create")),
):
    from app.services.rfq import create_rfq
    rfq = await create_rfq(db, data, {"employee_id": user.employee_id})
    return {"id": rfq.id, "rfq_no": rfq.rfq_no, "status": rfq.status}


@router.get("/rfqs")
async def list_rfqs_endpoint(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.rfq.read")),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.rfq import RFQ
    rows = (await db.execute(
        select(RFQ).options(selectinload(RFQ.quotes), selectinload(RFQ.items))
        .order_by(RFQ.created_at.desc()).limit(100)
    )).scalars().all()
    return [
        {"id": r.id, "rfq_no": r.rfq_no, "status": r.status,
         "need_date": r.need_date.isoformat() if r.need_date else None,
         "quote_count": len(r.quotes),
         "items": [
             {"part_id": it.part_id, "qty": it.qty, "line_no": it.line_no}
             for it in r.items
         ]}
        for r in rows
    ]


@router.post("/rfqs/{rfq_id}/send")
async def send_rfq_endpoint(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.rfq.create")),
):
    from app.services.rfq import send_rfq
    rfq = await send_rfq(db, rfq_id)
    return {"id": rfq.id, "rfq_no": rfq.rfq_no, "status": rfq.status}


@router.post("/rfqs/{rfq_id}/quotes")
async def receive_quote_endpoint(
    rfq_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.rfq.create")),
):
    from app.services.rfq import receive_quote
    quote = await receive_quote(db, {**data, "rfq_id": rfq_id},
                                {"employee_id": user.employee_id})
    return {"id": quote.id, "amount": quote.amount, "status": quote.status}


@router.get("/rfqs/{rfq_id}/compare")
async def compare_rfq_endpoint(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.rfq.read")),
):
    from app.services.rfq import compare_quotes
    return await compare_quotes(db, rfq_id)


@router.post("/rfqs/{rfq_id}/award")
async def award_rfq_endpoint(
    rfq_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.rfq.award")),
):
    from app.services.rfq import award_rfq
    return await award_rfq(db, rfq_id, data["quote_id"],
                           {"employee_id": user.employee_id})

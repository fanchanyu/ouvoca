"""Purchase API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_db
from sqlalchemy import select
from sqlalchemy.orm import joinedload
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
    q = select(PurchaseOrder).options(joinedload(PurchaseOrder.supplier))
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

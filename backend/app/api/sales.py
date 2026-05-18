"""Sales API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.core.deps import get_db
from app.core.security import require_permission, UserContext, apply_row_filter, apply_tenant_filter
from app.models.crm_sales import SalesOrder, Customer
from app.schemas.sales import (
    CustomerCreate, CustomerResponse,
    SalesOrderCreate, SalesOrderResponse,
)
from app.services import sales as svc

router = APIRouter(prefix="/api/sales", tags=["Sales"])


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.customer.create")),
):
    c = await svc.create_customer(db, data.model_dump())
    return CustomerResponse.model_validate(c)


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    grade: Optional[str] = None,
    keyword: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.customer.list")),
):
    # 第一道：tenant 隔離（多租戶 SaaS 命脈）
    # 第二道：Row-level scope（依使用者 scope own/tenant/all）
    q = select(Customer)
    q = apply_tenant_filter(q, Customer, user)
    q = apply_row_filter(q, user, "sales.customer")
    if grade: q = q.where(Customer.grade == grade)
    if keyword:
        like = f"%{keyword}%"
        q = q.where((Customer.name.like(like)) | (Customer.code.like(like)))
    q = q.offset(skip).limit(limit).order_by(Customer.code)
    rows = (await db.execute(q)).scalars().all()
    return [CustomerResponse.model_validate(r) for r in rows]


@router.post("/orders", response_model=SalesOrderResponse)
async def create_so(
    data: SalesOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.create")),
):
    so = await svc.create_sales_order(db, data.model_dump(), user=user.raw_user)
    return SalesOrderResponse.model_validate(so)


@router.get("/orders", response_model=List[SalesOrderResponse])
async def list_so(
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.list")),
):
    q = select(SalesOrder).options(joinedload(SalesOrder.customer))
    q = apply_row_filter(q, user, "sales.order")
    if status: q = q.where(SalesOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(SalesOrder.created_at.desc())
    rows = (await db.execute(q)).unique().scalars().all()
    return [SalesOrderResponse.model_validate(r) for r in rows]


@router.get("/orders/{so_id}", response_model=SalesOrderResponse)
async def get_so(
    so_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.read")),
):
    so = await svc.get_sales_order(db, so_id)
    if not so:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("銷售訂單不存在", so_id=so_id)
    return SalesOrderResponse.model_validate(so)


@router.post("/orders/{so_id}/confirm", response_model=SalesOrderResponse)
async def confirm_so(
    so_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.confirm")),
):
    so = await svc.confirm_sales_order(db, so_id, user.raw_user)
    return SalesOrderResponse.model_validate(so)


@router.post("/orders/{so_id}/ship", response_model=SalesOrderResponse)
async def ship_so(
    so_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.ship")),
):
    so = await svc.ship_sales_order(db, so_id, user.raw_user)
    return SalesOrderResponse.model_validate(so)


# ─── v3.10 PATCH/DELETE/Cancel ────────────────────────────

from pydantic import BaseModel as _BMs


class CustomerUpdate(_BMs):
    name: Optional[str] = None
    grade: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: Optional[float] = None
    is_active: Optional[bool] = None


class SOCancelRequest(_BMs):
    reason: str = ""


@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer_endpoint(
    customer_id: str,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.customer.update")),
):
    patch = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    c = await svc.update_customer(db, customer_id, patch, user=user.raw_user)
    return CustomerResponse.model_validate(c)


@router.delete("/customers/{customer_id}")
async def delete_customer_endpoint(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.customer.update")),
):
    return await svc.delete_customer(db, customer_id, user=user.raw_user)


@router.post("/orders/{so_id}/cancel", response_model=SalesOrderResponse)
async def cancel_so_endpoint(
    so_id: str,
    data: Optional[SOCancelRequest] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.update")),
):
    so = await svc.cancel_sales_order(
        db, so_id, user=user.raw_user, reason=(data.reason if data else ""),
    )
    return SalesOrderResponse.model_validate(so)


# v3.22: 單據備註
class SOPatchRequest(_BMs):
    remark: Optional[str] = None


@router.patch("/orders/{so_id}", response_model=SalesOrderResponse)
async def patch_so_endpoint(
    so_id: str,
    data: SOPatchRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.update")),
):
    """PATCH SO（目前只支援 remark / notes）。"""
    so = (await db.execute(select(SalesOrder).where(SalesOrder.id == so_id))).scalar_one_or_none()
    if not so:
        from fastapi import HTTPException
        raise HTTPException(404, "銷售訂單不存在")
    if data.remark is not None:
        so.remark = data.remark
    await db.commit()
    await db.refresh(so, attribute_names=["customer"])
    return SalesOrderResponse.model_validate(so)

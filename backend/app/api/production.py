"""Production API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.schemas.production import (
    ProductCreate, ProductResponse, BOMItemCreate, BOMItemResponse,
    ProductionOrderCreate, ProductionOrderResponse, WorkCenterCreate,
    OperationCreate, DispatchLogCreate,
)
from app.services import production as svc

router = APIRouter(prefix="/api/production", tags=["Production"])


@router.post("/products", response_model=ProductResponse)
async def create_product_endpoint(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.product.create")),
):
    p = await svc.create_product(db, data.model_dump())
    return ProductResponse.model_validate(p)


@router.get("/products", response_model=List[ProductResponse])
async def list_products_endpoint(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.product.list")),
):
    rows = await svc.list_products(db, skip, limit)
    return [ProductResponse.model_validate(p) for p in rows]


@router.post("/bom-items", response_model=BOMItemResponse)
async def add_bom_item_endpoint(
    data: BOMItemCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.bom.create")),
):
    item = await svc.add_bom_item(db, data.model_dump())
    return BOMItemResponse.model_validate(item)


@router.get("/bom/{product_id}", response_model=List[BOMItemResponse])
async def get_bom_endpoint(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.bom.read")),
):
    items = await svc.get_bom_tree(db, product_id)
    return [BOMItemResponse.model_validate(i) for i in items]


@router.post("/work-orders", response_model=ProductionOrderResponse)
async def create_wo_endpoint(
    data: ProductionOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.work_order.create")),
):
    wo = await svc.create_production_order(db, data.model_dump(), user=user.raw_user)
    return ProductionOrderResponse.model_validate(wo)


@router.post("/work-orders/{wo_id}/release", response_model=ProductionOrderResponse)
async def release_wo_endpoint(
    wo_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.work_order.release")),
):
    wo = await svc.release_production_order(db, wo_id, user=user.raw_user)
    return ProductionOrderResponse.model_validate(wo)


class CompleteWORequest(BaseModel):
    completed_qty: float


@router.post("/work-orders/{wo_id}/complete", response_model=ProductionOrderResponse)
async def complete_wo_endpoint(
    wo_id: str,
    payload: CompleteWORequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.work_order.complete")),
):
    wo = await svc.complete_production_order(db, wo_id, payload.completed_qty, user=user.raw_user)
    return ProductionOrderResponse.model_validate(wo)


@router.get("/work-orders", response_model=List[ProductionOrderResponse])
async def list_wo_endpoint(
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.work_order.list")),
):
    rows = await svc.list_production_orders(db, status, skip, limit)
    return [ProductionOrderResponse.model_validate(r) for r in rows]


@router.post("/work-centers")
async def create_work_center_endpoint(
    data: WorkCenterCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.work_center.create")),
):
    wc = await svc.create_work_center(db, data.model_dump())
    return {"id": wc.id, "code": wc.code, "name": wc.name}


@router.get("/work-centers")
async def list_work_centers_endpoint(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.work_center.list")),
):
    return [
        {"id": wc.id, "code": wc.code, "name": wc.name,
         "capacity_per_day": wc.capacity_per_day, "is_active": wc.is_active}
        for wc in await svc.list_work_centers(db)
    ]


@router.post("/operations")
async def create_operation_endpoint(
    data: OperationCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.operation.create")),
):
    op = await svc.create_operation(db, data.model_dump())
    return {"id": op.id, "op_no": op.op_no, "op_name": op.op_name}


@router.post("/dispatch-logs")
async def create_dispatch_log_endpoint(
    data: DispatchLogCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.dispatch.create")),
):
    log = await svc.create_dispatch_log(db, data.model_dump(), user=user.raw_user)
    return {"id": log.id, "status": log.status}


# ─── v3.10 Cancel WO ────────────────────────────────────

from pydantic import BaseModel as _BMp


class WOCancelRequest(_BMp):
    reason: str = ""


@router.post("/work-orders/{wo_id}/cancel", response_model=ProductionOrderResponse)
async def cancel_wo_endpoint(
    wo_id: str,
    data: Optional[WOCancelRequest] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("production.work_order.update")),
):
    wo = await svc.cancel_production_order(
        db, wo_id, user=user.raw_user, reason=(data.reason if data else ""),
    )
    return ProductionOrderResponse.model_validate(wo)

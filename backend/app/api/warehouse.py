"""Warehouse API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.schemas.warehouse import (
    WarehouseZoneCreate, WarehouseZoneResponse,
    BinLocationCreate, BinLocationResponse,
    PickTaskCreate, PickTaskResponse,
    CycleCountCreate,
)
from app.services import warehouse as svc

router = APIRouter(prefix="/api/warehouse", tags=["Warehouse"])


@router.post("/zones", response_model=WarehouseZoneResponse)
async def create_zone(
    data: WarehouseZoneCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.zone.list")),
):
    z = await svc.create_zone(db, data.model_dump())
    return WarehouseZoneResponse.model_validate(z)


@router.get("/zones", response_model=List[WarehouseZoneResponse])
async def list_zones(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.zone.list")),
):
    return [WarehouseZoneResponse.model_validate(z) for z in await svc.list_zones(db)]


@router.post("/bins", response_model=BinLocationResponse)
async def create_bin(
    data: BinLocationCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.bin.list")),
):
    b = await svc.create_bin(db, data.model_dump())
    return BinLocationResponse.model_validate(b)


@router.get("/bins", response_model=List[BinLocationResponse])
async def list_bins(
    zone_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.bin.list")),
):
    return [BinLocationResponse.model_validate(b) for b in await svc.list_bins(db, zone_id)]


@router.post("/pick-tasks", response_model=PickTaskResponse)
async def create_pick(
    data: PickTaskCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.pick.create")),
):
    t = await svc.create_pick_task(db, data.model_dump(), user=user.raw_user)
    return PickTaskResponse.model_validate(t)


@router.get("/pick-tasks", response_model=List[PickTaskResponse])
async def list_pick(
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.pick.create")),
):
    rows = await svc.list_pick_tasks(db, status, skip, limit)
    return [PickTaskResponse.model_validate(r) for r in rows]


class PickCompleteRequest(BaseModel):
    picked_qty: float


@router.post("/pick-tasks/{pick_id}/complete", response_model=PickTaskResponse)
async def complete_pick(
    pick_id: str,
    payload: PickCompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.pick.create")),
):
    t = await svc.complete_pick(db, pick_id, payload.picked_qty, user.raw_user)
    return PickTaskResponse.model_validate(t)


@router.post("/cycle-counts")
async def create_cc(
    data: CycleCountCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("warehouse.cycle_count.create")),
):
    cc = await svc.create_cycle_count(db, data.model_dump(), user=user.raw_user)
    return {"id": cc.id, "count_no": cc.count_no, "variance": cc.variance}

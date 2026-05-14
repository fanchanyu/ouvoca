"""MPS / MRP API — 全 endpoint RBAC 保護版。"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.core.exceptions import NotFoundError
from app.schemas.mps_mrp import MpsMasterCreate, MpsEntryCreate
from app.services import mps_mrp as svc

router = APIRouter(prefix="/api/mps-mrp", tags=["MPS / MRP"])


class MpsMasterResponse(BaseModel):
    id: str; mps_name: str
    horizon_start: datetime; horizon_end: datetime
    bucket: str; status: str; created_at: datetime
    class Config: from_attributes = True


class MpsEntryResponse(BaseModel):
    id: str; product_id: str; period: str
    forecast_demand: float; actual_demand: float
    planned_production: float; projected_on_hand: float
    available_to_promise: float
    class Config: from_attributes = True


class MrpMasterResponse(BaseModel):
    id: str; mps_master_id: str; mrp_name: str; status: str
    generated_at: Optional[datetime] = None
    class Config: from_attributes = True


class MrpItemResponse(BaseModel):
    id: str; part_id: str; period: str; bom_level: int; order_type: str
    gross_requirement: float; projected_on_hand: float
    net_requirement: float; planned_order_release: float
    class Config: from_attributes = True


@router.post("/mps", response_model=MpsMasterResponse)
async def create_mps(
    data: MpsMasterCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("mps_mrp.mps.create")),
):
    m = await svc.create_mps(db, data.model_dump(), user=user.raw_user)
    return MpsMasterResponse.model_validate(m)


@router.get("/mps", response_model=List[MpsMasterResponse])
async def list_mps(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("mps_mrp.mps.read")),
):
    rows = await svc.list_mps(db)
    return [MpsMasterResponse.model_validate(r) for r in rows]


@router.post("/mps/entries", response_model=MpsEntryResponse)
async def create_entry(
    data: MpsEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("mps_mrp.mps.create")),
):
    e = await svc.add_mps_entry(db, data.model_dump())
    return MpsEntryResponse.model_validate(e)


@router.post("/mrp/run/{mps_id}", response_model=MrpMasterResponse)
async def run_mrp(
    mps_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("mps_mrp.mrp.run")),
):
    m = await svc.run_mrp(db, mps_id, user=user.raw_user)
    return MrpMasterResponse.model_validate(m)


@router.get("/mrp", response_model=List[MrpMasterResponse])
async def list_mrp(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("mps_mrp.mrp.read")),
):
    rows = await svc.list_mrp(db)
    return [MrpMasterResponse.model_validate(r) for r in rows]


@router.get("/mrp/{mrp_id}/items", response_model=List[MrpItemResponse])
async def mrp_items(
    mrp_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("mps_mrp.mrp.read")),
):
    mrp = await svc.get_mrp(db, mrp_id)
    if not mrp:
        raise NotFoundError("MRP 不存在", mrp_id=mrp_id)
    return [MrpItemResponse.model_validate(i) for i in mrp.items]

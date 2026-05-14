"""Quality API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.schemas.quality import (
    InspectionCreate, InspectionResponse, InspectionCompleteRequest,
    NonConformanceResponse, CAPACreate, CAPAResponse,
)
from app.services import quality as svc

router = APIRouter(prefix="/api/quality", tags=["Quality"])


@router.post("/inspections", response_model=InspectionResponse)
async def create_inspection(
    data: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("quality.inspection.create")),
):
    i = await svc.create_inspection(db, data.model_dump(), user=user.raw_user)
    return InspectionResponse.model_validate(i)


@router.get("/inspections", response_model=List[InspectionResponse])
async def list_inspections(
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("quality.inspection.list")),
):
    rows = await svc.list_inspections(db, status, skip, limit)
    return [InspectionResponse.model_validate(r) for r in rows]


@router.post("/inspections/{inspection_id}/complete", response_model=InspectionResponse)
async def complete_inspection(
    inspection_id: str,
    payload: InspectionCompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("quality.inspection.complete")),
):
    i = await svc.complete_inspection(
        db, inspection_id, payload.accepted_qty, payload.rejected_qty, user=user.raw_user,
    )
    return InspectionResponse.model_validate(i)


@router.get("/non-conformances", response_model=List[NonConformanceResponse])
async def list_nc(
    severity: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("quality.nc.list")),
):
    rows = await svc.list_non_conformances(db, severity, skip, limit)
    return [NonConformanceResponse.model_validate(r) for r in rows]


@router.post("/capa", response_model=CAPAResponse)
async def create_capa(
    data: CAPACreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("quality.capa.create")),
):
    c = await svc.create_capa(db, data.model_dump(), user=user.raw_user)
    return CAPAResponse.model_validate(c)

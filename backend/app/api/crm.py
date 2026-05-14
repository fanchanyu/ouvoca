"""CRM API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.schemas.crm import (
    LeadCreate, LeadResponse,
    OpportunityCreate, OpportunityResponse,
    CrmEventCreate, CrmEventResponse,
)
from app.schemas.sales import CustomerCreate, CustomerResponse
from app.services import crm as svc

router = APIRouter(prefix="/api/crm", tags=["CRM"])


@router.post("/leads", response_model=LeadResponse)
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.lead.create")),
):
    l = await svc.create_lead(db, data.model_dump(), user=user.raw_user)
    return LeadResponse.model_validate(l)


@router.get("/leads", response_model=List[LeadResponse])
async def list_leads(
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.lead.read")),
):
    rows = await svc.list_leads(db, status, limit)
    return [LeadResponse.model_validate(r) for r in rows]


class LeadConvertRequest(BaseModel):
    customer: CustomerCreate


@router.post("/leads/{lead_id}/convert", response_model=CustomerResponse)
async def convert_lead(
    lead_id: str,
    payload: LeadConvertRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.lead.create")),
):
    c = await svc.convert_lead(db, lead_id, payload.customer.model_dump(), user.raw_user)
    return CustomerResponse.model_validate(c)


@router.post("/opportunities", response_model=OpportunityResponse)
async def create_opp(
    data: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.opportunity.create")),
):
    o = await svc.create_opportunity(db, data.model_dump(), user=user.raw_user)
    return OpportunityResponse.model_validate(o)


@router.get("/opportunities", response_model=List[OpportunityResponse])
async def list_opps(
    stage: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.opportunity.read")),
):
    rows = await svc.list_opportunities(db, stage, limit)
    return [OpportunityResponse.model_validate(r) for r in rows]


class OpportunityStageRequest(BaseModel):
    stage: str


@router.post("/opportunities/{opp_id}/stage", response_model=OpportunityResponse)
async def update_stage(
    opp_id: str,
    payload: OpportunityStageRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.opportunity.change_stage")),
):
    o = await svc.update_opportunity_stage(db, opp_id, payload.stage, user.raw_user)
    return OpportunityResponse.model_validate(o)


@router.post("/events", response_model=CrmEventResponse)
async def create_event(
    data: CrmEventCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.opportunity.read")),
):
    e = await svc.create_crm_event(db, data.model_dump(), user=user.raw_user)
    return CrmEventResponse.model_validate(e)


@router.get("/events", response_model=List[CrmEventResponse])
async def list_events(
    customer_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("crm.opportunity.read")),
):
    rows = await svc.list_crm_events(db, customer_id, limit)
    return [CrmEventResponse.model_validate(r) for r in rows]

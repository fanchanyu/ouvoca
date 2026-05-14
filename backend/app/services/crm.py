"""CRM service — Lead / Opportunity / Contract / CrmEvent."""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_sales import Lead, Opportunity, Contract, ContractPricing, CrmEvent, Customer
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError


async def create_lead(db: AsyncSession, data: dict, user: Optional[dict] = None) -> Lead:
    lead = Lead(id=str(uuid.uuid4()), assigned_to=(user or {}).get("employee_id"), **data)
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def convert_lead(db: AsyncSession, lead_id: str, customer_data: dict, user: dict) -> Customer:
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise NotFoundError("潛在客戶不存在", lead_id=lead_id)
    customer = Customer(
        id=str(uuid.uuid4()),
        **customer_data,
    )
    db.add(customer)
    lead.converted_to_customer_id = customer.id
    lead.status = "converted"
    await db.commit()
    await db.refresh(customer)
    await EventBus.emit(DomainEvent(
        name="lead.converted", domain="crm",
        entity_type="Lead", entity_id=lead_id,
        data={"customer_id": customer.id, "customer_name": customer.name},
    ))
    return customer


async def list_leads(db: AsyncSession, status: Optional[str] = None, limit: int = 100) -> List[Lead]:
    q = select(Lead)
    if status:
        q = q.where(Lead.status == status)
    return list((await db.execute(q.limit(limit).order_by(Lead.created_at.desc()))).scalars().all())


async def create_opportunity(db: AsyncSession, data: dict, user: Optional[dict] = None) -> Opportunity:
    opp = Opportunity(id=str(uuid.uuid4()), assigned_to=(user or {}).get("employee_id"), **data)
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


async def update_opportunity_stage(db: AsyncSession, opp_id: str, stage: str, user: dict) -> Opportunity:
    opp = (await db.execute(select(Opportunity).where(Opportunity.id == opp_id))).scalar_one_or_none()
    if not opp:
        raise NotFoundError("商機不存在", opp_id=opp_id)
    opp.stage = stage
    if stage in ("won", "lost"):
        opp.status = "closed"
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="opportunity.stage_changed", domain="crm",
        entity_type="Opportunity", entity_id=opp.id,
        data={"opp_id": opp.id, "stage": stage, "amount": opp.amount},
    ))
    return opp


async def list_opportunities(db: AsyncSession, stage: Optional[str] = None, limit: int = 100) -> List[Opportunity]:
    q = select(Opportunity)
    if stage:
        q = q.where(Opportunity.stage == stage)
    return list((await db.execute(q.limit(limit).order_by(Opportunity.expected_close_date))).scalars().all())


async def create_crm_event(db: AsyncSession, data: dict, user: Optional[dict] = None) -> CrmEvent:
    e = CrmEvent(id=str(uuid.uuid4()), created_by=(user or {}).get("employee_id"), **data)
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return e


async def list_crm_events(db: AsyncSession, customer_id: Optional[str] = None,
                          limit: int = 100) -> List[CrmEvent]:
    q = select(CrmEvent)
    if customer_id:
        q = q.where(CrmEvent.customer_id == customer_id)
    return list((await db.execute(q.limit(limit).order_by(CrmEvent.created_at.desc()))).scalars().all())

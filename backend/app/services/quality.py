"""Quality service — Inspection / Non-conformance / CAPA."""
import uuid
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quality import InspectionOrder, InspectionResult, NonConformance, CAPARecord
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


async def create_inspection(db: AsyncSession, data: dict, user: Optional[dict] = None) -> InspectionOrder:
    insp = InspectionOrder(
        id=str(uuid.uuid4()),
        inspection_no=f"INSP-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
        inspector_id=(user or {}).get("employee_id"),
        **data,
    )
    db.add(insp)
    await db.commit()
    await db.refresh(insp)
    await EventBus.emit(DomainEvent(
        name="inspection.created", domain="quality",
        entity_type="InspectionOrder", entity_id=insp.id,
        data={"inspection_no": insp.inspection_no, "part_id": insp.part_id},
    ))
    return insp


async def complete_inspection(db: AsyncSession, inspection_id: str,
                              accepted_qty: float, rejected_qty: float,
                              user: dict) -> InspectionOrder:
    insp = (await db.execute(
        select(InspectionOrder).where(InspectionOrder.id == inspection_id)
    )).scalar_one_or_none()
    if not insp:
        raise NotFoundError("檢驗單不存在", inspection_id=inspection_id)
    insp.accepted_qty = accepted_qty
    insp.rejected_qty = rejected_qty
    insp.inspected_qty = accepted_qty + rejected_qty
    insp.status = "completed" if rejected_qty == 0 else "rejected"
    insp.inspected_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="quality.inspected", domain="quality",
        entity_type="InspectionOrder", entity_id=insp.id,
        data={"inspection_no": insp.inspection_no, "accepted": accepted_qty,
              "rejected": rejected_qty, "status": insp.status},
    ))
    if rejected_qty > 0:
        # Auto-create NC
        nc = NonConformance(
            id=str(uuid.uuid4()),
            nc_no=f"NC-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
            inspection_order_id=insp.id,
            part_id=insp.part_id,
            severity="minor" if rejected_qty < insp.inspected_qty * 0.05 else "major",
            description=f"檢驗 {insp.inspection_no} 不良 {rejected_qty} PCS",
            qty_affected=rejected_qty,
            reported_by=user.get("employee_id"),
        )
        db.add(nc)
        await db.commit()
        await EventBus.emit(DomainEvent(
            name="nc.created", domain="quality",
            entity_type="NonConformance", entity_id=nc.id,
            data={"nc_no": nc.nc_no, "part_id": nc.part_id, "severity": nc.severity},
        ))
    return insp


async def list_inspections(db: AsyncSession, status: Optional[str] = None,
                           skip: int = 0, limit: int = 100) -> List[InspectionOrder]:
    q = select(InspectionOrder)
    if status:
        q = q.where(InspectionOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(InspectionOrder.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def list_non_conformances(db: AsyncSession, severity: Optional[str] = None,
                                skip: int = 0, limit: int = 100) -> List[NonConformance]:
    q = select(NonConformance)
    if severity:
        q = q.where(NonConformance.severity == severity)
    q = q.offset(skip).limit(limit).order_by(NonConformance.reported_at.desc())
    return list((await db.execute(q)).scalars().all())


async def create_capa(db: AsyncSession, data: dict, user: Optional[dict] = None) -> CAPARecord:
    capa = CAPARecord(id=str(uuid.uuid4()), **data)
    db.add(capa)
    await db.commit()
    await db.refresh(capa)
    await EventBus.emit(DomainEvent(
        name="capa.created", domain="quality",
        entity_type="CAPARecord", entity_id=capa.id,
        data={"nc_id": capa.nc_id, "type": capa.capa_type, "assigned_to": capa.assigned_to},
    ))
    return capa

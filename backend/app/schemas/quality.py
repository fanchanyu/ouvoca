from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class InspectionCreate(BaseModel):
    po_id: Optional[str] = None
    part_id: str
    sampling_plan: Optional[str] = None


class InspectionResponse(BaseModel):
    id: str
    inspection_no: str
    part_id: str
    inspected_qty: float
    accepted_qty: float
    rejected_qty: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class InspectionCompleteRequest(BaseModel):
    accepted_qty: float
    rejected_qty: float


class NonConformanceResponse(BaseModel):
    id: str
    nc_no: str
    part_id: str
    severity: str
    description: str
    qty_affected: float
    disposition: str
    reported_at: datetime

    class Config:
        from_attributes = True


class CAPACreate(BaseModel):
    nc_id: str
    capa_type: str = "corrective"
    description: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class CAPAResponse(BaseModel):
    id: str
    nc_id: str
    capa_type: str
    description: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

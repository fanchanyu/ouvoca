from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LeadCreate(BaseModel):
    company_name: str
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None


class LeadResponse(BaseModel):
    id: str
    company_name: str
    contact_person: Optional[str] = None
    status: str
    converted_to_customer_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OpportunityCreate(BaseModel):
    customer_id: str
    name: str
    stage: str = "prospect"
    amount: float = 0
    probability: float = 0
    expected_close_date: Optional[datetime] = None


class OpportunityResponse(BaseModel):
    id: str
    customer_id: str
    name: str
    stage: str
    amount: float
    probability: float
    status: str

    class Config:
        from_attributes = True


class CrmEventCreate(BaseModel):
    customer_id: str
    event_type: str
    subject: str
    description: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


class CrmEventResponse(BaseModel):
    id: str
    customer_id: str
    event_type: str
    subject: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

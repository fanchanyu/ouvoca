from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str
    parent_id: Optional[str] = None
    is_debit_normal: bool = True


class AccountResponse(BaseModel):
    id: str
    code: str
    name: str
    account_type: str
    is_debit_normal: bool
    is_active: bool

    class Config:
        from_attributes = True


class JournalLineCreate(BaseModel):
    account_id: str
    debit: float = 0
    credit: float = 0
    description: Optional[str] = None
    reference: Optional[str] = None


class JournalEntryCreate(BaseModel):
    entry_date: Optional[datetime] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    description: Optional[str] = None
    period: Optional[str] = None
    lines: List[JournalLineCreate]


class JournalLineResponse(BaseModel):
    id: str
    account_id: str
    line_no: int
    debit: float
    credit: float
    description: Optional[str] = None

    class Config:
        from_attributes = True


class JournalEntryResponse(BaseModel):
    id: str
    entry_no: str
    entry_date: datetime
    period: Optional[str] = None
    status: str
    description: Optional[str] = None
    lines: List[JournalLineResponse] = []

    class Config:
        from_attributes = True


class ARCreate(BaseModel):
    customer_id: str
    invoice_no: str
    invoice_date: datetime
    due_date: datetime
    amount: float


class ARResponse(BaseModel):
    id: str
    customer_id: str
    invoice_no: str
    invoice_date: datetime
    due_date: datetime
    amount: float
    paid_amount: float
    status: str
    aging_days: int

    class Config:
        from_attributes = True

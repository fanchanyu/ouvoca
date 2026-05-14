from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class CustomerCreate(BaseModel):
    code: str
    name: str
    grade: str = "C"
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: float = 0


class CustomerResponse(BaseModel):
    id: str
    code: str
    name: str
    grade: str
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    credit_limit: float
    is_active: bool

    class Config:
        from_attributes = True


class SalesOrderItemCreate(BaseModel):
    product_id: str
    ordered_qty: float
    unit_price: float = 0
    expected_date: Optional[datetime] = None


class SalesOrderCreate(BaseModel):
    customer_id: str
    requested_delivery_date: Optional[datetime] = None
    currency: str = "TWD"
    items: List[SalesOrderItemCreate] = []
    remark: Optional[str] = None


class SalesOrderResponse(BaseModel):
    id: str
    so_no: str
    customer_id: str
    status: str
    total_amount: float
    order_date: datetime
    requested_delivery_date: Optional[datetime] = None
    payment_status: str
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True

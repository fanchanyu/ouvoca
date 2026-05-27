from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    grade: Literal["A", "B", "C", "D"] = "C"
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: float = Field(default=0, ge=0)


class CustomerResponse(BaseModel):
    id: str
    code: str
    name: str
    grade: str
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    # F-2：credit_limit 改 Optional，API 端對非財務角色會 strip 為 None
    credit_limit: Optional[float] = None
    is_active: bool

    class Config:
        from_attributes = True


class SalesOrderItemCreate(BaseModel):
    product_id: str
    ordered_qty: float = Field(..., gt=0)
    unit_price: float = Field(default=0, ge=0)
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

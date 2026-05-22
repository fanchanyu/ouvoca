from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SupplierCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1)
    tier: str = "T3"
    parent_supplier_id: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: int = 0

class SupplierResponse(BaseModel):
    id: str
    code: str
    name: str
    tier: str
    parent_supplier_id: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    is_approved: bool
    is_active: bool

    class Config:
        from_attributes = True


class PurchaseOrderItemCreate(BaseModel):
    part_id: str
    ordered_qty: float = Field(..., gt=0)
    unit_price: float = Field(default=0, ge=0)
    expected_date: Optional[datetime] = None

class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    expected_delivery_date: Optional[datetime] = None
    currency: str = "TWD"
    items: List[PurchaseOrderItemCreate] = []
    remark: Optional[str] = None

class POItemResponse(BaseModel):
    id: str
    line_no: int
    part_id: str
    ordered_qty: float
    received_qty: float
    unit_price: float
    expected_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class PurchaseOrderResponse(BaseModel):
    id: str
    po_no: str
    supplier_id: str
    status: str
    total_amount: float
    order_date: datetime
    created_at: datetime
    supplier: Optional[SupplierResponse] = None
    items: List[POItemResponse] = []  # 缺漏修補：客戶要看 line items

    class Config:
        from_attributes = True


class SupplierPriceCreate(BaseModel):
    supplier_id: str
    part_id: str
    unit_price: float = Field(..., gt=0)
    currency: str = "TWD"
    moq: float = 0
    lead_time_days: int = 0
    valid_from: datetime
    valid_to: Optional[datetime] = None


class SupplierEvaluationCreate(BaseModel):
    supplier_id: str
    period: str
    quality_score: float = 0
    delivery_score: float = 0
    price_score: float = 0
    service_score: float = 0

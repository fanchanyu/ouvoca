from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    product_no: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit: str = "pcs"
    selling_price: float = 0
    standard_cost: float = 0
    moq: float = 1
    lead_time_days: int = 0

class ProductResponse(BaseModel):
    id: str
    product_no: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit: str
    selling_price: float
    standard_cost: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BOMItemCreate(BaseModel):
    product_id: str
    part_id: str
    parent_bom_id: Optional[str] = None
    level: int = 0
    sequence_no: int = 0
    qty_per: float = 1
    scrap_rate: float = 0
    is_critical: bool = False

class BOMItemResponse(BaseModel):
    id: str
    product_id: str
    part_id: str
    level: int
    sequence_no: int
    qty_per: float
    scrap_rate: float
    is_active: bool

    class Config:
        from_attributes = True


class ProductionOrderCreate(BaseModel):
    product_id: str
    ordered_qty: float = Field(..., gt=0)
    so_id: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    priority: int = 5

class ProductionOrderResponse(BaseModel):
    id: str
    wo_no: str
    product_id: str
    so_id: Optional[str] = None
    ordered_qty: float
    completed_qty: float
    rejected_qty: float
    status: str
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class WorkCenterCreate(BaseModel):
    code: str
    name: str
    capacity_per_day: float = 0
    efficiency: float = 1.0
    alternate_group: Optional[str] = None
    hourly_rate: float = 0


class OperationCreate(BaseModel):
    production_order_id: str
    op_no: int
    op_name: str
    work_center_id: str
    operator_id: Optional[str] = None
    setup_time: float = 0
    run_time_per_unit: float = 0
    scheduled_qty: float = 0


class DispatchLogCreate(BaseModel):
    production_order_id: str
    operation_id: str
    operator_id: Optional[str] = None
    dispatched_qty: float = 0

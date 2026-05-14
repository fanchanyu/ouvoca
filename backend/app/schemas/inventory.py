from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PartCreate(BaseModel):
    part_no: str
    name: str
    description: Optional[str] = None
    category: str = "raw_material"
    unit: str = "pcs"
    specification: Optional[str] = None
    drawing_no: Optional[str] = None
    min_stock: float = 0
    max_stock: float = 0
    safety_stock: float = 0
    lead_time_days: int = 0
    unit_cost: float = 0
    is_critical: bool = False

class PartUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    min_stock: Optional[float] = None
    max_stock: Optional[float] = None
    safety_stock: Optional[float] = None
    lead_time_days: Optional[int] = None
    unit_cost: Optional[float] = None
    is_active: Optional[bool] = None
    is_critical: Optional[bool] = None

class PartResponse(BaseModel):
    id: str
    part_no: str
    name: str
    description: Optional[str] = None
    category: str
    unit: str
    min_stock: float
    max_stock: float
    safety_stock: float
    lead_time_days: int
    unit_cost: float
    is_active: bool
    is_critical: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryResponse(BaseModel):
    id: str
    part_id: str
    qty_on_hand: float
    qty_allocated: float
    qty_available: float
    qty_in_transit: float
    part: Optional[PartResponse] = None

    class Config:
        from_attributes = True


class InventoryTransactionCreate(BaseModel):
    part_id: str
    transaction_type: str
    qty: float
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    source_location: Optional[str] = None
    target_location: Optional[str] = None
    batch_no: Optional[str] = None
    lot_no: Optional[str] = None
    remark: Optional[str] = None

class InventoryTransactionResponse(BaseModel):
    id: str
    part_id: str
    transaction_type: str
    qty: float
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    batch_no: Optional[str] = None
    created_at: datetime
    part: Optional[PartResponse] = None

    class Config:
        from_attributes = True


class InventoryTransferCreate(BaseModel):
    part_id: str
    qty: float
    source_warehouse: Optional[str] = None
    source_bin: Optional[str] = None
    target_warehouse: Optional[str] = None
    target_bin: Optional[str] = None

class InventoryTransferResponse(BaseModel):
    id: str
    transfer_no: str
    part_id: str
    qty: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

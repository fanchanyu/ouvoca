from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WarehouseZoneCreate(BaseModel):
    code: str
    name: str
    zone_type: Optional[str] = None


class WarehouseZoneResponse(BaseModel):
    id: str
    code: str
    name: str
    zone_type: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class BinLocationCreate(BaseModel):
    zone_id: str
    aisle: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    bin_code: str
    part_id: Optional[str] = None
    capacity: float = 0


class BinLocationResponse(BaseModel):
    id: str
    zone_id: str
    bin_code: str
    aisle: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    qty: float
    capacity: float

    class Config:
        from_attributes = True


class PickTaskCreate(BaseModel):
    so_id: Optional[str] = None
    wo_id: Optional[str] = None
    part_id: str
    bin_location_id: str
    qty_to_pick: float


class PickTaskResponse(BaseModel):
    id: str
    pick_no: str
    part_id: str
    qty_to_pick: float
    qty_picked: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CycleCountCreate(BaseModel):
    part_id: str
    bin_location_id: str
    system_qty: float = 0
    counted_qty: float = 0

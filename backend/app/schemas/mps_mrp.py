from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MpsMasterCreate(BaseModel):
    mps_name: str
    horizon_start: datetime
    horizon_end: datetime
    bucket: str = "week"


class MpsEntryCreate(BaseModel):
    mps_master_id: str
    product_id: str
    period: str
    forecast_demand: float = 0
    actual_demand: float = 0
    planned_production: float = 0


class TimeFenceCreate(BaseModel):
    mps_master_id: str
    product_id: str
    dtf_days: int = 0
    ptf_days: int = 0


class MrpMasterCreate(BaseModel):
    mps_master_id: str
    mrp_name: str


class MrpItemCreate(BaseModel):
    mrp_master_id: str
    part_id: str
    bom_level: int = 0
    order_type: str = "make"
    period: str
    gross_requirement: float = 0
    scheduled_receipts: float = 0

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class WarehouseZone(Base, TenantMixin):
    __tablename__ = "warehouse_zones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    zone_type = Column(String(30))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bin_locations = relationship("BinLocation", back_populates="zone")


class BinLocation(Base, TenantMixin):
    __tablename__ = "bin_locations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id = Column(String(36), ForeignKey("warehouse_zones.id"), nullable=False)
    aisle = Column(String(10))
    rack = Column(String(10))
    shelf = Column(String(10))
    bin_code = Column(String(50), unique=True, nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=True)
    qty = Column(Float, default=0)
    capacity = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    zone = relationship("WarehouseZone", back_populates="bin_locations")
    part = relationship("Part")


class PickTask(Base, TenantMixin):
    __tablename__ = "pick_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pick_no = Column(String(50), unique=True, nullable=False)
    so_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=True)
    wo_id = Column(String(36), ForeignKey("production_orders.id"), nullable=True)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    bin_location_id = Column(String(36), ForeignKey("bin_locations.id"), nullable=False)
    qty_to_pick = Column(Float, nullable=False)
    qty_picked = Column(Float, default=0)
    status = Column(String(20), default="pending")
    assigned_to = Column(String(36), ForeignKey("employees.id"))
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    sales_order = relationship("SalesOrder")
    production_order = relationship("ProductionOrder")
    part = relationship("Part")
    bin_location = relationship("BinLocation")
    assignee = relationship("Employee")


class CycleCount(Base, TenantMixin):
    __tablename__ = "cycle_counts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    count_no = Column(String(50), unique=True, nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    bin_location_id = Column(String(36), ForeignKey("bin_locations.id"), nullable=False)
    system_qty = Column(Float, default=0)
    counted_qty = Column(Float, default=0)
    variance = Column(Float, default=0)
    status = Column(String(20), default="pending")
    counted_by = Column(String(36), ForeignKey("employees.id"))
    approved_by = Column(String(36), ForeignKey("employees.id"))
    counted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("Part")
    bin_location = relationship("BinLocation")
    counter = relationship("Employee", foreign_keys=[counted_by])
    approver = relationship("Employee", foreign_keys=[approved_by])

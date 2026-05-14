import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class MpsMaster(Base, TenantMixin):
    __tablename__ = "mps_masters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mps_name = Column(String(100), nullable=False)
    horizon_start = Column(DateTime, nullable=False)
    horizon_end = Column(DateTime, nullable=False)
    bucket = Column(String(10), default="week")
    status = Column(String(20), default="draft")
    created_by = Column(String(36), ForeignKey("employees.id"))
    approved_by = Column(String(36), ForeignKey("employees.id"))
    generated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    entries = relationship("MpsEntry", back_populates="mps_master", cascade="all, delete-orphan")
    time_fences = relationship("TimeFence", back_populates="mps_master", cascade="all, delete-orphan")
    creator = relationship("Employee", foreign_keys=[created_by])
    approver = relationship("Employee", foreign_keys=[approved_by])


class MpsEntry(Base):
    __tablename__ = "mps_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mps_master_id = Column(String(36), ForeignKey("mps_masters.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    period = Column(String(20), nullable=False)
    forecast_demand = Column(Float, default=0)
    actual_demand = Column(Float, default=0)
    planned_production = Column(Float, default=0)
    projected_on_hand = Column(Float, default=0)
    available_to_promise = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    mps_master = relationship("MpsMaster", back_populates="entries")
    product = relationship("Product")


class TimeFence(Base):
    __tablename__ = "time_fences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mps_master_id = Column(String(36), ForeignKey("mps_masters.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    dtf_days = Column(Integer, default=0)
    ptf_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    mps_master = relationship("MpsMaster", back_populates="time_fences")
    product = relationship("Product")


class MrpMaster(Base, TenantMixin):
    __tablename__ = "mrp_masters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mps_master_id = Column(String(36), ForeignKey("mps_masters.id"), nullable=False)
    mrp_name = Column(String(100), nullable=False)
    status = Column(String(20), default="draft")
    generated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    mps_master = relationship("MpsMaster")
    items = relationship("MrpItem", back_populates="mrp_master", cascade="all, delete-orphan")


class MrpItem(Base):
    __tablename__ = "mrp_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mrp_master_id = Column(String(36), ForeignKey("mrp_masters.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    bom_level = Column(Integer, default=0)
    order_type = Column(String(10), default="make")
    period = Column(String(20), nullable=False)
    gross_requirement = Column(Float, default=0)
    scheduled_receipts = Column(Float, default=0)
    projected_on_hand = Column(Float, default=0)
    net_requirement = Column(Float, default=0)
    planned_order_release = Column(Float, default=0)
    planned_order_receipt = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    mrp_master = relationship("MrpMaster", back_populates="items")
    part = relationship("Part")

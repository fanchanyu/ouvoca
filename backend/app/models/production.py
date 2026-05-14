import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class WorkCenter(Base, TenantMixin):
    __tablename__ = "work_centers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    capacity_per_day = Column(Float, default=0)
    efficiency = Column(Float, default=1.0)
    alternate_group = Column(String(50))
    hourly_rate = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    operations = relationship("Operation", back_populates="work_center")


class ProductionOrder(Base, TenantMixin):
    __tablename__ = "production_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wo_no = Column(String(50), unique=True, nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    so_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=True)
    ordered_qty = Column(Float, nullable=False)
    completed_qty = Column(Float, default=0)
    rejected_qty = Column(Float, default=0)
    status = Column(String(20), default="draft")
    scheduled_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    priority = Column(Integer, default=5)
    created_by = Column(String(36), ForeignKey("employees.id"))
    released_by = Column(String(36), ForeignKey("employees.id"))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="production_orders")
    sales_order = relationship("SalesOrder", back_populates="production_orders", foreign_keys=[so_id])
    operations = relationship("Operation", back_populates="production_order", cascade="all, delete-orphan")
    dispatch_logs = relationship("DispatchLog", back_populates="production_order")
    creator = relationship("Employee", foreign_keys=[created_by])
    releaser = relationship("Employee", foreign_keys=[released_by])


class Operation(Base):
    __tablename__ = "operations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    production_order_id = Column(String(36), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False)
    op_no = Column(Integer, nullable=False)
    op_name = Column(String(200), nullable=False)
    work_center_id = Column(String(36), ForeignKey("work_centers.id"), nullable=False)
    operator_id = Column(String(36), ForeignKey("employees.id"), nullable=True)
    setup_time = Column(Float, default=0)
    run_time_per_unit = Column(Float, default=0)
    scheduled_qty = Column(Float, default=0)
    completed_qty = Column(Float, default=0)
    rejected_qty = Column(Float, default=0)
    status = Column(String(20), default="pending")
    scheduled_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    production_order = relationship("ProductionOrder", back_populates="operations")
    work_center = relationship("WorkCenter", back_populates="operations")
    operator = relationship("Employee")
    dispatch_logs = relationship("DispatchLog", back_populates="operation")


class DispatchLog(Base):
    __tablename__ = "dispatch_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    production_order_id = Column(String(36), ForeignKey("production_orders.id"), nullable=False)
    operation_id = Column(String(36), ForeignKey("operations.id"), nullable=False)
    operator_id = Column(String(36), ForeignKey("employees.id"))
    dispatched_qty = Column(Float, default=0)
    completed_qty = Column(Float, default=0)
    status = Column(String(20), default="dispatched")
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    production_order = relationship("ProductionOrder", back_populates="dispatch_logs")
    operation = relationship("Operation", back_populates="dispatch_logs")
    operator = relationship("Employee")

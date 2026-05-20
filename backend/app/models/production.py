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


# ════════════════════════════════════════════════════════════════════
# v3.26 — Routing master template
# ────────────────────────────────────────────────────────────────────
# Routing = product-level template specifying which work centers + ops
# are required to make 1 unit. RoutingStep = template line item.
# WO Operation (existing) = instantiation of a step for a specific WO.
# Reference: Vollmann et al. (2005) §7; Pinedo (2016) §1.2.
# ════════════════════════════════════════════════════════════════════

class Routing(Base, TenantMixin):
    """Product-level routing master.

    A Product can have at most one **default** Routing (is_default=True).
    Multiple historical routings may co-exist for versioning purposes.

    Reference: Vollmann et al. (2005) Ch.7 "Routing data is the
    cornerstone of capacity planning."
    """
    __tablename__ = "routings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    routing_no = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=True)  # at most one default per product
    is_active = Column(Boolean, default=True)
    version = Column(String(20), default="1.0")  # forward-compat for ECO/ECN
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", foreign_keys=[product_id])
    steps = relationship("RoutingStep", back_populates="routing",
                         cascade="all, delete-orphan",
                         order_by="RoutingStep.sequence_no")


class RoutingStep(Base):
    """A single operation step in a Routing template.

    Operation time decomposition (Karmarkar 1987 *Mgmt Sci* 33):
        total_op_time = setup_time + (qty × run_time_per_unit)
                        + queue_time + move_time + wait_time

    For capacity-aware MRP, the capacity load contribution of producing
    qty Q at work-center k in a single batch is:
        load_k = setup_time + Q × run_time_per_unit
    (queue/move/wait are not capacity-loading, only lead-time-loading)
    """
    __tablename__ = "routing_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    routing_id = Column(String(36), ForeignKey("routings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    sequence_no = Column(Integer, nullable=False)
    op_name = Column(String(200), nullable=False)
    work_center_id = Column(String(36), ForeignKey("work_centers.id"), nullable=False)
    setup_time = Column(Float, default=0)  # minutes, fixed per batch
    run_time_per_unit = Column(Float, default=0)  # minutes per unit
    queue_time = Column(Float, default=0)  # minutes (informational, not capacity)
    move_time = Column(Float, default=0)
    is_critical = Column(Boolean, default=False)  # bottleneck candidate
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    routing = relationship("Routing", back_populates="steps")
    work_center = relationship("WorkCenter")

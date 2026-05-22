import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class InspectionOrder(Base, TenantMixin):
    __tablename__ = "inspection_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_no = Column(String(50), unique=True, nullable=False)
    po_id = Column(String(36), ForeignKey("purchase_orders.id"), nullable=True)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    inspected_qty = Column(Float, default=0)
    accepted_qty = Column(Float, default=0)
    rejected_qty = Column(Float, default=0)
    status = Column(String(20), default="pending")
    sampling_plan = Column(String(50))
    inspector_id = Column(String(36), ForeignKey("employees.id"))
    inspected_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    purchase_order = relationship("PurchaseOrder", back_populates="inspection_orders")
    part = relationship("Part", back_populates="inspection_orders")
    inspector = relationship("Employee")
    results = relationship("InspectionResult", back_populates="inspection_order", cascade="all, delete-orphan")
    non_conformances = relationship("NonConformance", back_populates="inspection_order")


class InspectionResult(Base):
    __tablename__ = "inspection_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_order_id = Column(String(36), ForeignKey("inspection_orders.id", ondelete="CASCADE"), nullable=False)
    characteristic = Column(String(200), nullable=False)
    specification = Column(String(200))
    measured_value = Column(String(100))
    result = Column(String(20), default="pass")
    measured_by = Column(String(36), ForeignKey("employees.id"))
    measured_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection_order = relationship("InspectionOrder", back_populates="results")
    measurer = relationship("Employee")


class NonConformance(Base, TenantMixin):
    __tablename__ = "non_conformances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nc_no = Column(String(50), unique=True, nullable=False)
    inspection_order_id = Column(String(36), ForeignKey("inspection_orders.id"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    severity = Column(String(20), default="minor")
    description = Column(Text, nullable=False)
    disposition = Column(String(30), default="pending")
    qty_affected = Column(Float, default=0)
    root_cause = Column(Text)
    reported_by = Column(String(36), ForeignKey("employees.id"))
    reported_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

    inspection_order = relationship("InspectionOrder", back_populates="non_conformances")
    part = relationship("Part", back_populates="non_conformances")
    reporter = relationship("Employee")
    capa_records = relationship("CAPARecord", back_populates="non_conformance")


class CAPARecord(Base, TenantMixin):
    __tablename__ = "capa_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nc_id = Column(String(36), ForeignKey("non_conformances.id"), nullable=False)
    capa_type = Column(String(20), default="corrective")
    description = Column(Text, nullable=False)
    assigned_to = Column(String(36), ForeignKey("employees.id"))
    due_date = Column(DateTime)
    status = Column(String(20), default="open")
    completed_at = Column(DateTime)
    verified_by = Column(String(36), ForeignKey("employees.id"))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    non_conformance = relationship("NonConformance", back_populates="capa_records")
    assignee = relationship("Employee", foreign_keys=[assigned_to])
    verifier = relationship("Employee", foreign_keys=[verified_by])

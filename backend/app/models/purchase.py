import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class Supplier(Base, TenantMixin):
    __tablename__ = "suppliers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    tier = Column(String(10), default="T3")
    parent_supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=True)
    contact_person = Column(String(100))
    contact_email = Column(String(150))
    contact_phone = Column(String(30))
    address = Column(Text)
    payment_terms = Column(String(50))
    lead_time_days = Column(Integer, default=0)
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Supplier", remote_side=[id], backref="children")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    evaluations = relationship("SupplierEvaluation", back_populates="supplier")
    prices = relationship("SupplierPrice", back_populates="supplier")


class PurchaseOrder(Base, TenantMixin):
    __tablename__ = "purchase_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    po_no = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    status = Column(String(20), default="draft")
    order_date = Column(DateTime, default=datetime.utcnow)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    total_amount = Column(Float, default=0)
    currency = Column(String(10), default="TWD")
    payment_status = Column(String(20), default="unpaid")
    created_by = Column(String(36), ForeignKey("employees.id"))
    approved_by = Column(String(36), ForeignKey("employees.id"))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    creator = relationship("Employee", foreign_keys=[created_by])
    approver = relationship("Employee", foreign_keys=[approved_by])
    inspection_orders = relationship("InspectionOrder", back_populates="purchase_order")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    po_id = Column(String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    ordered_qty = Column(Float, nullable=False)
    received_qty = Column(Float, default=0)
    unit_price = Column(Float, default=0)
    line_total = Column(Float, default=0)
    expected_date = Column(DateTime)
    received_date = Column(DateTime)
    remark = Column(Text)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    part = relationship("Part", back_populates="purchase_order_items")


class SupplierPrice(Base):
    __tablename__ = "supplier_prices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    unit_price = Column(Float, nullable=False)
    currency = Column(String(10), default="TWD")
    moq = Column(Float, default=0)
    lead_time_days = Column(Integer, default=0)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="prices")
    part = relationship("Part", back_populates="supplier_prices")


class SupplierEvaluation(Base):
    __tablename__ = "supplier_evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    period = Column(String(20), nullable=False)
    quality_score = Column(Float, default=0)
    delivery_score = Column(Float, default=0)
    price_score = Column(Float, default=0)
    service_score = Column(Float, default=0)
    composite_score = Column(Float, default=0)
    evaluated_by = Column(String(36), ForeignKey("employees.id"))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="evaluations")
    evaluator = relationship("Employee")

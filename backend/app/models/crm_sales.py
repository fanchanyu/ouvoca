import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class Customer(Base, TenantMixin):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    grade = Column(String(5), default="C")
    contact_person = Column(String(100))
    contact_email = Column(String(150))
    contact_phone = Column(String(30))
    address = Column(Text)
    payment_terms = Column(String(50))
    credit_limit = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_orders = relationship("SalesOrder", back_populates="customer")
    leads = relationship("Lead", back_populates="customer", foreign_keys="Lead.converted_to_customer_id")
    opportunities = relationship("Opportunity", back_populates="customer")
    contracts = relationship("Contract", back_populates="customer")
    crm_events = relationship("CrmEvent", back_populates="customer")
    receivables = relationship("AccountsReceivable", back_populates="customer")


class SalesOrder(Base, TenantMixin):
    __tablename__ = "sales_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    so_no = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    status = Column(String(20), default="draft")
    order_date = Column(DateTime, default=datetime.utcnow)
    requested_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    total_amount = Column(Float, default=0)
    currency = Column(String(10), default="TWD")
    payment_status = Column(String(20), default="unpaid")
    created_by = Column(String(36), ForeignKey("employees.id"))
    approved_by = Column(String(36), ForeignKey("employees.id"))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="sales_orders")
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")
    production_orders = relationship("ProductionOrder", back_populates="sales_order", foreign_keys="ProductionOrder.so_id")
    creator = relationship("Employee", foreign_keys=[created_by])
    approver = relationship("Employee", foreign_keys=[approved_by])


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    so_id = Column(String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    ordered_qty = Column(Float, nullable=False)
    shipped_qty = Column(Float, default=0)
    unit_price = Column(Float, default=0)
    line_total = Column(Float, default=0)
    expected_date = Column(DateTime)
    remark = Column(Text)

    sales_order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product", back_populates="sales_order_items")


class Lead(Base, TenantMixin):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(200), nullable=False)
    contact_person = Column(String(100))
    contact_email = Column(String(150))
    contact_phone = Column(String(30))
    source = Column(String(50))
    status = Column(String(20), default="new")
    converted_to_customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True)
    assigned_to = Column(String(36), ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="leads", foreign_keys=[converted_to_customer_id])
    assignee = relationship("Employee")


class Opportunity(Base, TenantMixin):
    __tablename__ = "opportunities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    name = Column(String(200), nullable=False)
    stage = Column(String(30), default="prospect")
    amount = Column(Float, default=0)
    probability = Column(Float, default=0)
    expected_close_date = Column(DateTime)
    assigned_to = Column(String(36), ForeignKey("employees.id"))
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="opportunities")
    assignee = relationship("Employee")


class Contract(Base, TenantMixin):
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_no = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    status = Column(String(20), default="draft")
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    total_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="contracts")
    pricing = relationship("ContractPricing", back_populates="contract", cascade="all, delete-orphan")


class ContractPricing(Base):
    __tablename__ = "contract_pricing"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    unit_price = Column(Float, nullable=False)
    moq = Column(Float, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="pricing")
    product = relationship("Product")


class CrmEvent(Base, TenantMixin):
    __tablename__ = "crm_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    event_type = Column(String(30), nullable=False)
    subject = Column(String(200), nullable=False)
    description = Column(Text)
    reference_type = Column(String(50))
    reference_id = Column(String(36))
    created_by = Column(String(36), ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="crm_events")
    creator = relationship("Employee")

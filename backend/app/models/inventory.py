import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin

import enum


class UnitOfMeasure(str, enum.Enum):
    PCS = "pcs"
    KG = "kg"
    M = "m"
    L = "l"
    SET = "set"
    BOX = "box"
    ROLL = "roll"


class PartCategory(str, enum.Enum):
    RAW = "raw_material"
    SEMI = "semi_finished"
    COMPONENT = "component"
    CONSUMABLE = "consumable"
    PACKAGING = "packaging"


class Part(Base, TenantMixin):
    __tablename__ = "parts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(30), default=PartCategory.RAW.value)
    unit = Column(String(10), default=UnitOfMeasure.PCS.value)
    specification = Column(Text)
    drawing_no = Column(String(50))
    min_stock = Column(Float, default=0)
    max_stock = Column(Float, default=0)
    safety_stock = Column(Float, default=0)
    lead_time_days = Column(Integer, default=0)
    unit_cost = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    is_critical = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory = relationship("Inventory", back_populates="part", uselist=False)
    inventory_transactions = relationship("InventoryTransaction", back_populates="part")
    bom_items = relationship("BOMItem", back_populates="part")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="part")
    inspection_orders = relationship("InspectionOrder", back_populates="part")
    non_conformances = relationship("NonConformance", back_populates="part")
    supplier_prices = relationship("SupplierPrice", back_populates="part")
    reorder_rules = relationship("ReorderRule", back_populates="part")


class Inventory(Base, TenantMixin):
    __tablename__ = "inventory"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id = Column(String(36), ForeignKey("parts.id"), unique=True, nullable=False)
    qty_on_hand = Column(Float, default=0)
    qty_allocated = Column(Float, default=0)
    qty_available = Column(Float, default=0)
    qty_in_transit = Column(Float, default=0)
    last_counted_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    part = relationship("Part", back_populates="inventory")


class InventoryTransaction(Base, TenantMixin):
    __tablename__ = "inventory_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False, index=True)
    transaction_type = Column(String(30), nullable=False)
    qty = Column(Float, nullable=False)
    reference_type = Column(String(50))
    reference_id = Column(String(36))
    source_location = Column(String(100))
    target_location = Column(String(100))
    batch_no = Column(String(50))
    lot_no = Column(String(50))
    operator_id = Column(String(36), ForeignKey("employees.id"))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("Part", back_populates="inventory_transactions")
    operator = relationship("Employee")


class InventoryTransfer(Base, TenantMixin):
    __tablename__ = "inventory_transfers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_no = Column(String(50), unique=True, nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    qty = Column(Float, nullable=False)
    source_warehouse = Column(String(100))
    source_bin = Column(String(100))
    target_warehouse = Column(String(100))
    target_bin = Column(String(100))
    status = Column(String(20), default="pending")
    requested_by = Column(String(36), ForeignKey("employees.id"))
    approved_by = Column(String(36), ForeignKey("employees.id"))
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("Part")
    requester = relationship("Employee", foreign_keys=[requested_by])
    approver = relationship("Employee", foreign_keys=[approved_by])

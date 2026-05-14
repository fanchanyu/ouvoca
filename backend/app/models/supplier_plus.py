import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base import Base


class ReorderRule(Base):
    __tablename__ = "reorder_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False, unique=True)
    reorder_point = Column(Float, nullable=False)
    order_qty = Column(Float, nullable=False)
    safety_stock = Column(Float, default=0)
    lead_time_days = Column(Integer, default=0)
    is_auto_po = Column(Boolean, default=False)
    preferred_supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    part = relationship("Part", back_populates="reorder_rules")
    preferred_supplier = relationship("Supplier")


class ReplenishSuggestion(Base):
    __tablename__ = "replenish_suggestions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    reorder_rule_id = Column(String(36), ForeignKey("reorder_rules.id"), nullable=False)
    suggested_qty = Column(Float, nullable=False)
    current_qty = Column(Float, default=0)
    demand_forecast = Column(Float, default=0)
    status = Column(String(20), default="suggested")
    converted_po_id = Column(String(36), ForeignKey("purchase_orders.id"), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("Part")
    reorder_rule = relationship("ReorderRule")
    converted_po = relationship("PurchaseOrder")

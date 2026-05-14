import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class Product(Base, TenantMixin):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    unit = Column(String(10), default="pcs")
    selling_price = Column(Float, default=0)
    standard_cost = Column(Float, default=0)
    moq = Column(Float, default=1)
    lead_time_days = Column(Integer, default=0)
    drawing_no = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bom_items = relationship("BOMItem", back_populates="product", foreign_keys="BOMItem.product_id")
    sales_order_items = relationship("SalesOrderItem", back_populates="product")
    production_orders = relationship("ProductionOrder", back_populates="product")


class BOMItem(Base):
    __tablename__ = "bom_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    parent_bom_id = Column(String(36), ForeignKey("bom_items.id"), nullable=True)
    level = Column(Integer, default=0)
    sequence_no = Column(Integer, default=0)
    qty_per = Column(Float, default=1)
    scrap_rate = Column(Float, default=0)
    is_critical = Column(Boolean, default=False)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="bom_items", foreign_keys=[product_id])
    part = relationship("Part", back_populates="bom_items")
    parent = relationship("BOMItem", remote_side=[id], backref="children")

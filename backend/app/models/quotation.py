"""Quotation (報價單) — 業務在 SO 之前的階段（v3.32 進銷存深化）

SMB 業務每天用：客戶詢價 → 報價 → 議價 → 接受 → 自動轉 SO。
若無此模組，業務只能用 Excel 報價，缺少版本追蹤、缺少自動轉訂單。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class Quotation(Base, TenantMixin):
    """報價單主檔。狀態流：draft → sent → accepted/rejected/expired."""
    __tablename__ = "quotations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    quote_date = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime)  # 報價有效期
    status = Column(String(20), default="draft")
    # draft / sent / accepted / rejected / expired / converted
    subtotal = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    notes = Column(Text)
    # 轉訂單後存 SO 連結（避免重複轉）
    converted_so_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=True)
    converted_at = Column(DateTime)
    created_by = Column(String(36), ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", foreign_keys=[customer_id])
    items = relationship("QuotationItem", back_populates="quotation",
                         cascade="all, delete-orphan",
                         order_by="QuotationItem.sequence_no")


class QuotationItem(Base):
    """報價單行項目。"""
    __tablename__ = "quotation_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quotation_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no = Column(Integer, default=0)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    # 允許 free-text 報價（如尚未建檔之新品）
    description = Column(Text, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(10), default="pcs")
    unit_price = Column(Float, default=0)
    discount_rate = Column(Float, default=0)  # 0.0 - 1.0
    line_total = Column(Float, default=0)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    quotation = relationship("Quotation", back_populates="items")

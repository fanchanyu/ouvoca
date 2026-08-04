"""RFQ 詢價比價（M3-3）— 請購 → 詢價 → 比價 → 決標轉 PO。"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from app.core.base import Base
from app.models._mixins import TenantMixin


class RFQ(Base, TenantMixin):
    __tablename__ = "rfqs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_no = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="draft")  # draft / sent / awarded / cancelled
    need_date = Column(DateTime)
    remark = Column(Text)
    awarded_quote_id = Column(String(36), ForeignKey("supplier_quotes.id"))
    converted_po_id = Column(String(36), ForeignKey("purchase_orders.id"))
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("RFQItem", back_populates="rfq", cascade="all, delete-orphan")
    quotes = relationship(
        "SupplierQuote", back_populates="rfq",
        foreign_keys="SupplierQuote.rfq_id",
    )


class RFQItem(Base, TenantMixin):
    __tablename__ = "rfq_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id = Column(String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    line_no = Column(Integer, default=1)
    qty = Column(Float, nullable=False)
    need_date = Column(DateTime)

    rfq = relationship("RFQ", back_populates="items")
    part = relationship("Part")


class SupplierQuote(Base, TenantMixin):
    __tablename__ = "supplier_quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id = Column(String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    quote_date = Column(DateTime, nullable=False)
    amount = Column(Float, default=0)            # 總金額
    lead_time_days = Column(Integer, default=0)
    currency = Column(String(10), default="TWD")
    status = Column(String(20), default="received")  # received / awarded / declined
    remark = Column(Text)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)

    rfq = relationship("RFQ", back_populates="quotes",
                       foreign_keys="SupplierQuote.rfq_id")
    supplier = relationship("Supplier")
    items = relationship("SupplierQuoteItem", back_populates="quote",
                         cascade="all, delete-orphan")


class SupplierQuoteItem(Base, TenantMixin):
    __tablename__ = "supplier_quote_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_id = Column(String(36), ForeignKey("supplier_quotes.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    qty = Column(Float, nullable=False)
    unit_price = Column(Float, default=0)

    quote = relationship("SupplierQuote", back_populates="items")
    part = relationship("Part")

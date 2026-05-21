"""StockCount (盤點單) — SMB 月底必做（v3.32 進銷存深化）

流程：
  1. 建立盤點單（依倉位 / 部分料件 / 全廠）
  2. 列印盤點底稿 → 倉管實際清點
  3. Key in 實盤數
  4. 系統比對帳上 vs 實盤 → 產生差異
  5. ConfirmCard 主管確認 → 自動產生調整 inventory_transaction
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class StockCount(Base, TenantMixin):
    """盤點單主檔。狀態流：draft → counting → reviewed → adjusted."""
    __tablename__ = "stock_counts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    count_no = Column(String(50), unique=True, nullable=False, index=True)
    count_date = Column(DateTime, default=datetime.utcnow)
    scope = Column(String(30), default="partial")  # full / partial / location
    status = Column(String(20), default="draft")
    # draft → counting → reviewed → adjusted / cancelled
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("employees.id"))
    reviewed_by = Column(String(36), ForeignKey("employees.id"), nullable=True)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("StockCountItem", back_populates="count",
                         cascade="all, delete-orphan",
                         order_by="StockCountItem.sequence_no")


class StockCountItem(Base):
    """盤點單行項目（每料件一行）。"""
    __tablename__ = "stock_count_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    count_id = Column(String(36), ForeignKey("stock_counts.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no = Column(Integer, default=0)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    book_qty = Column(Float, default=0)       # 帳上庫存（snapshot）
    counted_qty = Column(Float, nullable=True)  # 實盤數（key in 後填）
    variance = Column(Float, default=0)        # counted - book
    variance_reason = Column(String(50))       # damaged / lost / found / count_error / other
    notes = Column(Text)
    counted_by = Column(String(36), ForeignKey("employees.id"), nullable=True)
    counted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    count = relationship("StockCount", back_populates="items")

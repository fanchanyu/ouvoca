"""批號 / 序號追溯（M3-2）— 正反向 Pegging 基礎。

- BatchLot：批號主檔（料件 + 數量 + 效期）
- SerialNumber：序號主檔（單件追蹤）
動向追蹤靠 InventoryTransaction.batch_no / reference_type / reference_id
（PO/GRN/WO/MI/SO/DN/RT 都寫 reference）。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, String,
)
from sqlalchemy.orm import relationship

from app.core.base import Base
from app.models._mixins import TenantMixin


class BatchLot(Base, TenantMixin):
    __tablename__ = "batch_lots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_no = Column(String(50), nullable=False, index=True)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    qty = Column(Float, default=0)
    expiry_date = Column(DateTime)
    status = Column(String(20), default="active")  # active / consumed / expired / void
    remark = Column(String(255))
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("Part")
    serial_numbers = relationship("SerialNumber", back_populates="batch")


class SerialNumber(Base, TenantMixin):
    __tablename__ = "serial_numbers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    serial_no = Column(String(100), nullable=False, index=True)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    batch_id = Column(String(36), ForeignKey("batch_lots.id"), nullable=True)
    status = Column(String(20), default="in_stock")  # in_stock / shipped / returned / scrapped
    last_document_type = Column(String(50))
    last_document_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    part = relationship("Part")
    batch = relationship("BatchLot", back_populates="serial_numbers")

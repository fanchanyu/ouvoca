"""Taiwan e-invoice persistence (v3.54 — 統一發票使用辦法 compliance).

統一發票須保存 5 年，原 in-memory dict 重啟即遺失，違反法規。
本表將每張開立 / 作廢之發票落 DB，並 FK 連回 SalesOrder + JournalEntry，
形成 SO -> Invoice -> JE -> AR 的合規追溯鏈。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey, Text, JSON,
)

from app.core.base import Base
from app.models._mixins import TenantMixin


class EInvoiceRecord(Base, TenantMixin):
    """單張電子發票之 DB 持久化紀錄（合規最小欄位集 + MIG 完整 payload）."""

    __tablename__ = "einvoice_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_no = Column(String(20), nullable=False, index=True)  # AB12345678
    invoice_date = Column(String(8), nullable=False)  # YYYYMMDD (Taiwan tax format)
    invoice_time = Column(String(8))  # HH:MM:SS

    # 買賣方
    seller_tax_id = Column(String(20), nullable=False)
    buyer_tax_id = Column(String(20))  # B2C may be null
    buyer_name = Column(String(200))

    # 金額
    sales_amount = Column(Float, nullable=False, default=0)  # 銷售額（未稅）
    tax_amount = Column(Float, nullable=False, default=0)     # 稅額
    total_amount = Column(Float, nullable=False, default=0)   # 總計
    tax_rate = Column(Float, default=0.05)

    # 關聯（合規追溯鏈）
    so_id = Column(String(36), ForeignKey("sales_orders.id"))
    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"))

    # 狀態
    status = Column(String(20), default="issued")  # issued / cancelled / voided
    tracking_no = Column(String(50))

    # 取消資訊
    cancelled_at = Column(DateTime)
    cancel_reason = Column(Text)

    # MIG 完整 payload（合規所需，5 年保存）
    mig_payload = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(36))  # employee_id

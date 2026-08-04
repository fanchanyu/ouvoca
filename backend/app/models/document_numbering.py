"""集中式單據編號計數器 — Phase C1（防並發重號）。"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from app.core.base import Base
from app.models._mixins import TenantMixin


class DocumentNumbering(Base, TenantMixin):
    """單據號碼原子計數器。

    每 (tenant_id, doc_type, period) 一列，seq 只透過
    INSERT ... ON CONFLICT DO UPDATE SET seq = seq + 1 RETURNING seq 遞增，
    多寫者並發下保證不重號（SQLite / PostgreSQL 皆支援）。

    period 慣例：日別 "YYYYMMDD"；月別 "YYYYMM"；不設分期間用 "GLOBAL"。
    """
    __tablename__ = "document_numbering"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "doc_type", "period",
            name="uq_document_numbering_tenant_doc_period",
        ),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_type = Column(String(50), nullable=False)   # SO / PO / JE / DN / ...
    period = Column(String(20), nullable=False)     # YYYYMMDD / YYYYMM / GLOBAL
    seq = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

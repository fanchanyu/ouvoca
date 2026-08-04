"""SystemSetting — 系統組態 key-value（M1-3 使用，v006 一併落地）。"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON, Boolean, DateTime
from app.core.base import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(80), primary_key=True)
    value = Column(JSON, nullable=False)
    group = Column(String(40), default="general")   # general/company/finance/backup/ai
    description = Column(String(200))
    is_system = Column(Boolean, default=False)
    updated_by = Column(String(36))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

"""External DB connection master — G-510 加密儲存連線設定。"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text

from app.core.base import Base
from app.models._mixins import TenantMixin


class ExternalConnection(Base, TenantMixin):
    """外部 DB 連接主檔。

    取代 services.connections 的 in-memory dict：
      - name:     唯一名稱（如 legacy_dingxin / customer_a_csv）
      - connector: connector 類型（sqlite / csv_folder / ...）
      - config_encrypted: 連線設定 JSON（含 host/port/user/password/path）
                          AES-256-GCM 加密後儲存，絕不明文落庫（G-510）
      - is_active: 停用時工具查詢直接回「已停用」
    """
    __tablename__ = "external_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    connector = Column(String(50), nullable=False)
    config_encrypted = Column(Text, nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_by = Column(String(36), ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

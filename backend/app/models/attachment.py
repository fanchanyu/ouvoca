"""Attachment model — 通用檔案上傳（Sprint E v3.13）。

用途：
  - 使用者上傳報價單 / 訂單 / 發票 / 一般附件
  - 後續可由 LLM tool 讀取並 parse 成 SO / PO / Quote 等業務實體
  - 暫存路徑：backend/uploads/{tenant_id}/{yyyy-mm}/{uuid}_{filename}

設計：
  - file_path 存相對路徑（不存 binary 進 DB，避免膨脹）
  - category 用 string union 而非 enum，方便擴充
  - parsed_target_type / parsed_target_id 給 LLM 工具填回（追蹤檔案被解析成哪個業務實體）
  - 含 TenantMixin → MESH 多廠隔離
"""
from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.base import Base
from app.models._mixins import TenantMixin


# category 合法值（service / api 層用 set 校驗）
ATTACHMENT_CATEGORIES = frozenset({
    "quote",      # 客戶報價單（待轉 SO）
    "invoice",    # 發票
    "po",         # 供應商報價 / 採購單
    "spec",       # 規格書 / 圖紙
    "contract",   # 合約
    "general",    # 一般附件
})


class Attachment(Base, TenantMixin):
    __tablename__ = "attachments"

    id              = Column(String(36), primary_key=True)
    filename        = Column(String(255), nullable=False)
    content_type    = Column(String(128), nullable=False, default="application/octet-stream")
    size_bytes      = Column(Integer, nullable=False, default=0)

    file_path       = Column(String(512), nullable=False)  # 相對 backend/uploads/ 的路徑
    category        = Column(String(32), nullable=False, default="general", index=True)
    description     = Column(Text, nullable=True)

    uploaded_by     = Column(String(36), nullable=True, index=True)  # User.id 或 employee_id
    uploaded_at     = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    # LLM 解析回填用（追蹤這檔變成哪個業務實體）
    parsed_status      = Column(String(16), nullable=False, default="pending")  # pending / parsed / failed
    parsed_target_type = Column(String(32), nullable=True)   # 'sales_order' / 'purchase_order' / ...
    parsed_target_id   = Column(String(36), nullable=True)
    parsed_at          = Column(DateTime, nullable=True)
    parsed_error       = Column(Text, nullable=True)

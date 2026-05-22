"""GlossaryItem DB model — Phase 2 G-201 同義詞持久化。

設計：
  啟動時從 DB 載入到 in-memory _GLOSSARY dict（熱路徑零 DB 查詢）。
  使用者透過 register_glossary_term tool 新增時同步寫入 DB。
  重啟後自動 reload，不丟失。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Text, DateTime
from app.database import Base


class GlossaryItem(Base):
    __tablename__ = "glossary_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    term = Column(String(200), nullable=False, index=True)
    canonical_type = Column(String(50), nullable=False, index=True)   # part/customer/supplier/product
    canonical_id = Column(String(200), nullable=False)
    canonical_label = Column(String(500), default="")
    confidence = Column(Float, default=1.0)
    language = Column(String(20), default="zh-TW")
    notes = Column(Text, default="")
    created_by = Column(String(36))                                    # employee_id
    created_at = Column(DateTime, default=datetime.utcnow)

"""共用 model mixin：所有業務表透過 inherit 加上 tenant_id 等基礎欄位。

設計重點
--------
- **TenantMixin**：所有業務表共享 tenant_id 欄位 → MESH 多廠隔離基石
- 預設值 "HQ"，向後相容（既有資料 backfill 為 HQ）
- index 為 True，row-level filter query 高效

用法
----
    class Part(Base, TenantMixin):
        __tablename__ = "parts"
        ...

注意：MIXIN 必須放在 Base 之後（MRO 順序），且 Mixin 不繼承 Base。
"""
from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_mixin


@declarative_mixin
class TenantMixin:
    """為業務表注入 tenant_id 欄位。

    - default="HQ"：既有資料/seed 自動填 HQ
    - nullable=True：相容舊資料（PostgreSQL 加欄位不卡）
    - index=True：所有 row-level filter 走 tenant_id 都會用到
    """
    tenant_id = Column(String(36), default="HQ", nullable=True, index=True)

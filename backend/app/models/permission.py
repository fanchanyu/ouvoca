"""RBAC 權限系統 — 8 張表的 SQLAlchemy ORM。

設計哲學
--------
- **輕量**：用 String FK + JSON 欄位，避免複雜關聯查詢
- **可擴充**：JSON 欄位保彈性，未來 ABAC 不需 ALTER TABLE
- **多租戶**：tenant_id 從 Day 1 就有
- **稽核完整**：每張表都有 created_at / 軟刪除 / audit trail
- **不破壞既有**：使用 `rbac_*` 前綴的表名，與舊 `roles`/`permissions` 共存

對應設計文件：docs/PERMISSION_MODEL.md
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Integer, ForeignKey, JSON,
    Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.core.base import Base


# ============================================================
# L1: Tenant — 多租戶 / MESH 廠別隔離單位
# ============================================================

class Tenant(Base):
    """租戶（HQ / 主廠 / 外協廠 / 客戶 portal）。

    這是多廠 MESH 戰略的基石。所有業務表都應有 tenant_id 欄位（Phase 1 同步遷移）。

    tenant_type 取值:
      - hq:              總部
      - factory:         自有工廠
      - outsource:       外協廠（部分權限）
      - customer_portal: 客戶端 portal（僅自己訂單）
    """
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    tenant_type = Column(String(30), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    mesh_role = Column(String(20))  # central / node / partner
    is_active = Column(Boolean, default=True)
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Tenant", remote_side=[id], backref="children")


# ============================================================
# L4: PermissionDef — 95 個權限碼（不可變主檔）
# ============================================================

class PermissionDef(Base):
    """權限定義（不可變主檔）。

    格式：`<module>.<resource>.<action>`
    例：sales.order.create, purchase.supplier.delete
    """
    __tablename__ = "rbac_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False, index=True)
    action = Column(String(30), nullable=False)
    module = Column(String(30), nullable=False, index=True)
    name_zh = Column(String(100))
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    is_sensitive = Column(Boolean, default=False)
    risk_level = Column(String(10), default="low")  # low/medium/high/critical
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# L3: RoleDef — 角色定義
# ============================================================

class RoleDef(Base):
    """角色（boss / sales_rep / outsource_partner / ...）。

    tenant_id 為 NULL 表示系統共用角色（如 super_admin）。
    """
    __tablename__ = "rbac_roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    code = Column(String(50), nullable=False)
    name_zh = Column(String(100), nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=50)
    icon = Column(String(20))
    color = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_rbac_role_tenant_code"),
    )

    tenant = relationship("Tenant")
    role_perms = relationship(
        "RolePermissionLink", back_populates="role",
        cascade="all, delete-orphan",
    )


# ============================================================
# L3↔L4: Role × Permission（M:N + Scope + Conditions）
# ============================================================

class RolePermissionLink(Base):
    """角色與權限的多對多，含 row-level scope 與 ABAC 條件。"""
    __tablename__ = "rbac_role_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id = Column(
        String(36), ForeignKey("rbac_roles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    permission_id = Column(
        String(36), ForeignKey("rbac_permissions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    scope = Column(String(20), default="tenant")  # all/tenant/department/team/own/assigned
    conditions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_rbac_role_perm"),
    )

    role = relationship("RoleDef", back_populates="role_perms")
    permission = relationship("PermissionDef")


# ============================================================
# L2↔L3: User × Role（含時效 + 代理）
# ============================================================

class UserRoleAssignment(Base):
    """使用者擁有的角色（含時效、代理）。

    取代舊的 employee_roles 表（保留以供向後兼容）。
    """
    __tablename__ = "user_role_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role_id = Column(
        String(36), ForeignKey("rbac_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(String(36))
    expires_at = Column(DateTime)  # 時效授權 NULL=永久
    delegation_from = Column(String(36))  # 若是代理 from 誰
    reason = Column(Text)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_user_role_active", "user_id", "is_active"),
        Index("idx_user_role_expires", "expires_at"),
    )

    role = relationship("RoleDef")
    tenant = relationship("Tenant")


# ============================================================
# 個別授權 (Permission Override)
# ============================================================

class PermissionOverride(Base):
    """個別使用者的權限例外（grant/revoke）。

    使用情境：
    - 「給小陳臨時開放匯出 PO 一週」
    - 「拒絕阿玲的某項權限（即使她的角色有）」
    """
    __tablename__ = "permission_overrides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    permission_code = Column(String(100), nullable=False, index=True)
    grant_or_revoke = Column(String(10), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(36))
    granted_by = Column(String(36), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    reason = Column(Text, nullable=False)  # 必填，稽核用
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_perm_override_user", "user_id", "is_active"),
    )


# ============================================================
# L5: Row Filter — 行級過濾規則庫
# ============================================================

class RowFilter(Base):
    """行級過濾規則（「業務只看自己客戶」等）。

    預設提供 6 種（own/tenant/department/team/assigned/all），
    亦可自訂（如「中區業務只看中區客戶」）。
    """
    __tablename__ = "row_filters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)
    resource = Column(String(50), nullable=False, index=True)
    scope = Column(String(20), nullable=False)
    filter_expr = Column(JSON, nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# Permission Audit — 權限變更稽核
# ============================================================

class PermissionAudit(Base):
    """權限變更稽核日誌。

    任何 grant_role / revoke_role / modify_permission 都會在此留下不可變紀錄。
    """
    __tablename__ = "permission_audit"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String(36), nullable=False)
    target_user_id = Column(String(36))
    target_role_id = Column(String(36))
    change_type = Column(String(30), nullable=False, index=True)
    before_state = Column(JSON)
    after_state = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_perm_audit_target", "target_user_id", "created_at"),
    )

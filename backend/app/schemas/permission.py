from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field


# --- Tenant ---

class TenantCreate(BaseModel):
    code: str
    name: str
    tenant_type: str = Field(..., description="hq/factory/outsource/customer_portal")
    parent_id: Optional[str] = None
    mesh_role: Optional[str] = None
    settings: Optional[dict] = None


class TenantResponse(BaseModel):
    id: str
    code: str
    name: str
    tenant_type: str
    parent_id: Optional[str] = None
    mesh_role: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Permission Def (唯讀) ---

class PermissionDefResponse(BaseModel):
    id: str
    code: str
    resource: str
    action: str
    module: str
    name_zh: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: bool
    risk_level: str

    class Config:
        from_attributes = True


# --- Role ---

class RolePermissionSpec(BaseModel):
    code: str
    scope: str = "tenant"
    conditions: Optional[dict] = None


class RoleCreateV2(BaseModel):
    tenant_id: Optional[str] = None
    code: str
    name_zh: str
    description: Optional[str] = None
    priority: int = 50
    icon: Optional[str] = None
    color: Optional[str] = None
    permissions: List[RolePermissionSpec] = []


class RolePermissionItem(BaseModel):
    code: str
    name_zh: Optional[str] = None
    scope: str

    class Config:
        from_attributes = True


class RoleResponseV2(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    code: str
    name_zh: str
    description: Optional[str] = None
    is_system: bool
    is_active: bool
    priority: int
    icon: Optional[str] = None
    color: Optional[str] = None
    permissions: List[RolePermissionItem] = []
    created_at: datetime

    class Config:
        from_attributes = True


class RoleCloneRequest(BaseModel):
    new_code: str
    new_name_zh: str
    tenant_id: Optional[str] = None


class UpdateRolePermissionsRequest(BaseModel):
    permissions: List[RolePermissionSpec]


# --- User Role Assignment ---

class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str
    tenant_id: str
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
    delegation_from: Optional[str] = None


class UserRoleAssignmentResponse(BaseModel):
    id: str
    user_id: str
    role_id: str
    tenant_id: str
    granted_at: datetime
    granted_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    delegation_from: Optional[str] = None
    reason: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# --- Permission Override ---

class GrantOverrideRequest(BaseModel):
    user_id: str
    permission_code: str
    grant_or_revoke: str = "grant"  # grant / revoke
    reason: str  # 必填
    expires_at: Optional[datetime] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


class PermissionOverrideResponse(BaseModel):
    id: str
    user_id: str
    permission_code: str
    grant_or_revoke: str
    reason: str
    expires_at: Optional[datetime] = None
    granted_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# --- Effective Permissions View ---

class EffectiveRoleItem(BaseModel):
    role_code: str
    granted_at: Optional[datetime] = None
    granted_by: Optional[str] = None
    scope: Optional[str] = None


class EffectivePermissionItem(BaseModel):
    permission_code: str
    source: str  # "role" or "override"
    role_code: Optional[str] = None


class EffectiveOverrideItem(BaseModel):
    permission_code: str
    grant_or_deny: str  # "grant" or "deny"
    reason: Optional[str] = None
    granted_by: Optional[str] = None


class EffectivePermissionsView(BaseModel):
    user_id: str
    roles: List[EffectiveRoleItem]
    permissions: List[EffectivePermissionItem]
    overrides: List[EffectiveOverrideItem]

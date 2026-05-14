"""權限管理 API — 給管理者用的 CRUD 介面。

所有端點本身都受權限保護（system.permission.*）。
demo-admin 一律放行。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.core.exceptions import NotFoundError
from app.schemas.permission import (
    TenantCreate, TenantResponse,
    PermissionDefResponse,
    RoleCreateV2, RoleResponseV2, RoleCloneRequest, UpdateRolePermissionsRequest,
    AssignRoleRequest, UserRoleAssignmentResponse,
    GrantOverrideRequest, PermissionOverrideResponse,
    EffectivePermissionsView,
)
from app.services import permission as svc

router = APIRouter(prefix="/api/permission", tags=["Permission / RBAC"])


# ============================================================
# Tenant
# ============================================================

@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.tenant.create")),
):
    t = await svc.create_tenant(db, data.model_dump())
    return TenantResponse.model_validate(t)


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    tenant_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.tenant.list")),
):
    rows = await svc.list_tenants(db, tenant_type)
    return [TenantResponse.model_validate(r) for r in rows]


# ============================================================
# Permission Definitions (唯讀)
# ============================================================

@router.get("/permissions", response_model=List[PermissionDefResponse])
async def list_permissions(
    module: Optional[str] = None,
    resource: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.permission.list")),
):
    rows = await svc.list_permissions(db, module, resource)
    return [PermissionDefResponse.model_validate(r) for r in rows]


# ============================================================
# Roles
# ============================================================

def _role_to_response(role) -> RoleResponseV2:
    """把 Role + role_perms（含 permission）轉成 response model。"""
    return RoleResponseV2(
        id=role.id, tenant_id=role.tenant_id, code=role.code,
        name_zh=role.name_zh, description=role.description,
        is_system=role.is_system, is_active=role.is_active,
        priority=role.priority, icon=role.icon, color=role.color,
        created_at=role.created_at,
        permissions=[
            {"code": rp.permission.code,
             "name_zh": rp.permission.name_zh,
             "scope": rp.scope}
            for rp in (role.role_perms or [])
        ],
    )


@router.post("/roles", response_model=RoleResponseV2)
async def create_role(
    data: RoleCreateV2,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.role.create")),
):
    role = await svc.create_role(
        db,
        {k: v for k, v in data.model_dump().items() if k != "permissions"},
        actor_id=user.user_id,
        permissions=[p.model_dump() for p in data.permissions],
    )
    role = await svc.get_role(db, role.id)
    return _role_to_response(role)


@router.get("/roles", response_model=List[RoleResponseV2])
async def list_roles(
    tenant_id: Optional[str] = None,
    include_system: bool = True,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.role.list")),
):
    rows = await svc.list_roles(db, tenant_id, include_system)
    # 每個 role 重新載入帶權限
    return [_role_to_response(await svc.get_role(db, r.id)) for r in rows]


@router.get("/roles/{role_id}", response_model=RoleResponseV2)
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.role.read")),
):
    role = await svc.get_role(db, role_id)
    if not role:
        raise NotFoundError("角色不存在", role_id=role_id)
    return _role_to_response(role)


@router.post("/roles/{role_id}/clone", response_model=RoleResponseV2)
async def clone_role(
    role_id: str,
    data: RoleCloneRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.role.create")),
):
    role = await svc.clone_role(
        db, source_role_id=role_id, new_code=data.new_code,
        new_name_zh=data.new_name_zh, tenant_id=data.tenant_id, actor_id=user.user_id,
    )
    role = await svc.get_role(db, role.id)
    return _role_to_response(role)


@router.put("/roles/{role_id}/permissions", response_model=RoleResponseV2)
async def update_role_permissions(
    role_id: str,
    data: UpdateRolePermissionsRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.role.update")),
):
    role = await svc.update_role_permissions(
        db, role_id, [p.model_dump() for p in data.permissions], actor_id=user.user_id,
    )
    role = await svc.get_role(db, role.id)
    return _role_to_response(role)


# ============================================================
# User-Role Assignment
# ============================================================

@router.post("/assignments", response_model=UserRoleAssignmentResponse)
async def assign_role(
    data: AssignRoleRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.permission.grant")),
):
    a = await svc.assign_role(
        db,
        user_id=data.user_id, role_id=data.role_id, tenant_id=data.tenant_id,
        actor_id=user.user_id, expires_at=data.expires_at,
        reason=data.reason, delegation_from=data.delegation_from,
    )
    return UserRoleAssignmentResponse.model_validate(a)


@router.delete("/assignments/{assignment_id}", response_model=UserRoleAssignmentResponse)
async def revoke_role(
    assignment_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.permission.revoke")),
):
    a = await svc.revoke_role(db, assignment_id, actor_id=user.user_id, reason=reason)
    return UserRoleAssignmentResponse.model_validate(a)


@router.get("/users/{user_id}/roles", response_model=List[UserRoleAssignmentResponse])
async def list_user_roles(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.user.read")),
):
    rows = await svc.list_user_roles(db, user_id)
    return [UserRoleAssignmentResponse.model_validate(r) for r in rows]


# ============================================================
# Permission Override
# ============================================================

@router.post("/overrides", response_model=PermissionOverrideResponse)
async def grant_override(
    data: GrantOverrideRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.permission.grant")),
):
    ov = await svc.grant_override(
        db,
        user_id=data.user_id, permission_code=data.permission_code,
        actor_id=user.user_id, reason=data.reason,
        expires_at=data.expires_at, grant_or_revoke=data.grant_or_revoke,
        resource_type=data.resource_type, resource_id=data.resource_id,
    )
    return PermissionOverrideResponse.model_validate(ov)


@router.get("/users/{user_id}/overrides", response_model=List[PermissionOverrideResponse])
async def list_user_overrides(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.user.read")),
):
    rows = await svc.list_user_overrides(db, user_id)
    return [PermissionOverrideResponse.model_validate(r) for r in rows]


# ============================================================
# Effective Permissions View（給管理介面 + AI 查詢）
# ============================================================

@router.get("/users/{user_id}/effective", response_model=EffectivePermissionsView)
async def get_effective_permissions(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.user.read")),
):
    """回傳使用者所有「實際生效」權限（含 role + override + scope）。"""
    return EffectivePermissionsView(**await svc.get_effective_permissions(db, user_id))


@router.get("/me/effective", response_model=EffectivePermissionsView)
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.permission.read")),
):
    """使用者查自己的權限（不需 organization.user.read）。"""
    if user.is_superuser:
        # demo / super 直接回傳 wildcard 視圖
        return EffectivePermissionsView(
            user_id=user.user_id,
            roles=[{"role_code": "super_admin", "tenant_id": user.tenant_id}],
            permissions=[{"code": "*", "scope": "all"}],
            overrides=[],
        )
    return EffectivePermissionsView(**await svc.get_effective_permissions(db, user.user_id))

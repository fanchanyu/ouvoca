"""權限管理 service — 角色 CRUD、授權、稽核。

商業化重點：
- 預設角色模板（從 seed 載入後可複製）
- 一鍵授權（assign role to user）
- 時效授權（自動到期）
- 變更稽核
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.security import invalidate_user_cache, audit_permission_change
from app.events import EventBus, DomainEvent
from app.models.permission import (
    Tenant, PermissionDef, RoleDef, RolePermissionLink,
    UserRoleAssignment, PermissionOverride,
)


# ============================================================
# Tenant
# ============================================================

async def create_tenant(db: AsyncSession, data: dict) -> Tenant:
    t = Tenant(id=str(uuid.uuid4()), **data)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def list_tenants(db: AsyncSession, tenant_type: Optional[str] = None) -> List[Tenant]:
    q = select(Tenant).where(Tenant.is_active == True)  # noqa: E712
    if tenant_type:
        q = q.where(Tenant.tenant_type == tenant_type)
    return list((await db.execute(q.order_by(Tenant.code))).scalars().all())


# ============================================================
# Permission Defs
# ============================================================

async def list_permissions(
    db: AsyncSession,
    module: Optional[str] = None,
    resource: Optional[str] = None,
) -> List[PermissionDef]:
    q = select(PermissionDef)
    if module:
        q = q.where(PermissionDef.module == module)
    if resource:
        q = q.where(PermissionDef.resource == resource)
    return list((await db.execute(q.order_by(PermissionDef.code))).scalars().all())


async def get_permission_by_code(db: AsyncSession, code: str) -> Optional[PermissionDef]:
    return (await db.execute(
        select(PermissionDef).where(PermissionDef.code == code)
    )).scalar_one_or_none()


# ============================================================
# Roles
# ============================================================

async def create_role(
    db: AsyncSession,
    data: dict,
    actor_id: str,
    permissions: Optional[List[dict]] = None,
) -> RoleDef:
    """建立角色 + 直接綁定權限。

    permissions: [{"code": "sales.order.read", "scope": "own"}, ...]
    """
    role = RoleDef(id=str(uuid.uuid4()), **data)
    db.add(role)
    await db.flush()

    if permissions:
        for perm_spec in permissions:
            perm = await get_permission_by_code(db, perm_spec["code"])
            if not perm:
                raise NotFoundError(f"權限不存在：{perm_spec['code']}")
            db.add(RolePermissionLink(
                id=str(uuid.uuid4()),
                role_id=role.id,
                permission_id=perm.id,
                scope=perm_spec.get("scope", "tenant"),
                conditions=perm_spec.get("conditions"),
            ))

    await db.commit()
    await db.refresh(role)
    await audit_permission_change(
        db, actor_id=actor_id, change_type="create_role",
        target_role_id=role.id,
        after_state={"code": role.code, "name_zh": role.name_zh,
                     "permissions": permissions or []},
    )
    await db.commit()
    return role


async def get_role(db: AsyncSession, role_id: str) -> Optional[RoleDef]:
    q = select(RoleDef).options(
        selectinload(RoleDef.role_perms).selectinload(RolePermissionLink.permission)
    ).where(RoleDef.id == role_id)
    return (await db.execute(q)).scalar_one_or_none()


async def list_roles(
    db: AsyncSession,
    tenant_id: Optional[str] = None,
    include_system: bool = True,
) -> List[RoleDef]:
    q = select(RoleDef).where(RoleDef.is_active == True)  # noqa: E712
    if tenant_id:
        from sqlalchemy import or_
        q = q.where(or_(RoleDef.tenant_id == tenant_id, RoleDef.tenant_id.is_(None)))
    if not include_system:
        q = q.where(RoleDef.is_system == False)  # noqa: E712
    return list((await db.execute(q.order_by(RoleDef.priority.desc(), RoleDef.code))).scalars().all())


async def update_role_permissions(
    db: AsyncSession,
    role_id: str,
    permissions: List[dict],
    actor_id: str,
) -> RoleDef:
    """覆寫角色的權限清單。

    permissions: [{"code": "sales.order.read", "scope": "own"}, ...]
    """
    role = await get_role(db, role_id)
    if not role:
        raise NotFoundError("角色不存在", role_id=role_id)
    if role.is_system:
        raise BusinessRuleError("系統內建角色不可直接修改，請複製後再改", role=role.code)

    before = [{"code": rp.permission.code, "scope": rp.scope} for rp in role.role_perms]

    # Clear existing
    for rp in role.role_perms:
        await db.delete(rp)
    await db.flush()

    # Add new
    for perm_spec in permissions:
        perm = await get_permission_by_code(db, perm_spec["code"])
        if not perm:
            raise NotFoundError(f"權限不存在：{perm_spec['code']}")
        db.add(RolePermissionLink(
            id=str(uuid.uuid4()),
            role_id=role.id,
            permission_id=perm.id,
            scope=perm_spec.get("scope", "tenant"),
            conditions=perm_spec.get("conditions"),
        ))
    await db.commit()
    await audit_permission_change(
        db, actor_id=actor_id, change_type="modify_role_permissions",
        target_role_id=role.id,
        before_state={"permissions": before},
        after_state={"permissions": permissions},
    )
    await db.commit()

    # Invalidate cache for all users having this role
    user_ids_q = await db.execute(
        select(UserRoleAssignment.user_id).where(UserRoleAssignment.role_id == role.id)
    )
    for (uid,) in user_ids_q.all():
        invalidate_user_cache(uid)

    return role


async def clone_role(db: AsyncSession, source_role_id: str, new_code: str, new_name_zh: str,
                     actor_id: str, tenant_id: Optional[str] = None) -> RoleDef:
    """複製一個角色（含全部權限），用於從系統模板派生客製角色。"""
    source = await get_role(db, source_role_id)
    if not source:
        raise NotFoundError("來源角色不存在")
    permissions = [
        {"code": rp.permission.code, "scope": rp.scope, "conditions": rp.conditions}
        for rp in source.role_perms
    ]
    return await create_role(
        db,
        {
            "tenant_id": tenant_id,
            "code": new_code,
            "name_zh": new_name_zh,
            "description": f"從 {source.code} 複製",
            "is_system": False,
            "priority": source.priority,
            "icon": source.icon,
            "color": source.color,
        },
        actor_id=actor_id,
        permissions=permissions,
    )


# ============================================================
# User-Role Assignment
# ============================================================

async def assign_role(
    db: AsyncSession,
    user_id: str,
    role_id: str,
    tenant_id: str,
    actor_id: str,
    expires_at: Optional[datetime] = None,
    reason: Optional[str] = None,
    delegation_from: Optional[str] = None,
) -> UserRoleAssignment:
    # 查 user 是否已有此 role × tenant
    existing = (await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.tenant_id == tenant_id,
            UserRoleAssignment.is_active == True,  # noqa: E712
        )
    )).scalar_one_or_none()
    if existing:
        raise BusinessRuleError("使用者已擁有此角色")

    assign = UserRoleAssignment(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role_id=role_id,
        tenant_id=tenant_id,
        granted_by=actor_id,
        expires_at=expires_at,
        delegation_from=delegation_from,
        reason=reason,
    )
    db.add(assign)
    await db.commit()
    await db.refresh(assign)

    invalidate_user_cache(user_id)
    await audit_permission_change(
        db, actor_id=actor_id, change_type="grant_role",
        target_user_id=user_id,
        after_state={"role_id": role_id, "tenant_id": tenant_id,
                     "expires_at": str(expires_at) if expires_at else None,
                     "reason": reason},
    )
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="permission.role_granted", domain="permission",
        entity_type="UserRoleAssignment", entity_id=assign.id,
        data={"user_id": user_id, "role_id": role_id, "by": actor_id},
    ))
    return assign


async def revoke_role(
    db: AsyncSession, assignment_id: str, actor_id: str, reason: Optional[str] = None,
) -> UserRoleAssignment:
    a = (await db.execute(
        select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
    )).scalar_one_or_none()
    if not a:
        raise NotFoundError("授權記錄不存在")
    a.is_active = False
    await db.commit()
    invalidate_user_cache(a.user_id)
    await audit_permission_change(
        db, actor_id=actor_id, change_type="revoke_role",
        target_user_id=a.user_id,
        before_state={"role_id": a.role_id, "tenant_id": a.tenant_id},
        after_state={"reason": reason},
    )
    await db.commit()
    return a


async def list_user_roles(db: AsyncSession, user_id: str) -> List[UserRoleAssignment]:
    q = (
        select(UserRoleAssignment)
        .options(selectinload(UserRoleAssignment.role), selectinload(UserRoleAssignment.tenant))
        .where(UserRoleAssignment.user_id == user_id, UserRoleAssignment.is_active == True)  # noqa: E712
    )
    return list((await db.execute(q)).scalars().all())


# ============================================================
# Permission Override
# ============================================================

async def grant_override(
    db: AsyncSession, user_id: str, permission_code: str,
    actor_id: str, reason: str,
    expires_at: Optional[datetime] = None,
    grant_or_revoke: str = "grant",
    resource_type: Optional[str] = None, resource_id: Optional[str] = None,
) -> PermissionOverride:
    ov = PermissionOverride(
        id=str(uuid.uuid4()),
        user_id=user_id,
        permission_code=permission_code,
        grant_or_revoke=grant_or_revoke,
        resource_type=resource_type,
        resource_id=resource_id,
        granted_by=actor_id,
        expires_at=expires_at,
        reason=reason,
    )
    db.add(ov)
    await db.commit()
    invalidate_user_cache(user_id)
    await audit_permission_change(
        db, actor_id=actor_id, change_type=f"{grant_or_revoke}_permission",
        target_user_id=user_id,
        after_state={"code": permission_code, "expires_at": str(expires_at) if expires_at else None,
                     "reason": reason},
    )
    await db.commit()
    return ov


async def list_user_overrides(db: AsyncSession, user_id: str) -> List[PermissionOverride]:
    q = select(PermissionOverride).where(
        PermissionOverride.user_id == user_id,
        PermissionOverride.is_active == True,  # noqa: E712
    )
    return list((await db.execute(q)).scalars().all())


# ============================================================
# 查詢：列出使用者所有效權限（含 role + override）
# ============================================================

async def get_effective_permissions(db: AsyncSession, user_id: str) -> dict:
    """回傳使用者所有效權限的完整視圖（給 UI 用）。

    回傳格式:
      {
        "user_id": "...",
        "roles": [{"role_id": "...", "role_code": "sales_rep", ...}],
        "permissions": [{"code": "...", "scope": "own", "source": "role:sales_rep"}, ...],
        "overrides": [{"code": "...", "type": "grant", ...}]
      }
    """
    from app.core.security import get_user_permissions

    perms_map = await get_user_permissions(db, user_id, fresh=True)
    roles = await list_user_roles(db, user_id)
    overrides = await list_user_overrides(db, user_id)

    return {
        "user_id": user_id,
        "roles": [
            {
                "role_code": r.role.code,
                "granted_at": r.granted_at,
                "granted_by": r.granted_by,
                "scope": r.tenant_id,
            }
            for r in roles
        ],
        "permissions": [
            {
                "permission_code": code,
                "source": "role",
                "role_code": None,
            }
            for code, scope in sorted(perms_map.items())
        ],
        "overrides": [
            {
                "permission_code": o.permission_code,
                "grant_or_deny": o.grant_or_revoke,
                "reason": o.reason,
                "granted_by": None,
            }
            for o in overrides
        ],
    }

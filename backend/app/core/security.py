"""核心安全模組：權限檢查 + Row-Level Filter。

設計重點
--------
- **單次 query 載入**：使用者所有效權限一次撈出，後續純記憶體判斷
- **5 分鐘 TTL cache**：權限變動少、查詢密集，快取大幅降低 DB 壓力
- **FastAPI Dependency 風格**：`Depends(require_permission("sales.order.create"))`
- **Wildcard 支援**：`sales.*` / `*.read` / `*`
- **Demo bypass 兼容**：demo-admin 視為 super_admin

對應設計：docs/PERMISSION_MODEL.md §7
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Request
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.logging import get_logger

log = get_logger(__name__)

# ============================================================
# UserContext — 已認證使用者的權限快照
# ============================================================

@dataclass
class UserContext:
    """單次請求中的權限上下文。

    從 JWT + DB 載入後快取於 request.state.user_ctx。
    """
    user_id: str
    employee_id: str
    username: str
    tenant_id: str  # 當前操作的 tenant
    is_superuser: bool = False
    permissions: dict[str, str] = field(default_factory=dict)  # {permission_code: scope}
    department_id: Optional[str] = None
    raw_user: dict = field(default_factory=dict)  # 原始 JWT payload

    def has(self, code: str) -> bool:
        """檢查是否擁有某權限（含 wildcard）。"""
        if self.is_superuser:
            return True
        if code in self.permissions:
            return True
        # Wildcard：sales.order.create → 試 sales.order.* / sales.* / *
        parts = code.split(".")
        for i in range(len(parts) - 1, -1, -1):
            wildcard = ".".join(parts[:i]) + (".*" if i else "*")
            if wildcard in self.permissions:
                return True
        return False

    def scope_for(self, code: str) -> str:
        """取得某權限的 row-level scope。"""
        if self.is_superuser:
            return "all"
        if code in self.permissions:
            return self.permissions[code]
        # Wildcard 沿用最寬鬆 scope
        parts = code.split(".")
        for i in range(len(parts) - 1, -1, -1):
            wildcard = ".".join(parts[:i]) + (".*" if i else "*")
            if wildcard in self.permissions:
                return self.permissions[wildcard]
        return "none"


# ============================================================
# 權限快取 — process-local TTL cache
# ============================================================

_PERMISSION_CACHE: dict[str, tuple[float, dict[str, str]]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def invalidate_user_cache(user_id: str) -> None:
    """權限變更時呼叫，清掉該 user 快取。"""
    _PERMISSION_CACHE.pop(user_id, None)


def invalidate_all() -> None:
    """全域權限變更（如角色定義改變）時清全部快取。"""
    _PERMISSION_CACHE.clear()


async def _load_user_permissions(db: AsyncSession, user_id: str) -> dict[str, str]:
    """從 DB 載入使用者所有效權限 → {permission_code: scope}。

    一次 JOIN query 完成，效能 O(N) for N permissions of this user。

    優先順序（後者覆蓋前者）：
      1. 角色帶來的權限（含時效檢查）
      2. permission_overrides：grant → 加入
      3. permission_overrides：revoke → 移除
    """
    from app.models.permission import (
        UserRoleAssignment, RolePermissionLink, PermissionDef, PermissionOverride,
    )
    from datetime import datetime, UTC

    now = datetime.now(UTC).replace(tzinfo=None)
    result: dict[str, str] = {}

    # 1) Role-based permissions
    q = (
        select(PermissionDef.code, RolePermissionLink.scope)
        .join(RolePermissionLink, RolePermissionLink.permission_id == PermissionDef.id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == RolePermissionLink.role_id)
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.is_active == True,  # noqa: E712
            or_(
                UserRoleAssignment.expires_at.is_(None),
                UserRoleAssignment.expires_at > now,
            ),
        )
    )
    rows = (await db.execute(q)).all()
    for code, scope in rows:
        # 同一 code 多角色時取最寬 scope（簡單規則：all > tenant > department > own）
        if code not in result or _scope_rank(scope) > _scope_rank(result[code]):
            result[code] = scope

    # 2) Apply individual grants
    grant_q = select(PermissionOverride).where(
        PermissionOverride.user_id == user_id,
        PermissionOverride.is_active == True,  # noqa: E712
        PermissionOverride.grant_or_revoke == "grant",
        or_(
            PermissionOverride.expires_at.is_(None),
            PermissionOverride.expires_at > now,
        ),
    )
    for ov in (await db.execute(grant_q)).scalars().all():
        result[ov.permission_code] = "tenant"  # 預設 scope（可未來擴充）

    # 3) Apply individual revokes
    revoke_q = select(PermissionOverride).where(
        PermissionOverride.user_id == user_id,
        PermissionOverride.is_active == True,  # noqa: E712
        PermissionOverride.grant_or_revoke == "revoke",
        or_(
            PermissionOverride.expires_at.is_(None),
            PermissionOverride.expires_at > now,
        ),
    )
    for ov in (await db.execute(revoke_q)).scalars().all():
        result.pop(ov.permission_code, None)

    return result


_SCOPE_RANK = {"none": 0, "assigned": 1, "own": 2, "team": 3, "department": 4, "tenant": 5, "all": 6}


def _scope_rank(scope: str) -> int:
    return _SCOPE_RANK.get(scope, 0)


async def get_user_permissions(db: AsyncSession, user_id: str, fresh: bool = False) -> dict[str, str]:
    """取得（含快取）使用者權限對照表。"""
    now = time.time()
    cached = _PERMISSION_CACHE.get(user_id)
    if not fresh and cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]
    perms = await _load_user_permissions(db, user_id)
    _PERMISSION_CACHE[user_id] = (now, perms)
    return perms


# ============================================================
# UserContext 載入 — 從 request.state.user (JWT) → 完整權限上下文
# ============================================================

async def load_user_context(request: Request, db: AsyncSession) -> UserContext:
    """從已驗證的 JWT 載入完整使用者上下文（含權限）。

    若已快取於 request.state.user_ctx，直接回傳。
    """
    cached = getattr(request.state, "user_ctx", None)
    if cached is not None:
        return cached

    raw = getattr(request.state, "user", None)
    if not raw:
        raise AuthenticationError("尚未登入")

    # Demo bypass: demo-admin → super-admin context（不查 DB）
    # F-6：production 環境（DEBUG=False 且 ALLOW_DEMO_BYPASS=False）一律擋掉，
    # 避免 JWT_SECRET 外洩時惡意人偽造 employee_id="demo-admin" 拿到 super-admin。
    employee_id = raw.get("employee_id")
    if employee_id == "demo-admin":
        from app.config import settings
        if not settings.DEBUG and not settings.ALLOW_DEMO_BYPASS:
            log.warning(
                "demo-admin bypass blocked in production: ip=%s ua=%s",
                getattr(request.client, "host", None) if request.client else None,
                request.headers.get("user-agent"),
            )
            raise AuthenticationError("demo-admin bypass disabled in production")
        ctx = UserContext(
            user_id="demo-admin",
            employee_id="demo-admin",
            username=raw.get("username", "demo"),
            tenant_id="HQ",
            is_superuser=True,
            raw_user=raw,
        )
        request.state.user_ctx = ctx
        from app.core.tenant_context import set_current_tenant
        set_current_tenant("HQ")
        return ctx

    # 真實使用者：依 employee_id 找 User
    from app.models.organization import User
    from app.models.permission import UserRoleAssignment

    user_q = select(User).where(User.employee_id == employee_id)
    user = (await db.execute(user_q)).scalar_one_or_none()
    if not user:
        raise AuthenticationError("使用者不存在", employee_id=employee_id)

    # 載入 tenant_id（取第一個有效的 UserRoleAssignment 的 tenant）
    tenant_q = (
        select(UserRoleAssignment.tenant_id)
        .where(UserRoleAssignment.user_id == user.id, UserRoleAssignment.is_active == True)  # noqa: E712
        .limit(1)
    )
    tenant_id = (await db.execute(tenant_q)).scalar_one_or_none() or "HQ"

    permissions = await get_user_permissions(db, user.id)

    ctx = UserContext(
        user_id=user.id,
        employee_id=user.employee_id,
        username=user.username,
        tenant_id=tenant_id,
        is_superuser=user.is_superuser,
        permissions=permissions,
        raw_user=raw,
    )
    request.state.user_ctx = ctx
    from app.core.tenant_context import set_current_tenant
    set_current_tenant(tenant_id)
    return ctx


# ============================================================
# Dependency: require_permission — 用於 FastAPI 路由保護
# ============================================================

def require_permission(*codes: str):
    """FastAPI Dependency 工廠：要求使用者具備所有指定權限。

    用法：
        @router.post("/sales/orders")
        async def create_so(
            data: SalesOrderCreate,
            db: AsyncSession = Depends(get_db),
            user: UserContext = Depends(require_permission("sales.order.create")),
        ):
            ...

    若要任一即可（OR 語意），請用 `require_any_permission`。
    """
    from fastapi import Depends
    from app.database import get_db

    async def _checker(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> UserContext:
        ctx = await load_user_context(request, db)
        for code in codes:
            if not ctx.has(code):
                log.info(
                    "Permission denied: user=%s code=%s scope=%s",
                    ctx.username, code, ctx.scope_for(code),
                )
                raise PermissionDeniedError(
                    f"缺少權限：{code}",
                    required=list(codes),
                    user=ctx.username,
                )
        return ctx

    return _checker


def require_any_permission(*codes: str):
    """任一權限即可（OR 語意）。"""
    from fastapi import Depends
    from app.database import get_db

    async def _checker(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> UserContext:
        ctx = await load_user_context(request, db)
        if any(ctx.has(c) for c in codes):
            return ctx
        raise PermissionDeniedError(
            f"缺少權限（任一）：{codes}",
            required=list(codes),
            user=ctx.username,
        )

    return _checker


# ============================================================
# Row-Level Filter — 自動加 WHERE 條件
# ============================================================

def apply_tenant_filter(query, model_class, ctx: UserContext):
    """強制依 tenant_id filter — 多廠/多租戶 SaaS 隔離的命脈。

    用法：
        query = select(Part)
        query = apply_tenant_filter(query, Part, ctx)

    規則：
    - ctx.tenant_id 為何，就 filter 為何（不可越界）
    - **即使 is_superuser=True 也不能跨 tenant 看別人的資料**
      （superuser 是「該 tenant 內」的最高權限，不是「全租戶」）
    - 唯一例外：顯式擁有 `tenant.cross` 權限（透過 RolePermissionLink 給）
    - 對無 tenant_id 欄位的 model（如 Tenant 自己、PermissionDef）不 filter

    這是 multi-tenant SaaS 的「最後一道防線」。
    比 RBAC 更底層 — 連 RBAC 表都應該過這層。
    """
    if not hasattr(model_class, "tenant_id"):
        return query  # 此 model 沒有 tenant_id 欄位（如系統表）

    # 顯式 tenant.cross 權限（不能靠 is_superuser bypass）
    # 直接看 permissions dict，不走 ctx.has()（會被 is_superuser 短路）
    if "tenant.cross" in ctx.permissions:
        return query

    target_tenant = ctx.tenant_id or "HQ"
    return query.where(model_class.tenant_id == target_tenant)


def apply_row_filter(
    query, ctx: UserContext, resource: str,
    *,
    created_by_column: str = "created_by",
    tenant_column: str = "tenant_id",
    assigned_column: str = "assigned_to",
    department_column: Optional[str] = None,
):
    """依使用者對 resource 的 scope 自動加 WHERE 條件。

    用法：
        query = select(SalesOrder)
        query = apply_row_filter(query, ctx, "sales.order")
        results = (await db.execute(query)).scalars().all()

    Scope 規則：
      - all:        無條件
      - tenant:     tenant_id = ctx.tenant_id
      - department: department 邏輯（需提供 department_column）
      - own:        created_by = ctx.employee_id
      - assigned:   assigned_to = ctx.employee_id
      - none:       永遠不匹配（user 沒這權限的 list scope）
    """
    # 找出該 resource 的所有 action permissions，取 list / read 的 scope（最常用）
    # 簡化：用 resource.list 或 resource.read 的 scope
    list_scope = ctx.scope_for(f"{resource}.list") or ctx.scope_for(f"{resource}.read")

    # Look up the underlying SQL entity
    entity = query.column_descriptions[0]["entity"] if query.column_descriptions else None
    if entity is None:
        return query

    if list_scope == "all":
        return query
    if list_scope == "tenant":
        col = getattr(entity, tenant_column, None)
        if col is not None:
            return query.where(col == ctx.tenant_id)
        return query  # 表沒 tenant_id 欄位則不過濾
    if list_scope == "own":
        col = getattr(entity, created_by_column, None)
        if col is not None:
            return query.where(col == ctx.employee_id)
        return query.where(False)  # 沒這欄位，安全起見回空
    if list_scope == "assigned":
        col = getattr(entity, assigned_column, None)
        if col is not None:
            return query.where(col == ctx.employee_id)
        return query.where(False)
    if list_scope == "department" and department_column:
        col = getattr(entity, department_column, None)
        if col is not None and ctx.department_id:
            return query.where(col == ctx.department_id)
        return query.where(False)
    if list_scope == "none":
        return query.where(False)
    # 預設保守：tenant 隔離
    col = getattr(entity, tenant_column, None)
    if col is not None:
        return query.where(col == ctx.tenant_id)
    return query


# ============================================================
# Audit Helper
# ============================================================

async def audit_permission_change(
    db: AsyncSession,
    actor_id: str,
    change_type: str,
    target_user_id: Optional[str] = None,
    target_role_id: Optional[str] = None,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> None:
    """記錄一筆權限變更到 permission_audit。"""
    from app.models.permission import PermissionAudit
    import uuid

    rec = PermissionAudit(
        id=str(uuid.uuid4()),
        actor_id=actor_id,
        target_user_id=target_user_id,
        target_role_id=target_role_id,
        change_type=change_type,
        before_state=before_state,
        after_state=after_state,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(rec)
    # commit 由呼叫方負責

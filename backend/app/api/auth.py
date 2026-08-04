"""Auth + Organization API — login 公開、其餘加 RBAC。"""
import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import require_permission, UserContext
from app.core.rate_limit import limiter, RATE_LIMITS
from app.schemas.organization import (
    DepartmentCreate, DepartmentResponse,
    EmployeeCreate, EmployeeResponse,
    UserCreate, UserLogin, UserResponse, TokenResponse,
    RoleCreate, RoleResponse,
)
from app.services.auth import (
    hash_password, verify_password, create_token,
    is_login_locked, record_failed_login, reset_login_attempts,
    mfa_challenge_token, verify_totp, generate_mfa_secret,
)
from app.models.organization import Department, Employee, User, Role

router = APIRouter(prefix="/api/auth", tags=["Auth"])
org_router = APIRouter(prefix="/api/organization", tags=["Organization"])


# ─── Auth：公開 ─────────────────────────────────────────
@router.post("/login")
@limiter.limit(RATE_LIMITS["auth_login"])
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    # v3.62：暴力破解鎖定 — 鎖定期間直接拒絕（連「帳號錯誤」都不同時揭露）
    if user is not None and is_login_locked(user):
        raise HTTPException(429, "嘗試次數過多，帳號已暫時鎖定，請 15 分鐘後再試")
    if not user or not verify_password(data.password, user.hashed_password):
        if user is not None:
            await record_failed_login(db, user)
        raise HTTPException(401, "帳號或密碼錯誤")
    await reset_login_attempts(db, user)
    if not user.is_active:
        raise HTTPException(403, "帳號已停用")

    # v3.64 MFA：啟用 MFA 的使用者先發挑戰 token，驗證 TOTP 後才給正式 token
    if user.mfa_enabled:
        return {
            "mfa_required": True,
            "mfa_token": mfa_challenge_token(user),
            "user": {"username": user.username},
        }

    # ⚠️ 修正：只取「此使用者實際擁有」的角色（透過 UserRoleAssignment）
    # 早期 bug 會把 DB 所有 Role 都塞進 JWT，安全與正確性都有問題
    from app.models.permission import UserRoleAssignment, RoleDef
    from datetime import datetime as _dt
    role_q = (
        select(RoleDef.code)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == RoleDef.id)
        .where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.is_active == True,  # noqa: E712
        )
    )
    user_roles = [row[0] for row in (await db.execute(role_q)).all()]
    token = create_token({
        "sub": user.employee_id,
        "username": user.username,
        "roles": user_roles,  # 只放此使用者真正擁有的角色 code
        "permissions": [],     # 權限走 RBAC，不放 JWT（避免 token 過大）
        "ver": user.token_version or 0,  # v3.62：改密碼後舊 token 失效
    })
    user.last_login = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, username=user.username, employee_id=user.employee_id,
            is_superuser=user.is_superuser, is_active=user.is_active,
            last_login=user.last_login,
        ),
    )


@router.post("/mfa/verify")
@limiter.limit(RATE_LIMITS["auth_login"])
async def mfa_verify(request: Request, data: dict, db: AsyncSession = Depends(get_db)):
    """第二步：驗證 TOTP code，換發正式 access token。"""
    from jose import JWTError
    from app.services.auth import decode_token
    mfa_token = data.get("mfa_token") or ""
    code = data.get("code") or ""
    try:
        payload = decode_token(mfa_token)
    except JWTError:
        raise HTTPException(401, "MFA 挑戰已失效，請重新登入")
    if not payload.get("mfa_pending"):
        raise HTTPException(401, "Token 不是 MFA 挑戰")

    user = (await db.execute(
        select(User).where(User.employee_id == payload.get("sub"))
    )).scalar_one_or_none()
    # 健檢 #13：MFA 驗證失敗也計入登入鎖定（防 TOTP 暴力猜測）
    if user is not None and is_login_locked(user):
        raise HTTPException(429, "嘗試次數過多，帳號已暫時鎖定，請 15 分鐘後再試")
    if user is None or not verify_totp(user.mfa_secret or "", code):
        if user is not None:
            await record_failed_login(db, user)
        raise HTTPException(401, "驗證碼錯誤")

    from app.models.permission import UserRoleAssignment, RoleDef
    role_q = (
        select(RoleDef.code)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == RoleDef.id)
        .where(UserRoleAssignment.user_id == user.id,
               UserRoleAssignment.is_active == True)  # noqa: E712
    )
    user_roles = [row[0] for row in (await db.execute(role_q)).all()]
    token = create_token({
        "sub": user.employee_id,
        "username": user.username,
        "roles": user_roles,
        "permissions": [],
        "ver": user.token_version or 0,
    })
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, username=user.username, employee_id=user.employee_id,
            is_superuser=user.is_superuser, is_active=user.is_active,
            last_login=user.last_login,
        ),
    )


@router.post("/mfa/setup")
async def mfa_setup(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("user.profile.read")),
):
    """取得 TOTP secret（尚未啟用）。"""
    u = (await db.execute(select(User).where(User.id == user.user_id))).scalar_one_or_none()
    if u is None:
        raise HTTPException(404, "使用者不存在")
    if not u.mfa_secret:
        u.mfa_secret = generate_mfa_secret()
        await db.commit()
    import pyotp
    otpauth = pyotp.totp.TOTP(u.mfa_secret).provisioning_uri(
        name=u.username, issuer_name="Ouvoca ERP",
    )
    return {"secret": u.mfa_secret, "otpauth_url": otpauth, "enabled": u.mfa_enabled}


@router.post("/mfa/enable")
async def mfa_enable(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("user.profile.read")),
):
    u = (await db.execute(select(User).where(User.id == user.user_id))).scalar_one_or_none()
    if u is None or not u.mfa_secret:
        raise HTTPException(400, "請先呼叫 /mfa/setup 取得 secret")
    if not verify_totp(u.mfa_secret, data.get("code", "")):
        raise HTTPException(401, "驗證碼錯誤")
    u.mfa_enabled = True
    await db.commit()
    return {"enabled": True, "message": "MFA 已啟用"}


@router.post("/mfa/disable")
async def mfa_disable(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("user.profile.read")),
):
    u = (await db.execute(select(User).where(User.id == user.user_id))).scalar_one_or_none()
    if u is None or not u.mfa_enabled:
        raise HTTPException(400, "MFA 未啟用")
    if not verify_totp(u.mfa_secret or "", data.get("code", "")):
        raise HTTPException(401, "驗證碼錯誤")
    u.mfa_enabled = False
    u.mfa_secret = None
    await db.commit()
    return {"enabled": False, "message": "MFA 已停用"}


@router.post("/register", response_model=UserResponse)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.user.create")),
):
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "帳號已存在")
    u = User(
        id=str(uuid.uuid4()), username=data.username,
        hashed_password=hash_password(data.password),
        employee_id=data.employee_id,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return UserResponse(
        id=u.id, username=u.username, employee_id=u.employee_id,
        is_superuser=u.is_superuser, is_active=u.is_active,
    )


# ─── Organization：RBAC 保護 ────────────────────────────
@org_router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.employee.create")),
):
    dept = Department(id=str(uuid.uuid4()), **data.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return DepartmentResponse.model_validate(dept)


@org_router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.employee.list")),
):
    result = await db.execute(select(Department))
    return [DepartmentResponse.model_validate(d) for d in result.scalars().all()]


@org_router.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.employee.create")),
):
    emp = Employee(id=str(uuid.uuid4()), **data.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return EmployeeResponse.model_validate(emp)


@org_router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.employee.list")),
):
    result = await db.execute(select(Employee))
    return [EmployeeResponse.model_validate(e) for e in result.scalars().all()]


# 舊版相容：org/roles 仍然存在但建議改用 /api/permission/roles
@org_router.post("/roles", response_model=RoleResponse)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.role.create")),
):
    role = Role(id=str(uuid.uuid4()), **data.model_dump())
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return RoleResponse.model_validate(role)


@org_router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.role.list")),
):
    result = await db.execute(select(Role))
    return [RoleResponse.model_validate(r) for r in result.scalars().all()]

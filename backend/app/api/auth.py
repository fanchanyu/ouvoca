"""Auth + Organization API — login 公開、其餘加 RBAC。"""
import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import require_permission, UserContext
from app.schemas.organization import (
    DepartmentCreate, DepartmentResponse,
    EmployeeCreate, EmployeeResponse,
    UserCreate, UserLogin, UserResponse, TokenResponse,
    RoleCreate, RoleResponse,
)
from app.services.auth import hash_password, verify_password, create_token
from app.models.organization import Department, Employee, User, Role

router = APIRouter(prefix="/api/auth", tags=["Auth"])
org_router = APIRouter(prefix="/api/organization", tags=["Organization"])


# ─── Auth：公開 ─────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "帳號或密碼錯誤")
    if not user.is_active:
        raise HTTPException(403, "帳號已停用")

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


@router.post("/register", response_model=UserResponse)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("organization.user.read")),
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

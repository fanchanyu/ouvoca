from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class EmployeeRoleType(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    SUPERVISOR = "supervisor"
    OPERATOR = "operator"
    INSPECTOR = "inspector"
    PLANNER = "planner"
    SALES = "sales"
    PURCHASER = "purchaser"


class DepartmentCreate(BaseModel):
    name: str
    code: str
    parent_id: Optional[str] = None
    manager_id: Optional[str] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    manager_id: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: str
    parent_id: Optional[str] = None
    manager_id: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    employee_no: str
    name: str
    email: str
    phone: Optional[str] = None
    department_id: str
    manager_id: Optional[str] = None
    title: Optional[str] = None
    hire_date: Optional[datetime] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[str] = None
    manager_id: Optional[str] = None
    title: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeResponse(BaseModel):
    id: str
    employee_no: str
    name: str
    email: str
    phone: Optional[str] = None
    department_id: str
    manager_id: Optional[str] = None
    title: Optional[str] = None
    hire_date: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    employee_id: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    employee_id: str
    is_superuser: bool
    is_active: bool
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None

class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    code: str
    name: str
    resource: str
    action: str

class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    resource: str
    action: str

    class Config:
        from_attributes = True


class ApprovalFlowCreate(BaseModel):
    name: str
    entity_type: str
    steps: List[dict]

class ApprovalFlowResponse(BaseModel):
    id: str
    name: str
    entity_type: str
    steps: Any
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalRequestCreate(BaseModel):
    flow_id: str
    entity_type: str
    entity_id: str

class ApprovalRequestResponse(BaseModel):
    id: str
    flow_id: str
    entity_type: str
    entity_id: str
    status: str
    current_step: int
    submitted_at: datetime

    class Config:
        from_attributes = True


class ApprovalRecordCreate(BaseModel):
    request_id: str
    step: int
    approver_id: str
    status: str
    comment: Optional[str] = None

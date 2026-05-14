import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, JSON, Table, Enum
from sqlalchemy.orm import relationship
from app.core.base import Base

import enum


class EmployeeRoleType(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    SUPERVISOR = "supervisor"
    OPERATOR = "operator"
    INSPECTOR = "inspector"
    PLANNER = "planner"
    SALES = "sales"
    PURCHASER = "purchaser"


employee_roles = Table(
    "employee_roles",
    Base.metadata,
    Column("employee_id", String(36), ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    parent_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    manager_id = Column(String(36), ForeignKey("employees.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Department", remote_side=[id], backref="children")
    employees = relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")
    manager = relationship("Employee", foreign_keys=[manager_id], post_update=True)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_no = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone = Column(String(30))
    department_id = Column(String(36), ForeignKey("departments.id"))
    manager_id = Column(String(36), ForeignKey("employees.id"), nullable=True)
    title = Column(String(100))
    hire_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    manager = relationship("Employee", remote_side=[id], backref="subordinates")
    user = relationship("User", back_populates="employee", uselist=False)
    roles = relationship("Role", secondary=employee_roles, back_populates="employees")
    approval_records = relationship("ApprovalRecord", back_populates="approver", foreign_keys="ApprovalRecord.approver_id")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    employee_id = Column(String(36), ForeignKey("employees.id"), unique=True, nullable=False)
    is_superuser = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", secondary=employee_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class ApprovalFlow(Base):
    __tablename__ = "approval_flows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    steps = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(36), ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_id = Column(String(36), ForeignKey("approval_flows.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    status = Column(String(20), default="pending")
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    submitted_by = Column(String(36), ForeignKey("employees.id"))
    submitted_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    flow = relationship("ApprovalFlow")
    records = relationship("ApprovalRecord", back_populates="request", cascade="all, delete-orphan")


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False)
    step = Column(Integer, nullable=False)
    approver_id = Column(String(36), ForeignKey("employees.id"))
    status = Column(String(20), default="pending")
    comment = Column(Text)
    decided_at = Column(DateTime)

    request = relationship("ApprovalRequest", back_populates="records")
    approver = relationship("Employee", back_populates="approval_records", foreign_keys=[approver_id])

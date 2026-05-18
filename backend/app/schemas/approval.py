"""Approval Workflow schemas (v3.22)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ── 規則 ────────────────────────────────────────────────────
class ApprovalRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    trigger_type: str = Field(..., description="po | so | payment")
    condition_field: str = Field(..., description="amount | discount_pct")
    condition_op: str = Field("gt", description="gt | gte | lt | lte | eq")
    condition_value: float
    approver_role: str = Field(..., min_length=1, max_length=40)
    stages: int = Field(1, ge=1, le=5)
    is_active: bool = True

    @field_validator("trigger_type")
    @classmethod
    def _ttype(cls, v: str) -> str:
        if v not in {"po", "so", "payment"}:
            raise ValueError(f"trigger_type must be po/so/payment, got {v!r}")
        return v

    @field_validator("condition_op")
    @classmethod
    def _op(cls, v: str) -> str:
        if v not in {"gt", "gte", "lt", "lte", "eq"}:
            raise ValueError(f"condition_op invalid: {v!r}")
        return v


class ApprovalRuleResponse(BaseModel):
    id: str
    name: str
    trigger_type: str
    condition_field: str
    condition_op: str
    condition_value: float
    approver_role: str
    stages: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── 步驟 ─────────────────────────────────────────────────
class ApprovalStepResponse(BaseModel):
    id: str
    stage: int
    approver_id: Optional[str] = None
    approver_username: Optional[str] = None
    action: str
    comment: Optional[str] = None
    decided_at: datetime

    class Config:
        from_attributes = True


# ── 申請單 ─────────────────────────────────────────────────
class ApprovalRequestResponse(BaseModel):
    id: str
    rule_id: str
    trigger_type: str
    trigger_id: str
    trigger_summary: str
    requested_by: Optional[str] = None
    approver_role: str
    current_stage: int
    total_stages: int
    status: str
    created_at: datetime
    updated_at: datetime
    steps: List[ApprovalStepResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ApprovalDecisionInput(BaseModel):
    """approve / reject payload。reject 時 comment 必填。"""
    comment: Optional[str] = None


__all__ = [
    "ApprovalRuleCreate", "ApprovalRuleResponse",
    "ApprovalStepResponse", "ApprovalRequestResponse",
    "ApprovalDecisionInput",
]

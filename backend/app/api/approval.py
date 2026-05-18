"""Approval Workflow API (v3.22)。

Endpoints
---------
- POST   /api/approvals/rules                     建規則
- GET    /api/approvals/rules                     列規則
- DELETE /api/approvals/rules/{rule_id}           刪規則
- GET    /api/approvals/pending                   待我審
- GET    /api/approvals/history                   歷史
- POST   /api/approvals/{request_id}/approve      批准
- POST   /api/approvals/{request_id}/reject       拒絕（comment 必填）
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.exceptions import NotFoundError
from app.schemas.approval import (
    ApprovalRuleCreate, ApprovalRuleResponse,
    ApprovalRequestResponse, ApprovalDecisionInput,
)
from app.services import approval as svc


router = APIRouter(prefix="/api/approvals", tags=["Approvals"])


# ── 規則 ────────────────────────────────────────────────────
@router.post("/rules", response_model=ApprovalRuleResponse)
async def create_rule_endpoint(
    data: ApprovalRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rule = await svc.create_rule(db, data.model_dump())
    return ApprovalRuleResponse.model_validate(rule)


@router.get("/rules", response_model=List[ApprovalRuleResponse])
async def list_rules_endpoint(
    trigger_type: Optional[str] = Query(None, description="po | so | payment"),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rules = await svc.list_rules(db, trigger_type=trigger_type, active_only=active_only)
    return [ApprovalRuleResponse.model_validate(r) for r in rules]


@router.delete("/rules/{rule_id}")
async def delete_rule_endpoint(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ok = await svc.delete_rule(db, rule_id)
    if not ok:
        raise NotFoundError("規則不存在", rule_id=rule_id)
    return {"deleted": True, "rule_id": rule_id}


# ── 待我審 / 歷史 ──────────────────────────────────────────
@router.get("/pending", response_model=List[ApprovalRequestResponse])
async def list_pending_endpoint(
    approver_role: Optional[str] = Query(None, description="未填則回全部 pending"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    reqs = await svc.list_pending_for_user(db, user_role=approver_role)
    return [ApprovalRequestResponse.model_validate(r) for r in reqs]


@router.get("/history", response_model=List[ApprovalRequestResponse])
async def list_history_endpoint(
    status: Optional[str] = Query(None, description="approved | rejected | cancelled"),
    trigger_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    reqs = await svc.list_history(db, status=status, trigger_type=trigger_type, limit=limit)
    return [ApprovalRequestResponse.model_validate(r) for r in reqs]


# ── 決議 ────────────────────────────────────────────────────
@router.post("/{request_id}/approve", response_model=ApprovalRequestResponse)
async def approve_endpoint(
    request_id: str,
    body: ApprovalDecisionInput,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    req = await svc.approve(db, request_id, user=user, comment=body.comment or "")
    return ApprovalRequestResponse.model_validate(req)


@router.post("/{request_id}/reject", response_model=ApprovalRequestResponse)
async def reject_endpoint(
    request_id: str,
    body: ApprovalDecisionInput,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # service 層會擋 comment 空字串並丟 BusinessRuleError
    req = await svc.reject(db, request_id, user=user, comment=body.comment or "")
    return ApprovalRequestResponse.model_validate(req)

"""Policy API — 家規 CRUD（Sprint S v3.25）。

Endpoints:
  GET    /api/policies/rules         列出所有家規（可篩 trigger）
  POST   /api/policies/rules         新增規則
  PATCH  /api/policies/rules/{id}    改規則（含 enable/disable）
  DELETE /api/policies/rules/{id}    刪規則
  POST   /api/policies/seed-defaults 一鍵灌預設規則
  GET    /api/policies/triggers      公開：列支援的 trigger
  GET    /api/policies/conditions    公開：列支援的 condition type
  POST   /api/policies/evaluate      手動評估（給 admin 測試規則）
  GET    /api/policies/audit         看稽核 log
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.logging import get_logger
from app.core.security import UserContext, require_permission
from app.models.policy_rule import (
    POLICY_ACTIONS, POLICY_CONDITION_TYPES, POLICY_TRIGGERS,
    PolicyAuditLog, PolicyRule,
)
from app.services.policy_engine import evaluate_policies, install_default_rules

log = get_logger(__name__)
router = APIRouter(prefix="/api/policies", tags=["Policy Rules"])


# ─── Schemas ─────────────────────────────────────────────

class PolicyRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    trigger: str
    condition_type: str = "always"
    condition_params: Optional[dict] = None
    action: str = "block"
    message: str
    override_role: Optional[str] = None
    priority: int = 100


class PolicyRulePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition_params: Optional[dict] = None
    action: Optional[str] = None
    message: Optional[str] = None
    override_role: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class PolicyRuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    trigger: str
    condition_type: str
    condition_params: Optional[dict]
    action: str
    message: str
    override_role: Optional[str]
    is_active: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluateRequest(BaseModel):
    trigger: str
    context: dict


class EvaluateResponse(BaseModel):
    action: str
    triggered_rule_id: Optional[str] = None
    message: str = ""
    can_override: bool = False


# ─── Public meta endpoints ───────────────────────────────

@router.get("/triggers")
async def list_triggers():
    """公開：列當前支援的 trigger 清單（給 UI 下拉用）。"""
    return {"triggers": sorted(POLICY_TRIGGERS)}


@router.get("/conditions")
async def list_conditions():
    """公開：列當前 condition type 清單（給 UI 下拉用）。"""
    return {
        "condition_types": sorted(POLICY_CONDITION_TYPES),
        "actions": sorted(POLICY_ACTIONS),
    }


# ─── CRUD ────────────────────────────────────────────────

@router.get("/rules", response_model=list[PolicyRuleResponse])
async def list_rules(
    trigger: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """列家規。可篩 trigger 與 is_active。"""
    q = select(PolicyRule).order_by(PolicyRule.trigger, PolicyRule.priority)
    if trigger:
        q = q.where(PolicyRule.trigger == trigger)
    if active_only:
        q = q.where(PolicyRule.is_active == True)
    return [PolicyRuleResponse.model_validate(r) for r in (await db.execute(q)).scalars().all()]


@router.post("/rules", response_model=PolicyRuleResponse, status_code=201)
async def create_rule(
    data: PolicyRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """新增家規。"""
    if data.trigger not in POLICY_TRIGGERS:
        raise HTTPException(400, f"trigger 不合法。允許：{sorted(POLICY_TRIGGERS)}")
    if data.condition_type not in POLICY_CONDITION_TYPES:
        raise HTTPException(400, f"condition_type 不合法。允許：{sorted(POLICY_CONDITION_TYPES)}")
    if data.action not in POLICY_ACTIONS:
        raise HTTPException(400, f"action 不合法。允許：{sorted(POLICY_ACTIONS)}")

    rule = PolicyRule(
        id=str(uuid.uuid4()),
        created_by=getattr(user, "employee_id", None),
        **data.model_dump(),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    log.info("Policy rule created: %s (%s) by %s", rule.name, rule.trigger,
             getattr(user, "username", "?"))
    return rule


@router.patch("/rules/{rule_id}", response_model=PolicyRuleResponse)
async def patch_rule(
    rule_id: str,
    data: PolicyRulePatch,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """改家規（含 enable/disable 用 is_active=true/false）。"""
    rule = (await db.execute(select(PolicyRule).where(PolicyRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "規則不存在")
    patch = data.model_dump(exclude_unset=True)
    if "action" in patch and patch["action"] not in POLICY_ACTIONS:
        raise HTTPException(400, f"action 不合法")
    for k, v in patch.items():
        setattr(rule, k, v)
    rule.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """刪家規。"""
    from sqlalchemy import delete
    res = await db.execute(delete(PolicyRule).where(PolicyRule.id == rule_id))
    await db.commit()
    if (res.rowcount or 0) == 0:
        raise HTTPException(404, "規則不存在")
    return {"deleted": True, "id": rule_id}


# ─── Seed defaults ───────────────────────────────────────

@router.post("/seed-defaults")
async def seed_defaults(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """一鍵灌預設家規（idempotent，已存在跳過）。"""
    await install_default_rules(db, tenant_id="HQ")
    return {"ok": True, "message": "預設家規已灌入（idempotent）"}


# ─── Evaluate ────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse)
async def manual_evaluate(
    req: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """手動評估某 trigger（給 admin 測試規則 / LLM tool 用）。"""
    result = await evaluate_policies(db, req.trigger, req.context)
    return EvaluateResponse(
        action=result.action,
        triggered_rule_id=result.triggered_rule_id,
        message=result.message,
        can_override=result.can_override,
    )


# ─── Audit logs ──────────────────────────────────────────

@router.get("/audit")
async def list_audit(
    rule_id: Optional[str] = None,
    trigger: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """看稽核 log（最新在前）。"""
    q = select(PolicyAuditLog).order_by(PolicyAuditLog.created_at.desc()).limit(min(limit, 500))
    if rule_id:
        q = q.where(PolicyAuditLog.rule_id == rule_id)
    if trigger:
        q = q.where(PolicyAuditLog.trigger == trigger)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "trigger": r.trigger,
            "action_taken": r.action_taken,
            "context": r.context,
            "override_by": r.override_by,
            "override_reason": r.override_reason,
            "created_at": r.created_at,
        }
        for r in rows
    ]

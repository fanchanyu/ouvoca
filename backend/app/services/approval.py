"""Approval Workflow service (v3.22 — 對標鼎新 / SAP B1)。

設計重點
--------
1. **規則 → 申請單 → 步驟** 三段分明
2. **非侵入式整合**：透過 EventBus 訂閱 po.created / so.created / payment.created
   → 自動 evaluate_rules → create_request。PO/SO service 完全不用改。
3. **拒絕必填 comment**（避免一句「不行」摸糊）
4. **多階審**：current_stage < total_stages 時 approve 推進階段；最後一階才 status = approved
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging import get_logger
from app.events import EventBus, DomainEvent
from app.models.approval_workflow import (
    ApprovalRule, ApprovalRequestV2, ApprovalStepV2,
)

log = get_logger(__name__)


# ──────────────────────────────────────────────────────────
# Rule CRUD
# ──────────────────────────────────────────────────────────
async def create_rule(db: AsyncSession, data: dict) -> ApprovalRule:
    rule = ApprovalRule(id=str(uuid.uuid4()), **data)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def list_rules(
    db: AsyncSession,
    trigger_type: Optional[str] = None,
    active_only: bool = False,
) -> list[ApprovalRule]:
    q = select(ApprovalRule)
    if trigger_type:
        q = q.where(ApprovalRule.trigger_type == trigger_type)
    if active_only:
        q = q.where(ApprovalRule.is_active.is_(True))
    q = q.order_by(ApprovalRule.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def get_rule(db: AsyncSession, rule_id: str) -> Optional[ApprovalRule]:
    return (await db.execute(
        select(ApprovalRule).where(ApprovalRule.id == rule_id)
    )).scalar_one_or_none()


async def delete_rule(db: AsyncSession, rule_id: str) -> bool:
    rule = await get_rule(db, rule_id)
    if not rule:
        return False
    await db.delete(rule)
    await db.commit()
    return True


# ──────────────────────────────────────────────────────────
# Rule evaluation
# ──────────────────────────────────────────────────────────
_OPS = {
    "gt":  lambda a, b: a >  b,
    "gte": lambda a, b: a >= b,
    "lt":  lambda a, b: a <  b,
    "lte": lambda a, b: a <= b,
    "eq":  lambda a, b: a == b,
}


def _match(rule: ApprovalRule, trigger_data: dict[str, Any]) -> bool:
    """單一規則命中判斷。缺欄位視為不命中。"""
    raw = trigger_data.get(rule.condition_field)
    if raw is None:
        return False
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return False
    op = _OPS.get(rule.condition_op)
    return bool(op and op(val, float(rule.condition_value)))


async def evaluate_rules(
    db: AsyncSession,
    trigger_type: str,
    trigger_data: dict[str, Any],
) -> Optional[ApprovalRule]:
    """找第一個 active + 命中的規則。未來可擴充為回傳 list（多規則並行）。"""
    rules = await list_rules(db, trigger_type=trigger_type, active_only=True)
    for r in rules:
        if _match(r, trigger_data):
            return r
    return None


# ──────────────────────────────────────────────────────────
# Request lifecycle
# ──────────────────────────────────────────────────────────
async def create_request(
    db: AsyncSession,
    rule: ApprovalRule,
    trigger_id: str,
    trigger_summary: str,
    requested_by: Optional[str] = None,
) -> ApprovalRequestV2:
    req = ApprovalRequestV2(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        trigger_type=rule.trigger_type,
        trigger_id=trigger_id,
        trigger_summary=trigger_summary,
        requested_by=requested_by,
        approver_role=rule.approver_role,
        current_stage=1,
        total_stages=int(rule.stages or 1),
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    await EventBus.emit(DomainEvent(
        name="approval.created", domain="approval",
        entity_type="ApprovalRequest", entity_id=req.id,
        data={
            "rule_id": rule.id,
            "trigger_type": rule.trigger_type,
            "trigger_id": trigger_id,
            "approver_role": rule.approver_role,
        },
    ))
    return req


async def get_request(db: AsyncSession, request_id: str) -> Optional[ApprovalRequestV2]:
    return (await db.execute(
        select(ApprovalRequestV2)
        .options(selectinload(ApprovalRequestV2.steps))
        .where(ApprovalRequestV2.id == request_id)
    )).scalar_one_or_none()


async def _record_step(
    db: AsyncSession,
    req: ApprovalRequestV2,
    action: str,
    user: Optional[dict],
    comment: Optional[str],
) -> ApprovalStepV2:
    user = user or {}
    step = ApprovalStepV2(
        id=str(uuid.uuid4()),
        request_id=req.id,
        stage=req.current_stage,
        approver_id=user.get("employee_id"),
        approver_username=user.get("username"),
        action=action,
        comment=comment,
        decided_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(step)
    return step


async def approve(
    db: AsyncSession,
    request_id: str,
    user: Optional[dict] = None,
    comment: str = "",
) -> ApprovalRequestV2:
    req = await get_request(db, request_id)
    if not req:
        raise NotFoundError("審批單不存在", request_id=request_id)
    if req.status != "pending":
        raise BusinessRuleError(f"審批單已結案（status={req.status}）")

    await _record_step(db, req, "approved", user, comment or None)

    if req.current_stage >= req.total_stages:
        req.status = "approved"
    else:
        req.current_stage += 1

    req.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(req, attribute_names=["steps"])

    await EventBus.emit(DomainEvent(
        name="approval.approved" if req.status == "approved" else "approval.stage_advanced",
        domain="approval",
        entity_type="ApprovalRequest", entity_id=req.id,
        data={
            "trigger_type": req.trigger_type,
            "trigger_id": req.trigger_id,
            "stage": req.current_stage,
            "total_stages": req.total_stages,
            "status": req.status,
        },
    ))
    return req


async def reject(
    db: AsyncSession,
    request_id: str,
    user: Optional[dict] = None,
    comment: str = "",
) -> ApprovalRequestV2:
    if not comment or not comment.strip():
        raise BusinessRuleError("拒絕需填原因（comment 不可空）")

    req = await get_request(db, request_id)
    if not req:
        raise NotFoundError("審批單不存在", request_id=request_id)
    if req.status != "pending":
        raise BusinessRuleError(f"審批單已結案（status={req.status}）")

    await _record_step(db, req, "rejected", user, comment.strip())
    req.status = "rejected"
    req.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(req, attribute_names=["steps"])

    await EventBus.emit(DomainEvent(
        name="approval.rejected", domain="approval",
        entity_type="ApprovalRequest", entity_id=req.id,
        data={
            "trigger_type": req.trigger_type,
            "trigger_id": req.trigger_id,
            "reason": comment.strip(),
        },
    ))
    return req


# ──────────────────────────────────────────────────────────
# Queries for UI
# ──────────────────────────────────────────────────────────
async def list_pending_for_user(
    db: AsyncSession,
    user_role: Optional[str] = None,
) -> list[ApprovalRequestV2]:
    """user_role=None 表示全列（admin / 超管視角）。"""
    q = (
        select(ApprovalRequestV2)
        .options(selectinload(ApprovalRequestV2.steps))
        .where(ApprovalRequestV2.status == "pending")
    )
    if user_role:
        q = q.where(ApprovalRequestV2.approver_role == user_role)
    q = q.order_by(ApprovalRequestV2.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def list_history(
    db: AsyncSession,
    status: Optional[str] = None,
    trigger_type: Optional[str] = None,
    limit: int = 100,
) -> list[ApprovalRequestV2]:
    q = (
        select(ApprovalRequestV2)
        .options(selectinload(ApprovalRequestV2.steps))
    )
    if status:
        q = q.where(ApprovalRequestV2.status == status)
    if trigger_type:
        q = q.where(ApprovalRequestV2.trigger_type == trigger_type)
    q = q.order_by(ApprovalRequestV2.created_at.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


# ──────────────────────────────────────────────────────────
# EventBus listeners — 非侵入式整合（PO/SO/payment service 完全不必改）
# ──────────────────────────────────────────────────────────
def _summary_for(trigger_type: str, data: dict) -> str:
    """組一句人話的摘要，給 UI 列表顯示。"""
    if trigger_type == "po":
        return f"PO {data.get('po_no', data.get('id', '?'))} NT${float(data.get('total', 0)):,.0f}"
    if trigger_type == "so":
        amt = float(data.get('total', 0))
        disc = data.get('discount_pct')
        disc_part = f" 折扣{disc}%" if disc is not None else ""
        return f"SO {data.get('so_no', data.get('id', '?'))} NT${amt:,.0f}{disc_part}"
    if trigger_type == "payment":
        return f"付款 {data.get('payment_no', data.get('id', '?'))} NT${float(data.get('amount', 0)):,.0f}"
    return f"{trigger_type} {data.get('id', '?')}"


async def _maybe_create_request(
    trigger_type: str,
    event: DomainEvent,
) -> None:
    """共用入口：evaluate_rules → 命中就 create_request。

    失敗只 log（不擋住主流程）— 跟 crm_auto_log 同套保護。
    """
    from app.database import AsyncSessionLocal
    data = dict(event.data or {})
    # 強化 condition_field 對映：trigger_data 至少要有 amount。
    if "amount" not in data:
        if "total" in data:
            data["amount"] = data["total"]
        elif "total_amount" in data:
            data["amount"] = data["total_amount"]

    async with AsyncSessionLocal() as db:
        try:
            rule = await evaluate_rules(db, trigger_type, data)
            if not rule:
                return
            summary = _summary_for(trigger_type, data)
            requested_by = (event.metadata or {}).get("requested_by")
            await create_request(
                db, rule,
                trigger_id=event.entity_id,
                trigger_summary=summary,
                requested_by=requested_by,
            )
            log.info(
                "approval auto-created: rule=%s trigger=%s id=%s",
                rule.name, trigger_type, event.entity_id,
            )
        except Exception as exc:  # pylint: disable=broad-except
            log.warning("approval listener failed (%s): %s", trigger_type, exc)


async def on_po_created(event: DomainEvent) -> None:
    await _maybe_create_request("po", event)


async def on_so_created(event: DomainEvent) -> None:
    await _maybe_create_request("so", event)


async def on_payment_created(event: DomainEvent) -> None:
    await _maybe_create_request("payment", event)


def install_approval_hooks() -> None:
    """App startup 呼叫一次，註冊事件監聽。"""
    EventBus.subscribe("po.created", on_po_created)
    EventBus.subscribe("so.created", on_so_created)
    EventBus.subscribe("payment.created", on_payment_created)
    log.info("Approval workflow hooks installed (po / so / payment)")

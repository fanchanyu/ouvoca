"""PolicyEngine — 家規評估引擎（Sprint S v3.25）。

提供「規則資料化 + pluggable condition + auditable」的家規系統。

使用方式（在 service 層替換寫死 if）：
  # 之前
  if not bom:
      raise BusinessRuleError("WO release 需 BOM")

  # 之後
  result = await evaluate_policies(db, "wo.release", {"product_id": product.id, "wo_id": wo.id})
  if result.blocked:
      raise BusinessRuleError(result.message, can_override=result.can_override)

優點：
  - 客戶可在 UI 開關 / 改條件 / 刪規則，不必動 code
  - 可以加新條件 type（plugin）
  - 每次 evaluate 寫 audit log → 合規
  - LLM 可以對話建規則 → ConfirmCard → 立即生效
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.policy_rule import PolicyRule, PolicyAuditLog

log = get_logger(__name__)


@dataclass
class PolicyResult:
    """規則評估結果。"""
    triggered_rule_id: str | None = None
    action: str = "allow"          # 'allow' / 'block' / 'warn' / 'require_approval'
    message: str = ""
    can_override: bool = False
    override_role: str | None = None

    @property
    def blocked(self) -> bool:
        return self.action == "block"

    @property
    def warned(self) -> bool:
        return self.action == "warn"

    @property
    def needs_approval(self) -> bool:
        return self.action == "require_approval"


# ─── Condition handlers (pluggable) ────────────────────────────

ConditionFn = Callable[[dict, dict, AsyncSession], Awaitable[bool]]
_CONDITIONS: dict[str, ConditionFn] = {}


def register_condition(name: str, fn: ConditionFn) -> None:
    """Plugin 機制：客戶 / extension 可自定 condition type。

    Usage:
        async def check_credit_limit(params, context, db):
            return context.get('amount', 0) <= params.get('limit', 0)
        register_condition("credit_check", check_credit_limit)
    """
    _CONDITIONS[name] = fn
    log.debug("Policy condition registered: %s", name)


async def _cond_always(params: dict, context: dict, db: AsyncSession) -> bool:
    """總是返回 True（規則總是觸發）。"""
    return True


async def _cond_has_bom(params: dict, context: dict, db: AsyncSession) -> bool:
    """產品有 BOM 才通過（用於 WO release）。

    context 需含 product_id。
    """
    from app.models.product import BOMItem
    product_id = context.get("product_id")
    if not product_id:
        return False
    count = (await db.execute(
        select(BOMItem).where(BOMItem.product_id == product_id).limit(1)
    )).scalar_one_or_none()
    return count is not None


async def _cond_field_compare(params: dict, context: dict, db: AsyncSession) -> bool:
    """比較欄位：{"field": "amount", "op": "gt", "value": 100000}

    op 支援: gt / gte / lt / lte / eq / ne
    """
    field = params.get("field")
    op = params.get("op", "eq")
    expected = params.get("value")
    actual = context.get(field) if field else None
    if actual is None:
        return False
    try:
        actual_n = float(actual)
        expected_n = float(expected)
    except (TypeError, ValueError):
        # 字串比較
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        return False
    return {
        "gt":  actual_n >  expected_n,
        "gte": actual_n >= expected_n,
        "lt":  actual_n <  expected_n,
        "lte": actual_n <= expected_n,
        "eq":  actual_n == expected_n,
        "ne":  actual_n != expected_n,
    }.get(op, False)


async def _cond_count_check(params: dict, context: dict, db: AsyncSession) -> bool:
    """計數檢查：context 內某 list 長度 op value。
    {"field": "items", "op": "gte", "value": 1}
    """
    field = params.get("field", "items")
    op = params.get("op", "gte")
    expected = int(params.get("value", 1))
    items = context.get(field, [])
    if not hasattr(items, "__len__"):
        return False
    count = len(items)
    return {
        "gt":  count >  expected,
        "gte": count >= expected,
        "lt":  count <  expected,
        "lte": count <= expected,
        "eq":  count == expected,
        "ne":  count != expected,
    }.get(op, False)


# 註冊內建 conditions
register_condition("always", _cond_always)
register_condition("has_bom", _cond_has_bom)
register_condition("field_compare", _cond_field_compare)
register_condition("count_check", _cond_count_check)


# ─── 主評估函式 ────────────────────────────────────────────

async def evaluate_policies(
    db: AsyncSession,
    trigger: str,
    context: dict[str, Any],
    user_id: str | None = None,
) -> PolicyResult:
    """評估某觸發點的所有家規。

    回傳第一個 block / require_approval 的結果；
    若全部都 allow / warn，回最後一個 warn 或預設 allow。

    每次評估都寫 audit log。
    """
    # 撈該 trigger 的活躍規則，依 priority 升冪
    rules = (await db.execute(
        select(PolicyRule)
        .where(PolicyRule.trigger == trigger, PolicyRule.is_active == True)
        .order_by(PolicyRule.priority.asc(), PolicyRule.created_at.asc())
    )).scalars().all()

    last_warn: PolicyResult | None = None

    for rule in rules:
        # 評估 condition
        cond_fn = _CONDITIONS.get(rule.condition_type)
        if cond_fn is None:
            log.warning("Unknown policy condition_type: %s (rule %s)",
                        rule.condition_type, rule.id)
            continue

        params = rule.condition_params or {}
        try:
            condition_holds = await cond_fn(params, context, db)
        except Exception as exc:  # pylint: disable=broad-except
            log.warning("Policy condition fn '%s' raised %s; treat as not-hold",
                        rule.condition_type, exc)
            condition_holds = False

        # 條件「不成立」 = 規則被觸發（block/warn/approval）
        # 條件「成立」 = 規則放行（continue 下一條）
        if condition_holds:
            continue

        # 規則被觸發
        result = PolicyResult(
            triggered_rule_id=rule.id,
            action=rule.action,
            message=rule.message,
            can_override=rule.override_role is not None,
            override_role=rule.override_role,
        )

        # 寫 audit log
        await _write_audit(db, rule, "blocked" if rule.action == "block" else rule.action,
                           context, user_id)

        if rule.action == "block" or rule.action == "require_approval":
            await db.commit()
            return result
        if rule.action == "warn":
            last_warn = result
            # continue 評估下一條
        # action == "allow" 也繼續

    if last_warn:
        await db.commit()
        return last_warn

    # 沒任何規則被觸發 → 允許
    await db.commit()
    return PolicyResult(action="allow")


async def evaluate_with_override(
    db: AsyncSession,
    trigger: str,
    context: dict[str, Any],
    override_user: dict | None = None,
    override_reason: str = "",
) -> PolicyResult:
    """有覆寫者時：先看主管 / admin 是否有權覆寫被擋的規則。

    override_user 應為 dict 含 role 或 employee_id。
    """
    result = await evaluate_policies(db, trigger, context,
                                     user_id=(override_user or {}).get("employee_id"))
    if not result.blocked or not override_user:
        return result
    if not result.can_override:
        return result
    # 簡化：admin 角色可覆寫任何，否則檢查 role 對應
    user_role = (override_user or {}).get("role")
    if user_role == "admin" or user_role == result.override_role:
        # 覆寫成功
        await _write_audit_override(db, result.triggered_rule_id, trigger, context,
                                    override_user.get("employee_id"), override_reason)
        await db.commit()
        return PolicyResult(action="allow", message=f"已覆寫：{override_reason}")
    return result


async def _write_audit(
    db: AsyncSession,
    rule: PolicyRule,
    action_taken: str,
    context: dict,
    user_id: str | None,
) -> None:
    """寫稽核 log（fire-and-forget；失敗不擋主流程）。"""
    try:
        # 不存敏感資料：context 只存 key 摘要
        safe_context = {k: str(v)[:100] for k, v in (context or {}).items()}
        db.add(PolicyAuditLog(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            trigger=rule.trigger,
            action_taken=action_taken,
            context=safe_context,
            user_id=user_id,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        ))
    except Exception as exc:  # pylint: disable=broad-except
        log.warning("Failed to write policy audit log: %s", exc)


async def _write_audit_override(
    db: AsyncSession,
    rule_id: str | None,
    trigger: str,
    context: dict,
    override_by: str | None,
    reason: str,
) -> None:
    """寫主管覆寫的稽核 log。"""
    try:
        safe_context = {k: str(v)[:100] for k, v in (context or {}).items()}
        db.add(PolicyAuditLog(
            id=str(uuid.uuid4()),
            rule_id=rule_id,
            trigger=trigger,
            action_taken="overridden",
            context=safe_context,
            override_by=override_by,
            override_reason=reason,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        ))
    except Exception as exc:  # pylint: disable=broad-except
        log.warning("Failed to write policy override audit: %s", exc)


# ─── Seed 預設家規 (startup) ─────────────────────────────────

DEFAULT_RULES = [
    {
        "name": "WO 釋放需有「做法 (Recipe)」",
        "description": "工單釋放到產線前，產品必須先設好做法（原 BOM）。可由廠長覆寫應急放行。",
        "trigger": "wo.release",
        "condition_type": "has_bom",
        "condition_params": {},
        "action": "block",
        "message": "此產品還沒設定「做法 (Recipe)」。請先去生產頁 → 編做法 (Recipe)。或請廠長覆寫。",
        "override_role": "manager",
        "priority": 100,
    },
    {
        "name": "PO > NT$10 萬需主管審",
        "description": "高額採購單需要主管核准（保護公司資金）。",
        "trigger": "po.create",
        "condition_type": "field_compare",
        "condition_params": {"field": "total_amount", "op": "lte", "value": 100000},
        "action": "require_approval",
        "message": "PO 金額超過 NT$10 萬需要主管審批。",
        "override_role": "manager",
        "priority": 50,
    },
    {
        "name": "PO 必須至少有 1 個項目",
        "description": "PO 不允許 0 項目（資料正確性）。",
        "trigger": "po.create",
        "condition_type": "count_check",
        "condition_params": {"field": "items", "op": "gte", "value": 1},
        "action": "block",
        "message": "採購單必須至少包含 1 個項目。",
        "override_role": None,
        "priority": 10,
    },
]


async def install_default_rules(db: AsyncSession, tenant_id: str = "HQ") -> None:
    """在 startup 或 admin 觸發時，把預設家規灌進 DB（idempotent）。"""
    for spec in DEFAULT_RULES:
        existing = (await db.execute(
            select(PolicyRule).where(
                PolicyRule.tenant_id == tenant_id,
                PolicyRule.trigger == spec["trigger"],
                PolicyRule.name == spec["name"],
            )
        )).scalar_one_or_none()
        if existing:
            continue
        db.add(PolicyRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **spec,
        ))
    await db.commit()
    log.info("Default policy rules installed (idempotent)")

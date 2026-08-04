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

from sqlalchemy import func, select
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


async def _cond_credit_check(params: dict, context: dict, db: AsyncSession) -> bool:
    """客戶信用額度：context 需含 customer_id 與 total_amount。
    未設額度 → 通過；未收應收 + 本單 ≤ 額度 → 通過。"""
    from app.models.crm_sales import Customer
    from app.models.accounting import AccountsReceivable
    customer_id = context.get("customer_id")
    amount = float(context.get("total_amount", 0) or 0)
    if not customer_id:
        return True
    customer = (await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )).scalar_one_or_none()
    if customer is None or not customer.credit_limit:
        return True
    open_ar = (await db.execute(
        select(func.coalesce(func.sum(AccountsReceivable.amount - AccountsReceivable.paid_amount), 0))
        .where(
            AccountsReceivable.customer_id == customer_id,
            AccountsReceivable.status.in_(("unpaid", "partial")),
        )
    )).scalar_one() or 0
    return float(open_ar) + amount <= float(customer.credit_limit)


async def _cond_has_customer_tax_id(params: dict, context: dict, db: AsyncSession) -> bool:
    """B2B 客戶有統編才通過（context.customer_id → Customer.tax_id 非空）。"""
    from app.models.crm_sales import Customer
    customer_id = context.get("customer_id")
    if not customer_id:
        return True
    customer = (await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )).scalar_one_or_none()
    return bool(customer and customer.tax_id)


async def _cond_period_open(params: dict, context: dict, db: AsyncSession) -> bool:
    """會計期間未鎖定才通過（context.period → MonthEndClose 無 closed）。"""
    from app.models.accounting import MonthEndClose
    period = context.get("period")
    if not period:
        return True
    closed = (await db.execute(
        select(MonthEndClose).where(
            MonthEndClose.period == period, MonthEndClose.status == "closed",
        )
    )).scalar_one_or_none()
    return closed is None


async def _cond_field_in(params: dict, context: dict, db: AsyncSession) -> bool:
    """欄位值在允許清單內才通過：{"field": "status", "values": ["approved", "sent"]}"""
    field = params.get("field")
    values = params.get("values") or []
    return context.get(field) in values


async def _cond_not_empty(params: dict, context: dict, db: AsyncSession) -> bool:
    """context 欄位非空才通過：{"field": "customer_id"}"""
    field = params.get("field")
    return bool(context.get(field))


# 註冊內建 conditions
register_condition("always", _cond_always)
register_condition("has_bom", _cond_has_bom)
register_condition("field_compare", _cond_field_compare)
register_condition("count_check", _cond_count_check)
register_condition("credit_check", _cond_credit_check)
register_condition("has_customer_tax_id", _cond_has_customer_tax_id)
register_condition("period_open", _cond_period_open)
register_condition("field_in", _cond_field_in)
register_condition("not_empty", _cond_not_empty)


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
    # ─── v3.67 Turnkey P0-3：家規 20 條（allow-predicate 語意） ───
    {
        "name": "SO 客戶信用額度檢查",
        "description": "未收應收 + 本單金額不得超過客戶信用額度（可設定關閉）。",
        "trigger": "so.create",
        "condition_type": "credit_check",
        "condition_params": {},
        "action": "block",
        "message": "信用額度不足：客戶未收應收加本單金額超過信用額度。",
        "override_role": "manager",
        "priority": 90,
    },
    {
        "name": "SO B2B 客戶應有統編",
        "description": "B2B 客戶缺少統編時提醒（開立電子發票需要）。",
        "trigger": "so.create",
        "condition_type": "has_customer_tax_id",
        "condition_params": {},
        "action": "warn",
        "message": "此客戶沒有統編（tax_id），開立 B2B 電子發票時會缺欄位。",
        "override_role": None,
        "priority": 40,
    },
    {
        "name": "出貨需 SO 已確認",
        "description": "未確認的 SO 不可出貨（狀態機外的家規防線）。",
        "trigger": "so.ship",
        "condition_type": "field_in",
        "condition_params": {"field": "status", "values": ["confirmed", "production", "ready_to_ship"]},
        "action": "block",
        "message": "此 SO 尚未確認，不可出貨。請先確認訂單。",
        "override_role": "manager",
        "priority": 90,
    },
    {
        "name": "收貨需 PO 已核准",
        "description": "未核准的 PO 不可收貨。",
        "trigger": "po.receive",
        "condition_type": "field_in",
        "condition_params": {"field": "status", "values": ["approved", "sent", "partial_received"]},
        "action": "block",
        "message": "此 PO 尚未核准，不可收貨。",
        "override_role": "manager",
        "priority": 90,
    },
    {
        "name": "傳票期間未鎖定",
        "description": "已結帳的會計期間不可再開傳票。",
        "trigger": "je.create",
        "condition_type": "period_open",
        "condition_params": {},
        "action": "block",
        "message": "此會計期間已結帳鎖定，不可新增傳票。",
        "override_role": "manager",
        "priority": 90,
    },
    {
        "name": "傳票借貸需平衡",
        "description": "借貸不平衡的傳票不可建立。",
        "trigger": "je.create",
        "condition_type": "field_compare",
        "condition_params": {"field": "balanced", "op": "eq", "value": True},
        "action": "block",
        "message": "傳票借貸不平衡。",
        "override_role": None,
        "priority": 95,
    },
    {
        "name": "退貨入庫需已核准",
        "description": "RMA 退貨必須核准後才能入庫。",
        "trigger": "return.process",
        "condition_type": "field_compare",
        "condition_params": {"field": "status", "op": "eq", "value": "approved"},
        "action": "block",
        "message": "退貨單尚未核准，不可入庫。",
        "override_role": "manager",
        "priority": 80,
    },
    {
        "name": "請購轉採購需已核准",
        "description": "PR 必須核准後才能轉成 PO。",
        "trigger": "pr.convert",
        "condition_type": "field_compare",
        "condition_params": {"field": "status", "op": "eq", "value": "approved"},
        "action": "block",
        "message": "請購單尚未核准，不可轉採購。",
        "override_role": "manager",
        "priority": 80,
    },
    {
        "name": "RFQ 決標需已送出",
        "description": "未送出的 RFQ 不可決標。",
        "trigger": "rfq.award",
        "condition_type": "field_compare",
        "condition_params": {"field": "status", "op": "eq", "value": "sent"},
        "action": "block",
        "message": "詢價單尚未送出，不可決標。",
        "override_role": "manager",
        "priority": 80,
    },
    {
        "name": "高額收款需主管審",
        "description": "單筆收款超過 NT$10 萬需要主管審批。",
        "trigger": "receipt.create",
        "condition_type": "field_compare",
        "condition_params": {"field": "amount", "op": "lte", "value": 100000},
        "action": "require_approval",
        "message": "收款金額超過 NT$10 萬需要主管審批。",
        "override_role": "manager",
        "priority": 50,
    },
    {
        "name": "高額付款需主管審",
        "description": "單筆付款超過 NT$10 萬需要主管審批。",
        "trigger": "payment.create",
        "condition_type": "field_compare",
        "condition_params": {"field": "amount", "op": "lte", "value": 100000},
        "action": "require_approval",
        "message": "付款金額超過 NT$10 萬需要主管審批。",
        "override_role": "manager",
        "priority": 50,
    },
    {
        "name": "領料需工單已釋放",
        "description": "未釋放的工單不可領料。",
        "trigger": "material_issue.create",
        "condition_type": "field_in",
        "condition_params": {"field": "wo_status", "values": ["released", "in_progress"]},
        "action": "block",
        "message": "工單尚未釋放，不可領料。",
        "override_role": "manager",
        "priority": 80,
    },
    {
        "name": "工單完工需已釋放",
        "description": "未釋放的工單不可完工。",
        "trigger": "wo.complete",
        "condition_type": "field_in",
        "condition_params": {"field": "status", "values": ["released", "in_progress"]},
        "action": "block",
        "message": "工單尚未釋放，不可完工。",
        "override_role": "manager",
        "priority": 80,
    },
    {
        "name": "報價單需有客戶",
        "description": "報價單必須指定客戶。",
        "trigger": "quotation.create",
        "condition_type": "not_empty",
        "condition_params": {"field": "customer_id"},
        "action": "block",
        "message": "報價單必須指定客戶。",
        "override_role": None,
        "priority": 60,
    },
    {
        "name": "工單需有產品",
        "description": "工單必須指定產品。",
        "trigger": "wo.create",
        "condition_type": "not_empty",
        "condition_params": {"field": "product_id"},
        "action": "block",
        "message": "工單必須指定產品。",
        "override_role": None,
        "priority": 60,
    },
    {
        "name": "庫存低於安全庫存提醒",
        "description": "可用庫存低於安全庫存時提醒補貨。",
        "trigger": "inventory.read",
        "condition_type": "field_compare",
        "condition_params": {"field": "qty_available", "op": "gte", "value": 0},
        "action": "warn",
        "message": "此料件可用庫存低於安全庫存，建議補貨。",
        "override_role": None,
        "priority": 20,
    },
    {
        "name": "批號效期提醒",
        "description": "建立批號時若有效期即記錄（提醒效期管理）。",
        "trigger": "inventory.batch.create",
        "condition_type": "not_empty",
        "condition_params": {"field": "lot_no"},
        "action": "warn",
        "message": "批號已建立，請留意效期管理。",
        "override_role": None,
        "priority": 20,
    },
    {
        "name": "付款需指定供應商",
        "description": "付款單必須指定供應商。",
        "trigger": "payment.create",
        "condition_type": "not_empty",
        "condition_params": {"field": "supplier_id"},
        "action": "block",
        "message": "付款單必須指定供應商。",
        "override_role": None,
        "priority": 60,
    },
    {
        "name": "收款需指定客戶",
        "description": "收款單必須指定客戶。",
        "trigger": "receipt.create",
        "condition_type": "not_empty",
        "condition_params": {"field": "customer_id"},
        "action": "block",
        "message": "收款單必須指定客戶。",
        "override_role": None,
        "priority": 60,
    },
    {
        "name": "收料不可超過訂購量",
        "description": "累計收貨量不得超過訂購量（防呆家規）。",
        "trigger": "po.receive",
        "condition_type": "always",
        "condition_params": {},
        "action": "warn",
        "message": "收料時請確認累計收貨量不超過訂購量。",
        "override_role": None,
        "priority": 5,
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

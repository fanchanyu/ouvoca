"""AccountingAgent — journals, AR, month-end (refactored to @register_tool v3.2.1)."""
from sqlalchemy import select
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.accounting import JournalEntry, AccountsReceivable, MonthEndClose


@register_tool(
    name="list_journals",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="列出傳票。可依期間 (YYYY-MM) 或狀態過濾。",
    slots=[
        Slot("period", "string", required=False, description="會計期間 YYYY-MM"),
        Slot("status", "string", required=False, description="draft/posted/reversed"),
        Slot("limit", "integer", required=False, description="回傳上限，預設 20"),
    ],
    required_permission="accounting.journal.list",
)
async def _list_journals(db, user, period: str = None, status: str = None, limit: int = 20):
    q = select(JournalEntry).order_by(JournalEntry.entry_date.desc()).limit(limit)
    if period:
        q = q.where(JournalEntry.period == period)
    if status:
        q = q.where(JournalEntry.status == status)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "journals": [
        {"entry_no": j.entry_no, "entry_date": str(j.entry_date),
         "period": j.period, "status": j.status, "description": j.description}
        for j in rows
    ]}


@register_tool(
    name="list_receivables",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="列出應收帳款（AR）。可只看逾期。",
    slots=[
        Slot("overdue_only", "boolean", required=False, description="只看逾期未付"),
        Slot("limit", "integer", required=False, description="回傳上限，預設 20"),
    ],
    required_permission="accounting.ar.list",
)
async def _list_ar(db, user, overdue_only: bool = False, limit: int = 20):
    from datetime import datetime, UTC
    q = select(AccountsReceivable).order_by(AccountsReceivable.due_date)
    if overdue_only:
        q = q.where(AccountsReceivable.due_date < datetime.now(UTC).replace(tzinfo=None),
                    AccountsReceivable.status != "paid")
    rows = (await db.execute(q.limit(limit))).scalars().all()
    return {"total": len(rows), "receivables": [
        {"invoice_no": ar.invoice_no, "customer_id": ar.customer_id,
         "amount": ar.amount, "paid_amount": ar.paid_amount,
         "due_date": str(ar.due_date), "status": ar.status,
         "aging_days": ar.aging_days}
        for ar in rows
    ]}


@register_tool(
    name="check_month_close",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="檢查某月份結帳狀態。",
    slots=[
        Slot("period", "string", required=True, description="會計期間 YYYY-MM"),
    ],
    required_permission="accounting.month_close.read",
)
async def _check_month_close(db, user, period: str):
    rec = (await db.execute(
        select(MonthEndClose).where(MonthEndClose.period == period)
    )).scalar_one_or_none()
    return {"period": period, "status": rec.status if rec else "open",
            "closed_at": str(rec.closed_at) if (rec and rec.closed_at) else None}


register_agent(
    "accounting", "AccountingAgent",
    system_prompt=(
        "你是 ERP 會計財務助手。職責：\n"
        "1. 查詢傳票與應收帳款\n"
        "2. 檢查月結狀態\n"
        "3. 提醒逾期款項\n\n"
        "請使用繁體中文，金額一律加上幣別。涉及借貸時務必驗證平衡。"
    ),
    tool_names=["list_journals", "list_receivables", "check_month_close"],
)

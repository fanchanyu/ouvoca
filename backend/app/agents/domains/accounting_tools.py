"""AccountingAgent — journals, AR, month-end."""
from sqlalchemy import select
from app.agents.engine import register_tool, register_agent
from app.models.accounting import JournalEntry, AccountsReceivable, MonthEndClose


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


async def _list_ar(db, user, overdue_only: bool = False, limit: int = 20):
    from datetime import datetime
    q = select(AccountsReceivable).order_by(AccountsReceivable.due_date)
    if overdue_only:
        q = q.where(AccountsReceivable.due_date < datetime.utcnow(),
                    AccountsReceivable.status != "paid")
    rows = (await db.execute(q.limit(limit))).scalars().all()
    return {"total": len(rows), "receivables": [
        {"invoice_no": ar.invoice_no, "customer_id": ar.customer_id,
         "amount": ar.amount, "paid_amount": ar.paid_amount,
         "due_date": str(ar.due_date), "status": ar.status,
         "aging_days": ar.aging_days}
        for ar in rows
    ]}


async def _check_month_close(db, user, period: str):
    rec = (await db.execute(
        select(MonthEndClose).where(MonthEndClose.period == period)
    )).scalar_one_or_none()
    return {"period": period, "status": rec.status if rec else "open",
            "closed_at": str(rec.closed_at) if (rec and rec.closed_at) else None}


register_tool("list_journals", "列出傳票。",
              {"type": "object", "properties": {"period": {"type": "string", "description": "YYYY-MM"},
                                                "status": {"type": "string"},
                                                "limit": {"type": "integer"}}},
              _list_journals)
register_tool("list_receivables", "列出應收帳款。",
              {"type": "object", "properties": {"overdue_only": {"type": "boolean"},
                                                "limit": {"type": "integer"}}},
              _list_ar)
register_tool("check_month_close", "檢查某月份結帳狀態。",
              {"type": "object", "properties": {"period": {"type": "string"}}, "required": ["period"]},
              _check_month_close)

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

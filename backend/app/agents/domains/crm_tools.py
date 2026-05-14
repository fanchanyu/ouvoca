"""CrmAgent — leads, opportunities, events."""
from sqlalchemy import select
from app.agents.engine import register_tool, register_agent
from app.models.crm_sales import Lead, Opportunity, CrmEvent


async def _list_leads(db, user, status: str = None, limit: int = 20):
    q = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    if status:
        q = q.where(Lead.status == status)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "leads": [
        {"id": l.id, "company": l.company_name, "contact": l.contact_person,
         "status": l.status, "source": l.source}
        for l in rows
    ]}


async def _list_opportunities(db, user, stage: str = None, limit: int = 20):
    q = select(Opportunity).order_by(Opportunity.expected_close_date).limit(limit)
    if stage:
        q = q.where(Opportunity.stage == stage)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "opportunities": [
        {"id": o.id, "name": o.name, "stage": o.stage, "amount": o.amount,
         "probability": o.probability, "expected_close": str(o.expected_close_date) if o.expected_close_date else None}
        for o in rows
    ]}


async def _customer_events(db, user, customer_id: str, limit: int = 20):
    rows = (await db.execute(
        select(CrmEvent).where(CrmEvent.customer_id == customer_id)
        .order_by(CrmEvent.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"total": len(rows), "events": [
        {"event_type": e.event_type, "subject": e.subject, "description": e.description,
         "created_at": str(e.created_at)}
        for e in rows
    ]}


register_tool("list_leads", "列出潛在客戶。",
              {"type": "object", "properties": {"status": {"type": "string"}, "limit": {"type": "integer"}}},
              _list_leads)
register_tool("list_opportunities", "列出商機 pipeline。",
              {"type": "object", "properties": {"stage": {"type": "string"}, "limit": {"type": "integer"}}},
              _list_opportunities)
register_tool("customer_events", "列出特定客戶的互動歷程。",
              {"type": "object", "properties": {"customer_id": {"type": "string"},
                                                "limit": {"type": "integer"}}, "required": ["customer_id"]},
              _customer_events)

register_agent(
    "crm", "CrmAgent",
    system_prompt=(
        "你是 ERP 客戶關係管理 (CRM) 助手。職責：\n"
        "1. 追蹤潛在客戶與商機 pipeline\n"
        "2. 統整客戶互動歷程\n"
        "3. 提醒成交機率高的商機\n\n"
        "請使用繁體中文，金額加上幣別。"
    ),
    tool_names=["list_leads", "list_opportunities", "customer_events", "list_customers"],
)

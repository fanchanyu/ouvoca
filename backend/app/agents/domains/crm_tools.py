"""CrmAgent — leads, opportunities, events (refactored v3.2.1)."""
from sqlalchemy import select
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.crm_sales import Lead, Opportunity, CrmEvent


@register_tool(
    name="list_leads",
    domain="crm",
    risk_tier=RiskTier.READ,
    description="列出潛在客戶。可按狀態過濾。",
    slots=[
        Slot("status", "string", required=False, description="new/qualified/lost/converted"),
        Slot("limit", "integer", required=False, description="預設 20"),
    ],
    required_permission="crm.lead.list",
)
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


@register_tool(
    name="list_opportunities",
    domain="crm",
    risk_tier=RiskTier.READ,
    description="列出商機 pipeline，按預計成交日排序。",
    slots=[
        Slot("stage", "string", required=False,
             description="prospecting/qualified/proposal/negotiation/closed_won/closed_lost"),
        Slot("limit", "integer", required=False, description="預設 20"),
    ],
    required_permission="crm.opportunity.list",
)
async def _list_opportunities(db, user, stage: str = None, limit: int = 20):
    q = select(Opportunity).order_by(Opportunity.expected_close_date).limit(limit)
    if stage:
        q = q.where(Opportunity.stage == stage)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "opportunities": [
        {"id": o.id, "name": o.name, "stage": o.stage, "amount": o.amount,
         "probability": o.probability,
         "expected_close": str(o.expected_close_date) if o.expected_close_date else None}
        for o in rows
    ]}


@register_tool(
    name="customer_events",
    domain="crm",
    risk_tier=RiskTier.READ,
    description="列出特定客戶的互動歷程（通話 / 拜訪 / Email）。",
    slots=[
        Slot("customer_id", "string", required=True, description="客戶 UUID"),
        Slot("limit", "integer", required=False, description="預設 20"),
    ],
    required_permission="crm.event.list",
)
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

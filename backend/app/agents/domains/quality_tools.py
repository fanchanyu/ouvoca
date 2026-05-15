"""QualityAgent — inspections, non-conformances, CAPA (refactored v3.2.1)."""
from sqlalchemy import select
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.quality import InspectionOrder, NonConformance, CAPARecord


@register_tool(
    name="list_inspections",
    domain="quality",
    risk_tier=RiskTier.READ,
    description="列出檢驗單。可按狀態過濾。",
    slots=[
        Slot("status", "string", required=False, description="pending/in_progress/passed/failed"),
        Slot("limit", "integer", required=False, description="預設 20"),
    ],
    required_permission="quality.inspection.list",
)
async def _list_inspections(db, user, status: str = None, limit: int = 20):
    q = select(InspectionOrder).order_by(InspectionOrder.created_at.desc()).limit(limit)
    if status:
        q = q.where(InspectionOrder.status == status)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "inspections": [
        {"inspection_no": i.inspection_no, "part_id": i.part_id, "status": i.status,
         "accepted_qty": i.accepted_qty, "rejected_qty": i.rejected_qty,
         "inspected_at": str(i.inspected_at) if i.inspected_at else None}
        for i in rows
    ]}


@register_tool(
    name="list_non_conformances",
    domain="quality",
    risk_tier=RiskTier.READ,
    description="列出不良品 (NC) 記錄。可按嚴重度過濾。",
    slots=[
        Slot("severity", "string", required=False, description="minor / major / critical"),
        Slot("limit", "integer", required=False, description="預設 20"),
    ],
    required_permission="quality.nc.list",
)
async def _list_nc(db, user, severity: str = None, limit: int = 20):
    q = select(NonConformance).order_by(NonConformance.reported_at.desc()).limit(limit)
    if severity:
        q = q.where(NonConformance.severity == severity)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "non_conformances": [
        {"nc_no": n.nc_no, "part_id": n.part_id, "severity": n.severity,
         "description": n.description, "qty_affected": n.qty_affected,
         "disposition": n.disposition}
        for n in rows
    ]}


@register_tool(
    name="list_capa",
    domain="quality",
    risk_tier=RiskTier.READ,
    description="列出矯正預防措施 (CAPA) 記錄。",
    slots=[
        Slot("status", "string", required=False, description="open/in_progress/closed/verified"),
        Slot("limit", "integer", required=False, description="預設 20"),
    ],
    required_permission="quality.capa.list",
)
async def _list_capa(db, user, status: str = None, limit: int = 20):
    q = select(CAPARecord).order_by(CAPARecord.created_at.desc()).limit(limit)
    if status:
        q = q.where(CAPARecord.status == status)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "capa": [
        {"id": c.id, "nc_id": c.nc_id, "type": c.capa_type, "status": c.status,
         "description": c.description, "due_date": str(c.due_date) if c.due_date else None}
        for c in rows
    ]}


register_agent(
    "quality", "QualityAgent",
    system_prompt=(
        "你是 ERP 品質管理助手。職責：\n"
        "1. 查詢檢驗單、不良記錄與 CAPA\n"
        "2. 分析合格率與品質趨勢\n"
        "3. 追蹤矯正措施執行狀態\n\n"
        "請使用繁體中文，若發現高嚴重度 NC，主動提醒應通報。"
    ),
    tool_names=["list_inspections", "list_non_conformances", "list_capa"],
)

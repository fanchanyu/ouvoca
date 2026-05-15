"""MpsMrpAgent — query MPS / MRP plans (refactored v3.2.1)."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.mps_mrp import MpsMaster, MrpMaster


@register_tool(
    name="list_mps",
    domain="mps_mrp",
    risk_tier=RiskTier.READ,
    description="列出已建立的 MPS 主排程。",
    slots=[Slot("limit", "integer", required=False, description="預設 20")],
    required_permission="mps_mrp.mps.list",
)
async def _list_mps(db, user, limit: int = 20):
    rows = (await db.execute(
        select(MpsMaster).options(selectinload(MpsMaster.entries))
        .order_by(MpsMaster.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"total": len(rows), "mps_list": [
        {"id": m.id, "name": m.mps_name, "status": m.status,
         "horizon_start": str(m.horizon_start), "horizon_end": str(m.horizon_end),
         "entry_count": len(m.entries)}
        for m in rows
    ]}


@register_tool(
    name="list_mrp",
    domain="mps_mrp",
    risk_tier=RiskTier.READ,
    description="列出已產生的 MRP 計算結果，含建議的計畫訂單。",
    slots=[Slot("limit", "integer", required=False, description="預設 20")],
    required_permission="mps_mrp.mrp.list",
)
async def _list_mrp(db, user, limit: int = 20):
    rows = (await db.execute(
        select(MrpMaster).options(selectinload(MrpMaster.items))
        .order_by(MrpMaster.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"total": len(rows), "mrp_list": [
        {"id": m.id, "name": m.mrp_name, "status": m.status,
         "mps_id": m.mps_master_id, "item_count": len(m.items)}
        for m in rows
    ]}


register_agent(
    "mps_mrp", "MpsMrpAgent",
    system_prompt=(
        "你是 ERP 排程規劃 (MPS/MRP) 助手。職責：\n"
        "1. 解釋主排程與物料需求計畫\n"
        "2. 解讀 DTF/PTF 柵欄、淨需求、計畫訂單\n"
        "3. 識別缺料風險\n\n"
        "請使用繁體中文，必要時用條列說明。"
    ),
    tool_names=["list_mps", "list_mrp", "list_below_safety", "query_inventory"],
)

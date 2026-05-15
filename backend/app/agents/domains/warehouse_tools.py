"""WarehouseAgent — zones, bins, pick tasks (refactored v3.2.1)."""
from sqlalchemy import select
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.warehouse import WarehouseZone, BinLocation, PickTask, CycleCount


@register_tool(
    name="list_warehouse_zones",
    domain="warehouse",
    risk_tier=RiskTier.READ,
    description="列出所有倉儲區域。",
    slots=[],
    required_permission="warehouse.zone.list",
)
async def _list_zones(db, user):
    rows = (await db.execute(select(WarehouseZone))).scalars().all()
    return {"total": len(rows), "zones": [
        {"code": z.code, "name": z.name, "zone_type": z.zone_type, "is_active": z.is_active}
        for z in rows
    ]}


@register_tool(
    name="list_pick_tasks",
    domain="warehouse",
    risk_tier=RiskTier.READ,
    description="列出揀貨任務。可按狀態過濾。",
    slots=[
        Slot("status", "string", required=False, description="pending/in_progress/completed"),
        Slot("limit", "integer", required=False, description="預設 20"),
    ],
    required_permission="warehouse.pick.list",
)
async def _list_pick_tasks(db, user, status: str = None, limit: int = 20):
    q = select(PickTask).order_by(PickTask.created_at.desc()).limit(limit)
    if status:
        q = q.where(PickTask.status == status)
    rows = (await db.execute(q)).scalars().all()
    return {"total": len(rows), "tasks": [
        {"pick_no": t.pick_no, "part_id": t.part_id, "qty_to_pick": t.qty_to_pick,
         "qty_picked": t.qty_picked, "status": t.status}
        for t in rows
    ]}


@register_tool(
    name="list_cycle_counts",
    domain="warehouse",
    risk_tier=RiskTier.READ,
    description="列出盤點記錄，含系統量 / 實點量 / 差異。",
    slots=[Slot("limit", "integer", required=False, description="預設 20")],
    required_permission="warehouse.cycle_count.list",
)
async def _list_cycle_counts(db, user, limit: int = 20):
    rows = (await db.execute(
        select(CycleCount).order_by(CycleCount.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"total": len(rows), "counts": [
        {"count_no": c.count_no, "part_id": c.part_id, "system_qty": c.system_qty,
         "counted_qty": c.counted_qty, "variance": c.variance, "status": c.status}
        for c in rows
    ]}


register_agent(
    "warehouse", "WarehouseAgent",
    system_prompt=(
        "你是 ERP 倉儲管理助手。職責：\n"
        "1. 查詢儲位、揀貨任務\n"
        "2. 分析盤點差異\n"
        "3. 追蹤調撥進度\n\n"
        "請使用繁體中文。盤點差異 > 5% 應主動標記。"
    ),
    tool_names=["list_warehouse_zones", "list_pick_tasks", "list_cycle_counts", "query_inventory"],
)

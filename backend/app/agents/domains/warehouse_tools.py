"""WarehouseAgent — zones, bins, pick tasks."""
from sqlalchemy import select
from app.agents.engine import register_tool, register_agent
from app.models.warehouse import WarehouseZone, BinLocation, PickTask, CycleCount


async def _list_zones(db, user):
    rows = (await db.execute(select(WarehouseZone))).scalars().all()
    return {"total": len(rows), "zones": [
        {"code": z.code, "name": z.name, "zone_type": z.zone_type, "is_active": z.is_active}
        for z in rows
    ]}


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


async def _list_cycle_counts(db, user, limit: int = 20):
    rows = (await db.execute(
        select(CycleCount).order_by(CycleCount.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"total": len(rows), "counts": [
        {"count_no": c.count_no, "part_id": c.part_id, "system_qty": c.system_qty,
         "counted_qty": c.counted_qty, "variance": c.variance, "status": c.status}
        for c in rows
    ]}


register_tool("list_warehouse_zones", "列出倉儲區域。",
              {"type": "object", "properties": {}}, _list_zones)
register_tool("list_pick_tasks", "列出揀貨任務。",
              {"type": "object", "properties": {"status": {"type": "string"}, "limit": {"type": "integer"}}},
              _list_pick_tasks)
register_tool("list_cycle_counts", "列出盤點記錄。",
              {"type": "object", "properties": {"limit": {"type": "integer"}}}, _list_cycle_counts)

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

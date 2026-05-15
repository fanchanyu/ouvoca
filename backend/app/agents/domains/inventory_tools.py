"""InventoryAgent — query inventory, parts, stock health.

✨ Phase 1 Day 1: refactored to use new @register_tool decorator with risk_tier.
   See docs/CONVERSATIONAL_ERP_DESIGN_ZH.md §5 原則 #1.
"""
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.services.inventory import get_part_by_no, get_inventory, list_parts, list_inventory_below_safety


@register_tool(
    name="query_inventory",
    domain="inventory",
    risk_tier=RiskTier.READ,
    description="查詢特定零件的當前庫存量。可提供 part_no 或 part_id 任一。",
    slots=[
        Slot("part_no", "string", required=False, description="零件料號（如 M6-BOLT-20）"),
        Slot("part_id", "string", required=False, description="零件 UUID"),
    ],
    required_permission="inventory.part.read",
)
async def _query_inventory(db, user, part_no: str = None, part_id: str = None):
    part = None
    if part_no:
        part = await get_part_by_no(db, part_no)
    if part_id and not part:
        from app.services.inventory import get_part
        part = await get_part(db, part_id)
    if not part:
        return {"error": "找不到該零件", "query": {"part_no": part_no, "part_id": part_id}}
    inv = await get_inventory(db, part.id)
    return {
        "part_no": part.part_no, "name": part.name,
        "qty_on_hand": inv.qty_on_hand if inv else 0,
        "qty_available": inv.qty_available if inv else 0,
        "qty_allocated": inv.qty_allocated if inv else 0,
        "safety_stock": part.safety_stock,
        "lead_time_days": part.lead_time_days,
        "status": "低於安全庫存" if (inv and inv.qty_available < part.safety_stock) else "正常",
    }


@register_tool(
    name="list_parts",
    domain="inventory",
    risk_tier=RiskTier.READ,
    description="列出零件清單，可按類別過濾。",
    slots=[
        Slot("category", "string", required=False,
             description="raw_material / semi_finished / component / consumable / packaging"),
        Slot("limit", "integer", required=False, description="回傳上限，預設 20"),
    ],
    required_permission="inventory.part.list",
)
async def _list_parts(db, user, category: str = None, limit: int = 20):
    parts = await list_parts(db, limit=limit, category=category)
    return {
        "total": len(parts),
        "parts": [
            {"part_no": p.part_no, "name": p.name, "category": p.category,
             "safety_stock": p.safety_stock, "unit_cost": p.unit_cost}
            for p in parts
        ],
    }


@register_tool(
    name="list_below_safety",
    domain="inventory",
    risk_tier=RiskTier.READ,
    description="列出庫存低於安全庫存的零件，每筆含短缺量。",
    slots=[Slot("limit", "integer", required=False, description="回傳上限，預設 20")],
    required_permission="inventory.part.list",
)
async def _below_safety(db, user, limit: int = 20):
    rows = await list_inventory_below_safety(db, limit=limit)
    return {
        "total": len(rows),
        "items": [
            {"part_no": p.part_no, "name": p.name,
             "qty_available": inv.qty_available, "safety_stock": p.safety_stock,
             "shortage": p.safety_stock - inv.qty_available}
            for inv, p in rows
        ],
    }


register_agent(
    "inventory", "InventoryAgent",
    system_prompt=(
        "你是 ERP 庫存管理助手。職責：\n"
        "1. 查詢零件庫存與水位\n"
        "2. 列出低於安全庫存的零件\n"
        "3. 解讀庫存狀態\n\n"
        "請使用繁體中文，語氣專業簡潔。若需要進一步動作，請建議使用者切換到對應頁面。"
    ),
    tool_names=["query_inventory", "list_parts", "list_below_safety"],
)

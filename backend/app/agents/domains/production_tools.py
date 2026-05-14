"""ProductionAgent — query work orders, BOM, work centers."""
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.agents.engine import register_tool, register_agent
from app.models.production import ProductionOrder, WorkCenter, Operation
from app.models.product import Product, BOMItem


async def _query_wo(db, user, wo_no: str = None, status: str = None):
    q = select(ProductionOrder).options(joinedload(ProductionOrder.product))
    if wo_no:
        q = q.where(ProductionOrder.wo_no == wo_no)
    if status:
        q = q.where(ProductionOrder.status == status)
    rows = (await db.execute(q.limit(20).order_by(ProductionOrder.created_at.desc()))).scalars().all()
    return {"total": len(rows), "orders": [
        {"wo_no": o.wo_no, "product": o.product.name if o.product else "",
         "status": o.status, "ordered_qty": o.ordered_qty, "completed_qty": o.completed_qty,
         "rejected_qty": o.rejected_qty, "priority": o.priority,
         "scheduled_start": str(o.scheduled_start) if o.scheduled_start else None,
         "scheduled_end": str(o.scheduled_end) if o.scheduled_end else None}
        for o in rows
    ]}


async def _list_products(db, user, limit: int = 20):
    rows = (await db.execute(select(Product).limit(limit))).scalars().all()
    return {"total": len(rows), "products": [
        {"product_no": p.product_no, "name": p.name, "selling_price": p.selling_price,
         "standard_cost": p.standard_cost}
        for p in rows
    ]}


async def _get_bom(db, user, product_id: str):
    rows = (await db.execute(
        select(BOMItem)
        .options(joinedload(BOMItem.part))
        .where(BOMItem.product_id == product_id, BOMItem.is_active == True)
        .order_by(BOMItem.level, BOMItem.sequence_no)
    )).scalars().all()
    return {"total": len(rows), "bom": [
        {"part_no": b.part.part_no if b.part else "", "part_name": b.part.name if b.part else "",
         "level": b.level, "qty_per": b.qty_per, "scrap_rate": b.scrap_rate}
        for b in rows
    ]}


async def _list_work_centers(db, user):
    rows = (await db.execute(select(WorkCenter).where(WorkCenter.is_active == True))).scalars().all()
    return {"total": len(rows), "work_centers": [
        {"code": wc.code, "name": wc.name, "capacity_per_day": wc.capacity_per_day,
         "efficiency": wc.efficiency, "alternate_group": wc.alternate_group}
        for wc in rows
    ]}


register_tool("query_work_order", "查詢生產工單。",
              {"type": "object", "properties": {"wo_no": {"type": "string"},
                                                "status": {"type": "string"}}},
              _query_wo)
register_tool("list_products_tool", "列出產品/成品清單。",
              {"type": "object", "properties": {"limit": {"type": "integer"}}},
              _list_products)
register_tool("get_bom", "查詢產品 BOM 結構。",
              {"type": "object", "properties": {"product_id": {"type": "string"}}, "required": ["product_id"]},
              _get_bom)
register_tool("list_work_centers", "列出所有工作站/機台。",
              {"type": "object", "properties": {}}, _list_work_centers)

register_agent(
    "production", "ProductionAgent",
    system_prompt=(
        "你是 ERP 生產管理助手。職責：\n"
        "1. 查詢工單進度\n"
        "2. 解讀 BOM 結構\n"
        "3. 分析機台稼動\n\n"
        "請使用繁體中文。當涉及缺料時，主動建議查詢庫存。"
    ),
    tool_names=["query_work_order", "list_products_tool", "get_bom", "list_work_centers", "query_inventory"],
)

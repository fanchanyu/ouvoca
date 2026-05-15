"""ProductionAgent — query work orders, BOM, work centers.

✨ Phase 1 Day 1: refactored to use @register_tool decorator with risk_tier.
"""
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.production import ProductionOrder, WorkCenter
from app.models.product import Product, BOMItem


@register_tool(
    name="query_work_order",
    domain="production",
    risk_tier=RiskTier.READ,
    description="查詢生產工單，可按單號或狀態過濾。回傳含進度（已完成 / 不良）。",
    slots=[
        Slot("wo_no", "string", required=False, description="工單號"),
        Slot("status", "string", required=False,
             description="draft/released/in_progress/completed/cancelled"),
    ],
    required_permission="production.wo.read",
)
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


@register_tool(
    name="list_products_tool",
    domain="production",
    risk_tier=RiskTier.READ,
    description="列出產品/成品清單，含售價與標準成本。",
    slots=[Slot("limit", "integer", required=False, description="回傳上限，預設 20")],
    required_permission="production.product.list",
)
async def _list_products(db, user, limit: int = 20):
    rows = (await db.execute(select(Product).limit(limit))).scalars().all()
    return {"total": len(rows), "products": [
        {"product_no": p.product_no, "name": p.name, "selling_price": p.selling_price,
         "standard_cost": p.standard_cost}
        for p in rows
    ]}


@register_tool(
    name="get_bom",
    domain="production",
    risk_tier=RiskTier.READ,
    description="查詢產品 BOM 結構（多階展開），含每階用量與耗損率。",
    slots=[Slot("product_id", "string", required=True, description="產品 UUID")],
    required_permission="production.bom.read",
)
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


@register_tool(
    name="list_work_centers",
    domain="production",
    risk_tier=RiskTier.READ,
    description="列出所有 active 工作站/機台，含日產能與效率。",
    slots=[],
    required_permission="production.workcenter.list",
)
async def _list_work_centers(db, user):
    rows = (await db.execute(select(WorkCenter).where(WorkCenter.is_active == True))).scalars().all()
    return {"total": len(rows), "work_centers": [
        {"code": wc.code, "name": wc.name, "capacity_per_day": wc.capacity_per_day,
         "efficiency": wc.efficiency, "alternate_group": wc.alternate_group}
        for wc in rows
    ]}


register_agent(
    "production", "ProductionAgent",
    system_prompt=(
        "你是 ERP 生產管理助手。職責：\n"
        "1. 查詢工單進度（read tools）\n"
        "2. 解讀 BOM 結構\n"
        "3. 接受寫入指令「釋放工單 / release WO」→ 必走 release_work_order_with_confirm\n\n"
        "重要原則：\n"
        "- hard-write 永遠不繞過確認卡\n"
        "- 當涉及缺料時，主動建議查詢庫存\n"
        "- 使用繁體中文"
    ),
    tool_names=[
        "query_work_order", "list_products_tool", "get_bom", "list_work_centers",
        "query_inventory",
        "release_work_order_with_confirm",  # v3.2 hard-write
    ],
)

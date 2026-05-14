"""PurchaseAgent — query suppliers, POs, prices."""
from sqlalchemy import select
from app.agents.engine import register_tool, register_agent
from app.models.purchase import Supplier, PurchaseOrder, SupplierPrice


async def _query_supplier(db, user, keyword: str = "", tier: str = None):
    q = select(Supplier)
    if keyword:
        q = q.where((Supplier.name.contains(keyword)) | (Supplier.code.contains(keyword)))
    if tier:
        q = q.where(Supplier.tier == tier)
    rows = (await db.execute(q.limit(20))).scalars().all()
    return {"total": len(rows), "suppliers": [
        {"id": s.id, "code": s.code, "name": s.name, "tier": s.tier,
         "lead_time_days": s.lead_time_days, "is_approved": s.is_approved}
        for s in rows
    ]}


async def _query_purchase_order(db, user, po_no: str = None, status: str = None):
    q = select(PurchaseOrder)
    if po_no:
        q = q.where(PurchaseOrder.po_no == po_no)
    if status:
        q = q.where(PurchaseOrder.status == status)
    rows = (await db.execute(q.limit(20).order_by(PurchaseOrder.created_at.desc()))).scalars().all()
    return {"total": len(rows), "orders": [
        {"po_no": o.po_no, "supplier_id": o.supplier_id, "status": o.status,
         "total_amount": o.total_amount, "order_date": str(o.order_date),
         "expected_delivery_date": str(o.expected_delivery_date) if o.expected_delivery_date else None}
        for o in rows
    ]}


async def _supplier_price_history(db, user, part_id: str):
    rows = (await db.execute(
        select(SupplierPrice).where(SupplierPrice.part_id == part_id).limit(20)
    )).scalars().all()
    return {"total": len(rows), "prices": [
        {"supplier_id": p.supplier_id, "unit_price": p.unit_price, "currency": p.currency,
         "moq": p.moq, "lead_time_days": p.lead_time_days, "is_current": p.is_current}
        for p in rows
    ]}


register_tool(
    "query_supplier",
    "查詢供應商資訊。",
    {"type": "object", "properties": {
        "keyword": {"type": "string"},
        "tier": {"type": "string", "description": "T1/T2/T3"},
    }},
    _query_supplier,
)
register_tool(
    "query_purchase_order",
    "查詢採購單。",
    {"type": "object", "properties": {
        "po_no": {"type": "string"},
        "status": {"type": "string", "description": "draft/approved/sent/received/cancelled"},
    }},
    _query_purchase_order,
)
register_tool(
    "supplier_price_history",
    "查詢某零件的歷史報價清單。",
    {"type": "object", "properties": {"part_id": {"type": "string"}}, "required": ["part_id"]},
    _supplier_price_history,
)

register_agent(
    "purchase", "PurchaseAgent",
    system_prompt=(
        "你是 ERP 採購管理助手。職責：\n"
        "1. 查詢供應商與採購單\n"
        "2. 比較歷史報價\n"
        "3. 追蹤交期、提醒逾期\n\n"
        "請使用繁體中文，引用具體數據時加上單位。"
    ),
    tool_names=["query_supplier", "query_purchase_order", "supplier_price_history", "query_inventory"],
)

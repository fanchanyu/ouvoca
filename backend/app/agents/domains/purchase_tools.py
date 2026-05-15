"""PurchaseAgent — query suppliers, POs, prices.

✨ Phase 1 Day 1: refactored to use @register_tool decorator with risk_tier.
"""
from sqlalchemy import select
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.purchase import Supplier, PurchaseOrder, SupplierPrice


@register_tool(
    name="query_supplier",
    domain="purchase",
    risk_tier=RiskTier.READ,
    description="查詢供應商資訊。可按關鍵字（名稱/編號）或等級過濾。",
    slots=[
        Slot("keyword", "string", required=False, description="搜尋名稱或編號片段"),
        Slot("tier", "string", required=False, description="供應商等級 T1/T2/T3"),
    ],
    required_permission="purchase.supplier.read",
)
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


@register_tool(
    name="query_purchase_order",
    domain="purchase",
    risk_tier=RiskTier.READ,
    description="查詢採購單。可按單號或狀態過濾。",
    slots=[
        Slot("po_no", "string", required=False, description="採購單號"),
        Slot("status", "string", required=False,
             description="draft/approved/sent/partial_received/received/cancelled"),
    ],
    required_permission="purchase.po.read",
)
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


@register_tool(
    name="supplier_price_history",
    domain="purchase",
    risk_tier=RiskTier.READ,
    description="查詢某零件的歷史報價清單，含 MOQ 與交期。",
    slots=[Slot("part_id", "string", required=True, description="零件 UUID")],
    required_permission="purchase.price.read",
)
async def _supplier_price_history(db, user, part_id: str):
    rows = (await db.execute(
        select(SupplierPrice).where(SupplierPrice.part_id == part_id).limit(20)
    )).scalars().all()
    return {"total": len(rows), "prices": [
        {"supplier_id": p.supplier_id, "unit_price": p.unit_price, "currency": p.currency,
         "moq": p.moq, "lead_time_days": p.lead_time_days, "is_current": p.is_current}
        for p in rows
    ]}


register_agent(
    "purchase", "PurchaseAgent",
    system_prompt=(
        "你是 ERP 採購管理助手。職責：\n"
        "1. 查詢供應商與採購單（read tools）\n"
        "2. 比較歷史報價\n"
        "3. 接受寫入指令「下單 / 建立採購單」→ 必走 create_purchase_order_with_confirm（會出確認卡）\n\n"
        "重要原則：\n"
        "- hard-write 永遠不繞過確認卡\n"
        "- 缺欄位（供應商、料件、數量、單價、交期）時反問使用者，不要編造\n"
        "- 使用繁體中文，引用具體數據時加上單位"
    ),
    tool_names=[
        "query_supplier", "query_purchase_order", "supplier_price_history",
        "query_inventory",
        "create_purchase_order_with_confirm",  # v3.2 hard-write
    ],
)

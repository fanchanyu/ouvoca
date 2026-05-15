"""SalesAgent — sales orders, customers (含 v3.2 hard-write)。"""
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.crm_sales import SalesOrder, Customer


@register_tool(
    name="query_so",
    domain="sales",
    risk_tier=RiskTier.READ,
    description="查詢銷售訂單。可依訂單號 / 狀態 / 客戶 ID 過濾。",
    slots=[
        Slot("so_no", "string", required=False, description="訂單號"),
        Slot("status", "string", required=False, description="draft/confirmed/shipped/closed"),
        Slot("customer_id", "string", required=False, description="客戶 UUID"),
    ],
    required_permission="sales.order.list",
)
async def _query_so(db, user, so_no: str = None, status: str = None, customer_id: str = None):
    q = select(SalesOrder).options(joinedload(SalesOrder.customer))
    if so_no:
        q = q.where(SalesOrder.so_no == so_no)
    if status:
        q = q.where(SalesOrder.status == status)
    if customer_id:
        q = q.where(SalesOrder.customer_id == customer_id)
    rows = (await db.execute(q.limit(20).order_by(SalesOrder.created_at.desc()))).unique().scalars().all()
    return {"total": len(rows), "orders": [
        {"so_no": o.so_no, "customer": o.customer.name if o.customer else "",
         "status": o.status, "total_amount": o.total_amount,
         "payment_status": o.payment_status, "order_date": str(o.order_date)}
        for o in rows
    ]}


@register_tool(
    name="list_customers",
    domain="sales",
    risk_tier=RiskTier.READ,
    description="列出客戶清單，可按等級 / 關鍵字過濾。",
    slots=[
        Slot("grade", "string", required=False, description="客戶等級 A/B/C/D"),
        Slot("keyword", "string", required=False, description="名稱或編號關鍵字"),
        Slot("limit", "integer", required=False, description="回傳上限，預設 20"),
    ],
    required_permission="sales.customer.list",
)
async def _list_customers(db, user, grade: str = None, keyword: str = None, limit: int = 20):
    q = select(Customer)
    if grade:
        q = q.where(Customer.grade == grade)
    if keyword:
        like = f"%{keyword}%"
        q = q.where((Customer.name.like(like)) | (Customer.code.like(like)))
    rows = (await db.execute(q.limit(limit))).scalars().all()
    return {"total": len(rows), "customers": [
        {"id": c.id, "code": c.code, "name": c.name, "grade": c.grade,
         "credit_limit": c.credit_limit}
        for c in rows
    ]}


register_agent(
    "sales", "SalesAgent",
    system_prompt=(
        "你是 ERP 業務銷售助手。職責：\n"
        "1. 查詢銷售訂單與客戶（read tools）\n"
        "2. 追蹤訂單狀態與付款情況\n"
        "3. 接受寫入指令「改訂單交期 / update SO delivery」→ 必走 update_sales_order_delivery_with_confirm\n\n"
        "重要原則：\n"
        "- hard-write 永遠不繞過確認卡\n"
        "- 缺欄位時反問使用者，不要編造\n"
        "- 使用繁體中文，金額顯示加上幣別"
    ),
    tool_names=[
        "query_so", "list_customers", "list_products_tool",
        "update_sales_order_delivery_with_confirm",  # v3.2 hard-write
    ],
)

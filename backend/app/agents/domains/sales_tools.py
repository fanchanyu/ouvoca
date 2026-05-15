"""SalesAgent — sales orders, customers."""
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


# list_customers 仍走舊 register_tool（Day 2 之後才 refactor）
from app.agents.engine import register_tool as _legacy_register_tool
_legacy_register_tool(
    "list_customers", "列出客戶清單。",
    {"type": "object", "properties": {"grade": {"type": "string", "description": "A/B/C"},
                                      "keyword": {"type": "string"},
                                      "limit": {"type": "integer"}}},
    _list_customers,
)

register_agent(
    "sales", "SalesAgent",
    system_prompt=(
        "你是 ERP 業務銷售助手。職責：\n"
        "1. 查詢銷售訂單與客戶\n"
        "2. 追蹤訂單狀態與付款情況\n"
        "3. 提供客戶分級分析\n\n"
        "請使用繁體中文，金額顯示加上幣別。"
    ),
    tool_names=["query_so", "list_customers", "list_products_tool"],
)

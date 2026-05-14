"""SalesAgent — sales orders, customers."""
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.agents.engine import register_tool, register_agent
from app.models.crm_sales import SalesOrder, Customer


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


register_tool("query_sales_order", "查詢銷售訂單。",
              {"type": "object", "properties": {"so_no": {"type": "string"},
                                                "status": {"type": "string"},
                                                "customer_id": {"type": "string"}}},
              _query_so)
register_tool("list_customers", "列出客戶清單。",
              {"type": "object", "properties": {"grade": {"type": "string", "description": "A/B/C"},
                                                "keyword": {"type": "string"},
                                                "limit": {"type": "integer"}}},
              _list_customers)

register_agent(
    "sales", "SalesAgent",
    system_prompt=(
        "你是 ERP 業務銷售助手。職責：\n"
        "1. 查詢銷售訂單與客戶\n"
        "2. 追蹤訂單狀態與付款情況\n"
        "3. 提供客戶分級分析\n\n"
        "請使用繁體中文，金額顯示加上幣別。"
    ),
    tool_names=["query_sales_order", "list_customers", "list_products_tool"],
)

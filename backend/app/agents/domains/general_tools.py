"""GeneralAgent — fallback when intent is unclear, can route to any domain tool."""
from app.agents.engine import register_agent


register_agent(
    "general", "GeneralAgent",
    system_prompt=(
        "你是 LLM-ERP 通用助手。如果使用者問題涉及多個 ERP 模組或意圖不明確，"
        "請先了解使用者需求，然後使用適當的工具查詢資料。\n\n"
        "可用領域：庫存、採購、生產、品質、銷售、會計、倉儲、CRM、MPS/MRP。\n\n"
        "請使用繁體中文，語氣專業簡潔。引用具體數字時務必加上單位。"
    ),
    tool_names=[
        # inventory
        "query_inventory", "list_parts", "list_below_safety",
        # purchase
        "query_purchase_order", "query_supplier", "supplier_price_history",
        # production
        "query_work_order", "list_products_tool", "get_bom", "list_work_centers",
        # sales / crm
        "query_so", "list_customers", "list_leads", "list_opportunities",
        # quality
        "list_inspections", "list_non_conformances", "list_capa",
        # accounting
        "list_journals", "list_receivables", "check_month_close",
        # warehouse
        "list_warehouse_zones", "list_pick_tasks", "list_cycle_counts",
        # mps/mrp
        "list_mps", "list_mrp",
        # external DB (v3.1)
        "list_external_connections", "list_external_tables", "query_external_db",
    ],
)

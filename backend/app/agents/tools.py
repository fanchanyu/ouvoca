"""Aggregate tool & agent registry — imports all domain modules.

Each app.agents.domains.<domain> module registers its own tools + agent.
Import order is irrelevant; modules just call register_tool / register_agent.
"""
from app.agents.domains import (  # noqa: F401
    inventory_tools, purchase_tools, production_tools, mps_mrp_tools,
    quality_tools, sales_tools, accounting_tools, warehouse_tools,
    crm_tools, general_tools,
    external_db_tools,  # v3.1 外部 DB connectors
    hard_write_tools,   # v3.2 ConfirmCard 包裝的 hard-write tools
    glossary_tools,     # v3.3 同義詞 / 別名解析
    undo_tools,         # v3.3 90 秒撤銷
    migration_tools,    # v3.4 Schema Mapping AI + migrate_from_external_with_confirm
    email_digest_tools, # v3.5 每日摘要 preview + send_with_confirm
    planning_llm_tools, # v3.30 把 v3.25.9-v3.29 全部演算法包成 LLM tools
    crud_completion_tools,  # v3.31 補完 cancel/receive/ship/QC/JE/pick 等高頻 hard-write
    inventory_sales_tools,  # v3.32 進銷存深化（Quotation + StockCount + Reorder + 修改 PO/SO 行）
)

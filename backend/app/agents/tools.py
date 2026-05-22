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
    inventory_sales_deep_tools,  # v3.33 進銷存再深化（查/複製/寄報價 + 批次盤點 + 智慧採購 + PO/SO 加刪行 / 改交期）
    business_completion_tools,  # v3.34 業務面補完（Tax + Accounting + Approval + Warehouse pick + Quality NCR/CAPA）
    smb_friendly_tools,  # v3.35 電腦小白友善（whoami / system_health / list_what_can_i_do / customer_360 / grant_role）
    print_export_tools,  # v3.36 PDF 列印 + CSV/Excel 匯出 + setup_status + seed_demo_data
    setup_wizard_tools,  # v3.37 Day 0/1 卡關修補：公司資料 / 改密碼 / 角色中文 / 匯入引導 / 主動推播
    polish_tools,        # v3.38 第二輪卡關修補：成本 / 備份 / Undo / 客戶 disambiguation
    polish_v339_tools,   # v3.39 第三輪卡關修補：LOGO / 刪除三件套 / 分頁 / 批次列印 / digest 觸發
    polish_v340_tools,   # v3.40 第四輪卡關修補：相對日期 / 帳齡 / 凍結 / Audit / 比較 / case-insensitive
    polish_v341_tools,   # v3.41 第五輪卡關修補：毛利率 / 訂單跟單 / 寄 PDF email / FAQ / 資料健康
    polish_v342_tools,   # v3.42 第六輪卡關修補：使用者帳號 / 全域搜尋 / 附件 / 工作天 / transcript / 時區
)

"""Aggregate tool & agent registry — imports all domain modules.

Each app.agents.domains.<domain> module registers its own tools + agent.
Import order is irrelevant; modules just call register_tool / register_agent.
"""
from app.agents.domains import (  # noqa: F401
    inventory_tools, purchase_tools, production_tools, mps_mrp_tools,
    quality_tools, sales_tools, accounting_tools, warehouse_tools,
    crm_tools, general_tools,
)

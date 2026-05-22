"""v3.x — add tenant_id column to CRM / warehouse / etc. tables (P0 multi-tenant leak fix).

Closes the cross-tenant data leak where Lead/Opportunity/Contract/CrmEvent,
MonthEndClose, SupplierPrice/SupplierEvaluation, CAPARecord, and warehouse
tables (WarehouseZone/BinLocation/PickTask/CycleCount) lacked TenantMixin.

Backward-compat: tenant_id is nullable with no server_default. Existing rows
remain NULL; operators may backfill (e.g. UPDATE leads SET tenant_id='HQ')
after upgrade.

Revision ID: 003_add_tenant_id_to_crm_warehouse
Revises: 002_add_glossary_items
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "003_add_tenant_id_to_crm_warehouse"
down_revision: Union[str, None] = "002_add_glossary_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES: tuple[str, ...] = (
    # crm_sales
    "leads",
    "opportunities",
    "contracts",
    "crm_events",
    # accounting
    "month_end_closes",
    # purchase
    "supplier_prices",
    "supplier_evaluations",
    # quality
    "capa_records",
    # warehouse
    "warehouse_zones",
    "bin_locations",
    "pick_tasks",
    "cycle_counts",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("tenant_id", sa.String(50), nullable=True))
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    for table in TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")

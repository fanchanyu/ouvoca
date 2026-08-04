"""v3.60 — add tenant_id to 16 child/detail tables (P0 multi-tenant leak fix).

Closes the cross-tenant data leak where detail tables (SalesOrderItem,
BOMItem, JournalLine, Operation, DispatchLog, InspectionResult,
StockCountItem, PurchaseOrderItem, QuotationItem, RoutingStep,
ApprovalStepV2, ContractPricing, MpsEntry, MrpItem, ReorderRule,
ReplenishSuggestion) lacked TenantMixin — the auto tenant filter only
applies to models with tenant_id, so direct queries on these tables could
leak rows across tenants in multi-tenant / multi-factory deployments.

Backward-compat: tenant_id is nullable. Existing rows are backfilled to
'HQ' (matching the TenantMixin default) so the auto-filter
(WHERE tenant_id = current) does not silently exclude legacy data.

Revision ID: 007_tenant_id_child_tables
Revises: 006_accounts_fs_and_settings
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "007_tenant_id_child_tables"
down_revision: Union[str, None] = "006_accounts_fs_and_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column_spec) — column_spec 對齊 TenantMixin 定義 (String(36))
TABLES: tuple[tuple[str, sa.Column], ...] = tuple(
    (t, sa.Column("tenant_id", sa.String(36), nullable=True))
    for t in (
        # product
        "bom_items",
        # accounting
        "journal_lines",
        # crm / sales
        "sales_order_items",
        "contract_pricing",
        # approval
        "approval_workflow_steps",
        # quotation
        "quotation_items",
        # stock count
        "stock_count_items",
        # quality
        "inspection_results",
        # production
        "operations",
        "dispatch_logs",
        "routing_steps",
        # purchase
        "purchase_order_items",
        # mps / mrp
        "mps_entries",
        "mrp_items",
        # supplier plus
        "reorder_rules",
        "replenish_suggestions",
    )
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, column in TABLES:
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        if "tenant_id" not in existing_cols:
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(column)
            op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        # backfill：既有資料一律歸 HQ（與 TenantMixin 預設一致），
        # 避免 auto tenant filter 把 NULL tenant_id 的舊資料靜默排除。
        op.execute(
            sa.text(
                f"UPDATE {table} SET tenant_id = 'HQ' "
                f"WHERE tenant_id IS NULL"
            )
        )


def downgrade() -> None:
    for table, _column in TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")

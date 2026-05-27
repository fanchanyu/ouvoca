"""v3.54 — add einvoice_records table + SO chain fields (invoice_no / delivery_note_no / ar_id).

合規修補（統一發票使用辦法 + Taiwan tax 法規）：
  - EInvoiceRecord 表落地（5 年保存要求）
  - SalesOrder 加 invoice_no / delivery_note_no / ar_id 形成追溯鏈

Revision ID: 004_einvoice_records
Revises: 003_add_tenant_id_to_crm_warehouse
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "004_einvoice_records"
down_revision: Union[str, None] = "003_add_tenant_id_to_crm_warehouse"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "einvoice_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_no", sa.String(20), nullable=False, index=True),
        sa.Column("invoice_date", sa.String(8), nullable=False),
        sa.Column("invoice_time", sa.String(8)),
        sa.Column("seller_tax_id", sa.String(20), nullable=False),
        sa.Column("buyer_tax_id", sa.String(20)),
        sa.Column("buyer_name", sa.String(200)),
        sa.Column("sales_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Float(), server_default="0.05"),
        sa.Column("so_id", sa.String(36), sa.ForeignKey("sales_orders.id")),
        sa.Column("journal_entry_id", sa.String(36), sa.ForeignKey("journal_entries.id")),
        sa.Column("status", sa.String(20), server_default="issued"),
        sa.Column("tracking_no", sa.String(50)),
        sa.Column("cancelled_at", sa.DateTime()),
        sa.Column("cancel_reason", sa.Text()),
        sa.Column("mig_payload", sa.JSON()),
        sa.Column("tenant_id", sa.String(36), index=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("created_by", sa.String(36)),
    )
    op.create_index(
        "ix_einvoice_no_date", "einvoice_records",
        ["invoice_no", "invoice_date"],
    )

    # SalesOrder chain fields — SQLite ALTER TABLE 限制：使用 batch_alter_table
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.add_column(sa.Column("invoice_no", sa.String(20)))
        batch_op.add_column(sa.Column("delivery_note_no", sa.String(50)))
        batch_op.add_column(sa.Column("ar_id", sa.String(36)))


def downgrade() -> None:
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.drop_column("ar_id")
        batch_op.drop_column("delivery_note_no")
        batch_op.drop_column("invoice_no")
    op.drop_index("ix_einvoice_no_date", table_name="einvoice_records")
    op.drop_table("einvoice_records")

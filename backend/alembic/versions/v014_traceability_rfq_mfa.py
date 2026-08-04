"""v3.64 — 批號/序號追溯 + RFQ 詢價 + MFA(TOTP) 欄位。

新表：batch_lots / serial_numbers / rfqs / rfq_items /
      supplier_quotes / supplier_quote_items
users 加：mfa_secret / mfa_enabled

Revision ID: 014_traceability_rfq_mfa
Revises: 013_m3_documents
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "014_traceability_rfq_mfa"
down_revision: Union[str, None] = "013_m3_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "batch_lots" not in existing:
        op.create_table(
            "batch_lots",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("lot_no", sa.String(50), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("qty", sa.Float(), nullable=True),
            sa.Column("expiry_date", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("remark", sa.String(255), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_batch_lots_lot_no", "batch_lots", ["lot_no"])
        op.create_index("ix_batch_lots_part_id", "batch_lots", ["part_id"])
        op.create_index("ix_batch_lots_tenant_id", "batch_lots", ["tenant_id"])

    if "serial_numbers" not in existing:
        op.create_table(
            "serial_numbers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("serial_no", sa.String(100), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("batch_id", sa.String(36), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("last_document_type", sa.String(50), nullable=True),
            sa.Column("last_document_id", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_serial_numbers_serial_no", "serial_numbers", ["serial_no"])
        op.create_index("ix_serial_numbers_part_id", "serial_numbers", ["part_id"])
        op.create_index("ix_serial_numbers_tenant_id", "serial_numbers", ["tenant_id"])

    if "rfqs" not in existing:
        op.create_table(
            "rfqs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("rfq_no", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("need_date", sa.DateTime(), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("awarded_quote_id", sa.String(36), nullable=True),
            sa.Column("converted_po_id", sa.String(36), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("rfq_no"),
        )
        op.create_index("ix_rfqs_tenant_id", "rfqs", ["tenant_id"])

    if "rfq_items" not in existing:
        op.create_table(
            "rfq_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("rfq_id", sa.String(36), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=True),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("need_date", sa.DateTime(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_rfq_items_rfq_id", "rfq_items", ["rfq_id"])
        op.create_index("ix_rfq_items_tenant_id", "rfq_items", ["tenant_id"])

    if "supplier_quotes" not in existing:
        op.create_table(
            "supplier_quotes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("rfq_id", sa.String(36), nullable=False),
            sa.Column("supplier_id", sa.String(36), nullable=False),
            sa.Column("quote_date", sa.DateTime(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=True),
            sa.Column("lead_time_days", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(10), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_supplier_quotes_rfq_id", "supplier_quotes", ["rfq_id"])
        op.create_index("ix_supplier_quotes_tenant_id", "supplier_quotes", ["tenant_id"])

    if "supplier_quote_items" not in existing:
        op.create_table(
            "supplier_quote_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("quote_id", sa.String(36), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_quote_items_quote_id", "supplier_quote_items", ["quote_id"])
        op.create_index("ix_quote_items_tenant_id", "supplier_quote_items", ["tenant_id"])

    # users MFA 欄位
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "mfa_secret" not in user_cols:
            batch_op.add_column(sa.Column("mfa_secret", sa.String(64), nullable=True))
        if "mfa_enabled" not in user_cols:
            batch_op.add_column(sa.Column("mfa_enabled", sa.Boolean(), server_default="0"))


def downgrade() -> None:
    for table in (
        "supplier_quote_items", "supplier_quotes",
        "rfq_items", "rfqs", "serial_numbers", "batch_lots",
    ):
        op.drop_table(table)
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("mfa_enabled")
        batch_op.drop_column("mfa_secret")

"""v3.60 — add finance closure base tables (Phase B1).

bank_accounts / accounts_payable / payments / receipts —
金流閉環（AP + 收付款 + 銀行帳戶）的第一批基礎表，
解決「只有 AR、付款鏈斷掉、無銀行帳戶」的審計缺口。

Revision ID: 010_finance_closure
Revises: 009_document_numbering
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "010_finance_closure"
down_revision: Union[str, None] = "009_document_numbering"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "bank_accounts" not in existing:
        op.create_table(
            "bank_accounts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("bank_name", sa.String(100), nullable=True),
            sa.Column("branch_name", sa.String(100), nullable=True),
            sa.Column("account_no", sa.String(50), nullable=True),
            sa.Column("currency", sa.String(10), nullable=True),
            sa.Column("opening_balance", sa.Float(), nullable=True),
            sa.Column("current_balance", sa.Float(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_bank_accounts_tenant_id", "bank_accounts", ["tenant_id"])

    if "accounts_payable" not in existing:
        op.create_table(
            "accounts_payable",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("supplier_id", sa.String(36), nullable=False),
            sa.Column("invoice_no", sa.String(50), nullable=False),
            sa.Column("invoice_date", sa.DateTime(), nullable=False),
            sa.Column("due_date", sa.DateTime(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("paid_amount", sa.Float(), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("aging_days", sa.Integer(), nullable=True),
            sa.Column("source_type", sa.String(30), nullable=True),
            sa.Column("source_id", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_accounts_payable_tenant_id", "accounts_payable", ["tenant_id"])
        op.create_index("ix_accounts_payable_supplier_id", "accounts_payable", ["supplier_id"])

    if "payments" not in existing:
        op.create_table(
            "payments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("payment_no", sa.String(50), nullable=False),
            sa.Column("supplier_id", sa.String(36), nullable=False),
            sa.Column("payable_id", sa.String(36), nullable=True),
            sa.Column("bank_account_id", sa.String(36), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("payment_date", sa.DateTime(), nullable=False),
            sa.Column("method", sa.String(20), nullable=True),
            sa.Column("reference", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("payment_no"),
        )
        op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])
        op.create_index("ix_payments_supplier_id", "payments", ["supplier_id"])

    if "receipts" not in existing:
        op.create_table(
            "receipts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("receipt_no", sa.String(50), nullable=False),
            sa.Column("customer_id", sa.String(36), nullable=False),
            sa.Column("receivable_id", sa.String(36), nullable=True),
            sa.Column("bank_account_id", sa.String(36), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("receipt_date", sa.DateTime(), nullable=False),
            sa.Column("method", sa.String(20), nullable=True),
            sa.Column("reference", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("receipt_no"),
        )
        op.create_index("ix_receipts_tenant_id", "receipts", ["tenant_id"])
        op.create_index("ix_receipts_customer_id", "receipts", ["customer_id"])


def downgrade() -> None:
    for table in ("receipts", "payments", "accounts_payable", "bank_accounts"):
        for index in (
            "ix_receipts_customer_id", "ix_receipts_tenant_id",
            "ix_payments_supplier_id", "ix_payments_tenant_id",
            "ix_accounts_payable_supplier_id", "ix_accounts_payable_tenant_id",
            "ix_bank_accounts_tenant_id",
        ):
            if index.startswith(f"ix_{table}"):
                op.drop_index(index, table_name=table)
        op.drop_table(table)

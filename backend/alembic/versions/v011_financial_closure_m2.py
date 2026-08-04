"""v3.61 — M2 財務閉環：3-Way Match / 票據 / 固定資產 + AP 進項稅欄位。

新增表：
  - supplier_invoices / supplier_invoice_items（供應商發票 + 3-Way Match）
  - promissory_notes（票據管理）
  - fixed_assets（固定資產 + 折舊）
accounts_payable 加 sales_amount / tax_amount（401/405 進項拆算）。

Revision ID: 011_financial_closure_m2
Revises: 010_finance_closure
Create Date: 2026-08-04
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011_financial_closure_m2"
down_revision: str | None = "010_finance_closure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "supplier_invoices" not in existing:
        op.create_table(
            "supplier_invoices",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("invoice_no", sa.String(50), nullable=False),
            sa.Column("supplier_id", sa.String(36), nullable=False),
            sa.Column("po_id", sa.String(36), nullable=True),
            sa.Column("invoice_date", sa.DateTime(), nullable=False),
            sa.Column("due_date", sa.DateTime(), nullable=True),
            sa.Column("sales_amount", sa.Float(), nullable=True),
            sa.Column("tax_amount", sa.Float(), nullable=True),
            sa.Column("total_amount", sa.Float(), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_supplier_invoices_invoice_no", "supplier_invoices", ["invoice_no"])
        op.create_index("ix_supplier_invoices_tenant_id", "supplier_invoices", ["tenant_id"])

    if "supplier_invoice_items" not in existing:
        op.create_table(
            "supplier_invoice_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("invoice_id", sa.String(36), nullable=False),
            sa.Column("po_item_id", sa.String(36), nullable=True),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=True),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=True),
            sa.Column("line_total", sa.Float(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_supplier_invoice_items_invoice_id", "supplier_invoice_items", ["invoice_id"])
        op.create_index("ix_supplier_invoice_items_tenant_id", "supplier_invoice_items", ["tenant_id"])

    if "promissory_notes" not in existing:
        op.create_table(
            "promissory_notes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("note_type", sa.String(20), nullable=False),
            sa.Column("party_id", sa.String(36), nullable=False),
            sa.Column("party_name", sa.String(200), nullable=True),
            sa.Column("bank_name", sa.String(100), nullable=True),
            sa.Column("check_no", sa.String(50), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("issue_date", sa.DateTime(), nullable=False),
            sa.Column("due_date", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("deposit_bank_account_id", sa.String(36), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_promissory_notes_tenant_id", "promissory_notes", ["tenant_id"])
        op.create_index("ix_promissory_notes_due_date", "promissory_notes", ["due_date"])

    if "fixed_assets" not in existing:
        op.create_table(
            "fixed_assets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("cost", sa.Float(), nullable=False),
            sa.Column("salvage_value", sa.Float(), nullable=True),
            sa.Column("useful_life_months", sa.Integer(), nullable=False),
            sa.Column("acquisition_date", sa.DateTime(), nullable=False),
            sa.Column("depreciation_method", sa.String(20), nullable=True),
            sa.Column("accumulated_depreciation", sa.Float(), nullable=True),
            sa.Column("monthly_depreciation", sa.Float(), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("journal_entry_id", sa.String(36), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_fixed_assets_tenant_id", "fixed_assets", ["tenant_id"])

    # accounts_payable 加進項稅欄位（401/405 拆算 + 3-Way Match 金額）
    ap_cols = {c["name"] for c in inspector.get_columns("accounts_payable")}
    with op.batch_alter_table("accounts_payable") as batch_op:
        if "sales_amount" not in ap_cols:
            batch_op.add_column(sa.Column("sales_amount", sa.Float(), nullable=True))
        if "tax_amount" not in ap_cols:
            batch_op.add_column(sa.Column("tax_amount", sa.Float(), nullable=True))


def downgrade() -> None:
    for table in ("fixed_assets", "promissory_notes", "supplier_invoice_items", "supplier_invoices"):
        op.drop_table(table)
    with op.batch_alter_table("accounts_payable") as batch_op:
        batch_op.drop_column("tax_amount")
        batch_op.drop_column("sales_amount")

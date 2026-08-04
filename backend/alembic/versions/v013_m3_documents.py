"""v3.63 — M3 表單工程：請購單 / 收料單 / 領料單 / 退貨單。

新增 8 張表：
  - purchase_requisitions / purchase_requisition_items（PR→PO）
  - goods_receipt_notes / goods_receipt_note_items（GRN 收料）
  - material_issues / material_issue_items（工單領料）
  - return_notes / return_note_items（RMA 退貨）

Revision ID: 013_m3_documents
Revises: 012_security_hardening
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "013_m3_documents"
down_revision: Union[str, None] = "012_security_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "purchase_requisitions" not in existing:
        op.create_table(
            "purchase_requisitions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("pr_no", sa.String(50), nullable=False),
            sa.Column("requester_id", sa.String(36), nullable=True),
            sa.Column("department_id", sa.String(36), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("need_date", sa.DateTime(), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("converted_po_id", sa.String(36), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("pr_no"),
        )
        op.create_index("ix_purchase_requisitions_tenant_id", "purchase_requisitions", ["tenant_id"])

    if "purchase_requisition_items" not in existing:
        op.create_table(
            "purchase_requisition_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("pr_id", sa.String(36), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=True),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("need_date", sa.DateTime(), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_pr_items_pr_id", "purchase_requisition_items", ["pr_id"])
        op.create_index("ix_pr_items_tenant_id", "purchase_requisition_items", ["tenant_id"])

    if "goods_receipt_notes" not in existing:
        op.create_table(
            "goods_receipt_notes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("grn_no", sa.String(50), nullable=False),
            sa.Column("po_id", sa.String(36), nullable=False),
            sa.Column("supplier_id", sa.String(36), nullable=False),
            sa.Column("received_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("grn_no"),
        )
        op.create_index("ix_grns_po_id", "goods_receipt_notes", ["po_id"])
        op.create_index("ix_grns_tenant_id", "goods_receipt_notes", ["tenant_id"])

    if "goods_receipt_note_items" not in existing:
        op.create_table(
            "goods_receipt_note_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("grn_id", sa.String(36), nullable=False),
            sa.Column("po_item_id", sa.String(36), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("qty_received", sa.Float(), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_grn_items_grn_id", "goods_receipt_note_items", ["grn_id"])
        op.create_index("ix_grn_items_tenant_id", "goods_receipt_note_items", ["tenant_id"])

    if "material_issues" not in existing:
        op.create_table(
            "material_issues",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("issue_no", sa.String(50), nullable=False),
            sa.Column("wo_id", sa.String(36), nullable=False),
            sa.Column("issued_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("issue_no"),
        )
        op.create_index("ix_material_issues_wo_id", "material_issues", ["wo_id"])
        op.create_index("ix_material_issues_tenant_id", "material_issues", ["tenant_id"])

    if "material_issue_items" not in existing:
        op.create_table(
            "material_issue_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("issue_id", sa.String(36), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("unit_cost", sa.Float(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_mi_items_issue_id", "material_issue_items", ["issue_id"])
        op.create_index("ix_mi_items_tenant_id", "material_issue_items", ["tenant_id"])

    if "return_notes" not in existing:
        op.create_table(
            "return_notes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("return_no", sa.String(50), nullable=False),
            sa.Column("customer_id", sa.String(36), nullable=False),
            sa.Column("so_id", sa.String(36), nullable=True),
            sa.Column("return_date", sa.DateTime(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("return_no"),
        )
        op.create_index("ix_return_notes_customer_id", "return_notes", ["customer_id"])
        op.create_index("ix_return_notes_tenant_id", "return_notes", ["tenant_id"])

    if "return_note_items" not in existing:
        op.create_table(
            "return_note_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("return_id", sa.String(36), nullable=False),
            sa.Column("part_id", sa.String(36), nullable=False),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_rt_items_return_id", "return_note_items", ["return_id"])
        op.create_index("ix_rt_items_tenant_id", "return_note_items", ["tenant_id"])


def downgrade() -> None:
    for table in (
        "return_note_items", "return_notes",
        "material_issue_items", "material_issues",
        "goods_receipt_note_items", "goods_receipt_notes",
        "purchase_requisition_items", "purchase_requisitions",
    ):
        op.drop_table(table)

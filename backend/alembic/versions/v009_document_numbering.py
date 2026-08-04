"""v3.60 — add document_numbering table (Phase C1 集中式單據編號).

原子計數器：每 (tenant_id, doc_type, period) 一列，
INSERT ... ON CONFLICT DO UPDATE SET seq = seq + 1 RETURNING seq，
解決 SO/PO/JE/DN 各自生成、並發重號問題。

Revision ID: 009_document_numbering
Revises: 008_external_connections
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "009_document_numbering"
down_revision: Union[str, None] = "008_external_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("document_numbering"):
        op.create_table(
            "document_numbering",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("doc_type", sa.String(50), nullable=False),
            sa.Column("period", sa.String(20), nullable=False),
            sa.Column("seq", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "tenant_id", "doc_type", "period",
                name="uq_document_numbering_tenant_doc_period",
            ),
        )
        op.create_index("ix_document_numbering_tenant_id", "document_numbering", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_document_numbering_tenant_id", table_name="document_numbering")
    op.drop_table("document_numbering")

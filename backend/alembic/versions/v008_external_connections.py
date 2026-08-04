"""v3.60 — add external_connections table (G-510 加密儲存外部 DB 連線).

連線設定（含 DB 帳密）只以 AES-256-GCM 密文存在 config_encrypted，
取代 services.connections 的 in-memory dict（重啟即失 + 明文風險）。

Revision ID: 008_external_connections
Revises: 007_tenant_id_child_tables
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "008_external_connections"
down_revision: Union[str, None] = "007_tenant_id_child_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("external_connections"):
        op.create_table(
            "external_connections",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("connector", sa.String(50), nullable=False),
            sa.Column("config_encrypted", sa.Text(), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("name"),
        )
        op.create_index("ix_external_connections_name", "external_connections", ["name"])
        op.create_index("ix_external_connections_tenant_id", "external_connections", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_external_connections_tenant_id", table_name="external_connections")
    op.drop_index("ix_external_connections_name", table_name="external_connections")
    op.drop_table("external_connections")

"""v3.46 — add glossary_items table for synonym persistence (Phase 2 G-201).

For deployments that already ran v001_initial_baseline and need this table
added incrementally. New installs get it via v001 (create_all includes it).

Revision ID: 002_add_glossary_items
Revises: 001_initial_baseline
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "002_add_glossary_items"
down_revision: Union[str, None] = "001_initial_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 冪等保護：v001 baseline 用 Base.metadata.create_all(checkfirst=True)
    # 會把「當下模型」的全部表一次建出（含 glossary_items），
    # 此處若直接 create_table 在全新 DB 會噴 duplicate。先檢查再建。
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("glossary_items"):
        op.create_table(
            "glossary_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("term", sa.String(200), nullable=False, index=True),
            sa.Column("canonical_type", sa.String(50), nullable=False, index=True),
            sa.Column("canonical_id", sa.String(200), nullable=False),
            sa.Column("canonical_label", sa.String(500), server_default=""),
            sa.Column("confidence", sa.Float(), server_default="1.0"),
            sa.Column("language", sa.String(20), server_default="zh-TW"),
            sa.Column("notes", sa.Text(), server_default=""),
            sa.Column("created_by", sa.String(36)),
            sa.Column("created_at", sa.DateTime()),
        )
        # Composite index for fast upsert lookups
        op.create_index(
            "ix_glossary_term_type",
            "glossary_items",
            ["term", "canonical_type"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_glossary_term_type", table_name="glossary_items")
    op.drop_table("glossary_items")

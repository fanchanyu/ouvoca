"""v3.66 — 健檢 #19：代碼欄位改租戶域唯一。

BankAccount.code / FixedAsset.code 原本全域 unique —
多租戶下 A 廠佔用代碼會擋住 B 廠。改為不設 DB unique，
租戶域唯一由 service 層查詢把關（含 tenant_id 過濾）。

Revision ID: 015_tenant_scoped_codes
Revises: 014_traceability_rfq_mfa
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "015_tenant_scoped_codes"
down_revision: Union[str, None] = "014_traceability_rfq_mfa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in ("bank_accounts", "fixed_assets"):
        if not inspector.has_table(table):
            continue
        # batch_alter_table + alter_column(unique=False)：
        # SQLite 會重建表（移除外建唯一 index），PostgreSQL 直接 drop constraint
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "code",
                existing_type=sa.String(50),
                existing_nullable=False,
                unique=False,
            )


def downgrade() -> None:
    # 還原全域 unique（僅提示；SQLite 重建成本高，實務上不回滾）
    pass

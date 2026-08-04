"""M1-1 — accounts 加 fs_line/is_system + system_settings 表。

  - Account.fs_line      : 三大報表行對應（值域 app.services.fs_defs.FS_LINES）
  - Account.is_system    : 系統內建科目保護（硬編碼五碼 1100/1200/2100/2200/4100）
  - system_settings 表   : 系統組態 key-value（M1-3）

Revision ID: 006_accounts_fs_and_settings
Revises: 005_delivery_notes
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "006_accounts_fs_and_settings"
down_revision: Union[str, None] = "005_delivery_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # 1) system_settings 表（新表，顯式建立）
    if not inspector.has_table("system_settings"):
        op.create_table(
            "system_settings",
            sa.Column("key", sa.String(80), primary_key=True),
            sa.Column("value", sa.JSON(), nullable=False),
            sa.Column("group", sa.String(40), server_default="general"),
            sa.Column("description", sa.String(200)),
            sa.Column("is_system", sa.Boolean(), server_default="0"),
            sa.Column("updated_by", sa.String(36)),
            sa.Column("updated_at", sa.DateTime()),
        )

    # 2) accounts 加欄位（SQLite 需 batch）
    existing_cols = {c["name"] for c in inspector.get_columns("accounts")}
    if "fs_line" not in existing_cols or "is_system" not in existing_cols:
        with op.batch_alter_table("accounts") as batch_op:
            if "fs_line" not in existing_cols:
                batch_op.add_column(sa.Column("fs_line", sa.String(80)))
            if "is_system" not in existing_cols:
                batch_op.add_column(sa.Column("is_system", sa.Boolean(), server_default="0"))

    # 3) 硬編碼五碼回填保護（既有安裝）
    op.execute(
        "UPDATE accounts SET is_system = 1 "
        "WHERE code IN ('1100', '1200', '2100', '2200', '4100')"
    )

    # 4) 報表查詢索引（Phase 1 三大報表用）
    if "ix_accounts_fs_line" not in {i["name"] for i in inspector.get_indexes("accounts")}:
        op.create_index("ix_accounts_fs_line", "accounts", ["fs_line"])


def downgrade() -> None:
    op.drop_index("ix_accounts_fs_line", table_name="accounts")
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("is_system")
        batch_op.drop_column("fs_line")
    op.drop_table("system_settings")

"""v3.62 — 資安強化：登入鎖定 + session 撤銷欄位。

users 加：
  - token_version（改密碼 +1 → 舊 JWT 失效）
  - failed_login_count / locked_until（暴力破解鎖定）

Revision ID: 012_security_hardening
Revises: 011_financial_closure_m2
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "012_security_hardening"
down_revision: Union[str, None] = "011_financial_closure_m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "token_version" not in cols:
            batch_op.add_column(sa.Column("token_version", sa.Integer(), server_default="0"))
        if "failed_login_count" not in cols:
            batch_op.add_column(sa.Column("failed_login_count", sa.Integer(), server_default="0"))
        if "locked_until" not in cols:
            batch_op.add_column(sa.Column("locked_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_count")
        batch_op.drop_column("token_version")

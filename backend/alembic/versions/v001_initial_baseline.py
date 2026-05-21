"""Baseline migration — auto-creates all tables from SQLAlchemy metadata.

v3.34: 客戶上 PostgreSQL prod 第一次部署用。將 Base.metadata 之全部 tables
一次性建立。後續若加新表，請用 `alembic revision --autogenerate` 產生
incremental migration。

設計選擇：
  • 不用手寫 op.create_table for each table（會有 ~30 個表，易出錯且難維護）
  • 改用 Base.metadata.create_all(bind=connection) — 與 init_db() 完全一致
  • 這樣若 model 改動，run alembic upgrade head 也能跟著建新表
  • Downgrade 用 Base.metadata.drop_all（謹慎用，僅 dev）

Revision ID: 001_initial_baseline
Revises:
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """建立全部 table。"""
    # 將 SQLAlchemy metadata 全部 create
    # 這比 op.create_table 手寫安全 — 不會與 model drift
    from app.core.base import Base
    import app.models  # noqa: F401 - populate metadata

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    """drop 全部 table（謹慎用）。"""
    from app.core.base import Base
    import app.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

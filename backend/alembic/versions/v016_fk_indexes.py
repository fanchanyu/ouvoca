"""v3.69 — 效能健檢 ①：外鍵欄位自動建索引。

背景（fixProblem.txt 效能審計）：181 個 FK 欄位中 159 個無索引（87%）。
資料量小時全表掃描看不出來，單據累積到數萬張後每個關聯查詢都變線性掃描
（實測 2 萬 PO 明細：無索引 6.9ms vs 有索引 0.007ms，1,030 倍）。

做法：掃 Base.metadata 的所有 ForeignKey 欄位，為每個建
複合索引 (tenant_id, fk) —— 一個索引同時吃掉自動租戶過濾與關聯查詢。
（PostgreSQL 正式環境建議改 CONCURRENTLY 建立避免鎖表，屬運維調用。）

Revision ID: 016_fk_indexes
Revises: 015_tenant_scoped_codes
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "016_fk_indexes"
down_revision: Union[str, None] = "015_tenant_scoped_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # v3.70：委派給共用函式 — 與 init_db() 同一來源，
    # 全新安裝與升級路徑的行為一致。
    from app.services.db_indexes import ensure_fk_indexes
    created = ensure_fk_indexes(op.get_bind())
    print(f"  ✓ FK/排序索引建立：{created} 個")


def downgrade() -> None:
    # 索引屬優化，不回滾（避免誤刪正式環境索引）
    pass

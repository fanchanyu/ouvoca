"""FK 索引守衛（v3.70）— 全新安裝與升級共用。

背景（Ouvoca vs.txt 審計 B）：v016 只走 alembic 建索引，
但一鍵安裝 / Docker / 每次啟動走的是 init_db()（create_all），
全新客戶拿到的是沒有 FK 索引的 DB（「越用越慢」原始狀態）。

解法：把 FK 索引邏輯抽成共用函式，init_db() 與 migration 都呼叫。
  - init_db()：create_all 後呼叫 → 全新安裝直接有索引
  - v016：呼叫同一函式 → 升級路徑一致
  - 全部用 CREATE INDEX IF NOT EXISTS → 冪等安全
"""
from __future__ import annotations

import sqlalchemy as sa

from app.core.logging import get_logger

log = get_logger(__name__)


def ensure_fk_indexes(connection) -> int:
    """掃 Base.metadata 為每個 FK 欄位建複合索引 (tenant_id, fk)，
    另為常用單據表建 (tenant_id, created_at) 排序索引。

    回傳本次建立的索引數（IF NOT EXISTS → 重跑不會重複）。
    """
    from app.core.base import Base
    import app.models  # noqa: F401 — populate metadata

    inspector = sa.inspect(connection)
    created = 0

    for table in Base.metadata.sorted_tables:
        tname = table.name
        if not inspector.has_table(tname):
            continue
        cols = {c["name"] for c in inspector.get_columns(tname)}
        existing = {
            idx["name"]: set(idx["column_names"] or [])
            for idx in inspector.get_indexes(tname)
        }
        has_tenant = "tenant_id" in cols

        for col in table.columns:
            if not col.foreign_keys or col.name not in cols:
                continue
            fk_col = col.name
            # 已含此欄位的索引存在 → 跳過
            if any(fk_col in covered for covered in existing.values()):
                continue
            idx_name = (
                f"ix_{tname}_{fk_col}_tenant" if has_tenant
                else f"ix_{tname}_{fk_col}"
            )
            if idx_name in existing:
                continue
            columns = ["tenant_id", fk_col] if has_tenant else [fk_col]
            quoted = ", ".join(f'"{c}"' for c in columns)
            connection.execute(sa.text(
                f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{tname}" ({quoted})'
            ))
            created += 1

    # 常用排序欄：(tenant_id, created_at)
    for tname in (
        "journal_entries", "inventory_transactions",
        "sales_orders", "purchase_orders", "production_orders",
    ):
        if not inspector.has_table(tname):
            continue
        cols = {c["name"] for c in inspector.get_columns(tname)}
        idx_name = f"ix_{tname}_created_at_tenant"
        existing = {i["name"] for i in inspector.get_indexes(tname)}
        if idx_name not in existing and {"tenant_id", "created_at"} <= cols:
            connection.execute(sa.text(
                f'CREATE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "{tname}" ("tenant_id", "created_at")'
            ))
            created += 1

    if created:
        log.info("FK indexes ensured: %d new", created)
    return created

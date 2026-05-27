"""v3.55 — add delivery_notes + delivery_note_items + DN linkback fields.

商業會計法第 33 條：出貨單為銷貨原始憑證。v3.55 將 DN 落 DB，與 SO/Invoice/JE
形成完整 O2C 鏈，解決王董「出貨單沒對應傳票及發票，進銷存沒同步」之痛。

Revision ID: 005_delivery_notes
Revises: 004_einvoice_records
Create Date: 2026-05-25
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "005_delivery_notes"
down_revision: Union[str, None] = "004_einvoice_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # v3.55: 升級腳本必須對既有 DB idempotent — 既有用戶若 DB 從 create_all 路徑
    # 建立（非 alembic-only），tax_id / tables 可能已存在；此處先檢查再執行，
    # 避免 ALTER TABLE failed 卡死整支 migration（修 v3.55 升級時實際踩過此坑）。
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Customer 加 tax_id（B2B 統編；B2C 留 NULL）— O2C 鏈判斷是否開發票
    existing_cols = {c["name"] for c in inspector.get_columns("customers")}
    if "tax_id" not in existing_cols:
        with op.batch_alter_table("customers") as batch_op:
            batch_op.add_column(sa.Column("tax_id", sa.String(20)))

    # 若兩個 table 都已存在，視為已 migrated 直接跳過
    if inspector.has_table("delivery_notes") and inspector.has_table("delivery_note_items"):
        return

    op.create_table(
        "delivery_notes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dn_no", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("so_id", sa.String(36), sa.ForeignKey("sales_orders.id"), nullable=False, index=True),
        sa.Column("ship_date", sa.DateTime(), nullable=False),
        sa.Column("carrier", sa.String(100)),
        sa.Column("tracking_no", sa.String(100)),
        sa.Column("signed_by", sa.String(100)),
        sa.Column("signed_at", sa.DateTime()),
        sa.Column("status", sa.String(20), server_default="shipped", nullable=False),
        sa.Column("invoice_no", sa.String(20)),
        sa.Column("journal_entry_id", sa.String(36), sa.ForeignKey("journal_entries.id")),
        sa.Column("remarks", sa.Text()),
        sa.Column("tenant_id", sa.String(36), index=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("created_by", sa.String(36)),
    )
    op.create_table(
        "delivery_note_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dn_id", sa.String(36), sa.ForeignKey("delivery_notes.id"), nullable=False, index=True),
        sa.Column("so_item_id", sa.String(36), sa.ForeignKey("sales_order_items.id")),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False),
        sa.Column("qty_shipped", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), server_default="0"),
        sa.Column("line_amount", sa.Float(), server_default="0"),
        sa.Column("tenant_id", sa.String(36), index=True),
    )


def downgrade() -> None:
    op.drop_table("delivery_note_items")
    op.drop_table("delivery_notes")
    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_column("tax_id")

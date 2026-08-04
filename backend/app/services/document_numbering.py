"""集中式單據編號服務（Phase C1）。

問題（審計 Phase C1）：SO/PO/JE/DN 各自生成單號，DN 用 COUNT+1（並發重號），
SO/PO/JE 用 timestamp+uuid（不可讀、無法序）。解法：
  - 單一 document_numbering 表做原子計數器（INSERT ... ON CONFLICT ... RETURNING）
  - 每 (tenant_id, doc_type, period) 獨立序號；單號含 tenant code 保證全域唯一
    （so_no / po_no / entry_no / dn_no 都是 unique constraint）
  - 格式統一：{PREFIX}-{TENANT}-{PERIOD}-{SEQ:04d}

使用：
    from app.services.document_numbering import next_document_no
    so_no = await next_document_no(db, "SO")
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.logging import get_logger

log = get_logger(__name__)


DEFAULT_FORMATS: dict[str, str] = {
    "SO": "SO-{TENANT}-{PERIOD}-{SEQ:04d}",
    "PO": "PO-{TENANT}-{PERIOD}-{SEQ:04d}",
    "JE": "JE-{TENANT}-{PERIOD}-{SEQ:04d}",
    "DN": "DN-{TENANT}-{PERIOD}-{SEQ:04d}",
    "QUOTATION": "QT-{TENANT}-{PERIOD}-{SEQ:04d}",
    "INVOICE": "INV-{TENANT}-{PERIOD}-{SEQ:04d}",
    "PAYMENT": "PY-{TENANT}-{PERIOD}-{SEQ:04d}",
    "RECEIPT": "RC-{TENANT}-{PERIOD}-{SEQ:04d}",
    "PR": "PR-{TENANT}-{PERIOD}-{SEQ:04d}",        # v3.63 請購單
    "GRN": "GRN-{TENANT}-{PERIOD}-{SEQ:04d}",      # v3.63 收料單
    "MI": "MI-{TENANT}-{PERIOD}-{SEQ:04d}",        # v3.63 領料單
    "RT": "RT-{TENANT}-{PERIOD}-{SEQ:04d}",        # v3.63 退貨單
    "RFQ": "RFQ-{TENANT}-{PERIOD}-{SEQ:04d}",      # v3.64 詢價單
}


def today_period() -> str:
    return datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%d")


async def next_document_no(
    db,
    doc_type: str,
    *,
    period: str | None = None,
    tenant_id: str | None = None,
    fmt: str | None = None,
) -> str:
    """原子取得下一個單據號碼。

    同一個 transaction 內多次呼叫會依序拿到 1, 2, 3...（counters 各自累加）。
    呼叫端應在建單據的 transaction 內使用（commit 由 caller 負責）。
    """
    from app.core.tenant_context import get_current_tenant
    from app.models.document_numbering import DocumentNumbering

    tenant = tenant_id or get_current_tenant() or "HQ"
    period = period or today_period()
    fmt = fmt or DEFAULT_FORMATS.get(doc_type, "{PREFIX}-{TENANT}-{PERIOD}-{SEQ:04d}")

    bind = db.get_bind()
    dialect = getattr(bind, "dialect", None)
    dialect_name = getattr(dialect, "name", "sqlite")

    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as _pg_insert
        stmt = _pg_insert(DocumentNumbering).values(
            tenant_id=tenant, doc_type=doc_type, period=period, seq=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                DocumentNumbering.tenant_id,
                DocumentNumbering.doc_type,
                DocumentNumbering.period,
            ],
            set_={"seq": DocumentNumbering.seq + 1},
        ).returning(DocumentNumbering.seq)
    else:
        from sqlalchemy.dialects.sqlite import insert as _sqlite_insert
        stmt = _sqlite_insert(DocumentNumbering).values(
            tenant_id=tenant, doc_type=doc_type, period=period, seq=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                DocumentNumbering.tenant_id,
                DocumentNumbering.doc_type,
                DocumentNumbering.period,
            ],
            set_={"seq": DocumentNumbering.seq + 1},
        ).returning(DocumentNumbering.seq)

    seq = (await db.execute(stmt)).scalar_one()
    return fmt.format(
        PREFIX=doc_type,
        TENANT=tenant,
        PERIOD=period,
        SEQ=int(seq),
    )

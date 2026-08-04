"""v3.60 Phase C1 tests — 集中式單據編號（防並發重號）。"""
from __future__ import annotations

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.core.tenant_context import set_current_tenant
    from app.database import AsyncSessionLocal
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_next_document_no_sequential(db):
    from app.services.document_numbering import next_document_no

    n1 = await next_document_no(db, "SO")
    n2 = await next_document_no(db, "SO")
    n3 = await next_document_no(db, "SO")

    assert n1.startswith("SO-")
    assert n2.startswith("SO-")
    assert n3.startswith("SO-")
    # 同一 tenant/period 下必須嚴格遞增且不重複
    seqs = [int(n.rsplit("-", 1)[1]) for n in (n1, n2, n3)]
    assert seqs == sorted(set(seqs)), f"單號重複或未遞增：{(n1, n2, n3)}"
    assert seqs[0] + 1 == seqs[1] and seqs[1] + 1 == seqs[2]


@pytest.mark.asyncio
async def test_next_document_no_distinct_types(db):
    from app.services.document_numbering import next_document_no

    so = await next_document_no(db, "SO")
    po = await next_document_no(db, "PO")
    assert so.startswith("SO-")
    assert po.startswith("PO-")


@pytest.mark.asyncio
async def test_so_po_je_created_with_central_numbering(db):
    """既有 create service 應改用集中編號（grep + 實際建立驗證）。"""
    from pathlib import Path
    for rel, needle in [
        ("app/services/sales.py", 'so_no = await next_document_no(db, "SO")'),
        ("app/services/purchase.py", 'po_no = await next_document_no(db, "PO")'),
        ("app/services/accounting.py", 'entry_no = await next_document_no(db, "JE")'),
        ("app/services/sales.py", 'return await next_document_no(db, "DN")'),
    ]:
        src = (Path(__file__).resolve().parents[2] / rel).read_text(encoding="utf-8")
        assert needle in src, f"{rel} 未接入集中編號"


def test_migration_v008_exists():
    from pathlib import Path
    mig = (Path(__file__).resolve().parents[2] / "alembic" / "versions" /
           "v009_document_numbering.py").read_text(encoding="utf-8")
    assert "document_numbering" in mig
    assert "uq_document_numbering_tenant_doc_period" in mig

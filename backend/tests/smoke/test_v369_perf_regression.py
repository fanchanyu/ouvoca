"""v3.69 效能健檢回歸 — PO 列表 400 bug、security headers、audit 只記 mutation。"""
from __future__ import annotations

import asyncio
import uuid


def test_po_list_http_with_items(seeded_client, admin_headers):
    """健檢 P0：GET /api/purchase/orders 在獨立 HTTP session 不得 400。"""
    from app.database import AsyncSessionLocal
    from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
    from app.models.inventory import Part

    async def _seed():
        async with AsyncSessionLocal() as db:
            sup = Supplier(id=str(uuid.uuid4()), code="PERF-SUP", name="效能供應商",
                           tier="T2", is_approved=True)
            part = Part(id=str(uuid.uuid4()), part_no="PERF-PART", name="效能料件",
                        category="component", unit_cost=5)
            db.add_all([sup, part])
            await db.commit()
            po = PurchaseOrder(id=str(uuid.uuid4()), po_no="PO-PERF-001",
                               supplier_id=sup.id, status="draft", total_amount=100)
            db.add(po)
            await db.commit()
            db.add(PurchaseOrderItem(id=str(uuid.uuid4()), po_id=po.id, line_no=1,
                                     part_id=part.id, ordered_qty=10, unit_price=10,
                                     line_total=100))
            await db.commit()
    asyncio.run(_seed())

    r = seeded_client.get("/api/purchase/orders", headers=admin_headers)
    assert r.status_code == 200, f"PO 列表不應 400：{r.status_code} {r.text[:200]}"
    assert any(p["po_no"] == "PO-PERF-001" for p in r.json())


def test_security_headers_and_request_id(seeded_client, admin_headers):
    """pure ASGI middleware：HSTS/X-Frame-Options + X-Request-ID 正常。"""
    r = seeded_client.get("/api/inventory/parts", headers=admin_headers)
    assert r.headers.get("strict-transport-security", "").startswith("max-age=")
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-request-id")


def test_audit_skips_get(seeded_client, admin_headers):
    """效能健檢 ②：GET 不寫 audit log（只記 mutation）。"""
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.ai_governance import AuditLog

    async def _count() -> int:
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(func.count(AuditLog.id)))).scalar_one()

    before = asyncio.run(_count())
    for _ in range(5):
        seeded_client.get("/api/inventory/parts", headers=admin_headers)
    after = asyncio.run(_count())
    assert after == before, f"GET 不應產生 audit log：{before} → {after}"

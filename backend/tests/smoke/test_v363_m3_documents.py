"""v3.63 M3 tests — 請購單(PR→PO) / 收料單(GRN) / 領料單 / 退貨單(RMA)。"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    from app.core.tenant_context import set_current_tenant
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_pr_approve_convert_to_po(db):
    """請購單：建立 → 核准 → 轉採購單（品項/數量帶入，狀態 converted）。"""
    from app.models.inventory import Part
    from app.models.purchase import Supplier
    from app.services.m3_documents import (
        approve_purchase_requisition, convert_pr_to_po, create_purchase_requisition,
    )

    part = Part(id=str(uuid.uuid4()), part_no="PR-PART-1", name="請購料件",
                category="component", unit_cost=10)
    sup = Supplier(id=str(uuid.uuid4()), code="SUP-PR", name="PR 供應商", tier="T2", is_approved=True)
    db.add_all([part, sup])
    await db.commit()

    pr = await create_purchase_requisition(db, {
        "items": [{"part_id": part.id, "qty": 50}],
        "remark": "M3 測試請購",
    }, {"employee_id": "e-pr"})
    assert pr.pr_no.startswith("PR-")
    assert pr.status == "draft"

    await approve_purchase_requisition(db, pr.id)
    po = await convert_pr_to_po(db, pr.id, sup.id, {"employee_id": "e-pr"})
    assert po.po_no.startswith("PO-")
    assert len(po.items) == 1
    assert po.items[0].ordered_qty == 50

    from app.models.documents_m3 import PurchaseRequisition
    from sqlalchemy import select
    pr_after = (await db.execute(
        select(PurchaseRequisition).where(PurchaseRequisition.id == pr.id)
    )).scalar_one()
    assert pr_after.status == "converted"
    assert pr_after.converted_po_id == po.id


@pytest.mark.asyncio
async def test_grn_receives_and_inbounds(db):
    """收料單：PO 收貨 + 入庫 + PO 狀態變 received。"""
    from app.models.inventory import Part, Inventory
    from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
    from app.services.m3_documents import create_grn
    from sqlalchemy import select

    sup = Supplier(id=str(uuid.uuid4()), code="SUP-GRN", name="GRN 供應商", tier="T2", is_approved=True)
    part = Part(id=str(uuid.uuid4()), part_no="GRN-PART-1", name="收料料件",
                category="raw", unit_cost=5)
    db.add_all([sup, part,
               Inventory(id=str(uuid.uuid4()), part_id=part.id,
                         qty_on_hand=0, qty_available=0)])
    await db.commit()
    po = PurchaseOrder(id=str(uuid.uuid4()), po_no="PO-GRN-001", supplier_id=sup.id,
                       status="approved", total_amount=1000)
    db.add(po)
    await db.commit()
    poi = PurchaseOrderItem(id=str(uuid.uuid4()), po_id=po.id, line_no=1,
                            part_id=part.id, ordered_qty=100, received_qty=0,
                            unit_price=10, line_total=1000)
    db.add(poi)
    await db.commit()

    grn = await create_grn(db, po.id, [{"item_id": poi.id, "received_qty": 100}],
                           {"employee_id": "e-grn"})
    assert grn.grn_no.startswith("GRN-")

    po_after = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po.id)
    )).scalar_one()
    assert po_after.status == "received"
    inv = (await db.execute(
        select(Inventory).where(Inventory.part_id == part.id)
    )).scalar_one_or_none()
    assert inv is not None and inv.qty_on_hand == 100


@pytest.mark.asyncio
async def test_material_issue_deducts_inventory(db):
    """領料單：扣原料庫存 + 成本快照 + 工單引用。"""
    from app.models.inventory import Part, Inventory
    from app.models.product import Product
    from app.models.production import ProductionOrder
    from app.services.m3_documents import issue_material
    from sqlalchemy import select

    part = Part(id=str(uuid.uuid4()), part_no="MI-PART-1", name="領料料件",
                category="raw", unit_cost=20)
    prod = Product(id=str(uuid.uuid4()), product_no="MI-FG", name="成品")
    db.add_all([part, prod])
    db.add(Inventory(id=str(uuid.uuid4()), part_id=part.id,
                     qty_on_hand=500, qty_available=500))
    await db.commit()
    wo = ProductionOrder(id=str(uuid.uuid4()), wo_no="WO-MI-001", product_id=prod.id,
                         ordered_qty=10, status="released")
    db.add(wo)
    await db.commit()

    issue = await issue_material(db, wo.id, [{"part_id": part.id, "qty": 100}],
                                 {"employee_id": "e-mi"})
    assert issue.issue_no.startswith("MI-")
    from app.models.documents_m3 import MaterialIssueItem
    from sqlalchemy import select as _sel
    issue_item = (await db.execute(
        _sel(MaterialIssueItem).where(MaterialIssueItem.issue_id == issue.id)
    )).scalar_one()
    assert issue_item.unit_cost == 20

    inv = (await db.execute(
        select(Inventory).where(Inventory.part_id == part.id)
    )).scalar_one()
    assert inv.qty_on_hand == 400


@pytest.mark.asyncio
async def test_return_note_flow(db):
    """退貨單：建立 → 核准 → 入庫（庫存增加）。"""
    from app.models.inventory import Part, Inventory
    from app.models.crm_sales import Customer
    from app.services.m3_documents import (
        approve_return_note, create_return_note, process_return_note,
    )
    from sqlalchemy import select

    part = Part(id=str(uuid.uuid4()), part_no="RT-PART-1", name="退貨料件",
                category="finished", unit_cost=30)
    cust = Customer(id=str(uuid.uuid4()), code="CUST-RT", name="退貨客戶")
    db.add_all([part, cust])
    db.add(Inventory(id=str(uuid.uuid4()), part_id=part.id,
                     qty_on_hand=100, qty_available=100))
    await db.commit()

    note = await create_return_note(db, {
        "customer_id": cust.id,
        "items": [{"part_id": part.id, "qty": 10, "unit_price": 50}],
        "reason": "品質問題",
    }, {"employee_id": "e-rt"})
    assert note.return_no.startswith("RT-")
    assert note.status == "draft"

    await approve_return_note(db, note.id)
    await process_return_note(db, note.id, {"employee_id": "e-rt"})

    inv = (await db.execute(
        select(Inventory).where(Inventory.part_id == part.id)
    )).scalar_one()
    assert inv.qty_on_hand == 110
    from app.models.documents_m3 import ReturnNote
    note_after = (await db.execute(
        select(ReturnNote).where(ReturnNote.id == note.id)
    )).scalar_one()
    assert note_after.status == "processed"


def test_m3_apis_and_tools_registered(seeded_client):
    """M3 endpoints + tools + migration（grep smoke）。"""
    from pathlib import Path
    for rel, needles in [
        ("app/api/purchase.py", ["/requisitions", "/grns"]),
        ("app/api/production.py", ["/material-issues"]),
        ("app/api/sales.py", ["/returns"]),
    ]:
        src = (Path(__file__).resolve().parents[2] / rel).read_text(encoding="utf-8")
        for n in needles:
            assert n in src, f"{rel} 缺 {n}"

    tools_src = (Path(__file__).resolve().parents[2] / "app" / "agents" / "domains" /
                 "m3_tools.py").read_text(encoding="utf-8")
    for tool in ("create_pr_with_confirm", "convert_pr_to_po_with_confirm",
                 "receive_grn_with_confirm", "issue_material_with_confirm",
                 "create_return_note_with_confirm"):
        assert f'name="{tool}"' in tools_src

    mig = (Path(__file__).resolve().parents[2] / "alembic" / "versions" /
           "v013_m3_documents.py").read_text(encoding="utf-8")
    for table in ("purchase_requisitions", "goods_receipt_notes",
                  "material_issues", "return_notes"):
        assert table in mig

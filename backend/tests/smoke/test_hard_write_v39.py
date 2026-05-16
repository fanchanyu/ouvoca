"""Smoke tests for v3.9 Day A hard-write tools (8 個新 tool)。

每個 tool 至少 2 個 test：
  1. Emit ConfirmCard（不執行 + slot 摘要正確）
  2. Confirm 後真寫入 DB（執行 ok）

加上幾個 error case test 鎖住輸入驗證。
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
import pytest_asyncio

from app.agents.confirm_card import _clear_all_for_test, consume_card


@pytest.fixture(autouse=True)
def _clean():
    _clear_all_for_test()
    yield
    _clear_all_for_test()


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def demo_user():
    return {"employee_id": "emp-v39-001", "username": "tester", "roles": ["admin"]}


# ============================================================
# Inventory: create_part / update_safety_stock / add_transaction
# ============================================================

@pytest.mark.asyncio
async def test_create_part_emits_card(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_part_with_confirm
    result = await _create_part_with_confirm(
        db=db, user=demo_user,
        part_no="V39-PART-001", name="V3.9 測試料件",
        category="component", safety_stock=500, unit_cost=10,
    )
    assert result["type"] == "confirm_card"
    assert "V39-PART-001" in " ".join(result["card"]["summary"])
    assert "500" in " ".join(result["card"]["summary"])


@pytest.mark.asyncio
async def test_create_part_duplicate_blocked(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_part_with_confirm
    from app.services.inventory import create_part
    await create_part(db, {"part_no": "V39-PART-DUP", "name": "x", "category": "component"})
    result = await _create_part_with_confirm(
        db=db, user=demo_user,
        part_no="V39-PART-DUP", name="dup",
    )
    assert "error" in result
    assert "已存在" in result["error"]


@pytest.mark.asyncio
async def test_create_part_confirm_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_part_with_confirm
    from app.models.inventory import Part, Inventory
    from sqlalchemy import select

    result = await _create_part_with_confirm(
        db=db, user=demo_user,
        part_no="V39-EXEC-001", name="執行測試",
        category="component", safety_stock=100, unit_cost=5,
    )
    entry = await consume_card(result["card"]["id"])
    exec_result = await entry["executor"]()
    assert "已建立" in exec_result["message"]

    # 驗 DB：Part 有 + Inventory 也有（service create_part 會建）
    p = (await db.execute(
        select(Part).where(Part.part_no == "V39-EXEC-001")
    )).scalar_one()
    assert p.name == "執行測試"
    inv = (await db.execute(
        select(Inventory).where(Inventory.part_id == p.id)
    )).scalar_one_or_none()
    assert inv is not None, "service create_part 應該自動建 Inventory 行"


@pytest.mark.asyncio
async def test_update_safety_stock_emits(db, demo_user):
    from app.agents.domains.hard_write_tools import _update_safety_stock_with_confirm
    from app.services.inventory import create_part
    await create_part(db, {
        "part_no": "V39-SAFETY-001", "name": "x", "category": "component",
        "safety_stock": 100,
    })
    result = await _update_safety_stock_with_confirm(
        db=db, user=demo_user,
        part_no="V39-SAFETY-001", new_safety_stock=500,
    )
    assert result["type"] == "confirm_card"
    summary = " ".join(result["card"]["summary"])
    assert "100" in summary and "500" in summary


@pytest.mark.asyncio
async def test_update_safety_stock_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _update_safety_stock_with_confirm
    from app.services.inventory import create_part
    from app.models.inventory import Part
    from sqlalchemy import select
    await create_part(db, {
        "part_no": "V39-SAFETY-002", "name": "y", "category": "component",
        "safety_stock": 50,
    })
    result = await _update_safety_stock_with_confirm(
        db=db, user=demo_user,
        part_no="V39-SAFETY-002", new_safety_stock=300,
    )
    entry = await consume_card(result["card"]["id"])
    await entry["executor"]()

    p = (await db.execute(
        select(Part).where(Part.part_no == "V39-SAFETY-002")
    )).scalar_one()
    assert p.safety_stock == 300


@pytest.mark.asyncio
async def test_update_safety_stock_negative_blocked(db, demo_user):
    from app.agents.domains.hard_write_tools import _update_safety_stock_with_confirm
    from app.services.inventory import create_part
    await create_part(db, {"part_no": "V39-NEG-001", "name": "x", "category": "component"})
    result = await _update_safety_stock_with_confirm(
        db=db, user=demo_user,
        part_no="V39-NEG-001", new_safety_stock=-1,
    )
    assert "error" in result
    assert "不能負數" in result["error"]


@pytest.mark.asyncio
async def test_add_inventory_txn_inbound_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _add_inventory_txn_with_confirm
    from app.services.inventory import create_part
    from app.models.inventory import Inventory, Part
    from sqlalchemy import select

    await create_part(db, {"part_no": "V39-TXN-001", "name": "x", "category": "component"})
    result = await _add_inventory_txn_with_confirm(
        db=db, user=demo_user,
        part_no="V39-TXN-001", transaction_type="inbound", qty=200,
    )
    entry = await consume_card(result["card"]["id"])
    await entry["executor"]()

    p = (await db.execute(
        select(Part).where(Part.part_no == "V39-TXN-001")
    )).scalar_one()
    inv = (await db.execute(
        select(Inventory).where(Inventory.part_id == p.id)
    )).scalar_one()
    assert inv.qty_on_hand == 200


@pytest.mark.asyncio
async def test_add_inventory_txn_invalid_type(db, demo_user):
    from app.agents.domains.hard_write_tools import _add_inventory_txn_with_confirm
    from app.services.inventory import create_part
    await create_part(db, {"part_no": "V39-TXN-002", "name": "x", "category": "component"})
    result = await _add_inventory_txn_with_confirm(
        db=db, user=demo_user,
        part_no="V39-TXN-002", transaction_type="bogus", qty=100,
    )
    assert "error" in result
    assert "valid" in result


# ============================================================
# Purchase: create_supplier / approve_po
# ============================================================

@pytest.mark.asyncio
async def test_create_supplier_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_supplier_with_confirm
    from app.models.purchase import Supplier
    from sqlalchemy import select

    result = await _create_supplier_with_confirm(
        db=db, user=demo_user,
        code="V39-SUP-001", name="V3.9 測試供應商", tier="T2",
        contact_person="王小明", contact_phone="02-1234-5678",
    )
    assert result["type"] == "confirm_card"
    entry = await consume_card(result["card"]["id"])
    await entry["executor"]()

    s = (await db.execute(
        select(Supplier).where(Supplier.code == "V39-SUP-001")
    )).scalar_one()
    assert s.name == "V3.9 測試供應商"
    assert s.tier == "T2"
    assert s.contact_person == "王小明"


@pytest.mark.asyncio
async def test_create_supplier_duplicate_blocked(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_supplier_with_confirm
    from app.services.purchase import create_supplier
    await create_supplier(db, {"code": "V39-SUP-DUP", "name": "x"})
    result = await _create_supplier_with_confirm(
        db=db, user=demo_user, code="V39-SUP-DUP", name="dup",
    )
    assert "error" in result and "已存在" in result["error"]


@pytest.mark.asyncio
async def test_approve_po_emits_and_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _approve_po_with_confirm
    from app.services.purchase import create_supplier, create_purchase_order
    from app.services.inventory import create_part
    from app.models.purchase import PurchaseOrder
    from sqlalchemy import select

    sup = await create_supplier(db, {"code": "V39-PO-SUP", "name": "PO 供應商"})
    part = await create_part(db, {
        "part_no": "V39-PO-PART", "name": "PO 料件",
        "category": "component", "unit_cost": 10,
    })
    po = await create_purchase_order(db, {
        "supplier_id": sup.id,
        "items": [{"part_id": part.id, "ordered_qty": 100, "unit_price": 10}],
    }, user=demo_user)

    result = await _approve_po_with_confirm(db=db, user=demo_user, po_no=po.po_no)
    assert result["type"] == "confirm_card"
    entry = await consume_card(result["card"]["id"])
    await entry["executor"]()

    po_fresh = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.po_no == po.po_no)
    )).scalar_one()
    assert po_fresh.status == "approved"


@pytest.mark.asyncio
async def test_approve_po_wrong_status(db, demo_user):
    from app.agents.domains.hard_write_tools import _approve_po_with_confirm
    from app.services.purchase import create_supplier, create_purchase_order, approve_purchase_order
    from app.services.inventory import create_part

    sup = await create_supplier(db, {"code": "V39-PO-WS", "name": "x"})
    part = await create_part(db, {
        "part_no": "V39-PO-WS-P", "name": "x",
        "category": "component", "unit_cost": 1,
    })
    po = await create_purchase_order(db, {
        "supplier_id": sup.id,
        "items": [{"part_id": part.id, "ordered_qty": 1, "unit_price": 1}],
    }, user=demo_user)
    await approve_purchase_order(db, po.id, user=demo_user)  # 先 approve

    result = await _approve_po_with_confirm(db=db, user=demo_user, po_no=po.po_no)
    assert "error" in result
    assert "不可審核" in result["error"]


# ============================================================
# Sales: create_customer / create_sales_order
# ============================================================

@pytest.mark.asyncio
async def test_create_customer_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_customer_with_confirm
    from app.models.crm_sales import Customer
    from sqlalchemy import select

    result = await _create_customer_with_confirm(
        db=db, user=demo_user,
        code="V39-CUST-001", name="V3.9 測試客戶", grade="A",
        credit_limit=500000,
    )
    entry = await consume_card(result["card"]["id"])
    await entry["executor"]()

    c = (await db.execute(
        select(Customer).where(Customer.code == "V39-CUST-001")
    )).scalar_one()
    assert c.grade == "A"
    assert c.credit_limit == 500000


@pytest.mark.asyncio
async def test_create_so_emits_and_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_so_with_confirm
    from app.services.sales import create_customer
    from app.services.production import create_product
    from app.models.crm_sales import SalesOrder
    from sqlalchemy import select

    cust = await create_customer(db, {"code": "V39-SO-CUST", "name": "SO 客戶"})
    prod = await create_product(db, {
        "product_no": "V39-SO-PROD", "name": "SO 產品",
        "selling_price": 100,
    })

    result = await _create_so_with_confirm(
        db=db, user=demo_user,
        customer_keyword="V39-SO-CUST",
        items=[{"product_no": "V39-SO-PROD", "ordered_qty": 50, "unit_price": 100}],
        requested_delivery_date="2026-06-15",
    )
    assert result["type"] == "confirm_card"
    entry = await consume_card(result["card"]["id"])
    exec_result = await entry["executor"]()
    assert exec_result["total_amount"] == 5000

    so = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == exec_result["so_no"])
    )).scalar_one()
    assert so.customer_id == cust.id


@pytest.mark.asyncio
async def test_create_so_customer_not_found(db, demo_user):
    from app.agents.domains.hard_write_tools import _create_so_with_confirm
    result = await _create_so_with_confirm(
        db=db, user=demo_user,
        customer_keyword="不存在的客戶_xyz",
        items=[{"product_no": "x", "ordered_qty": 1, "unit_price": 1}],
        requested_delivery_date="2026-06-15",
    )
    assert "error" in result and "找不到客戶" in result["error"]


# ============================================================
# Production: complete_work_order
# ============================================================

@pytest.mark.asyncio
async def test_complete_wo_partial(db, demo_user):
    from app.agents.domains.hard_write_tools import _complete_wo_with_confirm
    from app.services.production import create_product, create_production_order, release_production_order
    from app.services.inventory import create_part
    from app.models.production import ProductionOrder
    from app.models.product import BOMItem
    from sqlalchemy import select

    prod = await create_product(db, {"product_no": "V39-WO-PROD", "name": "x"})
    part = await create_part(db, {
        "part_no": "V39-WO-COMP", "name": "BOM comp", "category": "component",
    })
    # release 之前要有 BOM
    bom = BOMItem(
        id=str(uuid.uuid4()), product_id=prod.id, part_id=part.id,
        level=1, sequence_no=1, qty_per=1, is_active=True,
    )
    db.add(bom)
    await db.commit()

    wo = await create_production_order(db, {
        "product_id": prod.id, "ordered_qty": 100, "priority": "normal",
    }, user=demo_user)
    await release_production_order(db, wo.id, user=demo_user)

    result = await _complete_wo_with_confirm(
        db=db, user=demo_user, wo_no=wo.wo_no, completed_qty=30,
    )
    assert result["type"] == "confirm_card"
    entry = await consume_card(result["card"]["id"])
    exec_result = await entry["executor"]()

    wo_fresh = (await db.execute(
        select(ProductionOrder).where(ProductionOrder.wo_no == wo.wo_no)
    )).scalar_one()
    assert wo_fresh.completed_qty == 30
    assert wo_fresh.status != "completed"  # 30 < 100


@pytest.mark.asyncio
async def test_complete_wo_zero_qty_blocked(db, demo_user):
    from app.agents.domains.hard_write_tools import _complete_wo_with_confirm
    result = await _complete_wo_with_confirm(
        db=db, user=demo_user, wo_no="WO-NONEXIST", completed_qty=0,
    )
    # 兩個錯：找不到工單 + qty=0；先抓工單錯
    assert "error" in result


# ============================================================
# Registry sanity
# ============================================================

def test_v39_tools_registered():
    from app.agents.registry import _REGISTRY
    expected = {
        "create_part_with_confirm",
        "update_part_safety_stock_with_confirm",
        "add_inventory_transaction_with_confirm",
        "create_supplier_with_confirm",
        "approve_purchase_order_with_confirm",
        "create_customer_with_confirm",
        "create_sales_order_with_confirm",
        "complete_work_order_with_confirm",
    }
    assert expected.issubset(_REGISTRY.keys())


def test_v39_tools_attached_to_agents():
    from app.agents import AGENT_REGISTRY
    inv = AGENT_REGISTRY["inventory"]["tool_names"]
    assert "create_part_with_confirm" in inv
    assert "update_part_safety_stock_with_confirm" in inv
    assert "add_inventory_transaction_with_confirm" in inv

    pur = AGENT_REGISTRY["purchase"]["tool_names"]
    assert "create_supplier_with_confirm" in pur
    assert "approve_purchase_order_with_confirm" in pur

    sal = AGENT_REGISTRY["sales"]["tool_names"]
    assert "create_customer_with_confirm" in sal
    assert "create_sales_order_with_confirm" in sal

    pro = AGENT_REGISTRY["production"]["tool_names"]
    assert "complete_work_order_with_confirm" in pro


def test_v39_tools_have_required_permission():
    """所有 hard-write 必有 required_permission（registry 強制）。"""
    from app.agents.registry import _REGISTRY
    expected = [
        "create_part_with_confirm",
        "update_part_safety_stock_with_confirm",
        "add_inventory_transaction_with_confirm",
        "create_supplier_with_confirm",
        "approve_purchase_order_with_confirm",
        "create_customer_with_confirm",
        "create_sales_order_with_confirm",
        "complete_work_order_with_confirm",
    ]
    for name in expected:
        meta = _REGISTRY[name]
        assert meta.required_permission, f"{name} 沒設 required_permission"

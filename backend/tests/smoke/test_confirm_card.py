"""Smoke tests for ConfirmCard E2E flow（v3.1 對話式寫入解鎖）。

證明：
  1. ConfirmCard 暫存 / consume / cancel / GC 機制
  2. 3 個 hard-write tool 出卡（不直接執行）
  3. 確認後 executor 才呼叫 service 真寫入
  4. Permission：only creator can confirm
  5. TTL：過期後 consume 回 None
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, UTC

import pytest
import pytest_asyncio

from app.agents.confirm_card import (
    ConfirmCard, _PENDING, _clear_all_for_test, _gc_expired,
    cancel_card, consume_card, list_pending_cards,
    make_card, peek_card, stash_card,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def _clean():
    _clear_all_for_test()
    yield
    _clear_all_for_test()


@pytest_asyncio.fixture
async def db(client):
    """每個測試一個新的 AsyncSession（client fixture 已觸發 init_db 建 schema）。"""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def demo_user():
    """測試用 user dict。"""
    return {"employee_id": "emp-test-001", "username": "tester", "roles": ["admin"]}


# ============================================================
# Storage primitive tests
# ============================================================

@pytest.mark.asyncio
async def test_make_and_stash():
    """造卡 + stash + peek 都拿得到。"""
    executed = []

    async def executor():
        executed.append("ran")
        return {"ok": True}

    card = make_card(
        tool_name="test_tool",
        title="測試卡",
        summary=["item 1", "item 2"],
        slots={"x": 1},
        created_by="emp-001",
    )
    await stash_card(card, executor)

    peeked = await peek_card(card.id)
    assert peeked is not None
    assert peeked.tool_name == "test_tool"
    assert peeked.title == "測試卡"
    assert peeked.slots == {"x": 1}
    assert executed == []  # peek 不執行


@pytest.mark.asyncio
async def test_consume_executes():
    """consume 取出 entry，呼叫 executor 後寫入 results。"""
    async def executor():
        return {"result": "PO-001"}

    card = make_card(
        tool_name="test_tool", title="測試", summary=[], slots={},
        created_by="emp-001",
    )
    await stash_card(card, executor)

    entry = await consume_card(card.id)
    assert entry is not None
    assert entry["card"].id == card.id
    result = await entry["executor"]()
    assert result == {"result": "PO-001"}

    # 第二次 consume 失敗（已被取走）
    again = await consume_card(card.id)
    assert again is None


@pytest.mark.asyncio
async def test_cancel():
    card = make_card(tool_name="t", title="x", summary=[], slots={})
    await stash_card(card, lambda: None)
    assert await cancel_card(card.id) is True
    assert await cancel_card(card.id) is False  # already gone
    assert await peek_card(card.id) is None


@pytest.mark.asyncio
async def test_ttl_expiry_then_consume_none():
    """過 TTL 後 consume 拿不到（GC 機制）。"""
    card = make_card(
        tool_name="t", title="x", summary=[], slots={},
        ttl_seconds=1,
    )
    await stash_card(card, lambda: None)

    # 手動把 expires_at 改成過去
    card.expires_at = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    _PENDING[card.id]["card"] = card

    entry = await consume_card(card.id)
    assert entry is None


@pytest.mark.asyncio
async def test_gc_removes_expired():
    """_gc_expired 掃描並移除過期。"""
    c1 = make_card(tool_name="t1", title="alive", summary=[], slots={})
    c2 = make_card(tool_name="t2", title="dead", summary=[], slots={})
    await stash_card(c1, lambda: None)
    await stash_card(c2, lambda: None)

    # 把 c2 改成過期
    c2.expires_at = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    _PENDING[c2.id]["card"] = c2

    removed = await _gc_expired()
    assert removed == 1
    assert await peek_card(c1.id) is not None
    assert await peek_card(c2.id) is None


@pytest.mark.asyncio
async def test_list_pending_filter_by_employee():
    a = make_card(tool_name="t", title="for-A", summary=[], slots={}, created_by="emp-A")
    b = make_card(tool_name="t", title="for-B", summary=[], slots={}, created_by="emp-B")
    await stash_card(a, lambda: None)
    await stash_card(b, lambda: None)

    for_a = await list_pending_cards(employee_id="emp-A")
    assert len(for_a) == 1
    assert for_a[0].title == "for-A"


# ============================================================
# Hard-write tool tests — 透過 db fixture
# ============================================================

@pytest.mark.asyncio
async def test_create_po_with_confirm_emits_card(db, demo_user):
    """create_purchase_order_with_confirm 出 ConfirmCard，不執行 create。"""
    from app.agents.domains.hard_write_tools import _create_po_with_confirm
    from app.models.purchase import Supplier
    from app.models.inventory import Part

    # 準備 supplier + part
    sup = Supplier(
        id=str(uuid.uuid4()), code="SUP-001", name="長江五金",
        tier="T2", is_approved=True,
    )
    db.add(sup)
    part = Part(
        id=str(uuid.uuid4()), part_no="M6-BOLT-20", name="M6 螺絲",
        category="component", unit_cost=5.0,
    )
    db.add(part)
    await db.commit()

    # 呼叫 tool
    result = await _create_po_with_confirm(
        db=db, user=demo_user,
        supplier_keyword="長江",
        items=[{"part_id": part.id, "ordered_qty": 100, "unit_price": 5}],
        expected_delivery_date="2026-05-20",
    )
    # 應回 confirm_card payload，而非執行
    assert result["type"] == "confirm_card"
    assert "card" in result
    card_data = result["card"]
    assert card_data["tool_name"] == "create_purchase_order_with_confirm"
    assert "確認建立採購單" in card_data["title"]
    assert "長江" in " ".join(card_data["summary"])
    assert card_data["risk_tier"] == "hard-write"

    # 此時 DB 還沒有 PO（因為要點確認才執行）
    from app.models.purchase import PurchaseOrder
    pos = (await db.execute(__import__("sqlalchemy").select(PurchaseOrder))).scalars().all()
    assert len(pos) == 0, "Tool 不應該在出卡時就建 PO"

    # 確認卡有 stash 在 pending
    card = await peek_card(card_data["id"])
    assert card is not None


@pytest.mark.asyncio
async def test_create_po_supplier_not_found(db, demo_user):
    """找不到供應商時回 error，不出卡。"""
    from app.agents.domains.hard_write_tools import _create_po_with_confirm

    result = await _create_po_with_confirm(
        db=db, user=demo_user,
        supplier_keyword="不存在的廠",
        items=[{"part_id": "x", "ordered_qty": 1, "unit_price": 1}],
        expected_delivery_date="2026-05-20",
    )
    assert "error" in result
    assert "找不到供應商" in result["error"]


@pytest.mark.asyncio
async def test_create_po_confirm_executes(db, demo_user):
    """E2E：出卡 → consume → executor 跑 → 真的建 PO。"""
    from app.agents.domains.hard_write_tools import _create_po_with_confirm
    from app.models.purchase import PurchaseOrder, Supplier
    from app.models.inventory import Part

    sup = Supplier(
        id=str(uuid.uuid4()), code="SUP-002", name="大華五金",
        tier="T1", is_approved=True,
    )
    db.add(sup)
    part = Part(
        id=str(uuid.uuid4()), part_no="M8-NUT", name="M8 螺帽",
        category="component", unit_cost=3.0,
    )
    db.add(part)
    await db.commit()

    # 出卡
    result = await _create_po_with_confirm(
        db=db, user=demo_user,
        supplier_keyword="大華",
        items=[{"part_id": part.id, "ordered_qty": 200, "unit_price": 3}],
        expected_delivery_date="2026-06-01",
    )
    card_id = result["card"]["id"]

    # 確認執行
    entry = await consume_card(card_id)
    assert entry is not None
    exec_result = await entry["executor"]()
    assert "po_no" in exec_result
    assert exec_result["total_amount"] == 600.0

    # DB 內已建 PO
    from sqlalchemy import select
    po = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.po_no == exec_result["po_no"])
    )).scalar_one()
    assert po.total_amount == 600.0
    assert po.supplier_id == sup.id


@pytest.mark.asyncio
async def test_release_wo_with_confirm_emits_card(db, demo_user):
    """release_work_order_with_confirm 出卡。"""
    from app.agents.domains.hard_write_tools import _release_wo_with_confirm
    from app.models.production import ProductionOrder

    wo = ProductionOrder(
        id=str(uuid.uuid4()), wo_no="WO-TEST-001",
        product_id="prod-x", ordered_qty=100, status="draft",
        priority="normal",
    )
    db.add(wo)
    await db.commit()

    result = await _release_wo_with_confirm(
        db=db, user=demo_user, wo_no="WO-TEST-001",
    )
    assert result["type"] == "confirm_card"
    assert "確認釋放工單" in result["card"]["title"]
    assert "WO-TEST-001" in " ".join(result["card"]["summary"])


@pytest.mark.asyncio
async def test_release_wo_not_found(db, demo_user):
    from app.agents.domains.hard_write_tools import _release_wo_with_confirm
    result = await _release_wo_with_confirm(db=db, user=demo_user, wo_no="WO-XYZ-999")
    assert "error" in result
    assert "找不到工單" in result["error"]


@pytest.mark.asyncio
async def test_release_wo_wrong_status(db, demo_user):
    from app.agents.domains.hard_write_tools import _release_wo_with_confirm
    from app.models.production import ProductionOrder

    wo = ProductionOrder(
        id=str(uuid.uuid4()), wo_no="WO-TEST-002",
        product_id="prod-x", ordered_qty=100, status="released",
        priority="normal",
    )
    db.add(wo)
    await db.commit()

    result = await _release_wo_with_confirm(db=db, user=demo_user, wo_no="WO-TEST-002")
    assert "error" in result
    assert "只有 draft 狀態可釋放" in result["error"]


@pytest.mark.asyncio
async def test_update_so_delivery_with_confirm_emits_card(db, demo_user):
    """update_sales_order_delivery_with_confirm 出卡。"""
    from app.agents.domains.hard_write_tools import _update_so_delivery_with_confirm
    from app.models.crm_sales import SalesOrder, Customer
    from datetime import date

    cust = Customer(
        id=str(uuid.uuid4()), code="CUST-A001", name="A 客戶",
        grade="A",
    )
    db.add(cust)
    so = SalesOrder(
        id=str(uuid.uuid4()), so_no="SO-TEST-001",
        customer_id=cust.id, status="confirmed",
        requested_delivery_date=date(2026, 5, 20),
        total_amount=10000,
    )
    db.add(so)
    await db.commit()

    result = await _update_so_delivery_with_confirm(
        db=db, user=demo_user,
        so_no="SO-TEST-001", new_delivery_date="2026-05-22",
        reason="客戶要求延後",
    )
    assert result["type"] == "confirm_card"
    assert "2026-05-22" in " ".join(result["card"]["summary"])
    assert "客戶要求延後" in " ".join(result["card"]["summary"])


@pytest.mark.asyncio
async def test_update_so_delivery_confirm_executes(db, demo_user):
    from app.agents.domains.hard_write_tools import _update_so_delivery_with_confirm
    from app.models.crm_sales import SalesOrder, Customer
    from sqlalchemy import select
    from datetime import date

    cust = Customer(
        id=str(uuid.uuid4()), code="CUST-B002", name="B 客戶", grade="B",
    )
    db.add(cust)
    so = SalesOrder(
        id=str(uuid.uuid4()), so_no="SO-TEST-002",
        customer_id=cust.id, status="confirmed",
        requested_delivery_date=date(2026, 5, 20),
        total_amount=5000,
    )
    db.add(so)
    await db.commit()

    result = await _update_so_delivery_with_confirm(
        db=db, user=demo_user,
        so_no="SO-TEST-002", new_delivery_date="2026-05-25",
    )
    card_id = result["card"]["id"]

    entry = await consume_card(card_id)
    assert entry is not None
    exec_result = await entry["executor"]()
    assert exec_result["new_delivery_date"] == "2026-05-25"

    # DB 驗證
    so_fresh = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == "SO-TEST-002")
    )).scalar_one()
    assert so_fresh.requested_delivery_date == date(2026, 5, 25)


# ============================================================
# Registry sanity
# ============================================================

def test_all_3_hard_write_tools_registered():
    from app.agents import TOOL_FUNCTIONS
    expected = {
        "create_purchase_order_with_confirm",
        "release_work_order_with_confirm",
        "update_sales_order_delivery_with_confirm",
    }
    assert expected.issubset(TOOL_FUNCTIONS.keys())


def test_hard_write_tools_wired_into_domain_agents():
    """v3.2.1: hard-write tools 接到對應 domain agent（不再有獨立 HardWriteAgent）。

    這樣 intent classifier 走「下單」→ purchase → 看得到 create_po_with_confirm。
    """
    from app.agents import AGENT_REGISTRY
    # PurchaseAgent 有 create_purchase_order_with_confirm
    assert "create_purchase_order_with_confirm" in AGENT_REGISTRY["purchase"]["tool_names"]
    # ProductionAgent 有 release_work_order_with_confirm
    assert "release_work_order_with_confirm" in AGENT_REGISTRY["production"]["tool_names"]
    # SalesAgent 有 update_sales_order_delivery_with_confirm
    assert "update_sales_order_delivery_with_confirm" in AGENT_REGISTRY["sales"]["tool_names"]

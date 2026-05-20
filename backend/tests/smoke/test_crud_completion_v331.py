"""
Smoke: CRUD Completion Tools (v3.31)

電腦小白 QA：使用者強調「LLM 自然語言能修改和查詢系統是核心」。
v3.30 補了規劃 tools，但仍缺最常被問之 hard-write 操作。
本檔驗證 8 個新 tool 正確註冊 + 缺實體 graceful + ConfirmCard 流程。
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


# All 8 new CRUD completion tools
NEW_TOOLS = [
    "cancel_purchase_order_with_confirm",
    "receive_purchase_order_with_confirm",
    "cancel_sales_order_with_confirm",
    "ship_sales_order_with_confirm",
    "cancel_production_order_with_confirm",
    "complete_inspection_with_confirm",
    "post_journal_entry_with_confirm",
    "complete_pick_task_with_confirm",
]


def test_all_8_crud_completion_tools_registered():
    """v3.31 補完之 8 個 tools 全部在 registry 中。"""
    for name in NEW_TOOLS:
        assert get_tool(name) is not None, f"Tool {name!r} 未註冊"


def test_all_8_are_hard_write():
    """這些都是寫入操作，必須是 HARD_WRITE + 有 required_permission。"""
    for name in NEW_TOOLS:
        meta = get_tool(name)
        assert meta.risk_tier == RiskTier.HARD_WRITE, \
            f"{name} 應為 HARD_WRITE，實際 {meta.risk_tier}"
        assert meta.required_permission, f"{name} 缺 required_permission"


def test_attached_to_correct_domain_agents():
    """新 tools 應掛到對應 domain agent 之 tool_names。"""
    from app.agents.engine import AGENT_REGISTRY
    expected_attachments = {
        "purchase": ["cancel_purchase_order_with_confirm",
                      "receive_purchase_order_with_confirm"],
        "sales": ["cancel_sales_order_with_confirm",
                   "ship_sales_order_with_confirm"],
        "production": ["cancel_production_order_with_confirm"],
        "quality": ["complete_inspection_with_confirm"],
        "accounting": ["post_journal_entry_with_confirm"],
        "warehouse": ["complete_pick_task_with_confirm"],
    }
    for domain, tools in expected_attachments.items():
        if domain not in AGENT_REGISTRY:
            continue  # agent may not exist if domain not yet registered
        agent_tools = set(AGENT_REGISTRY[domain]["tool_names"])
        for t in tools:
            assert t in agent_tools, \
                f"Tool {t!r} 應掛到 {domain} agent，實際未掛"


# ════════════════════════════════════════════════════════════════════
# Graceful error handling — entity not found
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cancel_po_missing_entity(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.crud_completion_tools import _cancel_po_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _cancel_po_with_confirm(
            db, {"employee_id": "test"}, po_no="MISSING-PO-001",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_cancel_so_missing_entity(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.crud_completion_tools import _cancel_so_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _cancel_so_with_confirm(
            db, {"employee_id": "test"}, so_no="MISSING-SO-001",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_ship_so_missing_entity(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.crud_completion_tools import _ship_so_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _ship_so_with_confirm(
            db, {"employee_id": "test"}, so_no="MISSING-SO-002",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_post_journal_missing_entity(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.crud_completion_tools import _post_journal_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _post_journal_with_confirm(
            db, {"employee_id": "test"}, entry_no="MISSING-JE-001",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_complete_inspection_missing_entity(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.crud_completion_tools import _complete_inspection_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _complete_inspection_with_confirm(
            db, {"employee_id": "test"},
            inspection_no="MISSING-INS-001",
            accepted_qty=100, rejected_qty=0,
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_complete_pick_missing_entity(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.crud_completion_tools import _complete_pick_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _complete_pick_with_confirm(
            db, {"employee_id": "test"},
            pick_no="MISSING-PICK-001", picked_qty=50,
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# Slot definitions
# ════════════════════════════════════════════════════════════════════

def test_cancel_tools_require_entity_no_slot():
    """所有 cancel_* 都需要單號。"""
    for tool_name in [
        "cancel_purchase_order_with_confirm",
        "cancel_sales_order_with_confirm",
        "cancel_production_order_with_confirm",
    ]:
        meta = get_tool(tool_name)
        required = {s.name for s in meta.slots if s.required}
        # Each cancel tool has its own *_no required slot
        assert any(s.endswith("_no") for s in required), \
            f"{tool_name} 應有 required *_no slot"


def test_complete_inspection_requires_qty():
    """QC 完成需 accepted_qty（rejected_qty 可選預設 0）。"""
    meta = get_tool("complete_inspection_with_confirm")
    required = {s.name for s in meta.slots if s.required}
    assert "inspection_no" in required
    assert "accepted_qty" in required


def test_complete_pick_requires_picked_qty():
    """揀貨需 picked_qty。"""
    meta = get_tool("complete_pick_task_with_confirm")
    required = {s.name for s in meta.slots if s.required}
    assert "picked_qty" in required


def test_ship_so_has_only_one_required():
    """出貨只需 so_no（其他都自動算）。"""
    meta = get_tool("ship_sales_order_with_confirm")
    required = {s.name for s in meta.slots if s.required}
    assert required == {"so_no"}, \
        f"出貨應只需 so_no，實際 {required}"


# ════════════════════════════════════════════════════════════════════
# ConfirmCard flow — actual entity → ConfirmCard returned
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cancel_po_produces_confirm_card(seeded_client):
    """有實體時，cancel tool 應回 ConfirmCard 而非直接執行。"""
    from datetime import datetime, UTC
    from app.database import AsyncSessionLocal
    from app.models.purchase import PurchaseOrder
    from app.agents.domains.crud_completion_tools import _cancel_po_with_confirm

    from app.models.purchase import Supplier
    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        sup = Supplier(
            id=str(uuid.uuid4()),
            code=f"SUP-{s}", name="Test Supplier",
        )
        db.add(sup)
        await db.flush()
        po = PurchaseOrder(
            id=str(uuid.uuid4()), po_no=f"PO-CANCEL-{s}",
            supplier_id=sup.id, status="draft", total_amount=10000,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(po)
        await db.commit()

        result = await _cancel_po_with_confirm(
            db, {"employee_id": "test"},
            po_no=f"PO-CANCEL-{s}", reason="客戶撤單",
        )

    # Should be ConfirmCard payload
    assert "card_id" in result or result.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_cancel_po_blocked_when_received(seeded_client):
    """已收貨 PO 不可取消。"""
    from datetime import datetime, UTC
    from app.database import AsyncSessionLocal
    from app.models.purchase import PurchaseOrder, Supplier
    from app.agents.domains.crud_completion_tools import _cancel_po_with_confirm

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        sup = Supplier(
            id=str(uuid.uuid4()),
            code=f"SUP-RCV-{s}", name="Test Supplier",
        )
        db.add(sup)
        await db.flush()
        po = PurchaseOrder(
            id=str(uuid.uuid4()), po_no=f"PO-RCV-{s}",
            supplier_id=sup.id, status="received",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(po)
        await db.commit()

        result = await _cancel_po_with_confirm(
            db, {"employee_id": "test"},
            po_no=f"PO-RCV-{s}",
        )

    assert "error" in result
    assert "received" in result["error"]

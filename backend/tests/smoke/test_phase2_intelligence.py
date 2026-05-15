"""Smoke tests for v3.3 Phase 2 對話智能：
  - Slot-filling reverse-ask
  - Glossary（同義詞）
  - Undo 90 秒撤銷
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, UTC

import pytest
import pytest_asyncio

from app.agents.confirm_card import _clear_all_for_test, consume_card
from app.agents.engine import execute_tool, _missing_required_slots, _build_reverse_ask
from app.agents.glossary import (
    GlossaryEntry, clear_glossary, list_glossary, register_term, resolve_term,
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
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def demo_user():
    return {"employee_id": "emp-phase2-001", "username": "tester", "roles": ["admin"]}


# ============================================================
# Track A — Slot-filling 反問
# ============================================================

class TestSlotFilling:
    def test_missing_slot_detects_required(self):
        """缺 required slot 時偵測得到。"""
        missing = _missing_required_slots("create_purchase_order_with_confirm", {})
        assert len(missing) >= 2  # supplier_keyword + items + expected_delivery_date
        names = {s.name for s in missing}
        assert "supplier_keyword" in names
        assert "items" in names
        assert "expected_delivery_date" in names

    def test_missing_slot_ignores_optional(self):
        """optional slot 不在 missing 內。"""
        # 提供所有 required（含非空 items），缺 optional remark
        missing = _missing_required_slots(
            "create_purchase_order_with_confirm",
            {
                "supplier_keyword": "x",
                "items": [{"part_no": "Y", "ordered_qty": 1}],
                "expected_delivery_date": "2026-05-20",
            },
        )
        # 全部 required 都有 → missing 應該空
        assert missing == []

    def test_missing_slot_unknown_tool_safe(self):
        """未知 tool 不會炸，回空 list（向後相容）。"""
        assert _missing_required_slots("nonexistent_tool", {}) == []

    def test_missing_slot_empty_string_counts(self):
        """傳空字串應算缺。"""
        missing = _missing_required_slots(
            "create_purchase_order_with_confirm",
            {"supplier_keyword": "", "items": [], "expected_delivery_date": ""},
        )
        # supplier_keyword="" 和 expected_delivery_date="" 都算缺
        # items=[] 算缺（空 list）
        names = {s.name for s in missing}
        assert "supplier_keyword" in names
        assert "expected_delivery_date" in names

    def test_build_reverse_ask_single_field(self):
        from app.agents.registry import Slot
        s = Slot("supplier_keyword", "string", True, "供應商名稱或編號")
        ask = _build_reverse_ask("create_po", [s])
        assert "供應商名稱或編號" in ask
        assert "反問" in ask

    def test_build_reverse_ask_multi_field(self):
        from app.agents.registry import Slot
        missing = [
            Slot("a", "string", True, "AAA"),
            Slot("b", "string", True, "BBB"),
        ]
        ask = _build_reverse_ask("test_tool", missing)
        assert "AAA" in ask and "BBB" in ask
        assert "一次問完" in ask

    @pytest.mark.asyncio
    async def test_execute_tool_returns_needs_input_when_missing(self, db, demo_user):
        """execute_tool 在缺 slot 時不 call 真 tool，回 needs_input JSON。"""
        result_str = await execute_tool(
            "create_purchase_order_with_confirm",
            {},  # 全部缺
            db=db, user=demo_user,
        )
        result = json.loads(result_str)
        assert result.get("needs_input") is True
        assert "missing" in result
        assert "ask" in result
        # 必有的欄位
        names = {m["name"] for m in result["missing"]}
        assert "supplier_keyword" in names
        assert "items" in names
        assert "expected_delivery_date" in names

    @pytest.mark.asyncio
    async def test_execute_tool_proceeds_when_complete(self, db, demo_user):
        """slots 齊全時正常走，不出 needs_input。"""
        from app.models.purchase import Supplier
        from app.models.inventory import Part

        sup = Supplier(
            id=str(uuid.uuid4()), code="SUP-SF1", name="測試供應商",
            tier="T2", is_approved=True,
        )
        db.add(sup)
        part = Part(
            id=str(uuid.uuid4()), part_no="SF-PART-1", name="測試料件",
            category="component", unit_cost=10,
        )
        db.add(part)
        await db.commit()

        result_str = await execute_tool(
            "create_purchase_order_with_confirm",
            {
                "supplier_keyword": "測試供應商",
                "items": [{"part_no": "SF-PART-1", "ordered_qty": 5, "unit_price": 10}],
                "expected_delivery_date": "2026-05-20",
            },
            db=db, user=demo_user,
        )
        result = json.loads(result_str)
        # 不應有 needs_input
        assert "needs_input" not in result or result.get("needs_input") is None
        # 應該是 confirm_card payload
        assert result.get("type") == "confirm_card"


# ============================================================
# Track B — Glossary
# ============================================================

class TestGlossary:
    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_glossary()
        yield
        clear_glossary()

    def test_register_and_resolve_exact(self):
        register_term(GlossaryEntry(
            term="螺絲", canonical_type="part",
            canonical_id="M6-BOLT-20", canonical_label="M6 螺絲",
        ))
        e = resolve_term("螺絲", "part")
        assert e is not None
        assert e.canonical_id == "M6-BOLT-20"
        assert e.confidence == 1.0

    def test_resolve_alias(self):
        register_term(GlossaryEntry(
            term="螺絲", canonical_type="part",
            canonical_id="M6-BOLT-20",
            aliases=["鋼釘", "六角螺絲"],
        ))
        e = resolve_term("鋼釘", "part")
        assert e is not None
        assert e.canonical_id == "M6-BOLT-20"
        # alias 信心稍降
        assert 0.8 < e.confidence < 1.0

    def test_resolve_unknown_returns_none(self):
        assert resolve_term("xxx", "part") is None

    def test_resolve_type_isolation(self):
        """同名但不同 type 不會誤匹配。"""
        register_term(GlossaryEntry(
            term="中華", canonical_type="customer",
            canonical_id="CUST-A",
        ))
        register_term(GlossaryEntry(
            term="中華", canonical_type="supplier",
            canonical_id="SUP-X",
        ))
        c = resolve_term("中華", "customer")
        s = resolve_term("中華", "supplier")
        assert c.canonical_id == "CUST-A"
        assert s.canonical_id == "SUP-X"

    def test_resolve_partial_match_lower_confidence(self):
        register_term(GlossaryEntry(
            term="長江五金", canonical_type="supplier",
            canonical_id="SUP-001", canonical_label="長江五金",
        ))
        # 「長江」是 "長江五金" 的 substring
        e = resolve_term("長江", "supplier")
        assert e is not None
        assert e.canonical_id == "SUP-001"
        # 包含比對信心打 0.7
        assert e.confidence < 1.0

    def test_list_glossary_filter(self):
        register_term(GlossaryEntry(term="螺絲", canonical_type="part", canonical_id="A"))
        register_term(GlossaryEntry(term="長江", canonical_type="supplier", canonical_id="B"))
        parts = list_glossary(canonical_type="part")
        suppliers = list_glossary(canonical_type="supplier")
        assert len(parts) == 1
        assert len(suppliers) == 1

    @pytest.mark.asyncio
    async def test_lookup_term_tool_found(self, db, demo_user):
        from app.agents.domains.glossary_tools import _lookup_term
        register_term(GlossaryEntry(
            term="鋼釘", canonical_type="part",
            canonical_id="M6-BOLT-20", canonical_label="M6 螺絲",
        ))
        result = await _lookup_term(
            db=db, user=demo_user, term="鋼釘", canonical_type="part",
        )
        assert result["found"] is True
        assert result["canonical_id"] == "M6-BOLT-20"

    @pytest.mark.asyncio
    async def test_lookup_term_tool_not_found(self, db, demo_user):
        from app.agents.domains.glossary_tools import _lookup_term
        result = await _lookup_term(
            db=db, user=demo_user, term="不存在的詞", canonical_type="part",
        )
        assert result["found"] is False
        assert "hint" in result

    @pytest.mark.asyncio
    async def test_register_term_tool(self, db, demo_user):
        from app.agents.domains.glossary_tools import _register_term as _reg
        result = await _reg(
            db=db, user=demo_user,
            term="特製螺絲", canonical_type="part",
            canonical_id="X-SPECIAL-1", canonical_label="特製螺絲",
        )
        assert result["registered"] is True
        # 確認真的有進 glossary
        e = resolve_term("特製螺絲", "part")
        assert e is not None


# ============================================================
# Track C — Undo 90s
# ============================================================

class TestUndo:
    @pytest.mark.asyncio
    async def test_undo_no_recent_po(self, db, demo_user):
        """沒有 90 秒內的 PO → 回 error。"""
        from app.agents.domains.undo_tools import _undo_last_po
        result = await _undo_last_po(db=db, user=demo_user)
        assert "error" in result
        assert "找不到" in result["error"]

    @pytest.mark.asyncio
    async def test_undo_no_user(self, db):
        """沒有 user → 回 error。"""
        from app.agents.domains.undo_tools import _undo_last_po
        result = await _undo_last_po(db=db, user=None)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_undo_emits_confirm_card_then_executes(self, db, demo_user):
        """建一張 PO → undo → 出 ConfirmCard → consume → PO 變 cancelled。"""
        from app.models.purchase import PurchaseOrder
        from app.agents.domains.undo_tools import _undo_last_po
        from sqlalchemy import select

        # 模擬剛建的 PO（30 秒前）
        po = PurchaseOrder(
            id=str(uuid.uuid4()),
            po_no="PO-UNDO-001",
            supplier_id="sup-x",
            status="draft",
            total_amount=1234.0,
            order_date=datetime.now(UTC).replace(tzinfo=None),
            created_by=demo_user["employee_id"],
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=30),
        )
        db.add(po)
        await db.commit()

        # 呼叫 undo
        result = await _undo_last_po(db=db, user=demo_user)
        assert result.get("type") == "confirm_card"
        card_id = result["card"]["id"]
        assert "PO-UNDO-001" in " ".join(result["card"]["summary"])

        # 點確認
        entry = await consume_card(card_id)
        assert entry is not None
        exec_result = await entry["executor"]()
        assert exec_result["new_status"] == "cancelled"

        # DB 驗證
        po_fresh = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.po_no == "PO-UNDO-001")
        )).scalar_one()
        assert po_fresh.status == "cancelled"

    @pytest.mark.asyncio
    async def test_undo_skips_old_po(self, db, demo_user):
        """超過 90 秒的 PO 不算數。"""
        from app.models.purchase import PurchaseOrder
        from app.agents.domains.undo_tools import _undo_last_po

        # 100 秒前的 PO
        po = PurchaseOrder(
            id=str(uuid.uuid4()),
            po_no="PO-OLD-001",
            supplier_id="sup-x",
            status="draft",
            total_amount=500,
            order_date=datetime.now(UTC).replace(tzinfo=None),
            created_by=demo_user["employee_id"],
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=100),
        )
        db.add(po)
        await db.commit()

        result = await _undo_last_po(db=db, user=demo_user)
        assert "error" in result
        assert "找不到" in result["error"]


# ============================================================
# Registry sanity
# ============================================================

def test_v33_tools_registered():
    """v3.3 新增的 4 個 tool 都在 registry。"""
    from app.agents import TOOL_FUNCTIONS
    expected = {
        "lookup_term",
        "list_glossary_terms",
        "register_glossary_term",
        "undo_last_purchase_order",
    }
    assert expected.issubset(TOOL_FUNCTIONS.keys())


def test_undo_attached_to_purchase_agent():
    """undo_last_purchase_order 接在 PurchaseAgent 上。"""
    from app.agents import AGENT_REGISTRY
    assert "undo_last_purchase_order" in AGENT_REGISTRY["purchase"]["tool_names"]

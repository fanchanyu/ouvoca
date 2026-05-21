"""Smoke: v3.34 業務面補完（Tax + Accounting + Approval + Warehouse + Quality + Alembic baseline）

電腦小白每天最痛 17 個 LLM tools + 1 個 Alembic baseline migration。
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


V334_TOOLS = [
    # Tax (5)
    "issue_einvoice_with_confirm", "void_einvoice_with_confirm",
    "validate_tax_id_tool", "query_monthly_sales_tax", "query_einvoice_by_so",
    # Accounting (4)
    "record_payment_to_supplier_with_confirm",
    "record_receipt_from_customer_with_confirm",
    "query_outstanding_ar", "query_outstanding_ap",
    # Approval (3)
    "query_my_pending_approvals",
    "approve_request_with_confirm", "reject_request_with_confirm",
    # Warehouse (2)
    "create_pick_task_with_confirm", "query_pending_pick_tasks",
    # Quality (3)
    "create_ncr_with_confirm", "create_capa_with_confirm", "query_open_ncrs",
]


def test_all_17_v334_tools_registered():
    for n in V334_TOOLS:
        assert get_tool(n) is not None, f"Tool {n!r} 未註冊"


def test_v334_hard_writes_have_permission():
    for n in V334_TOOLS:
        if "with_confirm" in n:
            meta = get_tool(n)
            assert meta.risk_tier == RiskTier.HARD_WRITE
            assert meta.required_permission, f"{n} 缺 permission"


def test_v334_creates_tax_and_approval_agents():
    """v3.34 應註冊 tax + approval 兩個新 agent。"""
    from app.agents.engine import AGENT_REGISTRY
    assert "tax" in AGENT_REGISTRY, "tax agent 未註冊"
    assert "approval" in AGENT_REGISTRY, "approval agent 未註冊"
    # 確認 agent 有 tools
    assert len(AGENT_REGISTRY["tax"]["tool_names"]) >= 5
    assert len(AGENT_REGISTRY["approval"]["tool_names"]) >= 3


# ════════════════════════════════════════════════════════════════════
# Tax tools — validate_tax_id 純算法
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_validate_tax_id_taiwan_returns_bool(seeded_client):
    """Tax ID 算法應該對 8 位數字回傳 True/False（非 None）。
    具體 checksum 邏輯由 §3 演算法處理，這裡只驗 API 行為。"""
    from app.agents.domains.business_completion_tools import _validate_tax_id_tool
    # 任何 8 位數都會經過 checksum；結果可能 valid 或 invalid 但必定是 bool
    result = await _validate_tax_id_tool(None, None, tax_id="12345678", country="TW")
    assert isinstance(result["raw"]["valid"], bool)
    assert result["raw"]["tax_id"] == "12345678"


@pytest.mark.asyncio
async def test_validate_tax_id_invalid_format(seeded_client):
    from app.agents.domains.business_completion_tools import _validate_tax_id_tool
    result = await _validate_tax_id_tool(None, None, tax_id="ABC123", country="TW")
    assert result["raw"]["valid"] is False


@pytest.mark.asyncio
async def test_issue_einvoice_missing_so(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _issue_einvoice_tool
    async with AsyncSessionLocal() as db:
        result = await _issue_einvoice_tool(
            db, {"employee_id": "test"}, so_no="MISSING-SO-X",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# Accounting tools
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_record_payment_missing_supplier(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _record_payment_to_supplier
    async with AsyncSessionLocal() as db:
        result = await _record_payment_to_supplier(
            db, {"employee_id": "test"},
            supplier_keyword="NOSUCH-XYZ", amount=10000,
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_record_payment_produces_confirm_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.purchase import Supplier
    from app.agents.domains.business_completion_tools import _record_payment_to_supplier

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        sup = Supplier(id=str(uuid.uuid4()), code=f"SUP-PAY-{s}", name=f"Pay test {s}")
        db.add(sup)
        await db.commit()

        result = await _record_payment_to_supplier(
            db, {"employee_id": "test"},
            supplier_keyword=f"SUP-PAY-{s}", amount=50000,
            payment_method="wire",
        )
    assert "card_id" in result or result.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_query_outstanding_ar_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _query_outstanding_ar
    async with AsyncSessionLocal() as db:
        result = await _query_outstanding_ar(db, {"employee_id": "test"})
    assert "summary" in result


@pytest.mark.asyncio
async def test_query_outstanding_ap_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _query_outstanding_ap
    async with AsyncSessionLocal() as db:
        result = await _query_outstanding_ap(db, {"employee_id": "test"})
    assert "summary" in result


# ════════════════════════════════════════════════════════════════════
# Approval tools
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_my_pending_approvals_no_employee_id(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _query_my_pending_approvals
    async with AsyncSessionLocal() as db:
        result = await _query_my_pending_approvals(db, None)
    assert "error" in result


@pytest.mark.asyncio
async def test_reject_request_requires_comment(seeded_client):
    """拒絕必須填原因 — 空字串不行。"""
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _reject_request
    async with AsyncSessionLocal() as db:
        result = await _reject_request(
            db, {"employee_id": "x"}, request_id="ANY", comment="",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# Warehouse tools
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_pick_task_missing_so(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _create_pick_task
    async with AsyncSessionLocal() as db:
        result = await _create_pick_task(
            db, {"employee_id": "test"}, so_no="MISSING-SO-X",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_query_pending_pick_tasks_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _query_pending_pick_tasks
    async with AsyncSessionLocal() as db:
        result = await _query_pending_pick_tasks(db, {"employee_id": "test"})
    assert "summary" in result


# ════════════════════════════════════════════════════════════════════
# Quality tools
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_ncr_produces_confirm_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _create_ncr_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _create_ncr_with_confirm(
            db, {"employee_id": "test"},
            severity="high",
            description="客戶反映電鍍品質有色差",
            affected_qty=50,
        )
    assert "card_id" in result or result.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_query_open_ncrs_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.business_completion_tools import _query_open_ncrs
    async with AsyncSessionLocal() as db:
        result = await _query_open_ncrs(db, {"employee_id": "test"})
    assert "summary" in result


# ════════════════════════════════════════════════════════════════════
# Alembic baseline migration sanity check
# ════════════════════════════════════════════════════════════════════

def test_alembic_baseline_migration_exists():
    """v001 baseline migration 必須存在（客戶上 PostgreSQL prod 必需）。"""
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    base = os.path.abspath(os.path.join(base, ".."))
    mig = os.path.join(base, "backend", "alembic", "versions", "v001_initial_baseline.py")
    assert os.path.exists(mig), f"Alembic baseline 缺：{mig}"
    with open(mig, encoding="utf-8") as f:
        content = f.read()
    assert "001_initial_baseline" in content
    assert "Base.metadata.create_all" in content
    assert "down_revision: Union[str, None] = None" in content

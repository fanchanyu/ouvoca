"""
Smoke: Conversational Planning LLM Tools (v3.30)

Validates that v3.25.9 - v3.29 algorithms are now accessible via LLM tools.
Without these wrappers, all prior IE/OR sprints are invisible to SMB owners.

Reviewer-grade invariants:
  1. All 10 tools register correctly
  2. Tool metadata (slots, risk_tier, permission) follows architecture
  3. Tools handle missing entities gracefully (no 500)
  4. Hard-write tool produces ConfirmCard (not direct exec)
  5. Read tools return summary + raw + warning structure
  6. PlanningAgent agent exists and lists all 10 tools
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


# ════════════════════════════════════════════════════════════════════
# 1. Tool registration sanity
# ════════════════════════════════════════════════════════════════════

EXPECTED_TOOLS = [
    "forecast_demand_for_part",
    "commit_forecast_to_mps_with_confirm",
    "explain_planned_order_tool",
    "identify_bottlenecks_tool",
    "counterfactual_capacity_tool",
    "evaluate_order_acceptance_tool",
    "explore_pricing_curve_tool",
    "compute_dbr_schedule_tool",
    "where_used_tool",
    "daily_briefing_tool",
]


def test_all_10_tools_registered():
    """All 10 conversational planning tools must be in the registry."""
    for name in EXPECTED_TOOLS:
        assert get_tool(name) is not None, f"Tool {name!r} not registered"


def test_hard_write_tool_has_required_permission():
    """commit_forecast_to_mps_with_confirm is HARD_WRITE → must have permission."""
    meta = get_tool("commit_forecast_to_mps_with_confirm")
    assert meta.risk_tier == RiskTier.HARD_WRITE
    assert meta.required_permission == "mps_mrp.master.create"


def test_read_tools_are_read_tier():
    """Read tools tagged correctly."""
    read_tools = [
        "forecast_demand_for_part",
        "explain_planned_order_tool",
        "identify_bottlenecks_tool",
        "counterfactual_capacity_tool",
        "evaluate_order_acceptance_tool",
        "explore_pricing_curve_tool",
        "compute_dbr_schedule_tool",
        "where_used_tool",
        "daily_briefing_tool",
    ]
    for name in read_tools:
        meta = get_tool(name)
        assert meta.risk_tier == RiskTier.READ, \
            f"{name} should be READ, got {meta.risk_tier}"


def test_planning_agent_exists_and_lists_tools():
    """PlanningAgent should be registered with all 10 tools."""
    from app.agents.engine import AGENT_REGISTRY
    assert "planning" in AGENT_REGISTRY, "planning agent not registered"
    agent = AGENT_REGISTRY["planning"]
    tool_names = set(agent["tool_names"])
    for t in EXPECTED_TOOLS:
        assert t in tool_names, f"PlanningAgent missing tool {t}"


# ════════════════════════════════════════════════════════════════════
# 2. Tool execution — graceful error handling
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_forecast_demand_tool_missing_part(seeded_client):
    """Tool should return error dict (not raise) when part not found."""
    from app.database import AsyncSessionLocal
    from app.agents.domains.planning_llm_tools import _forecast_demand_tool

    async with AsyncSessionLocal() as db:
        result = await _forecast_demand_tool(
            db, {"employee_id": "test"},
            part_no="NONEXISTENT-XYZ", horizon=3,
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_evaluate_order_acceptance_tool_missing_product(seeded_client):
    """Tool returns error when product not found."""
    from app.database import AsyncSessionLocal
    from app.agents.domains.planning_llm_tools import _evaluate_order_acceptance_tool

    async with AsyncSessionLocal() as db:
        result = await _evaluate_order_acceptance_tool(
            db, {"employee_id": "test"},
            product_no="NOPE-XYZ", qty=10, unit_price=100,
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_where_used_tool_missing_part(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.planning_llm_tools import _where_used_tool

    async with AsyncSessionLocal() as db:
        result = await _where_used_tool(
            db, {"employee_id": "test"}, part_no="MISSING-PART-XYZ",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# 3. Tool output structure
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_evaluate_order_acceptance_tool_full_output(seeded_client):
    """Read tool returns dict with summary + raw + warning."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.product import Product
    from app.agents.domains.planning_llm_tools import _evaluate_order_acceptance_tool

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        prod = Product(
            id=str(uuid.uuid4()), product_no=f"EVAL-{s}",
            name="Eval Product", unit="pcs",
        )
        db.add(prod)
        await db.commit()

        result = await _evaluate_order_acceptance_tool(
            db, {"employee_id": "test"},
            product_no=f"EVAL-{s}", qty=10, unit_price=200,
            bottleneck_minutes_required=50,
            bottleneck_minutes_available=1000,
        )

    assert "summary" in result
    assert "raw" in result
    assert "warning" in result
    # Summary should mention recommendation
    assert any(
        keyword in result["summary"]
        for keyword in ["ACCEPT", "REJECT", "NEGOTIATE", "EVALUATE"]
    )


@pytest.mark.asyncio
async def test_daily_briefing_tool_runs_without_data(seeded_client):
    """Daily briefing must not crash even on empty DB."""
    from app.database import AsyncSessionLocal
    from app.agents.domains.planning_llm_tools import _daily_briefing_tool

    async with AsyncSessionLocal() as db:
        result = await _daily_briefing_tool(db, {"employee_id": "test"})

    assert "summary" in result
    assert "raw" in result
    # Either has items or shows the "calm day" message
    items = result["raw"]["items"]
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_explore_pricing_curve_returns_scenarios(seeded_client):
    """Pricing curve returns list of scenarios."""
    from app.database import AsyncSessionLocal
    from app.models.product import Product
    from app.agents.domains.planning_llm_tools import _explore_pricing_curve_tool

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        prod = Product(
            id=str(uuid.uuid4()), product_no=f"PRC-{s}",
            name="Price Test", unit="pcs",
        )
        db.add(prod)
        await db.commit()

        result = await _explore_pricing_curve_tool(
            db, {"employee_id": "test"},
            product_no=f"PRC-{s}", qty=100, base_price=200,
            bottleneck_minutes_required=100,
        )

    assert "raw" in result
    assert isinstance(result["raw"], list)
    assert len(result["raw"]) >= 4  # default discount levels


# ════════════════════════════════════════════════════════════════════
# 4. Slot definitions sanity
# ════════════════════════════════════════════════════════════════════

def test_forecast_demand_tool_required_slots():
    """forecast_demand_for_part: part_no is required."""
    meta = get_tool("forecast_demand_for_part")
    required_slot_names = {s.name for s in meta.slots if s.required}
    assert "part_no" in required_slot_names


def test_evaluate_order_acceptance_required_slots():
    """3 required: product_no, qty, unit_price."""
    meta = get_tool("evaluate_order_acceptance_tool")
    required_slot_names = {s.name for s in meta.slots if s.required}
    assert "product_no" in required_slot_names
    assert "qty" in required_slot_names
    assert "unit_price" in required_slot_names


def test_daily_briefing_no_required_slots():
    """daily_briefing requires no params — just call it."""
    meta = get_tool("daily_briefing_tool")
    required = [s for s in meta.slots if s.required]
    assert required == []


# ════════════════════════════════════════════════════════════════════
# 5. Hard-write ConfirmCard flow
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_commit_forecast_to_mps_produces_confirm_card(seeded_client):
    """Hard-write tool should return ConfirmCard payload, not execute directly."""
    from app.database import AsyncSessionLocal
    from app.models.product import Product
    from app.agents.domains.planning_llm_tools import _commit_forecast_to_mps

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        prod = Product(
            id=str(uuid.uuid4()), product_no=f"MPS-{s}",
            name="MPS Test", unit="pcs",
        )
        db.add(prod)
        await db.commit()

        result = await _commit_forecast_to_mps(
            db, {"employee_id": "test"},
            product_no=f"MPS-{s}", mps_name=f"Test MPS {s}",
            planned_production_per_period=[100, 120, 110],
            period_labels=["W22", "W23", "W24"],
        )

    # Should be ConfirmCard payload (not direct execution result)
    assert isinstance(result, dict)
    # ConfirmCard contract: contains card_id or type=confirm_card
    assert "card_id" in result or result.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_commit_forecast_to_mps_validates_input(seeded_client):
    """Empty planned_production array → error."""
    from app.database import AsyncSessionLocal
    from app.models.product import Product
    from app.agents.domains.planning_llm_tools import _commit_forecast_to_mps

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        prod = Product(
            id=str(uuid.uuid4()), product_no=f"MPS-V-{s}",
            name="Test", unit="pcs",
        )
        db.add(prod)
        await db.commit()

        result = await _commit_forecast_to_mps(
            db, {"employee_id": "test"},
            product_no=f"MPS-V-{s}",
            mps_name="Bad MPS",
            planned_production_per_period=[],
        )

    assert "error" in result

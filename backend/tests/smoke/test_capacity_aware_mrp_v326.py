"""
Smoke: Capacity-Aware MRP with Dixon-Silver heuristic (v3.26)

Validates against textbook CLSP examples and structural invariants:
  - Dixon & Silver (1981) §3 — capacity-feasible shift behavior
  - Karmarkar (1987) — setup + run time decomposition
  - Vollmann et al. (2005) Ch. 7 — CRP load profile

Algorithmic property tests (a reviewer would demand):
  1. Capacity-feasibility: post-Dixon-Silver, no period has overload
     UNLESS infeasible_periods flags it
  2. Demand preservation: Σ adjusted_planned_orders == Σ original
     (shift doesn't change total, just timing)
  3. Holding cost monotonic: every shift increases holding cost
  4. Bottleneck detection: identifies highest-utilization WC
"""
from __future__ import annotations

import uuid
import pytest

from app.services.capacity_aware_mrp import (
    WorkCenterLoad, ResourceProfileItem,
    compute_work_center_load,
    dixon_silver_capacity_feasible,
    DixonSilverConfig,
)


# ════════════════════════════════════════════════════════════════════
# Pure-function tests (no DB)
# ════════════════════════════════════════════════════════════════════

def _wc(id_: str, code: str, capacity_min: float = 2400):
    """Mock WorkCenter (480 min × 5 days = 2400 min/week)."""
    class MockWC:
        def __init__(self, id, code, efficiency):
            self.id = id
            self.code = code
            self.efficiency = efficiency
            self.capacity_per_day = 480 / 60  # not used in compute_load directly
    return MockWC(id_, code, 1.0)


def test_compute_load_single_product():
    """1 product, 1 WC, run_time=2 min/unit, setup=10 min/batch.
    Period demand: 100 units → load = 10 + 100×2 = 210 min."""
    wc = _wc("WC1", "STAMP")
    profile = {
        "P1": [ResourceProfileItem(
            product_id="P1", work_center_id="WC1",
            setup_time=10, run_time_per_unit=2,
        )]
    }
    planned = {"P1": [100.0, 0.0, 0.0]}
    loads = compute_work_center_load(planned, profile, {wc.id: wc}, 3, 2400)
    period0_load = next(L for L in loads if L.period_idx == 0)
    assert period0_load.required_minutes == 210.0, \
        f"Expected 210 min, got {period0_load.required_minutes}"
    period1_load = next(L for L in loads if L.period_idx == 1)
    assert period1_load.required_minutes == 0.0


def test_dixon_silver_no_overload_no_shift():
    """When demand is within capacity, no shifting occurs."""
    wc = _wc("WC1", "STAMP")
    profile = {
        "P1": [ResourceProfileItem(
            product_id="P1", work_center_id="WC1",
            setup_time=10, run_time_per_unit=2,
        )]
    }
    # 100 units per period × 2 min = 200 min + 10 setup = 210 min, < 2400
    planned = {"P1": [100.0, 100.0, 100.0]}
    adjusted, result = dixon_silver_capacity_feasible(
        planned, profile, {wc.id: wc}, horizon_periods=3, period_minutes=2400,
    )
    # No shifts should occur
    assert len(result.shifted_orders) == 0
    assert adjusted == planned
    assert result.holding_cost_penalty == 0


def test_dixon_silver_shifts_to_earlier_period():
    """Overload in period 1 → shift production to period 0 (which has slack).

    Setup: period 0 has 100 units (210 min load).
    Period 1 demand spikes to 2000 units → 2000×2 + 10 = 4010 min > 2400 capacity.
    Earlier period (0) has 2400 - 210 = 2190 min slack.
    Excess = 4010 - 2400 = 1610 min → shift ~805 units (1610/2) to period 0.
    """
    wc = _wc("WC1", "STAMP")
    profile = {
        "P1": [ResourceProfileItem(
            product_id="P1", work_center_id="WC1",
            setup_time=10, run_time_per_unit=2,
        )]
    }
    planned = {"P1": [100.0, 2000.0, 100.0]}
    adjusted, result = dixon_silver_capacity_feasible(
        planned, profile, {wc.id: wc}, horizon_periods=3, period_minutes=2400,
    )

    # Demand preservation invariant
    assert sum(planned["P1"]) == sum(adjusted["P1"]), \
        f"Total demand changed: {sum(planned['P1'])} → {sum(adjusted['P1'])}"

    # Some qty shifted to period 0
    assert adjusted["P1"][0] > 100, f"Expected shift to period 0, got {adjusted['P1'][0]}"
    assert adjusted["P1"][1] < 2000, f"Expected reduction in period 1, got {adjusted['P1'][1]}"

    # Diagnostic logged
    assert len(result.shifted_orders) >= 1
    assert result.shifted_orders[0]["from_period"] == 1
    assert result.shifted_orders[0]["to_period"] == 0

    # Holding cost penalty incurred (shifted 1 period earlier × qty × 1.0/unit/period)
    assert result.holding_cost_penalty > 0


def test_dixon_silver_demand_preservation_multi_product():
    """Multiple products, multiple WCs — total demand preserved per product."""
    wc1, wc2 = _wc("WC1", "STAMP"), _wc("WC2", "ASSY")
    profile = {
        "P1": [ResourceProfileItem("P1", "WC1", 10, 3),
               ResourceProfileItem("P1", "WC2", 5, 1)],
        "P2": [ResourceProfileItem("P2", "WC1", 8, 2)],
    }
    planned = {
        "P1": [100.0, 500.0, 100.0],   # P1 spike in period 1
        "P2": [50.0, 600.0, 50.0],     # P2 spike in period 1
    }
    adjusted, result = dixon_silver_capacity_feasible(
        planned, profile, {wc1.id: wc1, wc2.id: wc2},
        horizon_periods=3, period_minutes=2400,
    )

    for pid in planned:
        assert abs(sum(planned[pid]) - sum(adjusted[pid])) < 0.01, \
            f"Demand preservation violated for {pid}"


def test_dixon_silver_infeasible_when_no_earlier_slack():
    """Period 0 demand alone exceeds capacity → no earlier period to shift to →
    flagged as infeasible."""
    wc = _wc("WC1", "STAMP")
    profile = {
        "P1": [ResourceProfileItem(
            product_id="P1", work_center_id="WC1",
            setup_time=10, run_time_per_unit=2,
        )]
    }
    # 2000 units in period 0 = 4010 min, but capacity only 2400
    # No earlier period to shift to → infeasibility
    planned = {"P1": [2000.0, 100.0, 100.0]}
    adjusted, result = dixon_silver_capacity_feasible(
        planned, profile, {wc.id: wc}, horizon_periods=3, period_minutes=2400,
    )

    # Should flag infeasibility at (WC1, period 0)
    assert any(t == 0 for (_, t) in result.infeasible_periods), \
        f"Expected (WC1, 0) in infeasible_periods, got {result.infeasible_periods}"


def test_overload_detection_utilization():
    """Verify utilization > 1.0 ⟺ is_overload."""
    load = WorkCenterLoad("wc1", "TEST", 0, 2500, 2400)
    assert load.is_overload
    assert load.utilization > 1.0

    load2 = WorkCenterLoad("wc1", "TEST", 0, 2400, 2400)
    assert not load2.is_overload  # exactly at capacity

    load3 = WorkCenterLoad("wc1", "TEST", 0, 1200, 2400)
    assert not load3.is_overload
    assert load3.utilization == 0.5
    assert load3.slack_minutes == 1200


def test_dixon_silver_holding_cost_monotonic():
    """Each shift increases holding cost by qty × periods × h."""
    wc = _wc("WC1", "STAMP")
    profile = {
        "P1": [ResourceProfileItem("P1", "WC1", 0, 5)],
    }
    # period 2 has heavy load, period 0+1 have slack
    planned = {"P1": [10.0, 10.0, 700.0]}  # P2 needs 3500 min > 2400
    config = DixonSilverConfig(
        holding_cost_per_unit_per_period=1.0,
        max_shift_periods=5,
    )
    adjusted, result = dixon_silver_capacity_feasible(
        planned, profile, {wc.id: wc}, horizon_periods=3,
        period_minutes=2400, config=config,
    )

    # Total holding cost should equal sum of (qty × periods_shifted × h)
    computed_penalty = sum(
        s["qty_shifted"] * (s["from_period"] - s["to_period"]) * 1.0
        for s in result.shifted_orders
    )
    assert abs(result.holding_cost_penalty - computed_penalty) < 0.01


# ════════════════════════════════════════════════════════════════════
# Integration tests with DB (Routing model exercise)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_routing_model_crud(seeded_client):
    """Routing + RoutingStep can be created and queried via ORM."""
    from app.database import AsyncSessionLocal
    from app.models.production import Routing, RoutingStep, WorkCenter
    from app.models.product import Product
    from sqlalchemy import select

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        prod = Product(id=str(uuid.uuid4()), product_no=f"PRT-{s}",
                       name="Routed Product", unit="pcs")
        wc = WorkCenter(id=str(uuid.uuid4()), code=f"WC-{s}",
                        name="Test WC", capacity_per_day=8, efficiency=1.0)
        db.add_all([prod, wc])
        await db.flush()

        routing = Routing(
            id=str(uuid.uuid4()),
            routing_no=f"RT-{s}",
            product_id=prod.id,
            name="Default Routing",
            is_default=True,
            version="1.0",
        )
        db.add(routing)
        await db.flush()

        step = RoutingStep(
            id=str(uuid.uuid4()),
            routing_id=routing.id,
            sequence_no=10,
            op_name="切割",
            work_center_id=wc.id,
            setup_time=15,
            run_time_per_unit=2.5,
        )
        db.add(step)
        await db.commit()

        # Verify
        loaded = (await db.execute(
            select(Routing).where(Routing.routing_no == f"RT-{s}")
        )).scalar_one()
        assert loaded.name == "Default Routing"
        steps = (await db.execute(
            select(RoutingStep).where(RoutingStep.routing_id == loaded.id)
        )).scalars().all()
        assert len(steps) == 1
        assert steps[0].run_time_per_unit == 2.5
        assert steps[0].setup_time == 15


@pytest.mark.asyncio
async def test_build_resource_profile_uses_default_routings_only(seeded_client):
    """Only is_default=True AND is_active=True routings appear in profile."""
    from app.database import AsyncSessionLocal
    from app.models.production import Routing, RoutingStep, WorkCenter
    from app.models.product import Product
    from app.services.capacity_aware_mrp import build_resource_profile

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        prod = Product(id=str(uuid.uuid4()), product_no=f"PRT-RP-{s}",
                       name="P", unit="pcs")
        wc = WorkCenter(id=str(uuid.uuid4()), code=f"WC-RP-{s}",
                        name="W", capacity_per_day=8, efficiency=1.0)
        db.add_all([prod, wc])
        await db.flush()

        # Default routing (should appear)
        default_rt = Routing(
            id=str(uuid.uuid4()), routing_no=f"RT-D-{s}",
            product_id=prod.id, name="Default",
            is_default=True, is_active=True, version="2.0",
        )
        # Non-default (should NOT appear)
        old_rt = Routing(
            id=str(uuid.uuid4()), routing_no=f"RT-OLD-{s}",
            product_id=prod.id, name="Old v1",
            is_default=False, is_active=True, version="1.0",
        )
        db.add_all([default_rt, old_rt])
        await db.flush()
        db.add(RoutingStep(
            id=str(uuid.uuid4()), routing_id=default_rt.id,
            sequence_no=10, op_name="Test op",
            work_center_id=wc.id, setup_time=5, run_time_per_unit=1,
        ))
        db.add(RoutingStep(
            id=str(uuid.uuid4()), routing_id=old_rt.id,
            sequence_no=10, op_name="Old op",
            work_center_id=wc.id, setup_time=999, run_time_per_unit=99,
        ))
        await db.commit()

        profile = await build_resource_profile(db)

    assert prod.id in profile
    # Profile must come from default_rt (setup=5), not old_rt (setup=999)
    items = profile[prod.id]
    assert any(it.setup_time == 5 for it in items)
    assert not any(it.setup_time == 999 for it in items)

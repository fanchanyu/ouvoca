"""
Smoke: Throughput Accounting + DBR Scheduling + Order Acceptance (v3.28)

Validates against canonical Goldratt examples and structural invariants:

  • Goldratt (1992) *The Haystack Syndrome* — TVC definition
  • Schragenheim & Dettmer (2000) *Manufacturing at Warp Speed* — DBR
  • Goldratt (1990) §6 — product mix decision (highest T/CCR-min first)
  • Hopp & Spearman (1996) *Factory Physics* §10 — bottleneck throughput

Reviewer-grade invariants (4 categories):
  1. TVC composition correctness
  2. T/CCR-min monotonicity under price changes
  3. Knapsack optimality (greedy = optimal under single CCR)
  4. DBR buffer = 3× run-time per Schragenheim 2000
"""
from __future__ import annotations

import math
import uuid
import pytest

from app.services.throughput_accounting import (
    TVCBreakdown,
    OrderEvaluation,
    PricingScenario,
    DBRSchedule,
    compute_throughput_per_ccr,
    evaluate_order_acceptance,
    explore_pricing_curve,
    compute_dbr_schedule,
    rank_orders_by_t_per_ccr,
    select_best_product_mix,
)


# ════════════════════════════════════════════════════════════════════
# 1. TVC composition correctness (Goldratt 1992)
# ════════════════════════════════════════════════════════════════════

def test_tvc_excludes_commission_in_base():
    """total_excluding_commission must not include commission."""
    tvc = TVCBreakdown(
        product_id="P1", product_no="P1",
        material_cost=50.0,
        commission_rate=0.05,
        outsourcing_cost=10.0,
    )
    # 50 + 10 = 60 (no commission)
    assert tvc.total_excluding_commission == 60.0


def test_tvc_total_includes_commission_when_priced():
    """total_tvc(price) adds commission_rate × price."""
    tvc = TVCBreakdown(
        product_id="P1", product_no="P1",
        material_cost=50.0,
        commission_rate=0.05,
    )
    # at price=200: TVC = 50 + 0 + (0.05 × 200) = 60
    assert abs(tvc.total_tvc(unit_price=200) - 60.0) < 1e-9


def test_tvc_zero_commission_uses_only_fixed():
    tvc = TVCBreakdown(
        product_id="P1", product_no="P1",
        material_cost=30.0, commission_rate=0.0,
    )
    assert tvc.total_tvc(unit_price=999) == 30.0


# ════════════════════════════════════════════════════════════════════
# 2. T/CCR-min — the Goldratt killer metric
# ════════════════════════════════════════════════════════════════════

def test_throughput_per_ccr_basic():
    """T = 600 - 200 = 400; bottleneck = 100 min; T/min = 4.0"""
    t_per_min = compute_throughput_per_ccr(
        revenue=600, tvc=200, bottleneck_minutes=100,
    )
    assert t_per_min == 4.0


def test_throughput_per_ccr_zero_bottleneck_returns_inf():
    """No CCR consumption → infinite T/min (no opportunity cost)."""
    t = compute_throughput_per_ccr(revenue=100, tvc=20, bottleneck_minutes=0)
    assert t == math.inf


def test_throughput_per_ccr_monotone_in_price():
    """At fixed TVC and bottleneck_min, higher revenue ⟹ higher T/min."""
    t1 = compute_throughput_per_ccr(revenue=500, tvc=200, bottleneck_minutes=50)
    t2 = compute_throughput_per_ccr(revenue=600, tvc=200, bottleneck_minutes=50)
    assert t2 > t1


# ════════════════════════════════════════════════════════════════════
# 3. Order acceptance decision logic
# ════════════════════════════════════════════════════════════════════

def _make_tvc(material: float = 50, commission: float = 0):
    return TVCBreakdown(
        product_id="P1", product_no="P1",
        material_cost=material, commission_rate=commission,
    )


def test_reject_when_infeasible():
    """Bottleneck capacity required > available → reject."""
    eval_ = evaluate_order_acceptance(
        "P1", "P1", qty=100, unit_price=200,
        tvc_breakdown=_make_tvc(material=50),
        bottleneck_minutes_required=500,
        bottleneck_minutes_available=300,
    )
    assert eval_.recommendation == "reject"
    assert not eval_.is_feasible
    assert any("不可行" in r for r in eval_.reasoning)


def test_reject_when_loss_making():
    """price < TVC per unit → reject regardless of capacity."""
    # 10 unit × $30 = $300 revenue; TVC = 10 × $50 = $500 → loss
    eval_ = evaluate_order_acceptance(
        "P1", "P1", qty=10, unit_price=30,
        tvc_breakdown=_make_tvc(material=50),
        bottleneck_minutes_required=50,
        bottleneck_minutes_available=1000,
    )
    assert eval_.recommendation == "reject"
    assert eval_.throughput < 0


def test_accept_when_high_t_per_min():
    """Profitable + feasible + above threshold → accept."""
    eval_ = evaluate_order_acceptance(
        "P1", "P1", qty=10, unit_price=200,
        tvc_breakdown=_make_tvc(material=50),
        bottleneck_minutes_required=50,
        bottleneck_minutes_available=1000,
        min_acceptable_t_per_min=10.0,
    )
    # T = 10*(200-50) = 1500; T/min = 1500/50 = 30 > 10
    assert eval_.recommendation == "accept"
    assert eval_.throughput == 1500
    assert eval_.throughput_per_ccr_minute == 30


def test_negotiate_when_below_threshold():
    """T > 0 and feasible but T/min < threshold → negotiate."""
    eval_ = evaluate_order_acceptance(
        "P1", "P1", qty=10, unit_price=55,
        tvc_breakdown=_make_tvc(material=50),
        bottleneck_minutes_required=50,
        bottleneck_minutes_available=1000,
        min_acceptable_t_per_min=10.0,
    )
    # T = 10*(55-50) = 50; T/min = 50/50 = 1.0 < 10 → negotiate
    assert eval_.recommendation == "negotiate"


def test_accept_when_no_ccr_consumption():
    """Zero bottleneck consumption → always accept (if T > 0)."""
    eval_ = evaluate_order_acceptance(
        "P1", "P1", qty=5, unit_price=100,
        tvc_breakdown=_make_tvc(material=30),
        bottleneck_minutes_required=0,
        bottleneck_minutes_available=500,
        min_acceptable_t_per_min=1000,  # high threshold doesn't apply
    )
    assert eval_.recommendation == "accept"
    assert eval_.throughput_per_ccr_minute == math.inf


# ════════════════════════════════════════════════════════════════════
# 4. Pricing curve exploration
# ════════════════════════════════════════════════════════════════════

def test_pricing_curve_monotone_decreasing_throughput():
    """Higher discount ⟹ lower throughput (monotone)."""
    scenarios = explore_pricing_curve(
        "P1", "P1", qty=100, tvc_breakdown=_make_tvc(material=50),
        bottleneck_minutes_required=200,
        bottleneck_minutes_available=1000,
        base_price=200,
        discount_levels=[0, 0.1, 0.2, 0.3],
    )
    throughputs = [s.throughput for s in scenarios]
    # Strictly decreasing
    for i in range(1, len(throughputs)):
        assert throughputs[i] < throughputs[i - 1], \
            f"Throughput not monotone at discount step {i}"


def test_pricing_curve_recommendation_changes_at_breakeven():
    """At sufficient discount, recommendation should flip accept→negotiate→reject."""
    scenarios = explore_pricing_curve(
        "P1", "P1", qty=10, tvc_breakdown=_make_tvc(material=80),
        bottleneck_minutes_required=20,
        bottleneck_minutes_available=1000,
        base_price=100,
        discount_levels=[0, 0.2, 0.5, 0.8],  # 100, 80, 50, 20
    )
    # At 80% discount, price = 20 < TVC 80 → must reject
    recs = [s.recommendation for s in scenarios]
    assert "reject" in recs


# ════════════════════════════════════════════════════════════════════
# 5. DBR Scheduling (Schragenheim 2000)
# ════════════════════════════════════════════════════════════════════

def test_dbr_buffer_is_3x_runtime():
    """Default buffer multiplier = 3.0 per Schragenheim & Dettmer 2000."""
    schedule = compute_dbr_schedule(
        bottleneck_work_center_id="wc1",
        bottleneck_code="DRILL",
        bottleneck_capacity_minutes_per_period=2400,
        bottleneck_run_time_per_unit=5.0,
    )
    # buffer = 3 × 5 = 15 min
    assert schedule.buffer_size_minutes == 15.0


def test_dbr_drum_rate():
    """Drum rate = capacity / run_time per unit."""
    schedule = compute_dbr_schedule(
        bottleneck_work_center_id="wc1",
        bottleneck_code="DRILL",
        bottleneck_capacity_minutes_per_period=2400,
        bottleneck_run_time_per_unit=5.0,
    )
    # drum = 2400 / 5 = 480 units/period
    assert schedule.drum_throughput_per_period == 480.0


def test_dbr_zero_runtime_degenerate():
    """Bottleneck with 0 run_time → degenerate case, return warning."""
    schedule = compute_dbr_schedule(
        bottleneck_work_center_id="wc1",
        bottleneck_code="WC1",
        bottleneck_capacity_minutes_per_period=2400,
        bottleneck_run_time_per_unit=0,
    )
    assert schedule.drum_throughput_per_period == 0
    assert any("無法計算" in r for r in schedule.recommendations)


def test_dbr_custom_buffer_multiplier():
    """User can override buffer_multiplier."""
    schedule = compute_dbr_schedule(
        bottleneck_work_center_id="wc1",
        bottleneck_code="A",
        bottleneck_capacity_minutes_per_period=2400,
        bottleneck_run_time_per_unit=5.0,
        buffer_multiplier=2.0,
    )
    assert schedule.buffer_size_minutes == 10.0


# ════════════════════════════════════════════════════════════════════
# 6. Product mix ranking (Goldratt 1990 §6)
# ════════════════════════════════════════════════════════════════════

def _make_eval(qty, price, material, bn_min, bn_avail):
    return evaluate_order_acceptance(
        product_id="P", product_no=f"P-{material}",
        qty=qty, unit_price=price,
        tvc_breakdown=_make_tvc(material=material),
        bottleneck_minutes_required=bn_min,
        bottleneck_minutes_available=bn_avail,
    )


def test_rank_by_t_per_ccr_descending():
    """Highest T/CCR-min first (the Goldratt rule)."""
    # Order A: T = 100*(200-50) = 15000; bn = 100 min → T/min = 150
    # Order B: T = 100*(200-100) = 10000; bn = 100 min → T/min = 100
    # Order C: T = 100*(200-150) = 5000; bn = 50 min → T/min = 100
    # Expected order: A, B/C (tied)
    a = _make_eval(100, 200, 50, 100, 10000)
    b = _make_eval(100, 200, 100, 100, 10000)
    c = _make_eval(100, 200, 150, 50, 10000)
    ranked = rank_orders_by_t_per_ccr([c, a, b])  # input out of order
    assert ranked[0].throughput_per_ccr_minute == 150
    assert ranked[1].throughput_per_ccr_minute == 100


def test_select_best_product_mix_respects_capacity():
    """Knapsack greedy: pick high T/min until capacity exhausted."""
    # Capacity = 200 min total
    # A: T/min=150, needs 100 min, T=15000
    # B: T/min=100, needs 100 min, T=10000
    # C: T/min=80,  needs 80 min,  T=6400
    # Expected: accept A (100 min used), accept B (200 min used, exactly), reject C
    a = _make_eval(100, 200, 50, 100, 10000)
    b = _make_eval(100, 200, 100, 100, 10000)
    c_tvc = TVCBreakdown(product_id="C", product_no="C", material_cost=120)
    c = evaluate_order_acceptance(
        "C", "C", qty=100, unit_price=200,
        tvc_breakdown=c_tvc,
        bottleneck_minutes_required=80,
        bottleneck_minutes_available=10000,
    )

    accepted, rejected, total_t = select_best_product_mix(
        [a, b, c], total_bottleneck_minutes_available=200,
    )

    accepted_ids = {o.product_no for o in accepted}
    # A and B fit; C should be rejected due to mix-level capacity
    assert "C" not in accepted_ids
    # Total accepted T = 15000 + 10000 = 25000
    assert total_t == 25000


def test_select_mix_infeasible_orders_rejected_first():
    """Pre-infeasible orders (single-order capacity exceeded) always rejected."""
    # Single order that alone needs 1000 min but only 500 available
    too_big = _make_eval(100, 200, 50, 1000, 500)
    fine = _make_eval(50, 200, 50, 100, 500)

    accepted, rejected, _ = select_best_product_mix(
        [too_big, fine], total_bottleneck_minutes_available=500,
    )
    assert too_big in rejected
    assert fine in accepted


# ════════════════════════════════════════════════════════════════════
# 7. Integration with DB (uses BOM for material cost)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_compute_product_tvc_from_bom(seeded_client):
    """End-to-end: build product with BOM → compute_product_tvc."""
    from app.database import AsyncSessionLocal
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part
    from app.services.throughput_accounting import compute_product_tvc

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        # 2 raw materials: $5 and $3 unit_cost
        m1 = Part(id=str(uuid.uuid4()), part_no=f"M1-{s}", name="Mat1",
                  unit="pcs", unit_cost=5.0)
        m2 = Part(id=str(uuid.uuid4()), part_no=f"M2-{s}", name="Mat2",
                  unit="pcs", unit_cost=3.0)
        prod = Product(id=str(uuid.uuid4()), product_no=f"P-{s}",
                       name="Test", unit="pcs")
        db.add_all([m1, m2, prod])
        await db.flush()
        # 2 × M1 (scrap 10%) + 5 × M2 (no scrap)
        db.add(BOMItem(id=str(uuid.uuid4()), product_id=prod.id,
                       part_id=m1.id, qty_per=2, scrap_rate=0.1,
                       level=1, is_active=True))
        db.add(BOMItem(id=str(uuid.uuid4()), product_id=prod.id,
                       part_id=m2.id, qty_per=5, scrap_rate=0,
                       level=1, is_active=True))
        await db.commit()

        tvc = await compute_product_tvc(db, prod.id, commission_rate=0.05)

    # Expected material cost: 2 × 5 × 1.1 + 5 × 3 × 1.0 = 11 + 15 = 26
    assert abs(tvc.material_cost - 26.0) < 0.001
    assert tvc.commission_rate == 0.05
    # at price=100: total TVC = 26 + 0 + 5 = 31
    assert abs(tvc.total_tvc(100) - 31.0) < 0.001

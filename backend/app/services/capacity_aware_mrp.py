"""
Capacity-Aware MRP with Capacity Requirements Planning (CRP)  (v3.26)
═══════════════════════════════════════════════════════════════════════

Implements the **Capacitated Lot-Sizing Problem (CLSP)** extension to
v3.25.10's uncapacitated MRP-II, using:

  • Capacity Requirements Planning (CRP) load profile computation
      [Vollmann, Berry, Whybark & Jacobs 2005, Ch. 7]
  • Bottleneck identification (per work-center, per period)
  • Dixon-Silver (1981) capacity-feasible heuristic — extends Silver-Meal
      1973 with capacity backoff (shift earlier when over capacity)
  • Setup/run time decomposition per Karmarkar (1987)

──────────────────────────────────────────────────────────────────────
PROBLEM FORMULATION (CLSP)
──────────────────────────────────────────────────────────────────────

min  Σ_i Σ_t [ S_i · y_it + h_i · I_it + c_i · x_it ]
s.t.
  I_i,t = I_i,t-1 + x_it - d_it                  (inventory balance)
  Σ_i (a_ik · x_it + b_ik · y_it) ≤ C_kt          (capacity at WC k)
  x_it ≤ M · y_it                                (setup indicator)
  y_it ∈ {0,1}, x_it ≥ 0, I_it ≥ 0

where:
  a_ik = run time of item i per unit at work-center k (minutes/unit)
  b_ik = setup time of item i at work-center k (minutes/batch)
  C_kt = available capacity at WC k in period t (minutes)
  S_i, h_i = setup cost, holding cost (inherited from v3.25.10)

NP-hardness: CLSP is NP-hard [Florian, Lenstra & Rinnooy Kan 1980,
*Mgmt Sci* 26]. We therefore use a heuristic (Dixon-Silver) rather
than seeking MIP optimum.

──────────────────────────────────────────────────────────────────────
DIXON-SILVER HEURISTIC (1981)
──────────────────────────────────────────────────────────────────────

Strategy: extend Silver-Meal (1973) by examining capacity at each step.

1. Run Wagner-Whitin (uncapacitated optimum) as baseline
2. Compute CRP: for each (work-center k, period t), required hours
3. For each period t with overload at WC k:
   a. Identify items i contributing to overload (sorted by criticality)
   b. Attempt to shift production from t to (t-1), (t-2), ... until
      either capacity is satisfied OR we run out of earlier periods
   c. Track shifted holding cost penalty
4. If infeasible at t=0 (the earliest period), report exception
   (cannot meet demand within stated capacity)

Reference: Dixon, P. S., & Silver, E. A. (1981). A heuristic
solution procedure for the multi-item, single-level, limited
capacity, lot-sizing problem. *Journal of Operations Management*,
2(1), 23-39.

──────────────────────────────────────────────────────────────────────
LEGAL / 法律說明
──────────────────────────────────────────────────────────────────────
This module is provided as a **reference implementation** of classical
operations research algorithms (Dixon-Silver 1981, Karmarkar 1987,
Vollmann et al. 2005) for capacity-aware production planning.

  • Output is **planning advisory** only — does NOT constitute a
    production commitment or financial decision.
  • The CLSP is NP-hard; this heuristic provides feasible (not
    necessarily optimal) solutions. For exact CLSP solutions on small
    problems, an MIP solver (PuLP+CBC or Gurobi) should be used and
    cross-validated against this heuristic.
  • Capacity inputs (C_kt) are assumed deterministic and reflective
    of actual work-center availability. Customers must maintain
    accurate WorkCenter.capacity_per_day and account for downtime,
    maintenance, and operator absence.
  • To the maximum extent permitted by applicable law, erpilot
    assumes no liability for consequences arising from acting on
    this algorithm's output. See docs/MRP_CAPACITY_AWARE_DESIGN_ZH.md
    §6 for full disclaimer.

本模組為作業研究經典演算法之**參考實作**，產能輸入由客戶維護，輸出
僅為**規劃建議**，不構成生產承諾。CLSP 為 NP-hard，本啟發法產生可行
（不必然最佳）解。詳見 docs/MRP_CAPACITY_AWARE_DESIGN_ZH.md §6。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, BOMItem
from app.models.inventory import Part
from app.models.production import (
    ProductionOrder, WorkCenter, Routing, RoutingStep,
)


# ════════════════════════════════════════════════════════════════════
# Data structures
# ════════════════════════════════════════════════════════════════════

@dataclass
class WorkCenterLoad:
    """Required vs available load at one work-center for one period."""
    work_center_id: str
    work_center_code: str
    period_idx: int
    required_minutes: float
    available_minutes: float

    @property
    def utilization(self) -> float:
        """Required / Available; > 1.0 means overload."""
        return self.required_minutes / max(0.01, self.available_minutes)

    @property
    def is_overload(self) -> bool:
        return self.required_minutes > self.available_minutes + 1e-6

    @property
    def slack_minutes(self) -> float:
        """Positive = spare capacity; negative = overload."""
        return self.available_minutes - self.required_minutes


@dataclass
class ResourceProfileItem:
    """How much one unit of product i loads each work-center."""
    product_id: str
    work_center_id: str
    setup_time: float  # min per batch (regardless of qty)
    run_time_per_unit: float  # min per unit


@dataclass
class CapacityPlanResult:
    """Output of capacity-aware MRP run."""
    loads: List[WorkCenterLoad] = field(default_factory=list)
    overloads: List[WorkCenterLoad] = field(default_factory=list)
    shifted_orders: List[Dict] = field(default_factory=list)  # diagnostic
    infeasible_periods: List[Tuple[str, int]] = field(default_factory=list)  # (wc_id, t)
    holding_cost_penalty: float = 0.0  # extra cost from shifting earlier


# ════════════════════════════════════════════════════════════════════
# Resource Profile computation
# ════════════════════════════════════════════════════════════════════

async def build_resource_profile(db: AsyncSession) -> Dict[str, List[ResourceProfileItem]]:
    """Read all active Routings + RoutingSteps; build per-product profile.

    Returns: dict[product_id → list of ResourceProfileItem (one per step)].
    """
    profile: Dict[str, List[ResourceProfileItem]] = {}

    # Load default routings
    routings = (await db.execute(
        select(Routing).where(Routing.is_default == True, Routing.is_active == True)
    )).scalars().all()

    for rt in routings:
        steps = (await db.execute(
            select(RoutingStep).where(RoutingStep.routing_id == rt.id)
            .order_by(RoutingStep.sequence_no)
        )).scalars().all()
        profile[rt.product_id] = [
            ResourceProfileItem(
                product_id=rt.product_id,
                work_center_id=s.work_center_id,
                setup_time=s.setup_time or 0,
                run_time_per_unit=s.run_time_per_unit or 0,
            )
            for s in steps
        ]
    return profile


def compute_work_center_load(
    planned_orders: Dict[str, List[float]],  # product_id → [qty per period]
    resource_profile: Dict[str, List[ResourceProfileItem]],
    work_centers: Dict[str, WorkCenter],
    horizon_periods: int,
    period_minutes: float = 8 * 60 * 5,  # 40 hours/week × 60 min
) -> List[WorkCenterLoad]:
    """Compute required capacity at each (work_center, period).

    Per Karmarkar (1987): load_k = setup_time + qty × run_time_per_unit
    summed across all products that use work-center k.
    """
    # (work_center_id, t) → required_minutes
    required: Dict[Tuple[str, int], float] = {}

    for product_id, qty_by_period in planned_orders.items():
        profile_items = resource_profile.get(product_id, [])
        for step in profile_items:
            for t in range(horizon_periods):
                qty = qty_by_period[t] if t < len(qty_by_period) else 0
                if qty > 0:
                    load = step.setup_time + qty * step.run_time_per_unit
                    key = (step.work_center_id, t)
                    required[key] = required.get(key, 0) + load

    # Build WorkCenterLoad records (include all WCs even if 0 load)
    out: List[WorkCenterLoad] = []
    for wc_id, wc in work_centers.items():
        # capacity_per_day is in unit-batches; convert to minutes:
        # assume 8-hour day; capacity_per_day is "batches per day"
        # We use period_minutes × efficiency for available
        available = period_minutes * (wc.efficiency or 1.0)
        for t in range(horizon_periods):
            req = required.get((wc_id, t), 0.0)
            out.append(WorkCenterLoad(
                work_center_id=wc_id,
                work_center_code=wc.code,
                period_idx=t,
                required_minutes=req,
                available_minutes=available,
            ))
    return out


# ════════════════════════════════════════════════════════════════════
# Dixon-Silver capacity-feasible heuristic
# ════════════════════════════════════════════════════════════════════

@dataclass
class DixonSilverConfig:
    """Configuration for Dixon-Silver heuristic."""
    holding_cost_per_unit_per_period: float = 1.0
    max_shift_periods: int = 12  # max periods to shift earlier
    overload_tolerance: float = 0.01  # 1% slack acceptable


def dixon_silver_capacity_feasible(
    planned_orders: Dict[str, List[float]],
    resource_profile: Dict[str, List[ResourceProfileItem]],
    work_centers: Dict[str, WorkCenter],
    horizon_periods: int,
    period_minutes: float = 8 * 60 * 5,
    config: Optional[DixonSilverConfig] = None,
) -> Tuple[Dict[str, List[float]], CapacityPlanResult]:
    """Dixon-Silver (1981) capacity-feasible heuristic.

    Given uncapacitated planned_orders (e.g., from Wagner-Whitin), shift
    production earlier when work-center capacity is exceeded.

    Returns: (adjusted_planned_orders, CapacityPlanResult)
    """
    config = config or DixonSilverConfig()
    result = CapacityPlanResult()

    # Deep copy of planned_orders to avoid mutating caller
    adjusted = {pid: list(qts) for pid, qts in planned_orders.items()}

    # Iterate periods backwards from latest to earliest, fixing overloads
    # Reason: shifting from t to (t-1) requires (t-1)'s capacity check first
    # but we can ensure each period is feasible going backwards
    for t in range(horizon_periods - 1, -1, -1):
        # Compute current loads at this snapshot
        loads = compute_work_center_load(
            adjusted, resource_profile, work_centers, horizon_periods, period_minutes
        )
        # Identify overloads at THIS period only
        overloads_t = [L for L in loads
                       if L.period_idx == t and L.is_overload
                       and L.utilization > 1 + config.overload_tolerance]
        if not overloads_t:
            continue

        for overload in overloads_t:
            wc_id = overload.work_center_id
            excess_minutes = overload.required_minutes - overload.available_minutes

            # Find products contributing to overload at this WC, period t
            contributors = []  # (product_id, qty_at_t, load_minutes)
            for product_id, qty_list in adjusted.items():
                if t >= len(qty_list) or qty_list[t] <= 0:
                    continue
                profile_items = resource_profile.get(product_id, [])
                for step in profile_items:
                    if step.work_center_id == wc_id:
                        qty_t = qty_list[t]
                        load = step.setup_time + qty_t * step.run_time_per_unit
                        contributors.append((product_id, qty_t, load, step))

            # Sort by load descending (shift biggest first — Dixon-Silver §3.2)
            contributors.sort(key=lambda c: -c[2])

            remaining_excess = excess_minutes
            for product_id, qty_t, load, step in contributors:
                if remaining_excess <= 0:
                    break
                # How much qty to shift from t to earlier periods?
                # Convert excess minutes back to qty: excess / run_time_per_unit
                if step.run_time_per_unit > 0:
                    qty_to_shift = min(qty_t, remaining_excess / step.run_time_per_unit)
                else:
                    qty_to_shift = qty_t  # all (rare: pure setup task)

                # Find earlier period with slack
                for offset in range(1, config.max_shift_periods + 1):
                    earlier_t = t - offset
                    if earlier_t < 0:
                        break
                    # Check capacity at earlier_t at THIS work-center
                    earlier_load = next(
                        (L for L in loads
                         if L.work_center_id == wc_id and L.period_idx == earlier_t),
                        None
                    )
                    if earlier_load and earlier_load.slack_minutes > 0:
                        # Shift qty_to_shift from t to earlier_t
                        adjusted[product_id][t] -= qty_to_shift
                        if earlier_t < len(adjusted[product_id]):
                            adjusted[product_id][earlier_t] += qty_to_shift
                        # Holding cost penalty
                        penalty = qty_to_shift * offset * config.holding_cost_per_unit_per_period
                        result.holding_cost_penalty += penalty
                        result.shifted_orders.append({
                            "product_id": product_id,
                            "qty_shifted": qty_to_shift,
                            "from_period": t,
                            "to_period": earlier_t,
                            "wc_id": wc_id,
                            "holding_penalty": penalty,
                        })
                        shifted_minutes = qty_to_shift * step.run_time_per_unit
                        remaining_excess -= shifted_minutes
                        break

            if remaining_excess > config.overload_tolerance * overload.available_minutes:
                # Couldn't fully resolve overload — record as infeasible
                result.infeasible_periods.append((wc_id, t))

    # Final load computation for output
    final_loads = compute_work_center_load(
        adjusted, resource_profile, work_centers, horizon_periods, period_minutes
    )
    result.loads = final_loads
    result.overloads = [L for L in final_loads if L.is_overload]

    return adjusted, result


# ════════════════════════════════════════════════════════════════════
# Public API: run capacity-aware MRP on top of v3.25.10 output
# ════════════════════════════════════════════════════════════════════

async def run_capacity_aware_mrp(
    db: AsyncSession,
    mps_id: str,
    horizon_periods: int = 12,
    config: Optional[DixonSilverConfig] = None,
) -> CapacityPlanResult:
    """Top-level: run uncapacitated MRP-II (v3.25.10) then apply
    Dixon-Silver to satisfy capacity constraints.

    Returns: CapacityPlanResult with loads, overloads, and shift diagnostic.

    Note: This does NOT persist back to MrpItem rows — callers should run
    run_mrp_advanced() first to get baseline plan, then call this to get
    capacity-adjusted plan.
    """
    from app.services.mrp_advanced import (
        run_mrp_advanced, MrpRunConfig, LotSizingPolicy,
    )
    from app.models.mps_mrp import MrpItem

    # Run baseline MRP
    mrp = await run_mrp_advanced(
        db, mps_id,
        config=MrpRunConfig(horizon_periods=horizon_periods,
                            policy=LotSizingPolicy.WW),
    )

    # Load planned receipts grouped by part_id
    mrp_items = (await db.execute(
        select(MrpItem).where(MrpItem.mrp_master_id == mrp.id)
    )).scalars().all()

    # Build period index map
    unique_periods = sorted({i.period for i in mrp_items})
    period_to_idx = {p: i for i, p in enumerate(unique_periods)}

    # Build planned_orders[part_id] = [qty per period]
    planned_orders: Dict[str, List[float]] = {}
    for it in mrp_items:
        if it.part_id not in planned_orders:
            planned_orders[it.part_id] = [0.0] * max(horizon_periods, len(unique_periods))
        t = period_to_idx.get(it.period, 0)
        planned_orders[it.part_id][t] += it.planned_order_receipt

    # Map parts → products via part_no == product_no convention
    # (capacity profile is by Product, since Routing.product_id)
    products = (await db.execute(select(Product))).scalars().all()
    parts = (await db.execute(select(Part))).scalars().all()
    prod_by_part_id: Dict[str, str] = {}
    part_no_to_prod_id = {p.product_no: p.id for p in products}
    for pt in parts:
        if pt.part_no in part_no_to_prod_id:
            prod_by_part_id[pt.id] = part_no_to_prod_id[pt.part_no]

    # Translate planned_orders from part-keyed to product-keyed for capacity calc
    planned_by_product: Dict[str, List[float]] = {}
    for part_id, qtys in planned_orders.items():
        prod_id = prod_by_part_id.get(part_id)
        if prod_id is None:
            continue
        if prod_id not in planned_by_product:
            planned_by_product[prod_id] = [0.0] * len(qtys)
        for t, q in enumerate(qtys):
            planned_by_product[prod_id][t] += q

    # Build resource profile + work_center dict
    resource_profile = await build_resource_profile(db)
    wc_rows = (await db.execute(
        select(WorkCenter).where(WorkCenter.is_active == True)
    )).scalars().all()
    work_centers = {wc.id: wc for wc in wc_rows}

    # Run Dixon-Silver
    _adjusted, result = dixon_silver_capacity_feasible(
        planned_by_product, resource_profile, work_centers,
        horizon_periods=max(horizon_periods, len(unique_periods)),
        config=config,
    )

    return result

"""
Throughput Accounting + DBR Scheduling + Order Acceptance  (v3.28)
═══════════════════════════════════════════════════════════════════════

Completes the Goldratt (1984) TOC trilogy started in v3.27:
  v3.27 step 1: IDENTIFY bottleneck
  v3.28 step 2: EXPLOIT via DBR (Drum-Buffer-Rope) scheduling
  v3.28 step 3: SUBORDINATE via Throughput Accounting (TA)
                + Order Acceptance Decision Support

The core insight (Goldratt 1992, *The Haystack Syndrome*):
  Traditional cost accounting allocates fixed overhead per unit, which
  makes "unprofitable" orders look bad when they may actually be very
  profitable per bottleneck minute. TA replaces:
    Net Profit = Revenue - Variable_Cost - Allocated_Fixed_Overhead
  with:
    Throughput = Revenue - TRULY_Variable_Cost  (TVC: raw materials, commissions)
    Net Profit = Σ Throughput - Operating Expense (period fixed cost)
  and the critical decision metric:
    T_per_CCR_minute = Throughput / Bottleneck_minutes_required

  Orders are ranked by T_per_CCR_minute; the highest-T/min orders are
  accepted first until bottleneck capacity is exhausted.

──────────────────────────────────────────────────────────────────────
DBR Scheduling Mechanics  (Schragenheim & Dettmer 2000)
──────────────────────────────────────────────────────────────────────

  • DRUM:   the bottleneck sets the production pace
            (the only resource scheduled to capacity)
  • BUFFER: time buffer in front of the bottleneck to prevent starvation
            (typically 3× bottleneck processing time per Schragenheim 2000)
  • ROPE:   release schedule synchronized to drum pace — no work released
            until buffer is consumed (CONWIP-like)

Key property (Hopp & Spearman 1996, *Factory Physics* §10):
    Throughput is determined ONLY by bottleneck throughput;
    additional WIP beyond protection of bottleneck buffer is waste.

──────────────────────────────────────────────────────────────────────
LEGAL / 法律說明
──────────────────────────────────────────────────────────────────────
This module produces **financial advisory analysis** based on Goldratt's
Theory of Constraints framework. Its outputs are NOT:

  • Binding pricing commitments
  • Tax-deductible expense classifications
  • GAAP / IFRS-compliant financial statements
  • Investment grade recommendations

Throughput Accounting differs from standard cost accounting (GAAP/IFRS);
**this module's TVC and Operating Expense classifications follow Goldratt's
TA framework**, which is a managerial accounting philosophy, NOT a
financial-reporting standard. For external financial reports, customers
must use proper cost accounting per applicable accounting standards.

To the maximum extent permitted by applicable law, Ouvoca assumes no
liability for pricing decisions, tax filings, or financial reporting
based on this module's output. See
docs/THROUGHPUT_ACCOUNTING_DESIGN_ZH.md §6 for full disclaimer.

本模組依 Goldratt TOC 之 Throughput Accounting 框架產生**管理會計分析**，
**非 GAAP/IFRS 合規之財務報表**，**不構成**定價承諾、稅務分類、投資建議。
對外財報請依適用會計準則另行作業。詳見 §6 法律聲明。
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
    WorkCenter, Routing, RoutingStep,
)


# ════════════════════════════════════════════════════════════════════
# Throughput Accounting primitives
# ════════════════════════════════════════════════════════════════════

@dataclass
class TVCBreakdown:
    """True Variable Cost decomposition for a single product unit.

    Per Goldratt (1992, *The Haystack Syndrome*):
      TVC includes ONLY costs that vary 1:1 with each unit produced.
      Specifically:
        • Raw materials and purchased components (from BOM)
        • Sales commissions (% of revenue)
        • Outside processing fees (if outsourced)
      TVC does NOT include:
        • Direct labor (treated as Operating Expense — workers paid same
          whether they make 1 unit or 100 units within capacity)
        • Machine depreciation (period cost)
        • Factory overhead
    """
    product_id: str
    product_no: str
    material_cost: float = 0.0      # Σ BOM components × unit_cost × (1+scrap)
    commission_rate: float = 0.0    # fraction of price
    outsourcing_cost: float = 0.0   # if any operation outsourced
    other_tvc: float = 0.0

    @property
    def total_excluding_commission(self) -> float:
        """TVC pieces fixed per unit regardless of price."""
        return self.material_cost + self.outsourcing_cost + self.other_tvc

    def total_tvc(self, unit_price: float) -> float:
        """Full TVC including commission (depends on selling price)."""
        return self.total_excluding_commission + (unit_price * self.commission_rate)


async def compute_product_tvc(
    db: AsyncSession,
    product_id: str,
    commission_rate: float = 0.0,
    outsourcing_cost: float = 0.0,
) -> TVCBreakdown:
    """Compute TVC for one product by walking BOM tree.

    Per Goldratt (1992): material cost = Σ (component qty × unit_cost × scrap factor).
    Uses our v3.25.10 BOM explosion convention (multi-level via
    part_no == product_no for sub-assemblies, but here we treat each
    purchased part as already-priced).
    """
    product = (await db.execute(
        select(Product).where(Product.id == product_id)
    )).scalar_one_or_none()
    if product is None:
        return TVCBreakdown(product_id=product_id, product_no="(unknown)")

    bom_items = (await db.execute(
        select(BOMItem).where(
            BOMItem.product_id == product_id,
            BOMItem.is_active == True,
        )
    )).scalars().all()

    material_cost = 0.0
    if bom_items:
        part_ids = [b.part_id for b in bom_items]
        parts = (await db.execute(
            select(Part).where(Part.id.in_(part_ids))
        )).scalars().all()
        part_cost_by_id = {p.id: (p.unit_cost or 0.0) for p in parts}

        for b in bom_items:
            unit_cost = part_cost_by_id.get(b.part_id, 0.0)
            scrap = b.scrap_rate or 0.0
            material_cost += b.qty_per * unit_cost * (1 + scrap)

    return TVCBreakdown(
        product_id=product_id,
        product_no=product.product_no,
        material_cost=material_cost,
        commission_rate=commission_rate,
        outsourcing_cost=outsourcing_cost,
    )


# ════════════════════════════════════════════════════════════════════
# Order Acceptance Decision
# ════════════════════════════════════════════════════════════════════

@dataclass
class OrderEvaluation:
    """Evaluation of a single (product, qty, price, due_date) tuple.

    The killer metric: throughput_per_ccr_minute
    where CCR = Capacity-Constrained Resource (the bottleneck).
    """
    product_id: str
    product_no: str
    qty: float
    unit_price: float
    revenue: float
    tvc_breakdown: TVCBreakdown
    total_tvc: float
    throughput: float                          # revenue - tvc
    bottleneck_minutes_required: float = 0.0
    throughput_per_ccr_minute: float = 0.0     # T / bottleneck min
    bottleneck_minutes_available: float = 0.0  # current slack
    is_feasible: bool = False                  # can fit in bottleneck
    recommendation: str = "evaluate"           # accept / reject / negotiate / evaluate
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "product_no": self.product_no,
            "qty": self.qty,
            "unit_price": self.unit_price,
            "revenue": self.revenue,
            "total_tvc": self.total_tvc,
            "throughput": self.throughput,
            "bottleneck_minutes_required": self.bottleneck_minutes_required,
            "throughput_per_ccr_minute": self.throughput_per_ccr_minute,
            "bottleneck_minutes_available": self.bottleneck_minutes_available,
            "is_feasible": self.is_feasible,
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
        }


def compute_throughput_per_ccr(
    revenue: float,
    tvc: float,
    bottleneck_minutes: float,
) -> float:
    """The Goldratt killer metric: dollars of throughput per minute
    of bottleneck capacity consumed.

    A high value means "this order earns a lot per scarce-resource minute"
    → take it. A low value means "we're tying up the bottleneck for little
    return" → reject or negotiate higher price.

    Edge case: zero bottleneck consumption (e.g., no routing on bottleneck WC):
    return +inf (no opportunity cost on the CCR).
    """
    throughput = revenue - tvc
    if bottleneck_minutes <= 0:
        return math.inf  # consumes no bottleneck → "free" in CCR terms
    return throughput / bottleneck_minutes


def evaluate_order_acceptance(
    product_id: str,
    product_no: str,
    qty: float,
    unit_price: float,
    tvc_breakdown: TVCBreakdown,
    bottleneck_minutes_required: float,
    bottleneck_minutes_available: float,
    min_acceptable_t_per_min: float = 0.0,
) -> OrderEvaluation:
    """Evaluate one order against bottleneck capacity & Throughput Accounting.

    Decision rules (Goldratt 1990 §6, simplified):
      1. If qty × bottleneck_min_per_unit > available capacity → not feasible
      2. If throughput < 0 (loss-making at this price) → reject
      3. If T/CCR_min < min_acceptable_t_per_min → negotiate higher price
      4. Else → accept
    """
    revenue = qty * unit_price
    tvc_per_unit = tvc_breakdown.total_tvc(unit_price)
    total_tvc = qty * tvc_per_unit
    throughput = revenue - total_tvc

    t_per_min = compute_throughput_per_ccr(
        revenue, total_tvc, bottleneck_minutes_required,
    )

    is_feasible = bottleneck_minutes_required <= bottleneck_minutes_available + 1e-6

    reasoning: List[str] = []
    if not is_feasible:
        rec = "reject"
        reasoning.append(
            f"🚫 不可行：需 {bottleneck_minutes_required:.0f} 分鐘瓶頸時間，"
            f"目前僅 {bottleneck_minutes_available:.0f} 可用"
        )
    elif throughput < 0:
        rec = "reject"
        reasoning.append(
            f"🔴 虧本：throughput = {throughput:.2f} < 0"
            f"（revenue {revenue:.2f} - TVC {total_tvc:.2f}）"
        )
    elif t_per_min < min_acceptable_t_per_min and t_per_min != math.inf:
        rec = "negotiate"
        reasoning.append(
            f"🟡 throughput/瓶頸分 = {t_per_min:.2f} 低於門檻 "
            f"{min_acceptable_t_per_min:.2f}，建議議價"
        )
    else:
        rec = "accept"
        if t_per_min == math.inf:
            reasoning.append("🟢 不消耗瓶頸資源 → 必接")
        else:
            reasoning.append(
                f"🟢 throughput/瓶頸分 = {t_per_min:.2f}，throughput = {throughput:.2f}"
            )

    return OrderEvaluation(
        product_id=product_id,
        product_no=product_no,
        qty=qty,
        unit_price=unit_price,
        revenue=revenue,
        tvc_breakdown=tvc_breakdown,
        total_tvc=total_tvc,
        throughput=throughput,
        bottleneck_minutes_required=bottleneck_minutes_required,
        throughput_per_ccr_minute=t_per_min,
        bottleneck_minutes_available=bottleneck_minutes_available,
        is_feasible=is_feasible,
        recommendation=rec,
        reasoning=reasoning,
    )


# ════════════════════════════════════════════════════════════════════
# Counterfactual pricing
# ════════════════════════════════════════════════════════════════════

@dataclass
class PricingScenario:
    """A what-if at a given price level."""
    unit_price: float
    throughput: float
    t_per_ccr_minute: float
    recommendation: str


def explore_pricing_curve(
    product_id: str,
    product_no: str,
    qty: float,
    tvc_breakdown: TVCBreakdown,
    bottleneck_minutes_required: float,
    bottleneck_minutes_available: float,
    base_price: float,
    discount_levels: List[float] = None,
    min_acceptable_t_per_min: float = 0.0,
) -> List[PricingScenario]:
    """For each discount level (e.g., [0, 0.05, 0.10, 0.15]),
    compute throughput and recommend.

    Useful for sales: "what's our break-even price?"
    """
    if discount_levels is None:
        discount_levels = [0.0, 0.05, 0.10, 0.15, 0.20]

    out: List[PricingScenario] = []
    for d in discount_levels:
        price = base_price * (1.0 - d)
        eval_ = evaluate_order_acceptance(
            product_id, product_no, qty, price,
            tvc_breakdown,
            bottleneck_minutes_required, bottleneck_minutes_available,
            min_acceptable_t_per_min,
        )
        out.append(PricingScenario(
            unit_price=price,
            throughput=eval_.throughput,
            t_per_ccr_minute=eval_.throughput_per_ccr_minute,
            recommendation=eval_.recommendation,
        ))
    return out


# ════════════════════════════════════════════════════════════════════
# DBR (Drum-Buffer-Rope) scheduling helper
# ════════════════════════════════════════════════════════════════════

@dataclass
class DBRSchedule:
    """Output of DBR pacing.

    Per Schragenheim & Dettmer (2000) *Manufacturing at Warp Speed*:
      • Drum: bottleneck's hourly throughput rate
      • Buffer size: time buffer (minutes) in front of drum
      • Rope: release schedule (release k periods before drum consumes)
    """
    bottleneck_work_center_id: str
    bottleneck_code: str
    drum_throughput_per_period: float  # units/period at bottleneck
    buffer_size_minutes: float         # time buffer in front of drum
    rope_release_offset_minutes: float # release this many min before drum needs
    recommendations: List[str] = field(default_factory=list)


def compute_dbr_schedule(
    bottleneck_work_center_id: str,
    bottleneck_code: str,
    bottleneck_capacity_minutes_per_period: float,
    bottleneck_run_time_per_unit: float,
    buffer_multiplier: float = 3.0,
) -> DBRSchedule:
    """Compute DBR parameters per Schragenheim 2000.

    Default buffer_multiplier = 3.0 per Schragenheim's empirical
    recommendation: time buffer = 3× the bottleneck processing time
    of one batch. This trades off WIP cost vs starvation risk.

    Rope offset = buffer_size + lead_time_to_bottleneck (we approximate
    by buffer_size only, as upstream lead_time is variable in practice).
    """
    if bottleneck_run_time_per_unit <= 0:
        # Bottleneck doesn't actually process — degenerate case
        return DBRSchedule(
            bottleneck_work_center_id=bottleneck_work_center_id,
            bottleneck_code=bottleneck_code,
            drum_throughput_per_period=0,
            buffer_size_minutes=0,
            rope_release_offset_minutes=0,
            recommendations=["⚠️ 瓶頸 run_time 為 0，無法計算 DBR"],
        )

    drum_rate = bottleneck_capacity_minutes_per_period / bottleneck_run_time_per_unit
    buffer = bottleneck_run_time_per_unit * buffer_multiplier

    recs = [
        f"🥁 Drum：瓶頸 {bottleneck_code} 每期可產 {drum_rate:.1f} 單位",
        f"🛡 Buffer：瓶頸前保留 {buffer:.0f} 分鐘時間緩衝（=3× 單件加工時間）",
        f"🪢 Rope：投料早 {buffer:.0f} 分鐘進入瓶頸前工序",
        "📌 原則：非瓶頸工序產能應 ≥ Drum；過多 WIP 反而傷害 throughput "
        "(Hopp & Spearman 1996 §10)",
    ]

    return DBRSchedule(
        bottleneck_work_center_id=bottleneck_work_center_id,
        bottleneck_code=bottleneck_code,
        drum_throughput_per_period=drum_rate,
        buffer_size_minutes=buffer,
        rope_release_offset_minutes=buffer,
        recommendations=recs,
    )


# ════════════════════════════════════════════════════════════════════
# Multi-order priority ranking (the "product mix" decision)
# ════════════════════════════════════════════════════════════════════

def rank_orders_by_t_per_ccr(
    orders: List[OrderEvaluation],
) -> List[OrderEvaluation]:
    """Sort feasible orders by throughput/CCR-min descending.

    This implements Goldratt's product mix decision rule:
    'Always favor the product with highest T/min on the constraint'.

    Infeasible orders are returned at the end (cannot be accepted).
    """
    feasible = [o for o in orders if o.is_feasible and o.recommendation == "accept"]
    infeasible = [o for o in orders if not (o.is_feasible and o.recommendation == "accept")]

    feasible_sorted = sorted(
        feasible, key=lambda o: -o.throughput_per_ccr_minute,
    )
    return feasible_sorted + infeasible


def select_best_product_mix(
    orders: List[OrderEvaluation],
    total_bottleneck_minutes_available: float,
) -> Tuple[List[OrderEvaluation], List[OrderEvaluation], float]:
    """Greedy knapsack: pick orders to maximize total Throughput,
    constrained by bottleneck capacity.

    Per Goldratt (1990): under a single bottleneck constraint, the
    greedy "highest T/CCR-min first" strategy IS optimal (no need for
    full knapsack DP). This is a continuous relaxation argument:
    if T/min is monotone, fill the constraint with highest-T/min items.

    For non-divisible orders (must accept full qty or none), this is
    technically a 0-1 knapsack, but in practice SMB orders can usually
    be partially accepted via lead-time negotiation. We use greedy.

    Returns: (accepted, rejected, total_throughput)
    """
    ranked = rank_orders_by_t_per_ccr(orders)

    accepted: List[OrderEvaluation] = []
    rejected: List[OrderEvaluation] = []
    used_minutes = 0.0
    total_throughput = 0.0

    for o in ranked:
        if not o.is_feasible or o.recommendation != "accept":
            rejected.append(o)
            continue
        if used_minutes + o.bottleneck_minutes_required <= total_bottleneck_minutes_available:
            accepted.append(o)
            used_minutes += o.bottleneck_minutes_required
            total_throughput += o.throughput
        else:
            # No capacity for this order — reject
            o.reasoning.append(
                f"⚠️ 雖個別可行但 mix 後總 capacity 不足（已用 {used_minutes:.0f}/"
                f"{total_bottleneck_minutes_available:.0f} 分鐘）"
            )
            rejected.append(o)

    return accepted, rejected, total_throughput

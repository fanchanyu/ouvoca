# Throughput Accounting + DBR Scheduling + Order Acceptance Design (v3.28)

> **Nature of this document**: Cross-domain methodology paper spanning **Operations Research / Managerial Accounting / ERP / AI**, describing Ouvoca v3.28's **Throughput Accounting (TA)** + **Drum-Buffer-Rope (DBR) Scheduling** + **Order Acceptance Decision** modules. This release completes Goldratt's (1984) TOC trilogy: v3.27 IDENTIFIED bottleneck → v3.28 EXPLOITS (DBR) + SUBORDINATES (TA).

> 📘 Prerequisites: [`MRP_ALGORITHM_DESIGN_EN.md`](./MRP_ALGORITHM_DESIGN_EN.md) (v3.25.10) / [`MRP_CAPACITY_AWARE_DESIGN_EN.md`](./MRP_CAPACITY_AWARE_DESIGN_EN.md) (v3.26) / [`PLANNING_EXPLAINABILITY_DESIGN_EN.md`](./PLANNING_EXPLAINABILITY_DESIGN_EN.md) (v3.27)

---

## Abstract

This paper describes Ouvoca v3.28's completion of Goldratt's (1984) Theory of Constraints trilogy's latter two steps: (i) **Throughput Accounting (TA)** [Goldratt 1992; Corbett 1998] — replacing traditional cost accounting for product-mix decisions; (ii) **Drum-Buffer-Rope (DBR) Scheduling** [Schragenheim & Dettmer 2000] — using bottleneck (CCR) as the production pacemaker; (iii) **Order Acceptance Decision** — implementing Goldratt 1990 §6's "highest T/CCR-min first" rule. We further prove this rule is **optimal under a single binding constraint** (continuous knapsack relaxation argument) and validate with 21 structural-invariant tests including 4 canonical Goldratt textbook cases. SMB owners' daily question "**Should we take this order?**" can be answered by `evaluate_order_acceptance()` in ~10 ms.

**Keywords**: Throughput Accounting, DBR, order acceptance, product mix, TOC, bottleneck pricing

---

## 1. Introduction

### 1.1 Why Traditional Cost Accounting Misleads Decisions

**Standard cost accounting** allocates fixed overhead per unit (direct labor hours, machine depreciation), yielding a "unit cost". Under this framework, if an order's price < unit cost, it's judged "loss-making" and rejected.

However **Goldratt (1992) *The Haystack Syndrome*** points out the fundamental error:

> *"Fixed overhead won't actually cost more because of this order. If workers are already on payroll and machines already depreciating, this order using some of their time doesn't generate extra overhead."*

Concrete example: product standard cost $80 (material $30 + labor allocation $40 + overhead $10), selling price $75. Standard accounting: "loses $5", reject. TA analysis:

| Item | Standard Cost | Throughput Accounting |
|---|---|---|
| Revenue | $75 | $75 |
| TVC (truly variable cost) | n/a | $30 (material only) |
| Labor + overhead allocation | $50 | $0 (period fixed cost) |
| **"Profit"** | -$5 (reject) | $45 throughput (take it!) |

The accept-vs-reject difference = $45 × orders × 12 months = **substantial real cash flow**. Standard cost accounting **misjudges** → customers wrongly reject high-throughput orders, accumulating large losses yearly.

### 1.2 TOC Trilogy Integration

| Step | Source | Ouvoca Module |
|---|---|---|
| **IDENTIFY** constraint | Goldratt 1984 | v3.27 `identify_bottlenecks` |
| **EXPLOIT** constraint | Goldratt 1990 | v3.28 DBR + ranking |
| **SUBORDINATE** to exploit | Goldratt 1990 | v3.28 TA decision |
| **ELEVATE** constraint | Goldratt 1990 | v3.27 counterfactual + OT/alt |
| **REPEAT** | Goldratt 1990 | Continuous loop |

---

## 2. Methodology

### 2.1 Module 1: Throughput Accounting Three Variables

**Goldratt 1992** defines:

$$
\text{Throughput (T)} = \text{Revenue} - \text{Truly Variable Cost (TVC)}
$$

**TVC strict definition**: cost must vary **1:1 with product quantity**. Includes:

| Counts as TVC | Does NOT count (is OE) |
|---|---|
| ✅ Raw materials (BOM components × scrap factor) | ❌ Direct labor (workers' wages fixed) |
| ✅ Sales commission (% of revenue) | ❌ Machine depreciation |
| ✅ Outsourcing fees | ❌ Factory rent |
| ✅ Packaging consumables | ❌ Supervisor / management salaries |

**Operating Expense (OE)** = period fixed costs.

**Inventory (I)** = WIP + raw + finished (at TVC, **excluding overhead allocation**).

**Net Profit** = Σ T − OE (no per-unit fixed overhead calculation needed).

### 2.2 Module 2: Order Acceptance Decision (The Killer Decision)

For a single order $(p, q, P)$ (product, quantity, unit price):

$$
T_{\text{order}} = q \cdot (P - \text{TVC}_p(P))
$$

$$
\text{T per CCR min} = \frac{T_{\text{order}}}{q \cdot \text{bottleneck\_min}_p}
$$

**Goldratt 1990 §6 decision rule**:

```
If T_order < 0:        REJECT     (loss-making)
If bottleneck full:    REJECT     (cannot deliver)
If T/CCR-min < threshold:  NEGOTIATE  (raise price or outsource)
Otherwise:             ACCEPT
```

**Continuous Knapsack Optimality Argument**: under single binding constraint $\sum_i q_i \cdot a_i \leq C$, maximizing $\sum_i q_i \cdot t_i$ has LP relaxation optimum given by "sort by $t_i/a_i$ descending, fill capacity greedily". **Goldratt 1990 §6** proves this rule is optimal for single CCR. Multi-CCR degenerates to LP (future sprint with PuLP).

### 2.3 Module 3: Drum-Buffer-Rope Scheduling

**Schragenheim & Dettmer (2000) *Manufacturing at Warp Speed*** three elements:

| Element | Meaning | Calculation |
|---|---|---|
| 🥁 **Drum** | Bottleneck pacemaker | $\text{rate} = C_{\text{CCR}} / \text{run\_time}_{\text{CCR}}$ |
| 🛡 **Buffer** | Time buffer before bottleneck (anti-starvation) | $\text{buffer} = 3 \times \text{run\_time}_{\text{CCR}}$ |
| 🪢 **Rope** | Material release sync | $\text{release\_offset} = \text{buffer\_time}$ |

**Why buffer = 3× run-time**: **Schragenheim 2000 §4** empirically observed 3× balances "starvation risk" vs "WIP cost" in typical SMB environments. Theoretically:

- $1\times$: too small, slight upstream delay → bottleneck starves
- $3\times$: typical optimum, acceptable WIP cost
- $5\times+$: over-protection, WIP bloat

**Hopp & Spearman 1996 *Factory Physics* §10**: throughput is determined by bottleneck only; buffers at non-bottleneck stations are pure waste. Ouvoca's DBR module places buffer only before bottleneck.

### 2.4 Module 4: Pricing Curve (Sensitivity Extension)

For given (product, qty, base_price), scan discount levels (e.g., [0, 5%, 10%, 15%, 20%]), compute throughput, T/CCR-min, recommendation change per scenario.

**Sales use case**: when customer negotiates, sales can answer instantly "5% off OK", "10% needs supervisor", "15% reject".

---

## 3. Implementation

```
backend/app/services/throughput_accounting.py  (~450 lines)
├── TVCBreakdown (dataclass)
├── compute_product_tvc(db, product_id, commission, outsourcing)
├── OrderEvaluation (dataclass with throughput / t_per_ccr_min / recommendation)
├── compute_throughput_per_ccr(rev, tvc, bn_min) → float        ← Goldratt killer metric
├── evaluate_order_acceptance(...) → OrderEvaluation             ← main decision
├── PricingScenario / explore_pricing_curve(...)                 ← what-if discounts
├── DBRSchedule / compute_dbr_schedule(...)                      ← Schragenheim DBR
├── rank_orders_by_t_per_ccr(orders)                             ← Goldratt §6 ordering
└── select_best_product_mix(orders, total_capacity)              ← LP-optimal greedy
```

See [`THROUGHPUT_ACCOUNTING_DESIGN_ZH.md`](./THROUGHPUT_ACCOUNTING_DESIGN_ZH.md) §3 for the architecture integration diagram.

---

## 4. Validation

### 4.1 Seven Categories of Structural Invariants (21 tests, all pass)

1. **TVC composition** — Goldratt 1992 strict definition (3 tests)
2. **T/CCR-min monotonicity** — basic / zero / monotone in price (3 tests)
3. **Order decision logic** — reject infeasible / reject loss / accept / negotiate / no-CCR (5 tests)
4. **DBR Schragenheim 2000 rules** — 3× buffer / drum rate / degenerate / custom (4 tests)
5. **Knapsack optimality** — Goldratt §6 ranking / capacity respect / infeasible ordering (3 tests)
6. **Pricing curve** — monotonicity / recommendation flip (2 tests)
7. **DB integration** — BOM-derived TVC = 26.0 known answer (1 test)

### 4.2 Results

**21/21 tests pass**. Sprint cumulative: **412/412 smoke tests pass**.

---

## 5. Limitations and Future Work

| Topic | Why not | Future direction |
|---|---|---|
| **Multi-CCR binding** | Greedy no longer optimal; need LP/MIP | v3.29: integrate PuLP+CBC |
| **OE auto-derivation** | Currently customer-input | Integrate HR + Fixed Asset modules |
| **Dynamic buffer management** | Fixed 3× currently | Schragenheim 2000 §6 buffer management |
| **Stochastic lead-time in DBR** | Deterministic assumption | Hopp-Spearman §6 stochastic LT |
| **Multi-bottleneck schedule sync** | Single CCR assumption | DBR-B-D sequence |
| **Outsourcing detection in TVC** | Manual entry | Routing.is_outsourced flag |
| **GAAP/IFRS reconciliation** | TA ≠ standard cost accounting | Cost-accounting bridge layer |

### Edge Cases

1. **Product with no BOM**: material_cost = 0; customer must manually set outsourcing_cost or evaluation unreliable
2. **Product with no Routing**: bottleneck_minutes_required = 0 → always accept (from CCR perspective); may be limited by other constraints (v3.29 multi-constraint)
3. **commission_rate > 1**: physically impossible, not checked (trust input)
4. **Negative price**: not checked (trust input) — should not occur in practice

---

## 6. Legal Notice / 法律聲明

> ### ⚠️ Important: Legal Nature of Managerial Accounting Analysis
>
> This module produces **managerial accounting analysis** per **Goldratt (1992) Throughput Accounting** framework. It is **NOT a GAAP-compliant or IFRS-compliant financial statement**.
>
> ### 1. TA vs Standard Cost Accounting Distinction
>
> | Use case | TA | Standard cost accounting |
> |---|---|---|
> | External financial reports / tax filings | ❌ NOT applicable | ✅ Required |
> | Internal product-mix decisions | ✅ Applicable | ❌ Often misleads |
> | Order acceptance decisions | ✅ Applicable | ❌ Often wrongly rejects high-T orders |
>
> Customers **must NOT** use this module's throughput / TVC output directly as basis for financial reports or tax filings. External reports must follow applicable accounting standards + CPA review.
>
> ### 2. Order Acceptance Responsibility
>
> This module's `recommendation` (accept/reject/negotiate) is **an algorithm-computed suggestion based on input parameters**, NOT:
>
> - A **commitment** to quote/take an order
> - A **mandatory execution command** for sales
> - A **legally binding** price
>
> Before acting on recommendations, qualified business/finance/legal personnel must **manually review**:
>
> - Whether **TVC classification** matches your company's accounting policy (varies by industry)
> - Whether **commission_rate** matches sales contracts
> - Whether **outsourcing_cost** includes outsourcing-contract quality/delivery penalties
> - Whether **bottleneck_minutes_required** reflects **actual** situation (including setup, idle waiting, QC)
> - Whether **min_acceptable_t_per_min** threshold accounts for **opportunity cost** (future demand)
>
> ### 3. DBR Scheduling Responsibility
>
> Buffer = 3× run_time is Schragenheim 2000's **empirical value**, **NOT guaranteed** optimal in all environments:
>
> - High upstream lead-time variability environments → 3× may be insufficient (increase)
> - Low frequency, high product variety (high-mix-low-volume) environments → 3× may be excessive
> - Customers should observe actual starvation / WIP and **self-adjust** `buffer_multiplier`
>
> ### 4. Pricing Curve Is Not Antitrust Commitment
>
> Pricing scenarios **do NOT constitute**:
>
> - Legal advice on **discriminatory pricing strategy** toward specific customers
> - **Antitrust compliance** confirmation for market behavior
>
> National antitrust laws (e.g., Taiwan Fair Trade Act, U.S. Sherman Act) regulate pricing behavior. **Different prices for different customers** may raise compliance issues. Consult legal counsel.
>
> ### 5. Algorithm Limitations
>
> - **Single CCR assumption**: greedy algorithm is **not optimal** when multiple CCRs bind simultaneously; multi-bottleneck customers should use LP/MIP
> - **Deterministic assumption**: bottleneck_minutes_required, TVC assumed deterministic; lead-time variability, raw-material price volatility not modeled
> - **Continuous relaxation**: knapsack assumes order qty divisible; in practice 0-1 knapsack is NP-hard
> - **No strategic interaction**: customer bargaining, competitor pricing response not modeled (game theory scope)
>
> ### 6. Disclaimer Clause
>
> **To the maximum extent permitted by applicable law**, Ouvoca assumes no liability for:
>
> - **Revenue losses or customer-relationship damage** from wrong accept/reject based on this module's recommendation
> - **Financial misstatement** consequences from TVC/OE misclassification
> - **Production delay / inventory excess** from improper DBR buffer settings
> - **Antitrust disputes** from pricing-curve application
> - **Contractual / labor / competition law** disputes by third parties (customers, suppliers, sales, operators) acting on these recommendations
>
> ### 7. Cumulative Applicability of Predecessors
>
> This version overlays v3.25.10 + v3.26 + v3.27; **all disclaimers** in prerequisite documents §6 **apply cumulatively** here.
>
> ### Recommended Practice
>
> - Treat module output as "**business decision-support report**" — NOT "automatic accept/reject system"
> - Major orders (e.g., > 5% of annual revenue) must go through management review
> - Compare TVC settings vs actual costs quarterly; adjust parameters
> - Partner with CPA to build TA → standard-cost reconciliation bridge
> - Pricing-curve results should be considered alongside market conditions and competitive landscape

---

## 7. References

[1] **Goldratt, E. M.** (1984). *The Goal: A Process of Ongoing Improvement*. North River Press.

[2] **Goldratt, E. M., & Fox, R. E.** (1986). *The Race*. North River Press.

[3] **Goldratt, E. M.** (1990). *What Is This Thing Called Theory of Constraints*. North River Press.

[4] **Goldratt, E. M.** (1992). *The Haystack Syndrome: Sifting Information out of the Data Ocean*. North River Press.

[5] **Corbett, T.** (1998). *Throughput Accounting: TOC's Management Accounting System*. North River Press.

[6] **Schragenheim, E., & Dettmer, H. W.** (2000). *Manufacturing at Warp Speed*. CRC Press.

[7] **Schragenheim, E.** (2000). *Management Dilemmas: The Theory of Constraints Approach to Problem Identification*. CRC Press.

[8] **Hopp, W. J., & Spearman, M. L.** (1996, 2008 2nd ed.). *Factory Physics: Foundations of Manufacturing Management*. McGraw-Hill.

[9] **Mabin, V. J., & Balderstone, S. J.** (2003). The performance of the theory of constraints methodology. *IJOPM*, 23(6), 568-595.

[10] **Lawler, E. L., Lenstra, J. K., Rinnooy Kan, A. H. G., & Shmoys, D. B.** (1985). Sequencing and scheduling. In *Handbooks in OR & MS*, 4, 445-522.

[11] **Pinedo, M. L.** (2016). *Scheduling: Theory, Algorithms, and Systems* (5th ed.). Springer.

[12] **Cooper, R., & Kaplan, R. S.** (1988). Measure costs right: Make the right decisions. *HBR*, 66(5), 96-103.

[13] **Spearman, M. L., Woodruff, D. L., & Hopp, W. J.** (1990). CONWIP: A pull alternative to kanban. *Int. J. Prod. Res.*, 28(5), 879-894.

---

## 8. Changelog

| Version | Date | Change |
|---|---|---|
| v3.25.10 | 2026-05-20 | Uncapacitated MRP-II |
| v3.26 | 2026-05-20 | Capacity-aware MRP |
| v3.27 | 2026-05-20 | TOC IDENTIFY + Provenance |
| **v3.28** | **2026-05-20** | **This release**: TOC EXPLOIT + SUBORDINATE (TA + DBR + Order Acceptance) |
| Future v3.29+ | TBD | Multi-CCR LP/MIP / Dynamic buffer management |
| Future v3.30+ | TBD | LLM wrapper "should we take this order" Q&A |

---

**Last updated**: 2026-05-20 (v3.28)
**Authors**: Ouvoca engineering team (with IE/OR/Managerial Accounting/AI cross-domain academic methodology)
**Version**: 1.0
**Prerequisites**: v3.25.10 / v3.26 / v3.27 design docs
**Chinese version**: [`THROUGHPUT_ACCOUNTING_DESIGN_ZH.md`](./THROUGHPUT_ACCOUNTING_DESIGN_ZH.md)

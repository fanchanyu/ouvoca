# Explainable Planning + TOC Bottleneck Analysis Design — v3.27

> **Nature of this document**: Cross-domain methodology paper spanning **Operations Research / Algorithms / ERP / Explainable AI**, describing Ouvoca v3.27's **Explainable Planning** engine and **Goldratt (1984) Theory of Constraints (TOC)** bottleneck analysis module — design, implementation, and validation.

> 📘 Prerequisites: [`MRP_ALGORITHM_DESIGN_EN.md`](./MRP_ALGORITHM_DESIGN_EN.md) (v3.25.10) / [`MRP_CAPACITY_AWARE_DESIGN_EN.md`](./MRP_CAPACITY_AWARE_DESIGN_EN.md) (v3.26)

---

## Abstract

While Ouvoca v3.25.10 and v3.26 achieve operations-research rigor for MRP-II and CLSP heuristics respectively, their outputs remain **black-box** — customers cannot answer fundamental questions like "Why are we pulling so many M6 bolts next week?" This paper describes v3.27's three pillars: (i) **Provenance Graph** [Cheney, Chiticariu & Tan 2009] — tracing upstream causal chain for any planned order; (ii) **TOC Five-Focusing Steps** [Goldratt 1984, 1990] — automatic bottleneck identification from v3.26's CRP load with action suggestions; (iii) **OAT Sensitivity Analysis** [Saltelli et al. 2008] — marginal effect of +20% capacity. We argue these three modules form a **research-grade contribution at the intersection of IE/Algo/ERP/AI**, validated via 12 structural-invariant tests including Schragenheim-Ronen's (1990) 0.85 queueing threshold.

**Keywords**: Explainable AI, Theory of Constraints, data provenance, sensitivity analysis, ERP

---

## 1. Introduction

### 1.1 The Black-Box Problem

v3.25.10 + v3.26's MRP-II and capacity-aware MRP outputs:

| MrpItem (part='M6-BOLT', period='W22') |
|---|
| gross_requirement = 420 |
| net_requirement = 370 |
| planned_order_release = 370 |

But **no explanation** of why it's 420 and not some other number. Customers (especially non-IE SMB owners) see numbers without context, unable to assess:
- Which SO triggered this 420?
- Did a BOM change affect it?
- How full is our bottleneck work-center?
- If I added 20% capacity, how much better would this plan be?

**Vollmann et al. (2005) §11** explicitly states: *"Users will not trust plans they cannot understand."*

### 1.2 Lessons from Explainable AI

The ML community has well-developed interpretability research [Doshi-Velez & Kim 2017]:

- **LIME** [Ribeiro, Singh & Guestrin 2016, *KDD*] — local linear approximation
- **SHAP** [Lundberg & Lee 2017, *NIPS*] — Shapley value unified framework
- **Counterfactuals** [Wachter, Mittelstadt & Russell 2017] — counterfactual explanation

These target ML models, not IE/OR algorithms, but the **design philosophy** (trace causation, decompose contribution, what-if) applies directly to MRP black-boxes.

### 1.3 Cross-Domain Contribution

This version's innovation is **first integration of four domains' concepts** in ERP planning:

| Domain | Borrowed Concept | Application |
|---|---|---|
| **IE/OR** | TOC five-focusing-steps [Goldratt 1984]; Kingman formula [Schragenheim-Ronen 1990] | Automatic bottleneck identification at 0.85 threshold |
| **Algorithms** | Data provenance [Cheney et al. 2009]; DAG traversal | Causal chain tracing |
| **ERP** | Complete MPS-MRP-BOM-Routing data chain [Vollmann 2005] | Data foundation for tracing |
| **Explainable AI** | OAT sensitivity [Saltelli 2008]; counterfactuals [Wachter 2017] | What-if simulation |

---

## 2. Methodology

### 2.1 Module 1: Demand Provenance Graph

**Problem formulation**: given an `MrpItem` (part i, period t, planned_order_release q), find all upstream events causing q.

**Algorithm** (reverse DFS, demand upward tracing):

```
ALGORITHM: explain_planned_order(item)
1. Create root node from `item`
2. For each BOMItem b where b.part_id == item.part_id:
3.     parent_product ← b.product_id
4.     parent_item ← MrpItem in same MRP with part_no == product_no
5.     if parent_item exists:
6.         child_node ← recurse(parent_item, depth - 1)
7.         child_node.label += " because of making ..."
8.         root.children.append(child_node)
9. if no parents found:
10.    mps_node ← look up MPS entries for product equivalent
11.    root.children.append(mps_node)
12. return root
```

**Complexity**: $O(D \cdot F)$ where $D$ = max depth, $F$ = avg fan-in.

**Cycle protection**: `max_depth` (default 5) caps recursion, preventing infinite recursion from data anomalies.

### 2.2 Module 2: TOC Bottleneck Analysis (Goldratt)

**Five Focusing Steps** [Goldratt 1984]:

1. **IDENTIFY** the system's constraint
2. **EXPLOIT** the constraint
3. **SUBORDINATE** everything else to (2)
4. **ELEVATE** the constraint
5. **REPEAT** (if (4) succeeded, find new constraint)

**Origin of 0.85 threshold**: from **Kingman's formula** [Kingman 1961, *Math Proc Camb Phil Soc* 57], G/G/1 queue mean wait:

$$
W_q \approx \left(\frac{c_a^2 + c_s^2}{2}\right) \cdot \frac{\rho}{1 - \rho} \cdot \tau
$$

As $\rho \to 1$, $W_q \to \infty$. Practitioners (Schragenheim & Ronen 1990) find $\rho > 0.85$ triggers sharp $W_q$ increase, hence **0.85 as bottleneck-warning threshold**.

**Shadow Price**: from LP duality. Under binding constraint, marginal value of +1 unit RHS (capacity). For OR-novice SMB customers, we use minimal approximation: 1.0 when overloaded, 0.0 otherwise.

### 2.3 Module 3: Counterfactual Sensitivity (Saltelli)

**Method (OAT, one-factor-at-a-time)**:

1. Run baseline plan
2. Modify $C_{kt} \leftarrow \alpha \cdot C_{kt}$ for target WC
3. Re-run Dixon-Silver (other inputs fixed)
4. Compare: overload count / infeasible count / holding cost penalty delta

**Limitations** (Saltelli et al. 2008, §2.5):
- OAT misses **interactions**; simultaneous multi-factor effects ≠ sum of individuals
- For Global SA, need **Sobol indices** or **Morris elementary effects** (future sprint)

**Why still use OAT**:
1. SMB customers' intuitive questions are typically single-variable
2. Sobol indices need $N(d+2)$ simulations
3. Saltelli himself: *"OAT in well-understood systems can be informative"*

---

## 3. Implementation

```
backend/app/services/plan_explanation.py     (~500 lines)
├── ExplanationNode (dataclass + render_tree + to_dict)
├── explain_planned_order(db, mrp_item_id, max_depth=5)
├── _explain_via_mps(db, part_id, period, mrp_master_id)
├── BottleneckReport (dataclass)
├── BOTTLENECK_UTILIZATION_THRESHOLD = 0.85   ← Schragenheim-Ronen 1990
├── identify_bottlenecks_from_loads(loads, work_centers)
├── identify_bottlenecks(db, mps_id) → (reports, capacity_result)
├── CounterfactualResult (dataclass)
└── counterfactual_capacity_increase(db, mps_id, wc_id, multiplier=1.2)
```

See [`PLANNING_EXPLAINABILITY_DESIGN_ZH.md`](./PLANNING_EXPLAINABILITY_DESIGN_ZH.md) §3 for the architecture integration diagram.

---

## 4. Validation

### 4.1 Structural Invariant Tests (12 cases, all pass)

| Test | Validates |
|---|---|
| `explanation_node_to_dict_roundtrip` | Recursive serialization |
| `explanation_node_render_tree_shows_hierarchy` | ASCII tree depth indentation |
| `bottleneck_threshold_at_goldratt_0_85` | Threshold = Schragenheim-Ronen 1990 |
| `bottleneck_identification_basic` | Overloaded WC correctly flagged |
| `bottleneck_elevation_options_only_when_bottleneck` | No suggestions when not a bottleneck |
| `bottleneck_elevation_includes_alternate_group_when_set` | alternate_group in options |
| `bottleneck_shadow_price_positive_at_overload` | LP duality: binding ⟹ shadow > 0 |
| `bottleneck_threshold_boundary` | Strict > 0.85 (not ≥) |
| `bottleneck_sorted_by_peak_descending` | Reports sorted by peak_util desc |
| `explain_planned_order_traces_to_mps` | End-to-end: MRP → tree → MPS |
| `explanation_max_depth_clamps` | max_depth=0 → no recursion |
| `explain_nonexistent_mrp_item_returns_error_node` | Graceful return on missing |

### 4.2 Results

**12/12 tests pass** at v3.27 release. Sprint cumulative: **391/391 smoke tests pass**.

---

## 5. Limitations and Future Work

| Topic | Why not | Future direction |
|---|---|---|
| **SO/customer order tracing** | Currently starts from MPS; not connected to customer SO | v3.28: MPS_Entry ↔ SO_Item soft link |
| **Multi-factor what-if** | OAT limitation | Sobol indices (future research) |
| **Stochastic what-if** | Deterministic baseline | Monte Carlo simulation (v3.29 stochastic) |
| **TOC Drum-Buffer-Rope scheduling** | Only identification, no scheduling | DBR full impl (v3.28+) |
| **Throughput Accounting** | Throughput / OE / I ratios not quantified | Throughput Accounting module |
| **LLM-generated explanation** | Currently returns ASCII tree + dict | New explain tool in registry |
| **Provenance edge weighting** | Graph treats edges equally | Shapley values for OR (extension of Lundberg-Lee 1.5) |

---

## 6. Legal Notice / 法律聲明

> ### ⚠️ Important: Legal nature of explanation output
>
> This module produces **explanatory and advisory analysis** built on v3.25.10 + v3.26's IE/OR algorithm outputs. Its results constitute **decision-support information** only — NOT:
>
> 1. **Not a legal causation finding**: the "provenance graph" identifies **database lineage at query time**, NOT:
>    - Legal causal determinations (e.g., in litigation)
>    - Engineering-change responsibility attribution
>    - Supply-chain disruption liability attribution
>
> 2. **Not a production-decision command**: TOC bottleneck identification uses Goldratt's heuristic framework — outputs are **statistical signals**, NOT:
>    - Orders to immediately initiate overtime / outsourcing
>    - Requirements for operator scheduling
>    - Recommendations for capital expenditure (which requires dedicated financial review)
>
> 3. **Not a market-behavior guarantee**: counterfactual sensitivity uses OAT local sensitivity, assuming **other variables unchanged**. In practice:
>    - Adding capacity may affect supplier pricing, operator recruitment
>    - Multi-factor interactions are unmodeled (see Saltelli 2008 §2.5)
>    - Results provide "directional intuition" only — **must not be extrapolated to precise prediction**
>
> 4. **LLM wrapper warning** (if enabled in future): when explanations are rewritten by LLM:
>    - LLM may hallucinate: produce descriptions inconsistent with raw data
>    - LLM may over-simplify: lose important nuance
>    - For LLM-rewritten content, **customers should always defer to this module's raw data** (`to_dict()` / `render_tree()`)
>
> 5. **Algorithmic limitations**:
>    - **Provenance**: based on database snapshot; no time-travel queries
>    - **TOC**: 0.85 threshold from G/G/1 queue assumption; may differ for multi-server / batch / priority cases
>    - **OAT**: doesn't capture factor interactions [Saltelli 2008]
>
> 6. **Disclaimer**: **to the maximum extent permitted by applicable law**, Ouvoca assumes no responsibility for:
>    - **Erroneous accusations** against suppliers/customers/employees based on this explanation
>    - **Capital investment errors** due to TOC bottleneck mis-identification
>    - **Planning inaccuracy** from counterfactual deviating from reality
>    - **LLM rewrite hallucination** consequences
>    - **Labor/contractual disputes** with third parties acting on these explanations
>
> 7. **Cumulative applicability of predecessor disclaimers**: this version overlays v3.25.10 + v3.26; **all disclaimers** in [`MRP_ALGORITHM_DESIGN_EN.md`](./MRP_ALGORITHM_DESIGN_EN.md) §6 and [`MRP_CAPACITY_AWARE_DESIGN_EN.md`](./MRP_CAPACITY_AWARE_DESIGN_EN.md) §6 **apply cumulatively** here.
>
> ### Recommended practice
>
> - Treat provenance trees as "quick data-lookup tools" — not "responsibility reports"
> - Have plant manager / production controller review TOC suggestions before overtime / outsourcing / upgrade decisions
> - Treat counterfactual results as "directional intuition" — not "precise ROI reports"
> - Present LLM-rewritten natural-language explanations alongside raw structured data, allowing cross-verification

---

## 7. References

[1] **Goldratt, E. M.** (1984). *The Goal: A Process of Ongoing Improvement*. North River Press. — TOC founding work

[2] **Goldratt, E. M.** (1990). *What Is This Thing Called Theory of Constraints*. North River Press.

[3] **Cheney, J., Chiticariu, L., & Tan, W.-C.** (2009). Provenance in databases: Why, how, and where. *Foundations and Trends in Databases*, 1(4), 379-474.

[4] **Doshi-Velez, F., & Kim, B.** (2017). Towards a rigorous science of interpretable machine learning. *arXiv:1702.08608*.

[5] **Lundberg, S. M., & Lee, S.-I.** (2017). A unified approach to interpreting model predictions. *NIPS 30*.

[6] **Ribeiro, M. T., Singh, S., & Guestrin, C.** (2016). "Why Should I Trust You?": Explaining the predictions of any classifier. *KDD '16*.

[7] **Wachter, S., Mittelstadt, B., & Russell, C.** (2017). Counterfactual explanations without opening the black box. *Harv. J. L. & Tech.*, 31, 841.

[8] **Saltelli, A. et al.** (2008). *Global Sensitivity Analysis: The Primer*. Wiley.

[9] **Kingman, J. F. C.** (1961). The single server queue in heavy traffic. *Math. Proc. Cambridge Phil. Soc.*, 57(4), 902-904.

[10] **Schragenheim, E., & Ronen, B.** (1990). Drum-buffer-rope shop floor control. *Production and Inventory Management Journal*, 31(3), 18-22.

[11] **Mabin, V. J., & Balderstone, S. J.** (2003). The performance of the theory of constraints methodology. *IJOPM*, 23(6), 568-595.

[12] **Caruana, R. et al.** (2015). Intelligible models for healthcare. *KDD '15*.

[13] **Vollmann, T. E., Berry, W. L., Whybark, D. C., & Jacobs, F. R.** (2005). *Manufacturing Planning and Control for Supply Chain Management* (5th ed.). McGraw-Hill.

[14] **Pinedo, M. L.** (2016). *Scheduling: Theory, Algorithms, and Systems* (5th ed.). Springer.

---

## 8. Changelog

| Version | Date | Change |
|---|---|---|
| v3.25.10 | 2026-05-20 | Uncapacitated MRP-II |
| v3.26 | 2026-05-20 | Capacity-aware MRP (Dixon-Silver) |
| **v3.27** | **2026-05-20** | **This release**: Explainable Planning + TOC + OAT |
| Future v3.28+ | TBD | SO tracing + LLM wrapper + DBR |
| Future v3.29+ | TBD | Sobol global SA + Monte Carlo |

---

**Last updated**: 2026-05-20 (v3.27)
**Authors**: Ouvoca engineering team (with IE/OR/AI cross-domain academic methodology)
**Version**: 1.0
**Chinese version**: [`PLANNING_EXPLAINABILITY_DESIGN_ZH.md`](./PLANNING_EXPLAINABILITY_DESIGN_ZH.md)

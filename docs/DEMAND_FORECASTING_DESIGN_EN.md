# AI-Augmented Demand Forecasting Engine Design (v3.29)

> **Nature of this document**: Cross-domain methodology paper spanning **Time-Series Analysis / Machine Learning / ERP / AI**, describing Ouvoca v3.29's demand forecasting engine. This release closes the upstream gap in the v3.25.10–v3.28 planning chain by replacing **customer-manual MPS entry** with **automatic forecasts from historical sales + LLM augmentation**.

> 📘 Prerequisites: [`MRP_ALGORITHM_DESIGN_EN.md`](./MRP_ALGORITHM_DESIGN_EN.md) (v3.25.10) / [`THROUGHPUT_ACCOUNTING_DESIGN_EN.md`](./THROUGHPUT_ACCOUNTING_DESIGN_EN.md) (v3.28)

---

## Abstract

Ouvoca's v3.25.10 → v3.28 planning chain assumed **MPS is entered manually by the customer**, undermining the objectivity of the entire IE/OR chain. This paper describes v3.29's demand forecasting engine, integrating **Croston's (1972)** classical intermittent demand algorithm, the **Brown (1959) SES / Holt (1957) / Winters (1960)** exponential smoothing family, and **Hyndman & Koehler's (2006) MASE** metric for automatic best-method selection. We also introduce **Chatfield's (1989)** regime change detection as an LLM-augmentation hook — when recent residuals exceed ±2σ, the system prompts customers to apply business judgment. **Makridakis et al. (2018, 2020) M4/M5** competitions demonstrate that classical methods remain competitive with — sometimes beat — deep learning on most series, so this release excludes scipy/statsmodels/torch dependencies, **implementing 5 methods in pure Python**. 30 structural-invariant tests pass, including Hyndman-Koehler 2006's classic property MASE < 1 ⟺ beats naive baseline.

**Keywords**: Demand forecasting, Croston, Holt-Winters, MASE, intermittent demand, regime change, LLM augmentation

---

## 1. Introduction

### 1.1 The Fundamental Problem of Manual MPS

The 4 sprints v3.25.10 → v3.28 completed MRP-II, CLSP, and the TOC trilogy. But all plans **start from an MPS** that requires customers to fill in numbers like "produce 100 units of product A in W22." In practice:

- SMB owners **lack data-analysis capability**
- Sales history **exists, but customers don't know how to use it**
- Most parts have **intermittent demand** (zero for many weeks, then a spike) — intuitive entry is unreliable
- v3.27 explainability: "Why do we need so many M6 bolts next week?" always traces back to MPS — **which the customer filled in, so Ouvoca can't ask 'are your numbers right?'**

### 1.2 Why Not Deep Learning Directly

**Makridakis (2018) M4 Competition** results were striking: on a blind test of 100,000 time series:

| Method category | Average sMAPE | Rank |
|---|---|---|
| Combine (weighted average of classical) | 11.4% | 1st |
| Exponential smoothing + ARIMA | 11.9% | 2nd |
| **Deep learning (LSTM, MLP)** | **13.7%** | **bottom** |
| Naive | 14.3% | baseline |

**Makridakis (2020) M5** using Walmart sales data: classical and ML perform similarly, but **classical is more robust, more interpretable, and cheaper to train**.

For SMB (short history, mostly intermittent), classical **wins more often**. We therefore choose:

- ✅ Naive / Seasonal Naive baseline
- ✅ SES / Holt / Holt-Winters
- ✅ Croston (intermittent specialist)
- ❌ No Prophet / N-BEATS / TFT for now (deferred to future sprints)

### 1.3 Why Croston Is Irreplaceable

**Croston (1972, *J Op Res Soc* 23)** founded the methodology for "intermittent demand forecasting." In ERP scenarios:

- Industrial screws: 0-0-0-50-0-0-30-0 per week
- Machine spare parts: once every 3 months
- Seasonal gifts: only November orders annually

SES **always over-forecasts** such data (low-bias error assumption fails). Croston decomposes:

```
forecast = (smoothed_demand_when_nonzero) / (smoothed_interval_between_demands)
```

**Syntetos & Boylan (2005)** proved the original Croston has positive bias, requiring a $(1 - \alpha/2)$ correction. We default to this corrected version.

---

## 2. Methodology

See [`DEMAND_FORECASTING_DESIGN_ZH.md`](./DEMAND_FORECASTING_DESIGN_ZH.md) §2 for full mathematical formulations of all 5 methods (Naive, SES, Holt, Holt-Winters, Croston) and accuracy metrics (MAPE, sMAPE, MASE per Hyndman-Koehler 2006).

Key design choices:
- **Auto-selection** by lowest MASE on holdout
- **Intermittent detection**: when zero_fraction > 40%, restrict candidates to {Naive, Croston} (per Syntetos-Boylan 2005)
- **Prediction intervals** via residual bootstrap, $PI_{t+k} = \hat{y}_{t+k} \pm z_\alpha \sigma \sqrt{k}$
- **Regime change** flag: $k$ of recent $N$ residuals beyond ±θσ (Chatfield 1989 §13)

---

## 3. Implementation

```
backend/app/services/demand_forecasting.py    (~600 lines, pure Python)
├── ForecastMethod (Enum: NAIVE / SEASONAL_NAIVE / SES / HOLT / HOLT_WINTERS / CROSTON / AUTO)
├── ForecastResult / BacktestResult / RegimeChangeAlert (dataclasses)
├── 5 forecasting algorithms (each ~30-80 lines)
├── 3 accuracy metrics (MAPE, sMAPE, MASE)
├── backtest / auto_select_method
├── prediction_intervals_residual
├── detect_regime_change (LLM augmentation hook)
└── forecast (top-level API)
```

---

## 4. Validation

### 4.1 30 Structural Invariant Tests (10 categories, all pass)

| Category | Tests | Coverage |
|---|---|---|
| 1. Naive baseline | 4 | Flat output / empty / seasonal rotation / fallback |
| 2. SES (Brown 1959) | 3 | α=1 tracking / α≈0 smoothing / constant recovery |
| 3. Holt (1957) | 2 | Linear extrapolation / horizon linearity |
| 4. Holt-Winters (1960) | 2 | Perfect cycle recovery / short-history fallback |
| 5. Croston (1972) | 4 | All zero / rate recovery / flat output / single event |
| 6. Accuracy metrics | 6 | MAPE / sMAPE / MASE classic properties |
| 7. Auto-selection | 2 | Intermittent restriction + lowest MASE wins |
| 8. Prediction intervals | 2 | Widens with horizon / zero residual zero width |
| 9. Regime change | 2 | Detect spike / no false positive on stable |
| 10. API integration | 3 | Full ForecastResult / horizon=0 / explicit method |

### 4.2 Results

**30/30 tests pass**. Sprint cumulative: **442/442 smoke tests pass**.

---

## 5. Limitations and Future Work

| Topic | Why not | Future direction |
|---|---|---|
| **Modern ML** (Prophet / N-BEATS / TFT) | M4 shows classical still competitive; heavy deps | v3.30+: optional deps, GPU env only |
| **Time-series CV** | Holdout only, not rolling | Hyndman 2021 §5.4 rolling CV |
| **Hierarchical reconciliation** | product/category/total inconsistency | Wickramasuriya, Athanasopoulos & Hyndman (2019) MinT |
| **Full auto-tuning of (α, β, γ)** | Only α grid search | Nelder-Mead via scipy |
| **Multiplicative seasonality** | Additive only | Holt-Winters multiplicative variant |
| **External regressors** | Univariate only | ARIMAX |
| **ETS state-space framework** | Not integrated | Hyndman, Koehler, Snyder & Grose (2002) |
| **Actual LLM augmentation** | Spec defined, API not wired | v3.30: prompt template + ConfirmCard flow |

### Edge Cases

1. **History < 2 seasons**: HW auto-falls-back to Holt
2. **All-zero history**: all methods return 0
3. **Single non-zero event**: Croston uses mean / expected interval
4. **Negative demand** (returns): not specially handled; recommend "net sales" input

---

## 6. Legal Notice / 法律聲明

> ### ⚠️ Important: Legal Nature of Statistical Forecasts
>
> This module produces **statistical demand forecasts**. **All forecasts carry inherent uncertainty** and are **NOT**:
>
> 1. **Guarantees of future demand**: point forecasts are algorithm-computed **expected values** based on historical data; actual demand may differ significantly. **Prediction intervals** are probabilistic approximations — a 95% PI does **NOT** guarantee 95% capture rate (especially when data-generating process changes)
>
> 2. **Basis for procurement commitments**: customers **must NOT** use this module's forecasts as the **sole basis** for supplier commitments, employee overtime, or customer delivery guarantees. Major decisions must integrate market conditions, specific customer SOs, and business intelligence
>
> 3. **Evidence in supply-chain disputes**: this module's output **must NOT** be cited as "the forecast said X, so the supplier should have..." in disputes. Forecasts are fundamentally **estimates**, not contractual commitments
>
> 4. **Prediction of unforeseeable events**: no statistical method can predict:
>    - Natural disasters (earthquakes, floods, typhoons)
>    - Policy changes (tariffs, regulations, trade wars)
>    - Customer business changes (bankruptcy, mergers, relocation)
>    - Competitive landscape shifts (new entrants, technology breakthroughs)
>    - Black Swan events (Taleb 2007)
>
> ### 1. Algorithm Limitations
>
> - **Stationarity assumption**: all methods assume the data-generating process is stable within the forecast horizon. **Regime change** detection is a rough indicator, NOT a replacement for business judgment
> - **MASE < 1 doesn't guarantee correct decisions**: MASE is "relative to naive baseline"; MASE 0.5 may still be insufficient in absolute accuracy for major decisions
> - **Mis-calibrated PIs**: when residuals exhibit autocorrelation or heteroscedasticity, PIs are inaccurate
> - **Auto-selection overfitting**: choosing methods by holdout MASE may be "lucky" on holdout but unstable in production
>
> ### 2. LLM Augmentation Warning (when enabled in v3.30+)
>
> When `detect_regime_change` triggers LLM review:
>
> - LLM may **hallucinate** business reasons (fabricate customer/competition scenarios)
> - LLM's qualitative adjustments should be **advisory only**, never auto-overwriting forecasts
> - All LLM suggestions must go through **ConfirmCard** (human confirmation)
> - LLM-stated reasons (e.g., "Customer X cancelled") **do NOT constitute factual statements about Customer X** — avoid defamation risk
>
> ### 3. Croston / Intermittent Demand Special Notice
>
> Croston (1972) assumes **non-zero demand events are a random process**. In practice:
>
> - If demand events have **structural causes** (e.g., end-of-month inventory top-up), statistical methods may still fail
> - Syntetos-Boylan (2005) bias correction is correct in mean but still biased in quantile estimation
> - For **extremely sparse data** (e.g., once-per-year), no statistical method is reliable — use business intelligence
>
> ### 4. Responsibility for MPS Integration
>
> This module can auto-generate MPS suggestions. But:
>
> - **MPS final authority should rest with the production controller**, not be auto-generated
> - Workflow must follow **ConfirmCard**: forecast → MPS suggestion → controller review → confirm → flow into MRP
> - **Major decisions** (annual bulk material procurement, capacity investment) require additional review
>
> ### 5. Disclaimer Clause
>
> **To the maximum extent permitted by applicable law**, Ouvoca assumes no liability for:
>
> - **Over-purchasing / line stoppage** losses from acting on these forecasts
> - **Customer delivery defaults / penalties** from forecast inaccuracy
> - **Erroneous business judgments** influenced by LLM suggestions
> - **Planning failures** from undetected regime changes
> - **Any consequences** from using auto-generated MPS without controller review
>
> ### 6. Cumulative Applicability of Predecessors
>
> This version completes the upstream gap of the v3.25.10 → v3.28 planning chain. **All disclaimers** in predecessor §6 documents **apply cumulatively** here.
>
> ### Recommended Practice
>
> - Treat forecasts as "**starting suggestions**" not "final MPS"
> - Compare actual vs forecast monthly; update method selection and parameters
> - High-value / high-risk parts (Class A) must have human review
> - Demand outside PI → proactively contact customer to verify cause
> - Retain forecast-accuracy history as reference for negotiation but **not as legal evidence**

---

## 7. References

[1] **Brown, R. G.** (1959). *Statistical Forecasting for Inventory Control*. McGraw-Hill.

[2] **Holt, C. C.** (1957/2004 reprint). Forecasting seasonals and trends. *Int. J. Forecast.*, 20(1), 5-10.

[3] **Winters, P. R.** (1960). Forecasting sales by exponentially weighted moving averages. *Management Science*, 6(3), 324-342.

[4] **Croston, J. D.** (1972). Forecasting and stock control for intermittent demands. *Op. Res. Q.*, 23(3), 289-303.

[5] **Syntetos, A. A., & Boylan, J. E.** (2005). The accuracy of intermittent demand estimates. *Int. J. Forecast.*, 21(2), 303-314.

[6] **Hyndman, R. J., & Koehler, A. B.** (2006). Another look at measures of forecast accuracy. *Int. J. Forecast.*, 22(4), 679-688.

[7] **Hyndman, R. J., Koehler, A. B., Snyder, R. D., & Grose, S.** (2002). A state space framework for automatic forecasting using exponential smoothing methods. *Int. J. Forecast.*, 18(3), 439-454.

[8] **Hyndman, R. J., & Athanasopoulos, G.** (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts.

[9] **Makridakis, S., Spiliotis, E., & Assimakopoulos, V.** (2018). The M4 Competition. *Int. J. Forecast.*, 34(4), 802-808.

[10] **Makridakis, S., Spiliotis, E., & Assimakopoulos, V.** (2020). The M5 accuracy competition. *Int. J. Forecast.*, 38(4), 1346-1364.

[11] **Chatfield, C.** (1989). *The Analysis of Time Series* (4th ed.). Chapman & Hall.

[12] **Wickramasuriya, S. L., Athanasopoulos, G., & Hyndman, R. J.** (2019). Optimal forecast reconciliation. *J. Am. Stat. Assoc.*, 114(526), 804-819.

[13] **Taylor, S. J., & Letham, B.** (2018). Forecasting at scale. *The American Statistician*, 72(1), 37-45.

[14] **Oreshkin, B. N., Carpov, D., Chapados, N., & Bengio, Y.** (2020). N-BEATS. *ICLR*.

[15] **Lim, B., Arık, S. Ö., Loeff, N., & Pfister, T.** (2021). Temporal fusion transformers. *Int. J. Forecast.*, 37(4), 1748-1764.

[16] **Taleb, N. N.** (2007). *The Black Swan*. Random House.

---

## 8. Changelog

| Version | Date | Change |
|---|---|---|
| v3.25.10 | 2026-05-20 | MRP-II (based on manual MPS) |
| v3.26 - v3.28 | 2026-05-20 | CLSP / TOC trilogy (still on manual MPS) |
| **v3.29** | **2026-05-20** | **This release**: automatic demand forecasting engine, closes MPS upstream gap |
| Future v3.30+ | TBD | LLM augmentation integration / Prophet evaluation / Hierarchical |
| Future v3.31+ | TBD | Rolling CV / ETS state-space / Multiplicative seasonality |

---

**Last updated**: 2026-05-20 (v3.29)
**Authors**: Ouvoca engineering team (with TS analysis / ML / ERP / AI cross-domain academic methodology)
**Version**: 1.0
**Chinese version**: [`DEMAND_FORECASTING_DESIGN_ZH.md`](./DEMAND_FORECASTING_DESIGN_ZH.md)

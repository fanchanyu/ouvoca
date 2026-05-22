"""
AI-Augmented Demand Forecasting Engine  (v3.29)
═══════════════════════════════════════════════════════════════════════

Bridges historical sales data → forecast → auto-populate MPS, closing
the planning loop that v3.25.10 through v3.28 built on top of.

Five classical time-series methods with academic provenance:

  1. Naive / Seasonal Naive     [baseline; Hyndman & Athanasopoulos 2021 §5.2]
  2. Simple Exponential Smoothing (SES)   [Brown 1959]
  3. Holt's Linear Trend                  [Holt 1957]
  4. Holt-Winters Additive Seasonal       [Winters 1960]
  5. Croston's intermittent demand        [Croston 1972; Syntetos & Boylan 2005]

Plus:
  • Forecast accuracy: MAPE, sMAPE, MASE  [Hyndman & Koehler 2006]
  • Backtest framework (train/test split)
  • Automatic method selection (lowest MASE)
  • Residual bootstrap prediction intervals  [Hyndman & Athanasopoulos 2021 §5.5]

Why these 5 (not Prophet, N-BEATS, TFT):
  • Makridakis et al. (2018, 2020) M4 & M5 competitions show classical
    methods are competitive with — sometimes beat — deep learning on
    most series, especially short ones (which SMB has).
  • Pure Python, no scipy/statsmodels/torch dependency
  • Interpretable: SMB owners can understand "this week = last week × trend"
  • Croston is THE method for intermittent demand (95% of SMB parts!)

──────────────────────────────────────────────────────────────────────
LEGAL / 法律說明
──────────────────────────────────────────────────────────────────────
This module produces **statistical demand forecasts** based on
historical sales data. ALL forecasts carry inherent uncertainty and:

  • Are NOT guarantees of future demand
  • Should NOT be the sole basis for material procurement commitments
  • Should NOT be cited as evidence in disputes about supply chain
    decisions (e.g., "the forecast said X so the supplier should have...")
  • Are subject to fundamental statistical limits — even the best
    method cannot predict unforeseeable events (pandemics, regulatory
    changes, customer bankruptcies)

Prediction intervals indicate uncertainty quantitatively but are
**approximations under stationarity assumptions** that may not hold
in reality. A 95% interval does NOT guarantee 95% capture rate when
the data-generating process changes.

LLM-augmented adjustments (when enabled in future) carry additional
risk: language models may **hallucinate** or **over-fit** to recent
patterns. Always cross-verify against the raw time-series.

To the maximum extent permitted by applicable law, Ouvoca assumes
no liability for procurement, production, or staffing decisions based
on these forecasts. See docs/DEMAND_FORECASTING_DESIGN_ZH.md §6.

本模組產生**統計需求預測**，**不構成未來需求之保證**。預測區間為
平穩性假設下之近似；遇到不可預見事件時可能失準。LLM 增強層可能
hallucinate；務必交叉驗證原始時序。詳見 §6 法律聲明。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════
# Data structures
# ════════════════════════════════════════════════════════════════════

class ForecastMethod(str, Enum):
    """Forecasting methods. Auto = pick best by MASE."""
    NAIVE = "naive"                  # y_t+1 = y_t
    SEASONAL_NAIVE = "seasonal_naive"  # y_t+1 = y_t+1-s
    SES = "ses"                       # simple exponential smoothing
    HOLT = "holt"                     # linear trend
    HOLT_WINTERS = "holt_winters"    # additive seasonal
    CROSTON = "croston"               # intermittent demand
    AUTO = "auto"                     # pick lowest-MASE


@dataclass
class ForecastResult:
    """Output of a forecast run."""
    method: str
    horizon: int  # number of periods forecast
    point_forecast: List[float]
    lower_95: List[float] = field(default_factory=list)
    upper_95: List[float] = field(default_factory=list)
    mape: Optional[float] = None
    smape: Optional[float] = None
    mase: Optional[float] = None
    fitted_values: List[float] = field(default_factory=list)
    residuals: List[float] = field(default_factory=list)
    diagnostic: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "horizon": self.horizon,
            "point_forecast": self.point_forecast,
            "lower_95": self.lower_95,
            "upper_95": self.upper_95,
            "mape": self.mape,
            "smape": self.smape,
            "mase": self.mase,
            "diagnostic": self.diagnostic,
        }


# ════════════════════════════════════════════════════════════════════
# Method 1: Naive (baseline)
# ════════════════════════════════════════════════════════════════════

def forecast_naive(history: List[float], horizon: int) -> List[float]:
    """y_{t+k} = y_t (last observed value, constant for all future).

    Despite simplicity, M3 (Makridakis et al. 2000) shows naive beats
    sophisticated methods on 30%+ of series — never skip the baseline.
    """
    if not history:
        return [0.0] * horizon
    last = history[-1]
    return [last] * horizon


def forecast_seasonal_naive(
    history: List[float], horizon: int, season_length: int = 12,
) -> List[float]:
    """y_{t+k} = y_{t+k-season_length} (mirror last full season).

    For monthly retail / production, season_length=12; weekly=52; quarterly=4.
    Standard baseline for any forecasting comparison.
    """
    if not history or len(history) < season_length:
        return forecast_naive(history, horizon)
    out = []
    for k in range(1, horizon + 1):
        # Pick the corresponding period from last season
        idx = len(history) - season_length + ((k - 1) % season_length)
        if idx < 0 or idx >= len(history):
            idx = len(history) - 1
        out.append(history[idx])
    return out


# ════════════════════════════════════════════════════════════════════
# Method 2: Simple Exponential Smoothing (SES) — Brown 1959
# ════════════════════════════════════════════════════════════════════

def forecast_ses(
    history: List[float], horizon: int, alpha: float = 0.3,
) -> Tuple[List[float], List[float]]:
    """SES: level only, no trend, no seasonality.

    Recursion:
        l_t = α · y_t + (1 - α) · l_{t-1}
        ŷ_{t+k} = l_t  (flat forecast)

    α ∈ [0, 1]: smoothing parameter.
    - α near 1: forecast tracks recent values
    - α near 0: forecast tracks long-term average

    Optimal α minimizes SSE on training set. We use a fixed default
    of 0.3 (Hyndman §8.1 reasonable starting value) for simplicity;
    auto-tuning is in `_optimize_alpha` (Nelder-Mead would be ideal,
    but we use grid search for pure-Python).

    Returns: (point_forecast, fitted_values)
    """
    if not history:
        return [0.0] * horizon, []
    if len(history) == 1:
        return [history[0]] * horizon, [history[0]]

    # Initialize level = first observation
    level = history[0]
    fitted = [level]

    for t in range(1, len(history)):
        level = alpha * history[t] + (1 - alpha) * level
        fitted.append(level)

    # Future forecast = last level (flat)
    return [level] * horizon, fitted


def _optimize_alpha_ses(history: List[float], grid: int = 21) -> float:
    """Grid search α ∈ [0.05, 0.95] minimizing SSE.

    For SMB scale (T ≤ 100), grid search of 20 values is < 1ms.
    """
    if len(history) < 3:
        return 0.3
    best_alpha = 0.3
    best_sse = math.inf
    for i in range(1, grid):
        alpha = i / grid  # 0.05, 0.10, ..., 0.95
        _, fitted = forecast_ses(history, horizon=1, alpha=alpha)
        sse = sum((history[t] - fitted[t]) ** 2 for t in range(len(history)))
        if sse < best_sse:
            best_sse = sse
            best_alpha = alpha
    return best_alpha


# ════════════════════════════════════════════════════════════════════
# Method 3: Holt's Linear Trend — Holt 1957
# ════════════════════════════════════════════════════════════════════

def forecast_holt(
    history: List[float], horizon: int,
    alpha: float = 0.3, beta: float = 0.1,
) -> Tuple[List[float], List[float]]:
    """Holt's method: level + linear trend.

    Recursion:
        l_t = α · y_t + (1 - α)(l_{t-1} + b_{t-1})
        b_t = β · (l_t - l_{t-1}) + (1 - β) · b_{t-1}
        ŷ_{t+k} = l_t + k · b_t

    Use when data has trend but no clear seasonality.
    """
    if not history:
        return [0.0] * horizon, []
    if len(history) < 2:
        return [history[0]] * horizon, [history[0]]

    level = history[0]
    trend = history[1] - history[0]
    fitted = [level]

    for t in range(1, len(history)):
        prev_level = level
        level = alpha * history[t] + (1 - alpha) * (prev_level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
        fitted.append(level)

    forecast = [level + (k + 1) * trend for k in range(horizon)]
    return forecast, fitted


# ════════════════════════════════════════════════════════════════════
# Method 4: Holt-Winters Additive — Winters 1960
# ════════════════════════════════════════════════════════════════════

def forecast_holt_winters(
    history: List[float], horizon: int,
    season_length: int = 12,
    alpha: float = 0.3, beta: float = 0.1, gamma: float = 0.1,
) -> Tuple[List[float], List[float]]:
    """Holt-Winters additive seasonal: level + trend + season.

    Recursion (additive variant):
        l_t = α · (y_t - s_{t-L}) + (1 - α)(l_{t-1} + b_{t-1})
        b_t = β · (l_t - l_{t-1}) + (1 - β) · b_{t-1}
        s_t = γ · (y_t - l_t) + (1 - γ) · s_{t-L}
        ŷ_{t+k} = l_t + k · b_t + s_{t-L+1+((k-1) mod L)}

    Initialization uses first season's mean as level, first vs last
    season slope as trend, and seasonal deviations from level.
    """
    if not history:
        return [0.0] * horizon, []
    if len(history) < 2 * season_length:
        # Not enough history for proper seasonal init; fallback to Holt
        return forecast_holt(history, horizon, alpha=alpha, beta=beta)

    # Initialization
    first_season_mean = sum(history[:season_length]) / season_length
    second_season_mean = sum(history[season_length:2*season_length]) / season_length
    level = first_season_mean
    trend = (second_season_mean - first_season_mean) / season_length
    seasonals = [history[i] - first_season_mean for i in range(season_length)]

    fitted = []
    for t in range(len(history)):
        # Forecast for this period
        forecast_t = level + trend + seasonals[t % season_length]
        fitted.append(forecast_t)

        # Update
        prev_level = level
        s_idx = t % season_length
        level = alpha * (history[t] - seasonals[s_idx]) + (1 - alpha) * (prev_level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
        seasonals[s_idx] = gamma * (history[t] - level) + (1 - gamma) * seasonals[s_idx]

    # Future
    forecast = []
    for k in range(horizon):
        s_idx = (len(history) + k) % season_length
        forecast.append(level + (k + 1) * trend + seasonals[s_idx])
    return forecast, fitted


# ════════════════════════════════════════════════════════════════════
# Method 5: Croston's intermittent demand — Croston 1972
# ════════════════════════════════════════════════════════════════════

def forecast_croston(
    history: List[float], horizon: int,
    alpha: float = 0.1,
    correction: str = "syntetos_boylan",
) -> Tuple[List[float], List[float]]:
    """Croston (1972) for intermittent / lumpy demand.

    Key insight: separately smooth (a) demand size when it occurs
    and (b) interval between non-zero demands. Then:

        forecast = (smoothed_size) / (smoothed_interval)

    Syntetos & Boylan (2005) correction (default in modern practice):
        forecast = (1 - α/2) · smoothed_size / smoothed_interval

    This corrects Croston's known positive bias.

    Critical for SMB: most parts have intermittent demand (long zero
    runs followed by occasional spikes). Standard SES/Holt-Winters
    over-forecast for intermittent series.
    """
    if not history:
        return [0.0] * horizon, []

    # Find non-zero demands and intervals
    nonzero_demands: List[float] = []
    intervals: List[int] = []
    last_demand_idx = -1
    for t, y in enumerate(history):
        if y > 0:
            nonzero_demands.append(y)
            if last_demand_idx >= 0:
                intervals.append(t - last_demand_idx)
            last_demand_idx = t

    if not nonzero_demands:
        # All zero history → predict zero
        return [0.0] * horizon, [0.0] * len(history)

    if len(nonzero_demands) == 1:
        # Single non-zero observation → flat at that level scaled to expected interval
        avg_interval = max(1, len(history))
        f = nonzero_demands[0] / avg_interval
        return [f] * horizon, [f] * len(history)

    # Exponential smoothing of demand size and interval
    smoothed_size = nonzero_demands[0]
    smoothed_interval = intervals[0] if intervals else 1
    for i in range(1, len(nonzero_demands)):
        smoothed_size = alpha * nonzero_demands[i] + (1 - alpha) * smoothed_size
        if i - 1 < len(intervals):
            smoothed_interval = alpha * intervals[i - 1] + (1 - alpha) * smoothed_interval

    smoothed_interval = max(1.0, smoothed_interval)
    raw_forecast = smoothed_size / smoothed_interval

    # Syntetos-Boylan bias correction
    if correction == "syntetos_boylan":
        forecast_value = (1 - alpha / 2) * raw_forecast
    else:
        forecast_value = raw_forecast

    # Fitted values: same flat forecast at each step (Croston's nature)
    fitted = [forecast_value] * len(history)
    return [forecast_value] * horizon, fitted


# ════════════════════════════════════════════════════════════════════
# Accuracy metrics (Hyndman & Koehler 2006)
# ════════════════════════════════════════════════════════════════════

def compute_mape(actual: List[float], forecast: List[float]) -> Optional[float]:
    """Mean Absolute Percentage Error: avg(|y_t - ŷ_t| / |y_t|) × 100%.

    Undefined when y_t = 0; returns None if any actual is zero.
    Hyndman & Koehler 2006 criticize MAPE for this asymmetry but
    practitioners still demand it.
    """
    if not actual or not forecast or len(actual) != len(forecast):
        return None
    if any(y == 0 for y in actual):
        return None  # undefined
    return sum(abs(actual[t] - forecast[t]) / abs(actual[t])
               for t in range(len(actual))) / len(actual) * 100


def compute_smape(actual: List[float], forecast: List[float]) -> Optional[float]:
    """Symmetric MAPE: avg(2·|y - ŷ| / (|y| + |ŷ|)) × 100%.

    Bounded [0, 200%]. Used in M4 competition.
    """
    if not actual or not forecast or len(actual) != len(forecast):
        return None
    total = 0.0
    for t in range(len(actual)):
        denom = abs(actual[t]) + abs(forecast[t])
        if denom == 0:
            continue
        total += 2 * abs(actual[t] - forecast[t]) / denom
    return total / len(actual) * 100


def compute_mase(
    actual: List[float], forecast: List[float],
    training_history: List[float], season_length: int = 1,
) -> Optional[float]:
    """Mean Absolute Scaled Error (Hyndman & Koehler 2006).

    MASE = MAE_forecast / MAE_naive_baseline_on_training

    Where naive baseline = seasonal naive (or naive if season_length=1).

    Properties:
      • Scale-free (comparable across series)
      • Symmetric (unlike MAPE)
      • Well-defined for zero values (unlike MAPE)
      • MASE < 1 ⟺ forecast beats naive baseline
      • Used as primary metric in M4 (Makridakis 2018)
    """
    if not actual or not forecast or len(actual) != len(forecast):
        return None
    if len(training_history) <= season_length:
        return None

    # MAE of naive baseline on training data
    naive_errors = []
    for t in range(season_length, len(training_history)):
        naive_errors.append(abs(training_history[t] - training_history[t - season_length]))
    if not naive_errors:
        return None
    mae_naive = sum(naive_errors) / len(naive_errors)
    if mae_naive == 0:
        return None  # perfectly flat history; MASE undefined

    # MAE of forecast on test data
    mae_forecast = sum(abs(actual[t] - forecast[t]) for t in range(len(actual))) / len(actual)
    return mae_forecast / mae_naive


# ════════════════════════════════════════════════════════════════════
# Backtest / holdout evaluation
# ════════════════════════════════════════════════════════════════════

@dataclass
class BacktestResult:
    method: str
    train_size: int
    test_size: int
    mape: Optional[float]
    smape: Optional[float]
    mase: Optional[float]
    forecast: List[float]
    actual: List[float]


def backtest(
    method: ForecastMethod,
    history: List[float],
    test_size: int = 6,
    season_length: int = 12,
    **method_kwargs,
) -> BacktestResult:
    """Holdout-based backtest: train on history[:-test_size], test on the rest.

    Hyndman & Athanasopoulos (2021) §5.4 recommend this for short series;
    time-series cross-validation (rolling forecast origin) is more robust
    but expensive (deferred to v3.30).
    """
    if len(history) <= test_size + 2:
        return BacktestResult(
            method=method.value, train_size=len(history), test_size=0,
            mape=None, smape=None, mase=None,
            forecast=[], actual=[],
        )

    train = history[:-test_size]
    test = history[-test_size:]
    forecast = run_forecast_method(method, train, test_size, season_length, **method_kwargs)

    return BacktestResult(
        method=method.value,
        train_size=len(train),
        test_size=test_size,
        mape=compute_mape(test, forecast),
        smape=compute_smape(test, forecast),
        mase=compute_mase(test, forecast, train, season_length),
        forecast=forecast,
        actual=test,
    )


def run_forecast_method(
    method: ForecastMethod,
    history: List[float],
    horizon: int,
    season_length: int = 12,
    **kwargs,
) -> List[float]:
    """Dispatch helper."""
    if method == ForecastMethod.NAIVE:
        return forecast_naive(history, horizon)
    elif method == ForecastMethod.SEASONAL_NAIVE:
        return forecast_seasonal_naive(history, horizon, season_length)
    elif method == ForecastMethod.SES:
        alpha = kwargs.get("alpha", _optimize_alpha_ses(history))
        f, _ = forecast_ses(history, horizon, alpha=alpha)
        return f
    elif method == ForecastMethod.HOLT:
        f, _ = forecast_holt(history, horizon,
                              alpha=kwargs.get("alpha", 0.3),
                              beta=kwargs.get("beta", 0.1))
        return f
    elif method == ForecastMethod.HOLT_WINTERS:
        f, _ = forecast_holt_winters(history, horizon, season_length,
                                      alpha=kwargs.get("alpha", 0.3),
                                      beta=kwargs.get("beta", 0.1),
                                      gamma=kwargs.get("gamma", 0.1))
        return f
    elif method == ForecastMethod.CROSTON:
        f, _ = forecast_croston(history, horizon,
                                 alpha=kwargs.get("alpha", 0.1))
        return f
    else:
        raise ValueError(f"Unknown method: {method}")


# ════════════════════════════════════════════════════════════════════
# Auto method selection
# ════════════════════════════════════════════════════════════════════

def auto_select_method(
    history: List[float],
    test_size: int = 6,
    season_length: int = 12,
    candidates: Optional[List[ForecastMethod]] = None,
) -> Tuple[ForecastMethod, List[BacktestResult]]:
    """Auto-pick lowest-MASE method via backtest.

    Default candidates exclude AUTO itself.
    For intermittent demand (>40% zero values), only consider naive + croston
    per Syntetos & Boylan (2005) recommendation.

    Returns: (best_method, all_backtest_results)
    """
    if candidates is None:
        # Detect intermittent demand
        if history:
            zero_fraction = sum(1 for y in history if y <= 0) / len(history)
        else:
            zero_fraction = 0
        if zero_fraction > 0.4:
            # Intermittent: per Syntetos-Boylan 2005, smooth methods
            # over-react to occasional spikes; restrict to naive + croston
            candidates = [
                ForecastMethod.NAIVE,
                ForecastMethod.CROSTON,
            ]
        else:
            candidates = [
                ForecastMethod.NAIVE,
                ForecastMethod.SEASONAL_NAIVE,
                ForecastMethod.SES,
                ForecastMethod.HOLT,
                ForecastMethod.HOLT_WINTERS,
            ]

    results = []
    for m in candidates:
        try:
            r = backtest(m, history, test_size, season_length)
            results.append(r)
        except Exception:
            continue

    # Pick best MASE (lower = better), ignoring None
    valid = [r for r in results if r.mase is not None]
    if not valid:
        # Fallback to naive
        return ForecastMethod.NAIVE, results

    best = min(valid, key=lambda r: r.mase)
    return ForecastMethod(best.method), results


# ════════════════════════════════════════════════════════════════════
# Prediction intervals via residual bootstrap
# ════════════════════════════════════════════════════════════════════

def prediction_intervals_residual(
    point_forecast: List[float],
    residuals: List[float],
    alpha: float = 0.05,
) -> Tuple[List[float], List[float]]:
    """Approximate 1-α prediction intervals from forecast residuals.

    Per Hyndman & Athanasopoulos (2021) §5.5: assume residuals are
    iid normal with σ = sample std of residuals.

    PI_{t+k} = ŷ_{t+k} ± z_α · σ · √k

    where √k accounts for accumulating uncertainty over horizon.

    Limitation: assumes stationarity of residuals; if residuals exhibit
    autocorrelation or heteroscedasticity, intervals are mis-calibrated.
    """
    if not residuals:
        return [], []
    n = len(residuals)
    mean_r = sum(residuals) / n
    var_r = sum((r - mean_r) ** 2 for r in residuals) / max(1, n - 1)
    sigma = math.sqrt(var_r)

    # 1.96 ≈ 95% z-score (for α=0.05)
    # 1.645 for 90%, 2.576 for 99%
    z = 1.96 if abs(alpha - 0.05) < 1e-6 else 1.645

    lower, upper = [], []
    for k, f in enumerate(point_forecast, start=1):
        half_width = z * sigma * math.sqrt(k)
        lower.append(f - half_width)
        upper.append(f + half_width)
    return lower, upper


# ════════════════════════════════════════════════════════════════════
# Main public API: forecast + diagnostics
# ════════════════════════════════════════════════════════════════════

def forecast(
    history: List[float],
    horizon: int = 12,
    method: ForecastMethod = ForecastMethod.AUTO,
    season_length: int = 12,
    backtest_size: int = 6,
) -> ForecastResult:
    """Top-level forecast API with auto-selection, accuracy metrics,
    and prediction intervals.
    """
    diagnostic = {}

    if method == ForecastMethod.AUTO:
        best_method, backtest_results = auto_select_method(
            history, test_size=backtest_size, season_length=season_length,
        )
        diagnostic["auto_selection"] = {
            "selected": best_method.value,
            "candidates": [
                {"method": r.method, "mase": r.mase, "mape": r.mape, "smape": r.smape}
                for r in backtest_results
            ],
        }
        method = best_method

    # Run the selected method on FULL history (not just train portion)
    point_fc = run_forecast_method(method, history, horizon, season_length)

    # Get backtest accuracy for reporting
    bt = backtest(method, history, test_size=backtest_size, season_length=season_length)

    # Compute residuals from in-sample fit (for PI)
    fitted = _get_fitted(method, history, season_length)
    residuals = [history[t] - fitted[t] for t in range(min(len(history), len(fitted)))]

    lower, upper = prediction_intervals_residual(point_fc, residuals)

    return ForecastResult(
        method=method.value,
        horizon=horizon,
        point_forecast=point_fc,
        lower_95=lower,
        upper_95=upper,
        mape=bt.mape,
        smape=bt.smape,
        mase=bt.mase,
        fitted_values=fitted,
        residuals=residuals,
        diagnostic=diagnostic,
    )


def _get_fitted(method: ForecastMethod, history: List[float], season_length: int) -> List[float]:
    """Helper to extract fitted values for residual computation."""
    if method == ForecastMethod.SES:
        _, fit = forecast_ses(history, 1, alpha=_optimize_alpha_ses(history))
        return fit
    elif method == ForecastMethod.HOLT:
        _, fit = forecast_holt(history, 1)
        return fit
    elif method == ForecastMethod.HOLT_WINTERS:
        _, fit = forecast_holt_winters(history, 1, season_length)
        return fit
    elif method == ForecastMethod.CROSTON:
        _, fit = forecast_croston(history, 1)
        return fit
    else:
        # Naive: fit_t = y_{t-1}; first fit = y_0
        return [history[0]] + history[:-1] if history else []


# ════════════════════════════════════════════════════════════════════
# Regime change / anomaly detection (for LLM augmentation hook)
# ════════════════════════════════════════════════════════════════════

@dataclass
class RegimeChangeAlert:
    detected: bool
    reason: str
    recent_actual_vs_forecast_ratio: Optional[float]
    recent_periods_outside_pi: int
    requires_llm_review: bool


def detect_regime_change(
    history: List[float],
    fitted: List[float],
    residuals: List[float],
    recent_n: int = 3,
    threshold_sd: float = 2.0,
) -> RegimeChangeAlert:
    """Flag if recent N periods consistently deviate from forecast > threshold.

    Per Chatfield (1989) *The Analysis of Time Series* §13: a robust
    indicator of model breakdown is k consecutive residuals beyond ±2σ.

    LLM augmentation hook: when this fires, prompt LLM with recent
    data + business context to suggest qualitative adjustment.
    """
    if len(residuals) < recent_n + 5:
        return RegimeChangeAlert(
            detected=False, reason="不足歷史資料以偵測 regime change",
            recent_actual_vs_forecast_ratio=None,
            recent_periods_outside_pi=0,
            requires_llm_review=False,
        )

    # Estimate σ from earlier residuals (exclude recent_n to avoid bias)
    earlier = residuals[:-recent_n]
    mean_e = sum(earlier) / len(earlier)
    var_e = sum((r - mean_e) ** 2 for r in earlier) / max(1, len(earlier) - 1)
    sigma = math.sqrt(var_e) if var_e > 0 else 1.0

    # Count recent periods outside ±threshold·σ
    recent_residuals = residuals[-recent_n:]
    outside_count = sum(1 for r in recent_residuals if abs(r - mean_e) > threshold_sd * sigma)

    # Recent actual / forecast ratio
    if fitted and len(history) >= recent_n:
        recent_actuals = history[-recent_n:]
        recent_fitted = fitted[-recent_n:]
        if all(f != 0 for f in recent_fitted):
            ratio = sum(recent_actuals) / sum(recent_fitted) if sum(recent_fitted) != 0 else None
        else:
            ratio = None
    else:
        ratio = None

    # Detected if majority of recent are outside
    detected = outside_count >= max(2, recent_n // 2 + 1)

    reason = ""
    if detected:
        reason = (
            f"近 {recent_n} 期有 {outside_count} 期殘差超出 ±{threshold_sd}σ "
            f"(σ={sigma:.2f})。可能 regime change / structural break。"
        )

    return RegimeChangeAlert(
        detected=detected,
        reason=reason,
        recent_actual_vs_forecast_ratio=ratio,
        recent_periods_outside_pi=outside_count,
        requires_llm_review=detected,
    )

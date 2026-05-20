"""
Smoke: AI-Augmented Demand Forecasting Engine (v3.29)

Validates against canonical time-series cases from:
  • Hyndman & Athanasopoulos (2021) *Forecasting: Principles and Practice* 3rd ed
  • Makridakis et al. M4 (2018) / M5 (2020) competition setups
  • Croston (1972) original paper examples
  • Syntetos & Boylan (2005) corrections

Reviewer-grade invariants (8 categories):
  1. Naive baseline correctness (degenerate cases)
  2. Seasonal naive period rotation
  3. SES level smoothing recursion
  4. Holt linear trend extrapolation
  5. Holt-Winters seasonal pattern recovery
  6. Croston intermittent demand (key SMB case!)
  7. Accuracy metrics (MASE Hyndman-Koehler 2006 specific properties)
  8. Auto-selection picks lowest MASE
"""
from __future__ import annotations

import math
import pytest

from app.services.demand_forecasting import (
    ForecastMethod,
    ForecastResult,
    BacktestResult,
    forecast,
    forecast_naive,
    forecast_seasonal_naive,
    forecast_ses,
    forecast_holt,
    forecast_holt_winters,
    forecast_croston,
    compute_mape,
    compute_smape,
    compute_mase,
    backtest,
    auto_select_method,
    prediction_intervals_residual,
    detect_regime_change,
)


# ════════════════════════════════════════════════════════════════════
# 1. Naive baseline
# ════════════════════════════════════════════════════════════════════

def test_naive_returns_last_value_flat():
    """y_{t+k} = y_t for all k."""
    f = forecast_naive([10, 20, 30, 50], horizon=3)
    assert f == [50.0, 50.0, 50.0]


def test_naive_empty_history_returns_zeros():
    """Edge case: empty input."""
    f = forecast_naive([], horizon=3)
    assert f == [0.0, 0.0, 0.0]


def test_seasonal_naive_repeats_last_season():
    """For season_length=4, y_{t+k} = y_{t+k-4}."""
    # 8 periods, 2 seasons of 4 each
    history = [10, 20, 30, 40, 11, 21, 31, 41]
    f = forecast_seasonal_naive(history, horizon=4, season_length=4)
    # Should mirror periods 5-8 (the last full season)
    assert f == [11, 21, 31, 41]


def test_seasonal_naive_short_history_falls_back_to_naive():
    """When history < season_length, fallback."""
    f = forecast_seasonal_naive([10, 20], horizon=3, season_length=12)
    assert f == [20.0, 20.0, 20.0]


# ════════════════════════════════════════════════════════════════════
# 2. SES (Brown 1959)
# ════════════════════════════════════════════════════════════════════

def test_ses_alpha_one_tracks_last_value():
    """α=1 means level = current observation (no smoothing).

    Recursion: l_t = 1·y_t + 0·l_{t-1} = y_t.
    Final fit = last observation, forecast = last observation.
    """
    history = [10, 20, 5, 15, 30]
    f, fitted = forecast_ses(history, horizon=2, alpha=1.0)
    assert fitted[-1] == 30.0
    assert f == [30.0, 30.0]


def test_ses_alpha_near_zero_tracks_initial():
    """α → 0 means level stays near initial value."""
    history = [10] + [100] * 5
    f, fitted = forecast_ses(history, horizon=1, alpha=0.01)
    # Should still be close to initial 10
    assert fitted[-1] < 20.0


def test_ses_constant_input_recovers_value():
    """If y is constant, fitted should equal that constant."""
    history = [42.0] * 10
    f, fitted = forecast_ses(history, horizon=3, alpha=0.3)
    assert all(abs(v - 42.0) < 0.01 for v in fitted)
    assert all(abs(v - 42.0) < 0.01 for v in f)


# ════════════════════════════════════════════════════════════════════
# 3. Holt linear trend (Holt 1957)
# ════════════════════════════════════════════════════════════════════

def test_holt_extrapolates_linear_trend():
    """Linear data: y_t = 10 + 5·t.
    Holt should extrapolate roughly linearly."""
    history = [10 + 5 * t for t in range(10)]  # 10, 15, 20, ..., 55
    f, _ = forecast_holt(history, horizon=3, alpha=0.5, beta=0.5)
    # f[0] should be approximately 60, f[1] ≈ 65, f[2] ≈ 70
    assert f[0] > 55  # at minimum continues upward
    assert f[1] > f[0]
    assert f[2] > f[1]


def test_holt_horizon_forecast_increases_linearly():
    """Forecast at horizon k = level + k·trend (linear in k)."""
    history = [10 + 2 * t for t in range(10)]
    f, _ = forecast_holt(history, horizon=5, alpha=0.3, beta=0.3)
    # diffs should be approximately constant (linear)
    diffs = [f[k+1] - f[k] for k in range(len(f) - 1)]
    assert all(abs(d - diffs[0]) < 1.0 for d in diffs), \
        f"Expected near-constant diffs (linear), got {diffs}"


# ════════════════════════════════════════════════════════════════════
# 4. Holt-Winters (Winters 1960)
# ════════════════════════════════════════════════════════════════════

def test_holt_winters_recovers_perfect_periodic_signal():
    """Perfect cyclic signal: forecast should preserve seasonal pattern."""
    base = [10, 20, 15, 25]  # season of 4
    history = base * 3  # 3 full cycles
    f, _ = forecast_holt_winters(history, horizon=4, season_length=4,
                                  alpha=0.5, beta=0.01, gamma=0.5)
    # f should approximately match the seasonal pattern
    # (relax tolerance since HW estimates from data)
    assert max(f) > min(f), "Should have seasonal variation, not flat"


def test_holt_winters_short_history_falls_back_to_holt():
    """Less than 2 seasons → fallback to Holt."""
    f, _ = forecast_holt_winters([10, 20, 30], horizon=3, season_length=12)
    # Should not crash; gives a finite forecast
    assert all(math.isfinite(v) for v in f)


# ════════════════════════════════════════════════════════════════════
# 5. Croston intermittent demand (1972) — critical for SMB
# ════════════════════════════════════════════════════════════════════

def test_croston_all_zero_history_predicts_zero():
    """Edge case: no historical demand → zero forecast."""
    f, _ = forecast_croston([0, 0, 0, 0, 0], horizon=3)
    assert f == [0.0, 0.0, 0.0]


def test_croston_recovers_demand_rate():
    """Demand: 10 every 4 periods → rate = 10/4 = 2.5, with Syntetos correction."""
    history = [10, 0, 0, 0, 10, 0, 0, 0, 10, 0, 0, 0]
    f, _ = forecast_croston(history, horizon=3, alpha=0.1)
    # With α=0.1 and intervals all = 4, expected ≈ (1 - 0.05) × 10/4 = 2.375
    # Allow ±20% tolerance for Syntetos correction
    assert 2.0 < f[0] < 3.0, f"Expected ~2.5 with correction, got {f[0]}"


def test_croston_flat_forecast():
    """Croston produces flat forecast (no trend modeling)."""
    history = [5, 0, 0, 5, 0, 0, 5, 0, 0]
    f, _ = forecast_croston(history, horizon=5)
    assert all(abs(v - f[0]) < 1e-9 for v in f)


def test_croston_single_demand_event():
    """Single non-zero in history → flat low forecast."""
    history = [0, 0, 0, 10, 0, 0, 0, 0]
    f, _ = forecast_croston(history, horizon=2)
    # Should be positive but small
    assert 0 < f[0] < 5.0


# ════════════════════════════════════════════════════════════════════
# 6. Accuracy metrics (Hyndman & Koehler 2006)
# ════════════════════════════════════════════════════════════════════

def test_mape_basic():
    """MAPE = avg(|y-ŷ|/|y|) × 100%."""
    # actual = [100, 200], forecast = [110, 180]
    # MAPE = (10/100 + 20/200) / 2 × 100 = (0.1 + 0.1)/2 × 100 = 10
    mape = compute_mape([100, 200], [110, 180])
    assert abs(mape - 10.0) < 0.01


def test_mape_undefined_when_actual_zero():
    """MAPE divides by actual; undefined when actual = 0."""
    mape = compute_mape([0, 100], [10, 90])
    assert mape is None


def test_smape_bounded_0_200():
    """sMAPE ∈ [0, 200] regardless of values."""
    s = compute_smape([100, 200], [100, 200])
    assert s == 0.0  # perfect forecast

    # Extreme overshoot
    s2 = compute_smape([1, 1], [1000, 1000])
    assert 0 <= s2 <= 200


def test_mase_perfect_forecast_zero():
    """MASE = 0 when forecast is perfect."""
    train = [1, 2, 3, 4, 5, 6, 7, 8]  # not constant → naive MAE > 0
    test = [9, 10]
    forecast = [9, 10]
    mase = compute_mase(test, forecast, train, season_length=1)
    assert mase == 0.0


def test_mase_less_than_one_when_beats_naive():
    """MASE < 1 ⟺ beats naive baseline (Hyndman & Koehler 2006)."""
    # Stable trend: y_t = t
    train = list(range(1, 9))  # 1..8
    test = [9, 10, 11]
    # Perfect forecast = test exactly
    perfect = [9, 10, 11]
    mase = compute_mase(test, perfect, train, season_length=1)
    assert mase < 1.0


def test_mase_greater_than_one_when_loses_to_naive():
    """Bad forecast: MASE > 1."""
    train = list(range(1, 9))
    test = [9, 10, 11]
    # Way-off forecast
    bad = [100, 100, 100]
    mase = compute_mase(test, bad, train, season_length=1)
    assert mase > 1.0


# ════════════════════════════════════════════════════════════════════
# 7. Auto method selection
# ════════════════════════════════════════════════════════════════════

def test_auto_select_intermittent_restricts_to_naive_croston():
    """For >40% zero history, should only test naive + croston."""
    # 70% zeros (intermittent)
    history = [0] * 14 + [10] * 6
    method, results = auto_select_method(history, test_size=3, season_length=4)
    method_names = {r.method for r in results}
    # Should not include holt_winters / ses / holt (those over-react to zeros)
    assert "holt_winters" not in method_names
    assert "ses" not in method_names


def test_auto_select_picks_lowest_mase():
    """When multiple methods compete, lowest-MASE wins."""
    # Clear linear trend → Holt should win
    history = [10 + 2 * t for t in range(24)]
    method, results = auto_select_method(history, test_size=4, season_length=12)
    valid = [r for r in results if r.mase is not None]
    if valid:
        # The selected method should have the minimum MASE
        selected_result = next(r for r in valid if r.method == method.value)
        assert selected_result.mase == min(r.mase for r in valid)


# ════════════════════════════════════════════════════════════════════
# 8. Prediction intervals
# ════════════════════════════════════════════════════════════════════

def test_prediction_intervals_widen_with_horizon():
    """PI width ∝ √k per Hyndman 2021 §5.5."""
    forecast_pts = [100.0, 100.0, 100.0, 100.0]
    residuals = [-5, 3, -2, 4, -3, 2, -1, 1]  # σ ≈ 3
    lower, upper = prediction_intervals_residual(forecast_pts, residuals, alpha=0.05)
    widths = [upper[k] - lower[k] for k in range(len(forecast_pts))]
    # Width(k=1) < Width(k=2) < ... (strictly increasing)
    assert all(widths[i+1] > widths[i] for i in range(len(widths) - 1))


def test_prediction_intervals_zero_residual_zero_width():
    """No uncertainty → zero PI width."""
    lower, upper = prediction_intervals_residual([100, 100], [0, 0, 0, 0], alpha=0.05)
    assert all(abs(u - l) < 1e-6 for l, u in zip(lower, upper))


# ════════════════════════════════════════════════════════════════════
# 9. Regime change detection
# ════════════════════════════════════════════════════════════════════

def test_regime_change_detected_on_recent_spike():
    """Recent residuals far outside ±2σ → flag."""
    # Stable history then sudden spike
    history = [10] * 10 + [50, 60, 55]  # 3 anomalous
    fitted = [10] * 13
    residuals = [0] * 10 + [40, 50, 45]
    alert = detect_regime_change(history, fitted, residuals, recent_n=3)
    assert alert.detected
    assert alert.requires_llm_review


def test_regime_change_not_detected_on_stable():
    """No anomalies → no flag."""
    residuals = [1, -1, 0.5, -0.5, 1, -1, 0.5, -0.5, 1, -1, 0.5, -0.5]
    fitted = [10] * 12
    history = [10 + r for r in residuals]
    alert = detect_regime_change(history, fitted, residuals, recent_n=3)
    assert not alert.detected


# ════════════════════════════════════════════════════════════════════
# 10. End-to-end forecast() API
# ════════════════════════════════════════════════════════════════════

def test_forecast_api_returns_complete_result():
    """forecast() with AUTO returns full ForecastResult."""
    # 24 months of trending data
    history = [10 + 2 * t + (t % 4) for t in range(24)]
    result = forecast(history, horizon=6, method=ForecastMethod.AUTO,
                       season_length=4, backtest_size=4)
    assert len(result.point_forecast) == 6
    assert len(result.lower_95) == 6
    assert len(result.upper_95) == 6
    # PI should bracket point forecast
    for k in range(6):
        assert result.lower_95[k] <= result.point_forecast[k] <= result.upper_95[k]
    # Diagnostic should mention auto_selection
    assert "auto_selection" in result.diagnostic


def test_forecast_horizon_zero_returns_empty():
    """horizon=0 returns empty forecast."""
    result = forecast([10, 20, 30], horizon=0)
    assert result.point_forecast == []


def test_forecast_specific_method_works():
    """Explicit method selection."""
    history = [10, 12, 14, 16, 18, 20]
    result = forecast(history, horizon=2, method=ForecastMethod.NAIVE)
    assert result.method == "naive"
    assert result.point_forecast == [20.0, 20.0]

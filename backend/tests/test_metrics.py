"""Metrics unit tests (M1–M5)."""

from __future__ import annotations

from app.metrics import compute_paired_metrics, accuracy_report


def test_m1_known_series_mae_rmse_bias():
    forecast = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 10},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 20},
    ]
    actual = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 12},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 18},
    ]
    m = compute_paired_metrics(forecast, actual)
    assert m["n"] == 2
    assert m["mae"] == 2.0
    assert m["rmse"] == 2.0
    assert m["bias"] == 0.0


def test_m2_constant_overforecast_positive_bias():
    forecast = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 110},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 210},
    ]
    actual = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 100},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 200},
    ]
    m = compute_paired_metrics(forecast, actual)
    assert m["bias"] == 10.0
    assert m["mae"] == 10.0


def test_m3_empty_series():
    m = compute_paired_metrics([], [])
    assert m["n"] == 0
    assert m["mae"] is None
    assert m["rmse"] is None


def test_m4_zero_actual_excluded_from_mape():
    forecast = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 10},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 20},
    ]
    actual = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 0},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 20},
    ]
    m = compute_paired_metrics(forecast, actual)
    # Only second period contributes to MAPE: |0/20|*100 = 0
    assert m["mape"] == 0.0
    assert m["n"] == 2  # both still in absolute metrics


def test_m5_unequal_join_keys():
    forecast = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 10},
        {"startTime": "2026-01-15T01:00:00Z", "generation": 30},
    ]
    actual = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 12},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 18},
    ]
    m = compute_paired_metrics(forecast, actual)
    assert m["n"] == 1
    assert m["mae"] == 2.0


def test_accuracy_report_heatmap_shape():
    forecast = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 10},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 20},
    ]
    actual = [
        {"startTime": "2026-01-15T00:00:00Z", "generation": 12},
        {"startTime": "2026-01-15T00:30:00Z", "generation": 18},
    ]
    report = accuracy_report(forecast, actual)
    assert "heatmap" in report
    assert len(report["heatmap"]["periods"]) == 48
    assert len(report["daily"]) == 1

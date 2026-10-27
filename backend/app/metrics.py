"""Forecast accuracy metrics using pandas/numpy.

MAPE: periods with actual == 0 are excluded (undefined relative error).
Empty paired series returns zeros with n=0 rather than raising.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _to_frame(
    forecast: list[dict[str, Any]] | pd.DataFrame,
    actual: list[dict[str, Any]] | pd.DataFrame,
    forecast_col: str = "generation",
    actual_col: str = "generation",
) -> pd.DataFrame:
    if isinstance(forecast, pd.DataFrame):
        f = forecast.copy()
    else:
        f = pd.DataFrame(forecast)
    if isinstance(actual, pd.DataFrame):
        a = actual.copy()
    else:
        a = pd.DataFrame(actual)

    if f.empty or a.empty:
        return pd.DataFrame(columns=["startTime", "forecast", "actual", "error"])

    f = f.rename(columns={forecast_col: "forecast"})[["startTime", "forecast"]]
    a = a.rename(columns={actual_col: "actual"})[["startTime", "actual"]]
    f["startTime"] = pd.to_datetime(f["startTime"], utc=True)
    a["startTime"] = pd.to_datetime(a["startTime"], utc=True)
    merged = f.merge(a, on="startTime", how="inner")
    merged["error"] = merged["forecast"] - merged["actual"]
    return merged


def summarize_errors(paired: pd.DataFrame) -> dict[str, Any]:
    """Aggregate MAE, RMSE, bias, MAPE over paired rows."""
    if paired.empty or "error" not in paired.columns:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "mape": None,
            "p90_abs_error": None,
        }

    err = paired["error"].to_numpy(dtype=float)
    abs_err = np.abs(err)
    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(err**2)))
    bias = float(np.mean(err))
    p90 = float(np.percentile(abs_err, 90))

    actual = paired["actual"].to_numpy(dtype=float)
    mask = actual != 0
    if mask.any():
        mape = float(np.mean(np.abs(err[mask] / actual[mask])) * 100.0)
    else:
        mape = None

    return {
        "n": int(len(paired)),
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "bias": round(bias, 3),
        "mape": None if mape is None else round(mape, 3),
        "p90_abs_error": round(p90, 3),
    }


def compute_paired_metrics(
    forecast: list[dict[str, Any]] | pd.DataFrame,
    actual: list[dict[str, Any]] | pd.DataFrame,
) -> dict[str, Any]:
    paired = _to_frame(forecast, actual)
    return summarize_errors(paired)


def accuracy_report(
    forecast_rows: list[dict[str, Any]],
    actual_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Full accuracy payload: summary, daily, by settlement period, heatmap."""
    paired = _to_frame(forecast_rows, actual_rows)
    summary = summarize_errors(paired)

    if paired.empty:
        return {
            "summary": summary,
            "daily": [],
            "by_period": [],
            "heatmap": {"days": [], "periods": [], "values": []},
        }

    paired = paired.copy()
    # Settlement period 1..48 from London local time of start
    local = paired["startTime"].dt.tz_convert("Europe/London")
    paired["day"] = local.dt.strftime("%Y-%m-%d")
    paired["period"] = (local.dt.hour * 2 + local.dt.minute // 30 + 1).astype(int)

    daily = []
    for day, grp in paired.groupby("day", sort=True):
        m = summarize_errors(grp)
        daily.append({"date": day, **m})

    by_period = []
    for period, grp in paired.groupby("period", sort=True):
        m = summarize_errors(grp)
        by_period.append({"settlement_period": int(period), **m})

    days = sorted(paired["day"].unique().tolist())
    periods = list(range(1, 49))
    pivot = paired.pivot_table(
        index="day", columns="period", values="error", aggfunc="mean"
    )
    values: list[list[float | None]] = []
    for day in days:
        row: list[float | None] = []
        for p in periods:
            if day in pivot.index and p in pivot.columns and pd.notna(pivot.loc[day, p]):
                row.append(round(float(pivot.loc[day, p]), 2))
            else:
                row.append(None)
        values.append(row)

    return {
        "summary": summary,
        "daily": daily,
        "by_period": by_period,
        "heatmap": {"days": days, "periods": periods, "values": values},
    }

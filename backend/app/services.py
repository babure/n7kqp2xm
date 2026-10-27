"""Domain services: gate-time forecast and accuracy over the configured window.

Depends on AnalysisWindow (config) — not on hardcoded calendar months.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.cache import DataCache
from app.config import AnalysisWindow, get_window
from app.decision import decision_cutoff, select_gate_time_forecast
from app.metrics import accuracy_report, compute_paired_metrics

LONDON = ZoneInfo("Europe/London")


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _settlement_period(start: datetime) -> int:
    local = start.astimezone(LONDON)
    return local.hour * 2 + local.minute // 30 + 1


def _actuals_index(rows: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        st = row.get("startTime")
        if st is None:
            continue
        out[st] = float(row["generation"])
    return out


def list_delivery_days(
    cache: DataCache,
    window: AnalysisWindow | None = None,
) -> list[dict[str, Any]]:
    window = window or get_window()
    windfor = cache.load_windfor()
    fuelhh = cache.load_fuelhh()
    actual_keys = {
        _parse_dt(r["startTime"]).astimezone(LONDON).date()
        for r in fuelhh
        if "startTime" in r
    }

    days = []
    for d in window.iter_days():
        series, pub, _ = select_gate_time_forecast(
            windfor,
            d,
            cutoff=decision_cutoff(d, window.gate_time()),
        )
        days.append(
            {
                "date": d.isoformat(),
                "has_forecast": pub is not None and len(series) > 0,
                "has_actuals": d in actual_keys,
            }
        )
    return days


def build_forecast(
    cache: DataCache,
    delivery_date: date,
    uncertainty_k: float = 1.0,
    window: AnalysisWindow | None = None,
) -> dict[str, Any]:
    window = window or get_window()
    if not window.contains(delivery_date):
        raise ValueError(
            f"delivery_date must be within {window.delivery_from.isoformat()} "
            f"… {window.delivery_to.isoformat()}"
        )

    windfor = cache.load_windfor()
    fuelhh = cache.load_fuelhh()
    series_rows, publish_time, cutoff = select_gate_time_forecast(
        windfor,
        delivery_date,
        cutoff=decision_cutoff(delivery_date, window.gate_time()),
    )
    actuals = _actuals_index(fuelhh)

    uncertainty_mw = None
    month_pairs = _gate_pairs(
        windfor, fuelhh, window.delivery_from, window.delivery_to, window
    )
    if month_pairs["forecast"] and month_pairs["actual"]:
        m = compute_paired_metrics(month_pairs["forecast"], month_pairs["actual"])
        if m["rmse"] is not None:
            uncertainty_mw = round(float(m["rmse"]) * uncertainty_k, 2)

    series = []
    for row in series_rows:
        st = row["startTime"]
        start_dt = _parse_dt(st)
        series.append(
            {
                "start_time": st,
                "forecast_mw": float(row["generation"]),
                "actual_mw": actuals.get(st),
                "settlement_period": _settlement_period(start_dt),
            }
        )

    message = None
    if not series:
        message = (
            "No WINDFOR publish was available at or before gate for this delivery day."
        )

    return {
        "delivery_date": delivery_date.isoformat(),
        "decision_cutoff": cutoff.isoformat(),
        "publish_time": publish_time.isoformat() if publish_time else None,
        "uncertainty_mw": uncertainty_mw,
        "series": series,
        "message": message,
    }


def build_accuracy(
    cache: DataCache,
    from_date: date | None = None,
    to_date: date | None = None,
    window: AnalysisWindow | None = None,
) -> dict[str, Any]:
    window = window or get_window()
    from_date = from_date or window.delivery_from
    to_date = to_date or window.delivery_to
    if (
        not window.contains(from_date)
        or not window.contains(to_date)
        or from_date > to_date
    ):
        raise ValueError(
            f"date range must fall within {window.delivery_from.isoformat()} "
            f"… {window.delivery_to.isoformat()}"
        )

    windfor = cache.load_windfor()
    fuelhh = cache.load_fuelhh()
    pairs = _gate_pairs(windfor, fuelhh, from_date, to_date, window)
    report = accuracy_report(pairs["forecast"], pairs["actual"])

    summary = report["summary"]
    mae = summary.get("mae")
    rmse = summary.get("rmse")
    bias = summary.get("bias")
    if mae is not None and rmse is not None:
        if bias is None or abs(bias) < 50:
            lean = "with little systematic lean"
        elif bias > 0:
            lean = "usually overstating how much wind would show up"
        else:
            lean = "usually understating how much wind would show up"
        note = (
            f"In this window the gate-time forecast was typically about {mae:.0f} MW off "
            f"(MAE), and large misses push RMSE to {rmse:.0f} MW — {lean}. "
            f"A practical starting cover buffer is roughly ±{rmse:.0f} MW around the "
            f"gate-time forecast when sizing residual thermal or market purchases."
        )
    else:
        note = "Not enough matched forecast and outturn pairs yet to size a cover buffer."

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "summary": summary,
        "daily": report["daily"],
        "by_period": report["by_period"],
        "heatmap": report["heatmap"],
        "procurement_note": note,
    }


def _gate_pairs(
    windfor: list[dict[str, Any]],
    fuelhh: list[dict[str, Any]],
    from_date: date,
    to_date: date,
    window: AnalysisWindow,
) -> dict[str, list[dict[str, Any]]]:
    """Build forecast/actual row lists using gate-time selection per delivery day."""
    actuals = {r["startTime"]: r for r in fuelhh if "startTime" in r}
    forecast_rows: list[dict[str, Any]] = []
    actual_rows: list[dict[str, Any]] = []

    d = from_date
    while d <= to_date:
        series, pub, _ = select_gate_time_forecast(
            windfor,
            d,
            cutoff=decision_cutoff(d, window.gate_time()),
        )
        if pub is None:
            d += timedelta(days=1)
            continue
        for row in series:
            st = row["startTime"]
            if st not in actuals:
                continue
            forecast_rows.append({"startTime": st, "generation": row["generation"]})
            actual_rows.append(
                {"startTime": st, "generation": actuals[st]["generation"]}
            )
        d += timedelta(days=1)

    return {"forecast": forecast_rows, "actual": actual_rows}


def parse_delivery_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("delivery_date must be YYYY-MM-DD") from exc

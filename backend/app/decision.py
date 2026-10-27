"""Point-in-time forecast selection for N2EX day-ahead gate closure.

Assumption (documented for reviewers): UK N2EX day-ahead gate is 09:50
Europe/London on day D-1 for delivery day D. We use the latest WINDFOR
publishTime that is still <= that cutoff.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
GATE_TIME = time(9, 50)


def decision_cutoff(
    delivery_date: date,
    gate: time | None = None,
) -> datetime:
    """Return timezone-aware cutoff (Europe/London) for delivery day D."""
    decision_day = delivery_date - timedelta(days=1)
    return datetime.combine(decision_day, gate or GATE_TIME, tzinfo=LONDON)


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        # Elexon returns ISO with Z
        text = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def _start_on_delivery_day(start: datetime, delivery_date: date) -> bool:
    """Settlement startTimes are UTC; map to London calendar date for matching."""
    local = start.astimezone(LONDON)
    return local.date() == delivery_date


def select_gate_time_forecast(
    windfor_rows: list[dict[str, Any]],
    delivery_date: date,
    cutoff: datetime | None = None,
) -> tuple[list[dict[str, Any]], datetime | None, datetime]:
    """Pick the latest usable forecast run for delivery_date at or before gate.

    Returns:
        (series_rows, publish_time, cutoff_used)

    series_rows have keys startTime, generation (and passthrough fields).
    If no usable publish exists, series_rows is empty and publish_time is None.
    """
    cutoff = cutoff or decision_cutoff(delivery_date)
    # Ensure cutoff is timezone-aware
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=LONDON)

    # Group by publishTime among rows whose startTime falls on delivery day
    by_publish: dict[datetime, list[dict[str, Any]]] = {}
    for row in windfor_rows:
        try:
            start = _parse_dt(row["startTime"])
            pub = _parse_dt(row["publishTime"])
        except (KeyError, ValueError, TypeError):
            continue
        if not _start_on_delivery_day(start, delivery_date):
            continue
        if pub > cutoff:
            continue
        by_publish.setdefault(pub, []).append(row)

    if not by_publish:
        return [], None, cutoff

    best_pub = max(by_publish.keys())
    series = sorted(by_publish[best_pub], key=lambda r: _parse_dt(r["startTime"]))
    # Deduplicate by startTime keeping first (already sorted)
    seen: set[datetime] = set()
    deduped: list[dict[str, Any]] = []
    for row in series:
        st = _parse_dt(row["startTime"])
        if st in seen:
            continue
        seen.add(st)
        deduped.append(row)
    return deduped, best_pub, cutoff

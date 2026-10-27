"""Application configuration — single place to extend the analysis window.

SOLID notes
-----------
* Single responsibility: this module owns *what period we analyse* and how
  the Elexon publish fetch window is derived. Domain logic (gate selection,
  metrics) stays ignorant of "January 2026".
* Open/closed: extend by env vars or a new AnalysisWindow factory — do not
  edit services/decision/metrics for a new month.
* Dependency inversion: jobs and services depend on AnalysisWindow, not on
  scattered date literals.

Extend for a future month
-------------------------
1. Set env (or .env):
     GRIDBRICKS_DELIVERY_FROM=2026-02-01
     GRIDBRICKS_DELIVERY_TO=2026-02-28
     GRIDBRICKS_LABEL=Feb 2026 · GB wind
2. Clear the disk cache (backend/data/cache/*.json) or POST /api/v1/jobs/refresh
3. Restart the API — UI reads scope from GET /api/v1/scope automatically.

Optional:
  GRIDBRICKS_GATE_HOUR=9
  GRIDBRICKS_GATE_MINUTE=50
  GRIDBRICKS_PUBLISH_LEAD_DAYS=2   # days before delivery_from for WINDFOR
  GRIDBRICKS_PUBLISH_LAG_DAYS=1    # days after delivery_to for WINDFOR
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from typing import Iterator


def _parse_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD, got {value!r}") from exc


@dataclass(frozen=True)
class AnalysisWindow:
    """Inclusive delivery-day window the product analyses."""

    delivery_from: date
    delivery_to: date
    label: str
    gate_hour: int = 9
    gate_minute: int = 50
    publish_lead_days: int = 2
    publish_lag_days: int = 1

    def __post_init__(self) -> None:
        if self.delivery_from > self.delivery_to:
            raise ValueError("delivery_from must be on or before delivery_to")
        if not (0 <= self.gate_hour <= 23 and 0 <= self.gate_minute <= 59):
            raise ValueError("invalid gate time")

    def contains(self, day: date) -> bool:
        return self.delivery_from <= day <= self.delivery_to

    def iter_days(self) -> Iterator[date]:
        d = self.delivery_from
        while d <= self.delivery_to:
            yield d
            d += timedelta(days=1)

    def default_delivery_date(self) -> date:
        """Prefer mid-window; clamp to bounds."""
        span = (self.delivery_to - self.delivery_from).days
        return self.delivery_from + timedelta(days=span // 2)

    def gate_time(self) -> time:
        return time(self.gate_hour, self.gate_minute)

    def publish_window_utc(self) -> tuple[datetime, datetime]:
        """WINDFOR publishTime query range covering D-1 decisions for all days."""
        start = datetime.combine(
            self.delivery_from - timedelta(days=self.publish_lead_days),
            time.min,
            tzinfo=timezone.utc,
        )
        end = datetime.combine(
            self.delivery_to + timedelta(days=self.publish_lag_days),
            time.min,
            tzinfo=timezone.utc,
        )
        return start, end

    def describe(self) -> dict[str, str | int]:
        pub_from, pub_to = self.publish_window_utc()
        return {
            "delivery_from": self.delivery_from.isoformat(),
            "delivery_to": self.delivery_to.isoformat(),
            "label": self.label,
            "default_delivery_date": self.default_delivery_date().isoformat(),
            "gate_local": f"{self.gate_hour:02d}:{self.gate_minute:02d}",
            "publish_from": pub_from.isoformat(),
            "publish_to": pub_to.isoformat(),
        }

    @classmethod
    def from_env(cls) -> AnalysisWindow:
        delivery_from = _parse_date(
            os.environ.get("GRIDBRICKS_DELIVERY_FROM", "2026-01-01"),
            "GRIDBRICKS_DELIVERY_FROM",
        )
        delivery_to = _parse_date(
            os.environ.get("GRIDBRICKS_DELIVERY_TO", "2026-01-31"),
            "GRIDBRICKS_DELIVERY_TO",
        )
        label = os.environ.get("GRIDBRICKS_LABEL", "Jan 2026 · GB wind")
        return cls(
            delivery_from=delivery_from,
            delivery_to=delivery_to,
            label=label,
            gate_hour=int(os.environ.get("GRIDBRICKS_GATE_HOUR", "9")),
            gate_minute=int(os.environ.get("GRIDBRICKS_GATE_MINUTE", "50")),
            publish_lead_days=int(os.environ.get("GRIDBRICKS_PUBLISH_LEAD_DAYS", "2")),
            publish_lag_days=int(os.environ.get("GRIDBRICKS_PUBLISH_LAG_DAYS", "1")),
        )


@lru_cache(maxsize=1)
def get_window() -> AnalysisWindow:
    """Process-wide window (cached). Clear cache in tests after env changes."""
    return AnalysisWindow.from_env()


def reset_window_cache() -> None:
    get_window.cache_clear()

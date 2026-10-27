"""Point-in-time forecast selection tests (D1–D7)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.decision import decision_cutoff, select_gate_time_forecast

LONDON = ZoneInfo("Europe/London")


def test_d1_ignores_post_gate_picks_at_gate(windfor_rows):
    series, pub, cutoff = select_gate_time_forecast(windfor_rows, date(2026, 1, 15))
    assert pub is not None
    assert pub <= cutoff
    assert len(series) == 48
    # at-gate run uses base 5000
    assert series[0]["generation"] == 5000
    assert all(r["generation"] < 9000 for r in series)


def test_d2_publish_exactly_at_gate_included(windfor_rows):
    cutoff = decision_cutoff(date(2026, 1, 15))
    assert cutoff == datetime(2026, 1, 14, 9, 50, tzinfo=LONDON)
    _, pub, _ = select_gate_time_forecast(windfor_rows, date(2026, 1, 15))
    assert pub == datetime(2026, 1, 14, 9, 50, tzinfo=LONDON)


def test_d3_all_publishes_after_gate():
    rows = [
        {
            "publishTime": "2026-01-14T12:00:00Z",
            "startTime": "2026-01-15T00:00:00Z",
            "generation": 1,
        }
    ]
    series, pub, _ = select_gate_time_forecast(rows, date(2026, 1, 15))
    assert series == []
    assert pub is None


def test_d4_bst_offset_for_late_march():
    # 2026-03-29 is UK BST start; delivery 2026-03-30 → decision 2026-03-29 09:50 BST = 08:50 UTC
    cutoff = decision_cutoff(date(2026, 3, 30))
    assert cutoff.tzinfo == LONDON
    assert cutoff.utcoffset().total_seconds() == 3600  # BST
    assert cutoff.hour == 9 and cutoff.minute == 50


def test_d5_year_boundary_jan1(windfor_rows):
    cutoff = decision_cutoff(date(2026, 1, 1))
    assert cutoff.date() == date(2025, 12, 31)
    series, pub, _ = select_gate_time_forecast(windfor_rows, date(2026, 1, 1))
    assert pub is not None
    # late publish 11:00 is after gate — should pick early 08:00 (gen 2000)
    assert series[0]["generation"] == 2000


def test_d6_two_runs_before_gate_picks_latest(windfor_rows):
    # early (06:00, gen 1000) and at_gate (09:50, gen 5000) — pick 5000
    series, pub, _ = select_gate_time_forecast(windfor_rows, date(2026, 1, 15))
    assert series[0]["generation"] == 5000


def test_d7_filters_other_delivery_days(windfor_rows):
    series, _, _ = select_gate_time_forecast(windfor_rows, date(2026, 1, 15))
    for row in series:
        assert row["startTime"].startswith("2026-01-15")

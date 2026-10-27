"""AnalysisWindow config tests."""

from __future__ import annotations

from datetime import date

import pytest

from app.config import AnalysisWindow, get_window, reset_window_cache


def test_window_iter_and_contains():
    w = AnalysisWindow(
        delivery_from=date(2026, 2, 1),
        delivery_to=date(2026, 2, 3),
        label="Feb slice",
    )
    assert list(w.iter_days()) == [
        date(2026, 2, 1),
        date(2026, 2, 2),
        date(2026, 2, 3),
    ]
    assert w.contains(date(2026, 2, 2))
    assert not w.contains(date(2026, 1, 31))


def test_publish_window_derived_from_delivery():
    w = AnalysisWindow(
        delivery_from=date(2026, 2, 1),
        delivery_to=date(2026, 2, 28),
        label="Feb",
        publish_lead_days=2,
        publish_lag_days=1,
    )
    pub_from, pub_to = w.publish_window_utc()
    assert pub_from.date() == date(2026, 1, 30)
    assert pub_to.date() == date(2026, 3, 1)


def test_invalid_range_raises():
    with pytest.raises(ValueError):
        AnalysisWindow(
            delivery_from=date(2026, 3, 1),
            delivery_to=date(2026, 2, 1),
            label="bad",
        )


def test_from_env(monkeypatch):
    reset_window_cache()
    monkeypatch.setenv("GRIDBRICKS_DELIVERY_FROM", "2026-03-01")
    monkeypatch.setenv("GRIDBRICKS_DELIVERY_TO", "2026-03-31")
    monkeypatch.setenv("GRIDBRICKS_LABEL", "Mar 2026 · GB wind")
    w = AnalysisWindow.from_env()
    assert w.delivery_from == date(2026, 3, 1)
    assert w.label.startswith("Mar")
    reset_window_cache()
    # Restore defaults for other tests
    monkeypatch.delenv("GRIDBRICKS_DELIVERY_FROM", raising=False)
    monkeypatch.delenv("GRIDBRICKS_DELIVERY_TO", raising=False)
    monkeypatch.delenv("GRIDBRICKS_LABEL", raising=False)
    _ = get_window()

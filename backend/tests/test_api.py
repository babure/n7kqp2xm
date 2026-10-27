"""API integration tests (A1–A6)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest


def test_a1_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["cache_ready"] is True


def test_a1b_scope(client):
    r = client.get("/api/v1/scope")
    assert r.status_code == 200
    body = r.json()
    assert body["delivery_from"] <= body["delivery_to"]
    assert body["default_delivery_date"]
    assert body["gate_local"]
    assert "label" in body


def test_a2_forecast_gate_time(client):
    r = client.get("/api/v1/forecast", params={"delivery_date": "2026-01-15"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["series"]) == 48
    assert body["publish_time"] is not None
    assert body["decision_cutoff"] is not None
    # publish <= cutoff
    pub = datetime.fromisoformat(body["publish_time"].replace("Z", "+00:00"))
    cut = datetime.fromisoformat(body["decision_cutoff"])
    assert pub <= cut
    assert body["series"][0]["forecast_mw"] == 5000


def test_a3_invalid_date(client):
    r = client.get("/api/v1/forecast", params={"delivery_date": "2025-06-01"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "invalid_date"


def test_a4_accuracy(client):
    r = client.get(
        "/api/v1/accuracy",
        params={"from": "2026-01-15", "to": "2026-01-15"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["n"] == 48
    assert body["summary"]["mae"] is not None
    assert "days" in body["heatmap"]
    assert body["procurement_note"]


def test_a5_missing_query_params(client):
    r = client.get("/api/v1/forecast")
    assert r.status_code == 422


def test_a6_refresh_busy_returns_409(client):
    jobs = client.app.state.jobs

    async def hang():
        await asyncio.sleep(60)

    # Simulate running state
    jobs._state.status = "running"
    jobs._state.job_id = "busy-test"

    r = client.post("/api/v1/jobs/refresh")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "job_busy"

    # reset
    jobs._state.status = "idle"

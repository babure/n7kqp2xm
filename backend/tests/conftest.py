"""Shared fixtures for Gridbricks backend tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Skip cold refresh against live Elexon during tests
os.environ["SKIP_COLD_REFRESH"] = "1"

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def windfor_rows():
    with (FIXTURES / "windfor.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def fuelhh_rows():
    with (FIXTURES / "fuelhh_wind.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def cache_dir(tmp_path, windfor_rows, fuelhh_rows):
    from app.cache import DataCache

    c = DataCache(cache_dir=tmp_path / "cache")
    c.save(fuelhh_rows, windfor_rows)
    return c


@pytest.fixture
def client(cache_dir, monkeypatch):
    monkeypatch.setenv("SKIP_COLD_REFRESH", "1")
    monkeypatch.setenv("CACHE_DIR", str(cache_dir.cache_dir))

    # Re-import app with env set — create fresh app state via TestClient
    from app.cache import DataCache
    from app.jobs.refresh import RefreshJobManager
    from app.main import app

    cache = DataCache(cache_dir=cache_dir.cache_dir)
    jobs = RefreshJobManager(cache=cache)

    with TestClient(app, raise_server_exceptions=True) as tc:
        app.state.cache = cache
        app.state.jobs = jobs
        yield tc

"""Elexon client + cache tests (E1–E4)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import httpx
import pytest
import respx

from app.cache import DataCache
from app.elexon import BASE_URL, ElexonClient, ElexonError


@respx.mock
@pytest.mark.asyncio
async def test_e1_parse_fuelhh_wind():
    respx.get(f"{BASE_URL}/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "dataset": "FUELHH",
                    "startTime": "2026-01-01T00:00:00Z",
                    "fuelType": "WIND",
                    "generation": 100,
                    "publishTime": "2026-01-01T00:30:00Z",
                },
                {
                    "dataset": "FUELHH",
                    "startTime": "2026-01-01T00:00:00Z",
                    "fuelType": "CCGT",
                    "generation": 50,
                    "publishTime": "2026-01-01T00:30:00Z",
                },
            ],
        )
    )
    client = ElexonClient()
    rows = await client.fetch_fuelhh_wind(date(2026, 1, 1), date(2026, 1, 1))
    await client.aclose()
    assert len(rows) == 1
    assert rows[0]["fuelType"] == "WIND"
    assert rows[0]["generation"] == 100


@respx.mock
@pytest.mark.asyncio
async def test_e2_rate_limit_raises():
    respx.get(f"{BASE_URL}/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(429, json={"error": "slow down"})
    )
    client = ElexonClient()
    with pytest.raises(ElexonError) as exc:
        await client.fetch_fuelhh_wind(date(2026, 1, 1), date(2026, 1, 1))
    await client.aclose()
    assert exc.value.status_code == 429


def test_e3_cache_hit(tmp_path):
    cache = DataCache(cache_dir=tmp_path)
    payload = [{"startTime": "2026-01-01T00:00:00Z", "generation": 1, "fuelType": "WIND"}]
    cache.save(payload, [{"startTime": "x", "generation": 2, "publishTime": "y"}])
    assert cache.has_data()
    assert cache.load_fuelhh()[0]["generation"] == 1
    assert cache.meta()["fuelhh_count"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_e4_chunked_date_range_dedupes():
    # Two overlapping chunk responses with same startTime
    route = respx.get(f"{BASE_URL}/datasets/FUELHH/stream")
    route.side_effect = [
        httpx.Response(
            200,
            json=[
                {
                    "startTime": "2026-01-01T00:00:00Z",
                    "fuelType": "WIND",
                    "generation": 10,
                    "publishTime": "2026-01-01T00:30:00Z",
                }
            ],
        ),
        httpx.Response(
            200,
            json=[
                {
                    "startTime": "2026-01-01T00:00:00Z",
                    "fuelType": "WIND",
                    "generation": 20,
                    "publishTime": "2026-01-01T01:00:00Z",
                },
                {
                    "startTime": "2026-01-08T00:00:00Z",
                    "fuelType": "WIND",
                    "generation": 30,
                    "publishTime": "2026-01-08T00:30:00Z",
                },
            ],
        ),
    ]
    client = ElexonClient()
    # chunk_days=7 → two chunks for Jan 1..8
    rows = await client.fetch_fuelhh_wind(
        date(2026, 1, 1), date(2026, 1, 8), chunk_days=7
    )
    await client.aclose()
    starts = [r["startTime"] for r in rows]
    assert starts.count("2026-01-01T00:00:00Z") == 1
    # later publish preferred
    jan1 = next(r for r in rows if r["startTime"] == "2026-01-01T00:00:00Z")
    assert jan1["generation"] == 20

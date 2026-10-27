"""Async Elexon BMRS Insights API client (FUELHH + WINDFOR streams)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"


class ElexonError(Exception):
    """Raised when Elexon returns an error or unexpected payload."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ElexonClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        client: httpx.AsyncClient | None = None,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get_stream(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{self.base_url}{path}"
        try:
            resp = await self._client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise ElexonError(f"Elexon request failed: {exc}") from exc

        if resp.status_code == 429:
            raise ElexonError("Elexon rate limited", status_code=429)
        if resp.status_code >= 500:
            raise ElexonError("Elexon server error", status_code=resp.status_code)
        if resp.status_code >= 400:
            raise ElexonError(
                f"Elexon client error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        if not isinstance(data, list):
            raise ElexonError("Unexpected Elexon payload (expected list)")
        return data

    async def fetch_fuelhh_wind(
        self,
        settlement_date_from: date,
        settlement_date_to: date,
        chunk_days: int = 7,
    ) -> list[dict[str, Any]]:
        """Fetch FUELHH WIND actuals, chunking by settlement date range."""
        rows: list[dict[str, Any]] = []
        cursor = settlement_date_from
        while cursor <= settlement_date_to:
            end = min(cursor + timedelta(days=chunk_days - 1), settlement_date_to)
            chunk = await self._get_stream(
                "/datasets/FUELHH/stream",
                {
                    "settlementDateFrom": cursor.isoformat(),
                    "settlementDateTo": end.isoformat(),
                    "fuelType": "WIND",
                },
            )
            for item in chunk:
                if item.get("fuelType") == "WIND":
                    rows.append(item)
            cursor = end + timedelta(days=1)

        return _dedupe_by_start(rows)

    async def fetch_windfor(
        self,
        publish_from: datetime,
        publish_to: datetime,
        chunk_days: int = 3,
    ) -> list[dict[str, Any]]:
        """Fetch WINDFOR rows by publish datetime window, chunked."""
        if publish_from.tzinfo is None:
            publish_from = publish_from.replace(tzinfo=timezone.utc)
        if publish_to.tzinfo is None:
            publish_to = publish_to.replace(tzinfo=timezone.utc)

        rows: list[dict[str, Any]] = []
        cursor = publish_from
        while cursor < publish_to:
            end = min(cursor + timedelta(days=chunk_days), publish_to)
            chunk = await self._get_stream(
                "/datasets/WINDFOR/stream",
                {
                    "publishDateTimeFrom": _iso_z(cursor),
                    "publishDateTimeTo": _iso_z(end),
                },
            )
            rows.extend(chunk)
            cursor = end

        return rows


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dedupe_by_start(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("startTime")
        if not key:
            continue
        prev = best.get(key)
        if prev is None:
            best[key] = row
            continue
        # Prefer later publishTime if present
        if row.get("publishTime", "") >= prev.get("publishTime", ""):
            best[key] = row
    return list(best.values())

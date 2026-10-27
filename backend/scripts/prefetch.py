"""Prefetch Elexon data for the configured analysis window into the local cache.

Uses AnalysisWindow / get_window() — set GRIDBRICKS_DELIVERY_* to change the range.


Usage (from backend/):
  python scripts/prefetch.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.cache import DataCache
from app.jobs.refresh import RefreshJobManager


async def main() -> None:
    cache = DataCache()
    jobs = RefreshJobManager(cache=cache)
    status, started = await jobs.start()
    print("started:", started, status)
    while True:
        await asyncio.sleep(2)
        s = jobs.status()
        print(s["status"], s.get("duration_ms"), s.get("error"))
        if s["status"] in ("succeeded", "failed", "idle"):
            if s["status"] == "failed":
                raise SystemExit(1)
            break


if __name__ == "__main__":
    asyncio.run(main())

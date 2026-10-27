"""Async Elexon ingest/refresh job (Celery-shaped interface without Redis).

For a production deploy this would become a Celery/RQ worker; the HTTP
status contract (idle/running/failed) stays the same.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.cache import DataCache
from app.config import AnalysisWindow, get_window
from app.elexon import ElexonClient, ElexonError

logger = logging.getLogger(__name__)

JobStatus = Literal["idle", "running", "failed", "succeeded"]


@dataclass
class RefreshJobState:
    status: JobStatus = "idle"
    job_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    duration_ms: int | None = None
    fuelhh_count: int | None = None
    windfor_count: int | None = None


@dataclass
class RefreshJobManager:
    cache: DataCache
    client_factory: Any = field(default=ElexonClient)
    window: AnalysisWindow | None = None
    _state: RefreshJobState = field(default_factory=RefreshJobState)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _task: asyncio.Task | None = None

    def _window(self) -> AnalysisWindow:
        return self.window or get_window()

    def status(self) -> dict[str, Any]:
        s = self._state
        return {
            "status": s.status,
            "job_id": s.job_id,
            "started_at": s.started_at,
            "finished_at": s.finished_at,
            "error": s.error,
            "duration_ms": s.duration_ms,
            "fuelhh_count": s.fuelhh_count,
            "windfor_count": s.windfor_count,
        }

    async def start(self, force: bool = False) -> tuple[dict[str, Any], bool]:
        """Start refresh. Returns (status, started_new).

        If already running, returns current status and started_new=False (409).
        """
        async with self._lock:
            if self._state.status == "running":
                return self.status(), False

            job_id = str(uuid.uuid4())
            self._state = RefreshJobState(
                status="running",
                job_id=job_id,
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            self._task = asyncio.create_task(self._run(job_id))
            return self.status(), True

    async def ensure_warm(self) -> None:
        """Cold-start: refresh if cache empty."""
        if not self.cache.has_data():
            logger.info("cache empty — starting cold refresh")
            await self.start()

    async def _run(self, job_id: str) -> None:
        t0 = time.perf_counter()
        client: ElexonClient | None = None
        try:
            client = self.client_factory()
            window = self._window()
            pub_from, pub_to = window.publish_window_utc()
            logger.info(
                "refresh job started",
                extra={"job_id": job_id, "status": "running"},
            )
            fuelhh = await client.fetch_fuelhh_wind(
                window.delivery_from, window.delivery_to
            )
            windfor = await client.fetch_windfor(pub_from, pub_to)
            self.cache.save(fuelhh, windfor)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            self._state = RefreshJobState(
                status="succeeded",
                job_id=job_id,
                started_at=self._state.started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms,
                fuelhh_count=len(fuelhh),
                windfor_count=len(windfor),
            )
            logger.info(
                "refresh job succeeded",
                extra={"job_id": job_id, "duration_ms": duration_ms, "status": "succeeded"},
            )
        except ElexonError as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            self._state = RefreshJobState(
                status="failed",
                job_id=job_id,
                started_at=self._state.started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                error=str(exc),
                duration_ms=duration_ms,
            )
            logger.error(
                "refresh job failed",
                extra={"job_id": job_id, "duration_ms": duration_ms, "status": "failed"},
            )
        except Exception as exc:  # noqa: BLE001 — surface as job failure
            duration_ms = int((time.perf_counter() - t0) * 1000)
            self._state = RefreshJobState(
                status="failed",
                job_id=job_id,
                started_at=self._state.started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                error=str(exc),
                duration_ms=duration_ms,
            )
            logger.exception(
                "refresh job crashed",
                extra={"job_id": job_id, "duration_ms": duration_ms, "status": "failed"},
            )
        finally:
            if client is not None:
                await client.aclose()

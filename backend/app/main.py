"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.routes import router as v1_router
from app.cache import DataCache
from app.jobs.refresh import RefreshJobManager
from app.logging_config import configure_logging, request_id_ctx

configure_logging()
logger = logging.getLogger(__name__)

STATIC_DIR = Path(
    os.environ.get(
        "STATIC_DIR",
        str(Path(__file__).resolve().parents[2] / "frontend" / "dist"),
    )
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = rid
            return response
        finally:
            request_id_ctx.reset(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = DataCache(
        Path(os.environ["CACHE_DIR"]) if os.environ.get("CACHE_DIR") else None
    )
    jobs = RefreshJobManager(cache=cache)
    app.state.cache = cache
    app.state.jobs = jobs
    # Cold-start refresh when empty (skip in tests via SKIP_COLD_REFRESH=1)
    if os.environ.get("SKIP_COLD_REFRESH") != "1":
        await jobs.ensure_warm()
    yield


app = FastAPI(
    title="Gridbricks",
    description=(
        "UK day-ahead wind forecast pilot. Gate-time WINDFOR selection at "
        "N2EX 09:50 Europe/London on D-1, accuracy vs FUELHH WIND actuals "
        "over the configured analysis window (default January 2026; see /api/v1/scope)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.include_router(v1_router)


@app.get("/api/health")
async def legacy_health(request: Request):
    """Alias for probes that expect /api/health."""
    from app.api.v1.routes import health

    return await health(request)


def _mount_frontend() -> None:
    if not STATIC_DIR.is_dir():
        logger.warning("frontend dist not found at %s — API only", STATIC_DIR)
        return

    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    async def spa_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api"):
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")


_mount_frontend()

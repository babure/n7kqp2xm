"""Versioned API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.config import get_window
from app.schemas import (
    AccuracyResponse,
    DeliveryDaysResponse,
    ErrorBody,
    ForecastResponse,
    HealthResponse,
    JobStatusResponse,
    ScopeResponse,
)
from app.services import (
    build_accuracy,
    build_forecast,
    list_delivery_days,
    parse_delivery_date,
)

router = APIRouter(prefix="/api/v1", tags=["v1"])


def _state(request: Request):
    return request.app.state


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness and cache readiness",
)
async def health(request: Request) -> HealthResponse:
    cache = _state(request).cache
    jobs = _state(request).jobs
    meta = cache.meta()
    return HealthResponse(
        status="ok",
        cache_ready=bool(meta.get("ready")),
        cache_updated_at=meta.get("updated_at"),
        fuelhh_count=int(meta.get("fuelhh_count") or 0),
        windfor_count=int(meta.get("windfor_count") or 0),
        last_job=jobs.status(),
    )


@router.get(
    "/scope",
    response_model=ScopeResponse,
    summary="Configured analysis window",
    description=(
        "Returns the delivery-day window and gate settings. Change via "
        "GRIDBRICKS_DELIVERY_FROM / GRIDBRICKS_DELIVERY_TO env vars — see docs/EXTENDING.md."
    ),
)
async def scope() -> ScopeResponse:
    return ScopeResponse(**get_window().describe())


@router.get(
    "/delivery-days",
    response_model=DeliveryDaysResponse,
    summary="Delivery days in the configured window",
)
async def delivery_days(request: Request) -> DeliveryDaysResponse:
    cache = _state(request).cache
    if not cache.has_data():
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(
                code="cache_empty",
                message="Data cache not ready; trigger POST /api/v1/jobs/refresh",
            ).model_dump(),
        )
    window = get_window()
    return DeliveryDaysResponse(
        days=list_delivery_days(cache, window),
        scope=ScopeResponse(**window.describe()),
    )


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Gate-time wind forecast for a delivery day",
    description=(
        "Returns the latest national wind forecast (Elexon WINDFOR) that would have "
        "been available at day-ahead gate (configured local time on D-1), "
        "joined to FUELHH WIND actuals when present. "
        "uncertainty_mw is historical RMSE for a simple ± procurement band."
    ),
)
async def forecast(
    request: Request,
    delivery_date: Annotated[
        str,
        Query(description="Delivery day YYYY-MM-DD within the configured scope"),
    ],
) -> ForecastResponse:
    cache = _state(request).cache
    if not cache.has_data():
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(
                code="cache_empty",
                message="Data cache not ready; trigger POST /api/v1/jobs/refresh",
            ).model_dump(),
        )
    try:
        d = parse_delivery_date(delivery_date)
        payload = build_forecast(cache, d)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorBody(code="invalid_date", message=str(exc)).model_dump(),
        ) from exc
    return ForecastResponse(**payload)


@router.get(
    "/accuracy",
    response_model=AccuracyResponse,
    summary="Gate-time forecast accuracy over a date range",
)
async def accuracy(
    request: Request,
    from_date: Annotated[str | None, Query(alias="from")] = None,
    to_date: Annotated[str | None, Query(alias="to")] = None,
) -> AccuracyResponse:
    cache = _state(request).cache
    if not cache.has_data():
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(
                code="cache_empty",
                message="Data cache not ready; trigger POST /api/v1/jobs/refresh",
            ).model_dump(),
        )
    try:
        f = parse_delivery_date(from_date) if from_date else None
        t = parse_delivery_date(to_date) if to_date else None
        payload = build_accuracy(cache, f, t)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorBody(code="invalid_date", message=str(exc)).model_dump(),
        ) from exc
    return AccuracyResponse(**payload)


@router.get(
    "/jobs/refresh",
    response_model=JobStatusResponse,
    summary="Refresh job status",
)
async def refresh_status(request: Request) -> JobStatusResponse:
    return JobStatusResponse(**_state(request).jobs.status())


@router.post(
    "/jobs/refresh",
    response_model=JobStatusResponse,
    summary="Start Elexon data refresh",
    responses={409: {"description": "Refresh already running"}},
)
async def refresh_start(request: Request) -> JobStatusResponse:
    status, started = await _state(request).jobs.start()
    if not started:
        raise HTTPException(
            status_code=409,
            detail=ErrorBody(
                code="job_busy",
                message="A refresh job is already running",
            ).model_dump(),
        )
    return JobStatusResponse(**status)

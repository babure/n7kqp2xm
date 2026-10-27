"""Pydantic response models for /api/v1."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"
    cache_ready: bool
    cache_updated_at: str | None = None
    fuelhh_count: int = 0
    windfor_count: int = 0
    last_job: dict[str, Any] | None = None


class ScopeResponse(BaseModel):
    """Configured analysis window — UI should drive all date pickers from this."""

    delivery_from: str
    delivery_to: str
    label: str
    default_delivery_date: str
    gate_local: str
    publish_from: str
    publish_to: str


class DeliveryDay(BaseModel):
    date: str
    has_forecast: bool
    has_actuals: bool


class DeliveryDaysResponse(BaseModel):
    days: list[DeliveryDay]
    scope: ScopeResponse | None = None


class SeriesPoint(BaseModel):
    start_time: str
    forecast_mw: float | None = None
    actual_mw: float | None = None
    settlement_period: int | None = None


class ForecastResponse(BaseModel):
    delivery_date: str
    decision_cutoff: str = Field(
        description="N2EX day-ahead gate: 09:50 Europe/London on D-1"
    )
    publish_time: str | None = None
    uncertainty_mw: float | None = Field(
        default=None,
        description="Historical RMSE used as ± band for procurement buffer",
    )
    series: list[SeriesPoint]
    message: str | None = None


class MetricSummary(BaseModel):
    n: int
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    mape: float | None = None
    p90_abs_error: float | None = None


class DailyMetric(MetricSummary):
    date: str


class PeriodMetric(MetricSummary):
    settlement_period: int


class Heatmap(BaseModel):
    days: list[str]
    periods: list[int]
    values: list[list[float | None]]


class AccuracyResponse(BaseModel):
    from_date: str
    to_date: str
    summary: MetricSummary
    daily: list[DailyMetric]
    by_period: list[PeriodMetric]
    heatmap: Heatmap
    procurement_note: str


class JobStatusResponse(BaseModel):
    status: str
    job_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    duration_ms: int | None = None
    fuelhh_count: int | None = None
    windfor_count: int | None = None

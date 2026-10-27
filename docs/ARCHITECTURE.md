# Architecture

## Purpose

Gridbricks helps a UK utility trading team see the **national wind forecast that was actually available at N2EX day-ahead gate** (default **09:50 Europe/London on D−1**) and measure how accurate those gate-time forecasts were against Elexon outturn. The default analysis window is **January 2026**; the window is config-driven (`AnalysisWindow` / `GET /api/v1/scope`) so other months need env changes only — see [EXTENDING.md](EXTENDING.md).

## Point-in-time rule

For delivery day `D`:

1. Cutoff = `D−1` at the configured gate time (default 09:50) `Europe/London`.
2. Among Elexon `WINDFOR` rows whose `startTime` falls on `D`, keep publishes with `publishTime ≤` cutoff.
3. Use the run with the latest such `publishTime`.
4. Join to `FUELHH` (`fuelType=WIND`) on `startTime`.

This deliberately ignores forecast revisions published after the trader would have acted.

## Extending the analysis window

`backend/app/config.py` owns `AnalysisWindow`. Refresh jobs and services take that object (or `get_window()`); the SPA seeds date pickers from `/api/v1/scope`. Domain modules (`decision.py`, `metrics.py`) stay calendar-agnostic. Step-by-step: [EXTENDING.md](EXTENDING.md).

## Components

| Piece | Role |
|-------|------|
| React + Vite SPA | Decision desk + accuracy views (TanStack Query, Recharts, custom heatmap) |
| FastAPI `/api/v1` | Versioned JSON API with Pydantic models |
| Async refresh job | Pulls Elexon streams into a disk cache; same *status shape* a Celery worker would expose |
| pandas / NumPy | Vectorized error metrics and heatmap matrix |
| Structured logs | JSON lines with `request_id` |

## Why not Celery here

A single Docker process (local Compose or Render) keeps the pilot deployable in one URL. The job API (`POST/GET /api/v1/jobs/refresh`) is intentionally worker-shaped so a Redis/Celery (or RQ) worker can replace the in-process task without changing clients.

## Data sources

- Actuals: `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream`
- Forecasts: `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`

No API key required for these public Insights endpoints.

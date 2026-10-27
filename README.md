# Gridbricks

UK day-ahead **national wind** forecast pilot. Default analysis window is **January 2026** (configurable — see [docs/EXTENDING.md](docs/EXTENDING.md)).

Traders need two things before N2EX gate (~09:50 UK on D−1):

1. The latest Elexon **WINDFOR** publish still available at gate for the delivery day.
2. Quantified error versus **FUELHH** WIND outturn, to size residual cover.

Live app: _<paste Render URL after deploy>_

## Repository layout

```
backend/                 FastAPI app, Elexon client, metrics, tests
  app/
    api/v1/routes.py     Versioned HTTP API
    decision.py          Gate-time forecast selection
    metrics.py           pandas/NumPy accuracy
    jobs/refresh.py      Async ingest job + status
  tests/                 pytest suite (no live Elexon)
frontend/                React + Vite + TypeScript SPA
docs/                    Architecture + how to extend the window
Dockerfile               Multi-stage image (SPA + API)
docker-compose.yml       One-command local run
render.yaml              Render Blueprint (Docker web service)
.github/workflows/ci.yml Backend pytest on push
```

## Quick start (Docker)

```bash
docker compose up --build
```

Open http://localhost:8000  

On first boot the API refreshes Elexon data into a disk cache (one to a few minutes). The UI polls until the cache is ready.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
export SKIP_COLD_REFRESH=1   # optional while iterating on fixtures
uvicorn app.main:app --reload --port 8000
```

Optional prefetch (live Elexon):

```bash
python scripts/prefetch.py
```

Tests:

```bash
pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

## API (v1)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health` | Liveness + cache readiness |
| GET | `/api/v1/scope` | Configured delivery window + gate (drives UI) |
| GET | `/api/v1/delivery-days` | Days in scope + data flags |
| GET | `/api/v1/forecast?delivery_date=YYYY-MM-DD` | Gate-time series + uncertainty band |
| GET | `/api/v1/accuracy?from=&to=` | Metrics, daily, by period, heatmap |
| POST/GET | `/api/v1/jobs/refresh` | Start / inspect cache refresh |

### Extending the date window

Set `GRIDBRICKS_DELIVERY_FROM` / `GRIDBRICKS_DELIVERY_TO` / `GRIDBRICKS_LABEL`, refresh the cache, restart. Details: [docs/EXTENDING.md](docs/EXTENDING.md).

OpenAPI: `/docs`

**Gate assumption:** N2EX day-ahead gate at **09:50 Europe/London** on day D−1. Documented in code and OpenAPI; change in one place (`app/decision.py`) if the desk uses a different cutoff.

## Deploy (Render)

The app ships as one Docker image (React build + FastAPI). On Render:

1. Go to [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**.
2. Connect the GitHub repo `babure/n7kqp2xm` and apply `render.yaml`.
3. Wait for the first Docker build (several minutes). On boot the API cold-refreshes Elexon data — the UI shows a skeleton until `cache_ready` is true.
4. Paste the public URL into **Live app** above.

**Manual (no Blueprint):** New → Web Service → connect repo → **Docker** runtime → root Dockerfile. Health check path: `/api/v1/health`. Free plan is fine for the pilot (service may sleep when idle).

`PORT` is set by Render; the container already binds `0.0.0.0:$PORT`.

## AI tools

AI coding assistants were used to help scaffold and implement this application (boilerplate, tests, and UI wiring). Domain rules (gate-time selection, metrics definitions) and review remain human-owned.

## License

Assessment submission — all rights reserved by the author.

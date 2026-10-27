# Extending Gridbricks beyond January 2026

The pilot ships with **Jan 2026** as the default analysis window. Extending to another month (or a custom range) should not require editing domain logic.

## Design (SOLID)

| Principle | How we apply it |
|-----------|-----------------|
| **S**ingle responsibility | `AnalysisWindow` (`backend/app/config.py`) owns the calendar window. Gate selection, metrics, and UI stay window-agnostic. |
| **O**pen/closed | New periods via env vars (or a new window factory). Do not hardcode months inside `decision.py` / `metrics.py`. |
| **D**ependency inversion | Refresh job and services take `AnalysisWindow` (or `get_window()`), not scattered date literals. |
| **I**nterface segregation | UI reads `GET /api/v1/scope` — one contract for labels and date bounds. |

```text
Env / config  →  AnalysisWindow  →  refresh job (Elexon fetch)
                               →  services (forecast / accuracy)
                               →  GET /api/v1/scope  →  React date pickers
```

## Change the window (typical path)

1. **Set environment variables** (Docker / Heroku / shell):

```bash
export GRIDBRICKS_DELIVERY_FROM=2026-02-01
export GRIDBRICKS_DELIVERY_TO=2026-02-28
export GRIDBRICKS_LABEL="Feb 2026 · GB wind"
```

Optional:

```bash
export GRIDBRICKS_GATE_HOUR=9
export GRIDBRICKS_GATE_MINUTE=50
export GRIDBRICKS_PUBLISH_LEAD_DAYS=2   # WINDFOR history before first delivery day
export GRIDBRICKS_PUBLISH_LAG_DAYS=1
```

2. **Clear or refresh cache** so Elexon data matches the new range:

```bash
# local
rm -rf backend/data/cache/*.json
# or
curl -X POST http://localhost:8000/api/v1/jobs/refresh
```

3. **Restart the API** (process caches `get_window()` once at import).

4. **Reload the UI** — header pill, delivery picks, and accuracy From/To come from `/api/v1/scope`. No frontend rebuild required for a date-only change.

## Docker Compose example

```yaml
services:
  app:
    environment:
      GRIDBRICKS_DELIVERY_FROM: "2026-02-01"
      GRIDBRICKS_DELIVERY_TO: "2026-02-28"
      GRIDBRICKS_LABEL: "Feb 2026 · GB wind"
```

## What you should *not* need to touch

- `app/decision.py` — point-in-time gate logic
- `app/metrics.py` — MAE / RMSE / heatmap math
- Chart components — they plot whatever the API returns

## Adding a new fuel or market later

Keep the same pattern: new adapter (like `elexon.py`) + thin service methods + versioned `/api/v1` routes. Prefer **additive** fields on responses so existing clients keep working.

## Verify

```bash
curl -s http://localhost:8000/api/v1/scope | jq
pytest -q
```

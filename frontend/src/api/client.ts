const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      message = body?.detail?.message ?? body?.detail ?? message
    } catch {
      /* ignore */
    }
    throw new Error(typeof message === 'string' ? message : 'Request failed')
  }
  return res.json() as Promise<T>
}

export type Scope = {
  delivery_from: string
  delivery_to: string
  label: string
  default_delivery_date: string
  gate_local: string
  publish_from: string
  publish_to: string
}

export type DeliveryDay = {
  date: string
  has_forecast: boolean
  has_actuals: boolean
}

export type SeriesPoint = {
  start_time: string
  forecast_mw: number | null
  actual_mw: number | null
  settlement_period: number | null
}

export type ForecastResponse = {
  delivery_date: string
  decision_cutoff: string
  publish_time: string | null
  uncertainty_mw: number | null
  series: SeriesPoint[]
  message: string | null
}

export type MetricSummary = {
  n: number
  mae: number | null
  rmse: number | null
  bias: number | null
  mape: number | null
  p90_abs_error: number | null
}

export type AccuracyResponse = {
  from_date: string
  to_date: string
  summary: MetricSummary
  daily: Array<MetricSummary & { date: string }>
  by_period: Array<MetricSummary & { settlement_period: number }>
  heatmap: {
    days: string[]
    periods: number[]
    values: Array<Array<number | null>>
  }
  procurement_note: string
}

export type HealthResponse = {
  status: string
  cache_ready: boolean
  cache_updated_at: string | null
  fuelhh_count: number
  windfor_count: number
}

export const api = {
  health: () => getJson<HealthResponse>('/api/v1/health'),
  scope: () => getJson<Scope>('/api/v1/scope'),
  deliveryDays: () =>
    getJson<{ days: DeliveryDay[]; scope?: Scope }>('/api/v1/delivery-days').then(
      (r) => r,
    ),
  forecast: (deliveryDate: string) =>
    getJson<ForecastResponse>(
      `/api/v1/forecast?delivery_date=${encodeURIComponent(deliveryDate)}`,
    ),
  accuracy: (from?: string, to?: string) => {
    const params = new URLSearchParams()
    if (from) params.set('from', from)
    if (to) params.set('to', to)
    const q = params.toString()
    return getJson<AccuracyResponse>(`/api/v1/accuracy${q ? `?${q}` : ''}`)
  },
}

/** Inclusive YYYY-MM-DD list between from and to. */
export function daysInRange(from: string, to: string): string[] {
  const out: string[] = []
  const cur = new Date(`${from}T12:00:00Z`)
  const end = new Date(`${to}T12:00:00Z`)
  while (cur <= end) {
    out.push(cur.toISOString().slice(0, 10))
    cur.setUTCDate(cur.getUTCDate() + 1)
  }
  return out
}

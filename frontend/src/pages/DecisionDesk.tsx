import { useDeferredValue, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from 'recharts'
import { api } from '../api/client'
import { ChartFrame } from '../components/charts/ChartFrame'
import { chartMargin, yDomainWithHeadroom } from '../components/charts/chartHelpers'
import { YAxisMw } from '../components/charts/YAxisMw'
import { LoadingOverlay } from '../components/LoadingOverlay'
import { DeskSkeleton } from '../components/Skeleton'
import { useIsNarrow } from '../hooks/useIsNarrow'
import {
  setDeliveryDate,
  setShowActuals,
  setShowBand,
  useUiStore,
} from '../state/uiStore'

function formatTick(iso: string) {
  return new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/London',
  })
}

function formatWhenShort(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    timeZone: 'Europe/London',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDayOption(dateStr: string) {
  return new Date(`${dateStr}T12:00:00Z`).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}

function gw(n: number | null | undefined, digits = 1) {
  if (n == null) return '—'
  return `${(n / 1000).toFixed(digits)} GW`
}

export function DecisionDesk() {
  const ui = useUiStore()
  const narrow = useIsNarrow()
  const deferredDate = useDeferredValue(ui.deliveryDate)

  const daysQuery = useQuery({
    queryKey: ['delivery-days'],
    queryFn: async () => {
      const res = await api.deliveryDays()
      return res.days
    },
  })

  const forecastQuery = useQuery({
    queryKey: ['forecast', deferredDate],
    queryFn: () => api.forecast(deferredDate),
    placeholderData: (prev) => prev,
  })

  const chartData = useMemo(() => {
    const series = forecastQuery.data?.series ?? []
    const band = forecastQuery.data?.uncertainty_mw
    return series.map((p, idx) => {
      const f = p.forecast_mw
      return {
        idx,
        start_time: p.start_time,
        label: formatTick(p.start_time),
        forecast: f,
        actual: p.actual_mw,
        upper: f != null && band != null ? f + band : null,
        lower: f != null && band != null ? Math.max(0, f - band) : null,
      }
    })
  }, [forecastQuery.data])

  const deferredData = useDeferredValue(chartData)
  const band = forecastQuery.data?.uncertainty_mw
  const chartHeight = narrow ? 260 : 340

  const yDomain = useMemo(() => {
    const vals: Array<number | null | undefined> = []
    for (const row of deferredData) {
      vals.push(row.forecast, row.actual, row.upper, row.lower)
    }
    return yDomainWithHeadroom(vals, { floorZero: true, headroom: 0.2 })
  }, [deferredData])

  const peakForecast = useMemo(() => {
    const nums = deferredData
      .map((d) => d.forecast)
      .filter((v): v is number => v != null)
    return nums.length ? Math.max(...nums) : null
  }, [deferredData])

  const headline =
    band != null
      ? `Gate-time wind · ±${(band / 1000).toFixed(1)} GW cover buffer`
      : 'Gate-time national wind'

  return (
    <div className="page">
      <div className="toolbar">
        <label className="day-pick">
          <span>Delivery</span>
          <select
            value={ui.deliveryDate}
            onChange={(e) => setDeliveryDate(e.target.value)}
            disabled={!daysQuery.data}
          >
            {(daysQuery.data ?? [{ date: ui.deliveryDate }]).map((d) => (
              <option key={d.date} value={d.date}>
                {formatDayOption(d.date)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {forecastQuery.isError && (
        <p className="status error">{(forecastQuery.error as Error).message}</p>
      )}

      {forecastQuery.isPending && !forecastQuery.data && (
        <DeskSkeleton compactToolbar />
      )}

      {forecastQuery.data && (
        <div
          className={`content-panel${forecastQuery.isFetching ? ' content-busy' : ''}`}
        >
          <LoadingOverlay
            show={forecastQuery.isFetching}
            label="Updating forecast…"
          />
          <div className="metric-row">
            <div className="metric-card">
              <span className="metric-label">Peak forecast</span>
              <strong className="metric-value">{gw(peakForecast)}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Cover buffer</span>
              <strong className="metric-value">
                {band != null ? `±${(band / 1000).toFixed(1)} GW` : '—'}
              </strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Gate cutoff</span>
              <strong className="metric-value metric-value-sm">
                {formatWhenShort(forecastQuery.data.decision_cutoff)}
              </strong>
            </div>
          </div>

          <div className="desk-grid">
            <section className="card chart-card">
              <div className="card-head">
                <div>
                  <p className="eyebrow">Wind outlook</p>
                  <h1>{headline}</h1>
                </div>
                <div className="card-head-aside">
                  <div className="chart-toggles">
                    <label>
                      <input
                        type="checkbox"
                        checked={ui.showActuals}
                        onChange={(e) => setShowActuals(e.target.checked)}
                      />
                      Outturn
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={ui.showBand}
                        onChange={(e) => setShowBand(e.target.checked)}
                      />
                      Buffer
                    </label>
                  </div>
                  <p className="meta">
                    Forecast @ {formatWhenShort(forecastQuery.data.publish_time)}
                  </p>
                </div>
              </div>

              <ChartFrame
                yLabel="Wind generation (MW)"
                xLabel="Time of day (UK)"
              >
                <ResponsiveContainer width="100%" height={chartHeight}>
                  <ComposedChart
                    data={deferredData}
                    margin={narrow ? chartMargin.narrow : chartMargin.desktop}
                  >
                    <defs>
                      <linearGradient id="forecastFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="var(--accent)" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--grid)" strokeDasharray="4 4" vertical={false} />
                    <XAxis
                      dataKey="label"
                      minTickGap={narrow ? 36 : 28}
                      tick={{ fill: 'var(--muted)', fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxisMw domain={yDomain} narrow={narrow} />
                    <Tooltip
                      contentStyle={{
                        background: '#fff',
                        border: '1px solid var(--line)',
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      formatter={(value, name) => [
                        value == null ? '—' : `${Number(value).toFixed(0)} MW`,
                        String(name),
                      ]}
                    />
                    <Legend
                      verticalAlign="top"
                      align="right"
                      iconType="plainline"
                      wrapperStyle={{ fontSize: 11, paddingBottom: 8 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="forecast"
                      stroke="none"
                      fill="url(#forecastFill)"
                      legendType="none"
                      isAnimationActive={false}
                    />
                    {ui.showBand && (
                      <Line
                        type="monotone"
                        dataKey="upper"
                        name="Upper buffer (+RMSE)"
                        stroke="var(--band)"
                        strokeWidth={1.25}
                        strokeDasharray="3 4"
                        dot={false}
                        isAnimationActive={false}
                      />
                    )}
                    {ui.showBand && (
                      <Line
                        type="monotone"
                        dataKey="lower"
                        name="Lower buffer (−RMSE)"
                        stroke="var(--band)"
                        strokeWidth={1.25}
                        strokeDasharray="3 4"
                        dot={false}
                        isAnimationActive={false}
                      />
                    )}
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      name="Gate-time forecast"
                      stroke="var(--accent)"
                      strokeWidth={2.4}
                      dot={false}
                      isAnimationActive={false}
                    />
                    {ui.showActuals && (
                      <Line
                        type="monotone"
                        dataKey="actual"
                        name="Actual outturn"
                        stroke="var(--actual)"
                        strokeWidth={2}
                        strokeDasharray="5 4"
                        dot={false}
                        isAnimationActive={false}
                      />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartFrame>
            </section>

            <aside className="side-stack">
              <div className="signal-card">
                <p className="signal-kicker">Forecast signal</p>
                <p className="signal-head">Bank the gate-time line</p>
                <p className="signal-body">
                  Use the green profile for day-ahead cover. Add about{' '}
                  {band != null ? `±${band.toFixed(0)} MW` : 'the RMSE buffer'} for
                  residual buys.
                </p>
              </div>
              <div className="watch-card">
                <p className="watch-title">Watch list</p>
                <ul>
                  <li>Ignore post-gate forecast revisions</li>
                  <li>
                    <Link to="/accuracy">Check forecast miss stats</Link>
                  </li>
                </ul>
              </div>
            </aside>
          </div>
        </div>
      )}
    </div>
  )
}

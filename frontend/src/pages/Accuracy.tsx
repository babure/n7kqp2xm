import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from 'recharts'
import { api, daysInRange } from '../api/client'
import { ChartFrame } from '../components/charts/ChartFrame'
import { chartMargin, yDomainWithHeadroom } from '../components/charts/chartHelpers'
import { YAxisMw } from '../components/charts/YAxisMw'
import { ErrorHeatmap } from '../components/ErrorHeatmap'
import { LoadingOverlay } from '../components/LoadingOverlay'
import { AccuracySkeleton } from '../components/Skeleton'
import { useIsNarrow } from '../hooks/useIsNarrow'
import { setAccuracyRange, useUiStore } from '../state/uiStore'

function gw(n: number | null | undefined) {
  if (n == null) return '—'
  return `${(n / 1000).toFixed(1)} GW`
}

function formatDayOption(dateStr: string) {
  return new Date(`${dateStr}T12:00:00Z`).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}

export function Accuracy() {
  const ui = useUiStore()
  const narrow = useIsNarrow(900)
  const days = useMemo(() => {
    if (!ui.scope) return []
    return daysInRange(ui.scope.delivery_from, ui.scope.delivery_to)
  }, [ui.scope])

  const accuracyQuery = useQuery({
    queryKey: ['accuracy', ui.accuracyFrom, ui.accuracyTo],
    queryFn: () => api.accuracy(ui.accuracyFrom, ui.accuracyTo),
    placeholderData: (prev) => prev,
  })

  const summary = accuracyQuery.data?.summary
  const chartH = narrow ? 150 : 132

  const dailyDomain = useMemo(
    () =>
      yDomainWithHeadroom(
        (accuracyQuery.data?.daily ?? []).map((d) => d.mae),
        { floorZero: true, headroom: 0.22 },
      ),
    [accuracyQuery.data?.daily],
  )

  const periodDomain = useMemo(
    () =>
      yDomainWithHeadroom(
        (accuracyQuery.data?.by_period ?? []).map((d) => d.mae),
        { floorZero: true, headroom: 0.22 },
      ),
    [accuracyQuery.data?.by_period],
  )

  if (accuracyQuery.isPending && !accuracyQuery.data) {
    return <AccuracySkeleton />
  }

  return (
    <div className="page page-accuracy">
      <div className="toolbar accuracy-toolbar">
        <div className="range-pick">
          <label className="day-pick">
            <span>From</span>
            <select
              value={ui.accuracyFrom}
              onChange={(e) => setAccuracyRange(e.target.value, ui.accuracyTo)}
            >
              {days.map((d) => (
                <option key={d} value={d}>
                  {formatDayOption(d)}
                </option>
              ))}
            </select>
          </label>
          <label className="day-pick">
            <span>To</span>
            <select
              value={ui.accuracyTo}
              onChange={(e) => setAccuracyRange(ui.accuracyFrom, e.target.value)}
            >
              {days.map((d) => (
                <option key={d} value={d}>
                  {formatDayOption(d)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {summary && (
          <div className="metric-inline" aria-label="Summary metrics">
            <div className="metric-pill">
              <span className="metric-label">MAE</span>
              <strong>{gw(summary.mae)}</strong>
            </div>
            <div className="metric-pill">
              <span className="metric-label">RMSE</span>
              <strong>{gw(summary.rmse)}</strong>
            </div>
            <div className="metric-pill">
              <span className="metric-label">Bias</span>
              <strong>
                {summary.bias == null
                  ? '—'
                  : `${summary.bias >= 0 ? '+' : ''}${gw(summary.bias)}`}
              </strong>
            </div>
          </div>
        )}
      </div>

      {accuracyQuery.isError && (
        <p className="status error">{(accuracyQuery.error as Error).message}</p>
      )}

      {accuracyQuery.data && summary && (
        <div
          className={`content-panel content-panel-tight${accuracyQuery.isFetching ? ' content-busy' : ''}`}
        >
          <LoadingOverlay show={accuracyQuery.isFetching} label="Updating accuracy…" />

          <div className="accuracy-board">
            <div className="charts-duo">
              <section className="card chart-card">
                <p className="section-label">Daily MAE</p>
                <ChartFrame yLabel="MW" xLabel="Delivery day">
                  <ResponsiveContainer width="100%" height={chartH}>
                    <LineChart
                      data={accuracyQuery.data.daily}
                      margin={narrow ? chartMargin.narrow : chartMargin.desktop}
                    >
                      <CartesianGrid stroke="var(--grid)" strokeDasharray="4 4" vertical={false} />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: 'var(--muted)', fontSize: 10 }}
                        minTickGap={narrow ? 36 : 28}
                        tickFormatter={(v: string) => v.slice(5)}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxisMw domain={dailyDomain} narrow={narrow} />
                      <Tooltip
                        formatter={(value) => [`${Number(value).toFixed(0)} MW`, 'Daily MAE']}
                        labelFormatter={(label) => `Delivery ${label}`}
                      />
                      <Line
                        type="monotone"
                        dataKey="mae"
                        name="Daily MAE"
                        stroke="var(--accent)"
                        strokeWidth={2.25}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartFrame>
              </section>

              <section className="card chart-card">
                <p className="section-label">By settlement period</p>
                <ChartFrame yLabel="MW" xLabel="SP 1–48">
                  <ResponsiveContainer width="100%" height={chartH}>
                    <BarChart
                      data={accuracyQuery.data.by_period}
                      margin={narrow ? chartMargin.narrow : chartMargin.desktop}
                    >
                      <CartesianGrid stroke="var(--grid)" strokeDasharray="4 4" vertical={false} />
                      <XAxis
                        dataKey="settlement_period"
                        tick={{ fill: 'var(--muted)', fontSize: 10 }}
                        interval={narrow ? 5 : 3}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxisMw domain={periodDomain} narrow={narrow} />
                      <Tooltip
                        formatter={(value) => [`${Number(value).toFixed(0)} MW`, 'Period MAE']}
                        labelFormatter={(label) => `Settlement period ${label}`}
                      />
                      <Bar
                        dataKey="mae"
                        name="Period MAE"
                        fill="var(--accent)"
                        fillOpacity={0.8}
                        radius={[2, 2, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartFrame>
              </section>
            </div>

            <section className="card chart-card heatmap-card">
              <div className="card-head card-head-tight">
                <p className="section-label">Error heatmap · forecast − actual</p>
                <p className="meta heatmap-axis-meta">rows = days · columns = settlement periods</p>
              </div>
              <ErrorHeatmap
                days={accuracyQuery.data.heatmap.days}
                periods={accuracyQuery.data.heatmap.periods}
                values={accuracyQuery.data.heatmap.values}
              />
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

import { Fragment, useMemo, useState } from 'react'

type Props = {
  days: string[]
  periods: number[]
  values: Array<Array<number | null>>
}

type Tip = {
  x: number
  y: number
  day: string
  period: number
  value: number | null
}

function colorFor(value: number | null, maxAbs: number): string {
  if (value === null || maxAbs === 0) return 'var(--heat-empty)'
  const t = Math.max(-1, Math.min(1, value / maxAbs))
  if (t >= 0) {
    const a = 0.2 + 0.75 * t
    return `rgba(196, 92, 58, ${a})`
  }
  const a = 0.2 + 0.75 * -t
  return `rgba(31, 107, 74, ${a})`
}

function fmtMw(n: number): string {
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)} GW`
  return `${Math.round(n)} MW`
}

function formatDayLong(dateStr: string) {
  return new Date(`${dateStr}T12:00:00Z`).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

/** Settlement period 1–48 → London clock window (approx). */
function periodClock(period: number): string {
  const startMin = (period - 1) * 30
  const endMin = startMin + 30
  const fmt = (m: number) =>
    `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
  return `${fmt(startMin)}–${fmt(endMin)}`
}

function errorMeaning(value: number | null): string {
  if (value == null) return 'No paired forecast / outturn'
  if (Math.abs(value) < 50) return 'Near zero — forecast matched outturn'
  if (value > 0) return 'Over-forecast — less wind than expected'
  return 'Under-forecast — more wind than expected'
}

/** Show only a few axis ticks so the matrix stays readable. */
function showAxisTick(index: number, total: number, targetTicks: number): boolean {
  if (total <= targetTicks) return true
  if (index === 0 || index === total - 1) return true
  const step = Math.max(1, Math.ceil((total - 1) / (targetTicks - 1)))
  return index % step === 0
}

/** Dense error matrix — sparse axis labels; detail on hover. */
export function ErrorHeatmap({ days, periods, values }: Props) {
  const [tip, setTip] = useState<Tip | null>(null)

  const maxAbs = useMemo(() => {
    let m = 0
    for (const row of values) {
      for (const v of row) {
        if (v !== null) m = Math.max(m, Math.abs(v))
      }
    }
    return m
  }, [values])

  const scaleMax = maxAbs > 0 ? maxAbs : 1
  const rowPx = days.length > 20 ? 7 : days.length > 10 ? 9 : 12

  return (
    <div
      className="heatmap-wrap"
      onMouseLeave={() => setTip(null)}
    >
      <div
        className="heatmap"
        style={{
          gridTemplateColumns: `2rem repeat(${periods.length}, minmax(0, 1fr))`,
          ['--heat-row' as string]: `${rowPx}px`,
        }}
      >
        <div className="heatmap-corner" aria-hidden />
        {periods.map((p, pi) => (
          <div key={p} className="heatmap-colhead">
            {showAxisTick(pi, periods.length, 7) ? p : ''}
          </div>
        ))}
        {days.map((day, di) => (
          <Fragment key={day}>
            <div className="heatmap-rowhead" aria-hidden={!showAxisTick(di, days.length, 6)}>
              {showAxisTick(di, days.length, 6) ? day.slice(5) : ''}
            </div>
            {periods.map((p, pi) => {
              const v = values[di]?.[pi] ?? null
              return (
                <div
                  key={`${day}-${p}`}
                  className={`heatmap-cell${tip?.day === day && tip.period === p ? ' is-active' : ''}`}
                  style={{ background: colorFor(v, maxAbs) }}
                  onMouseEnter={(e) => {
                    const r = e.currentTarget.getBoundingClientRect()
                    setTip({
                      x: r.left + r.width / 2,
                      y: r.top,
                      day,
                      period: p,
                      value: v,
                    })
                  }}
                  onMouseMove={(e) => {
                    setTip((prev) =>
                      prev
                        ? { ...prev, x: e.clientX, y: e.clientY }
                        : prev,
                    )
                  }}
                />
              )
            })}
          </Fragment>
        ))}
      </div>

      {tip && (
        <div
          className="heatmap-tip"
          style={{ left: tip.x, top: tip.y }}
          role="tooltip"
        >
          <p className="heatmap-tip-day">{formatDayLong(tip.day)}</p>
          <dl className="heatmap-tip-meta">
            <div>
              <dt>Settlement period</dt>
              <dd>
                SP {tip.period} · {periodClock(tip.period)}
              </dd>
            </div>
            <div>
              <dt>Forecast − actual</dt>
              <dd>
                {tip.value == null
                  ? '—'
                  : `${tip.value > 0 ? '+' : ''}${fmtMw(tip.value)}`}
              </dd>
            </div>
            <div>
              <dt>Reading</dt>
              <dd>{errorMeaning(tip.value)}</dd>
            </div>
          </dl>
        </div>
      )}

      <div className="heatmap-legend-compact" aria-label="Colour meaning">
        <div className="spectrum spectrum-inline">
          <div className="spectrum-bar" aria-hidden />
          <div className="spectrum-ticks">
            <span>−{fmtMw(scaleMax)}</span>
            <span>0</span>
            <span>+{fmtMw(scaleMax)}</span>
          </div>
        </div>
        <p className="heatmap-legend-hint">
          <span className="swatch swatch-under" aria-hidden /> under-forecast
          <span className="legend-sep" aria-hidden>
            ·
          </span>
          <span className="swatch swatch-neutral" aria-hidden /> near zero
          <span className="legend-sep" aria-hidden>
            ·
          </span>
          <span className="swatch swatch-over" aria-hidden /> over-forecast
          <span className="legend-sep" aria-hidden>
            ·
          </span>
          hover a cell for detail
        </p>
      </div>
    </div>
  )
}

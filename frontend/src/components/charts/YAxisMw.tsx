import { YAxis } from 'recharts'
import { formatMwTick } from './chartHelpers'

type Props = {
  domain: [number, number]
  narrow?: boolean
}

/**
 * Tick-only Y axis. Axis titles are rendered outside the SVG
 * (see ChartFrame) so they never collide with tick labels.
 */
export function YAxisMw({ domain, narrow }: Props) {
  const top = domain[1]
  return (
    <YAxis
      domain={domain}
      allowDataOverflow={false}
      ticks={buildTicks(domain)}
      width={narrow ? 40 : 46}
      tickMargin={6}
      tick={(props) => {
        const { x, y, payload } = props
        const isTop = payload.value === top
        return (
          <text
            x={x}
            y={y}
            dy={isTop ? 10 : 3}
            dx={-2}
            textAnchor="end"
            fill="var(--muted)"
            fontSize={narrow ? 10 : 11}
          >
            {formatMwTick(payload.value)}
          </text>
        )
      }}
      axisLine={false}
      tickLine={false}
    />
  )
}

function buildTicks([min, max]: [number, number]): number[] {
  const steps = 4
  const out: number[] = []
  for (let i = 0; i <= steps; i++) {
    out.push(min + ((max - min) * i) / steps)
  }
  return out
}

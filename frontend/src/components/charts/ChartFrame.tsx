import type { ReactNode } from 'react'

type Props = {
  yLabel: string
  xLabel: string
  children: ReactNode
  className?: string
}

/** Chart shell with HTML axis titles — avoids Recharts label/tick overlap. */
export function ChartFrame({ yLabel, xLabel, children, className = '' }: Props) {
  return (
    <div className={`chart-shell ${className}`.trim()}>
      <div className="chart-shell-body">
        <span className="chart-y-label" aria-hidden>
          {yLabel}
        </span>
        <div className="chart-frame short chart-frame-plot">{children}</div>
      </div>
      <span className="chart-x-label">{xLabel}</span>
    </div>
  )
}

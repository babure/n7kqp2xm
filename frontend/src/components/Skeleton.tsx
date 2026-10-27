function Bone({ className = '' }: { className?: string }) {
  return <div className={`skel ${className}`.trim()} aria-hidden />
}

/**
 * Matches Decision desk output:
 * toolbar (Delivery) → metrics (Peak / Buffer / Gate) → desk-grid (chart + side stack).
 * compactToolbar: content only (parent already renders the Delivery toolbar).
 */
export function DeskSkeleton({ compactToolbar = false }: { compactToolbar?: boolean }) {
  const body = (
    <div className="content-panel" aria-busy="true" aria-label="Loading outlook">
      <div className="metric-row">
        {[0, 1, 2].map((i) => (
          <div key={i} className="metric-card">
            <Bone className="skel-metric-label" />
            <Bone className="skel-metric-value" />
          </div>
        ))}
      </div>

      <div className="desk-grid">
        <section className="card chart-card">
          <div className="card-head">
            <div>
              <Bone className="skel-eyebrow" />
              <Bone className="skel-title" />
            </div>
            <div className="card-head-aside">
              <div className="chart-toggles">
                <Bone className="skel-toggle" />
                <Bone className="skel-toggle" />
              </div>
              <Bone className="skel-meta" />
            </div>
          </div>
          <Bone className="skel-chart" />
        </section>

        <aside className="side-stack">
          <div className="signal-card skel-card-pad">
            <Bone className="skel-eyebrow" />
            <Bone className="skel-title" />
            <Bone className="skel-line" />
            <Bone className="skel-line skel-line-short" />
          </div>
          <div className="watch-card skel-card-pad skel-watch">
            <Bone className="skel-eyebrow skel-on-dark" />
            <Bone className="skel-line skel-on-dark" />
            <Bone className="skel-line skel-line-short skel-on-dark" />
          </div>
        </aside>
      </div>
    </div>
  )

  if (compactToolbar) return body

  return (
    <div className="page" aria-busy="true" aria-label="Loading outlook">
      <div className="toolbar">
        <div className="day-pick">
          <Bone className="skel-label" />
          <Bone className="skel-select" />
        </div>
      </div>
      {body}
    </div>
  )
}

/** Matches Accuracy: toolbar metrics + duo charts + full-width heatmap */
export function AccuracySkeleton() {
  return (
    <div className="page page-accuracy" aria-busy="true" aria-label="Loading accuracy">
      <div className="toolbar accuracy-toolbar">
        <div className="range-pick">
          <div className="day-pick">
            <Bone className="skel-label" />
            <Bone className="skel-select" />
          </div>
          <div className="day-pick">
            <Bone className="skel-label" />
            <Bone className="skel-select" />
          </div>
        </div>
        <div className="metric-inline">
          {[0, 1, 2].map((i) => (
            <div key={i} className="metric-pill">
              <Bone className="skel-metric-label" />
              <Bone className="skel-metric-value" />
            </div>
          ))}
        </div>
      </div>
      <div className="content-panel content-panel-tight">
        <div className="accuracy-board">
          <div className="charts-duo">
            <section className="card chart-card">
              <Bone className="skel-section-label" />
              <Bone className="skel-chart skel-chart-sm" />
            </section>
            <section className="card chart-card">
              <Bone className="skel-section-label" />
              <Bone className="skel-chart skel-chart-sm" />
            </section>
          </div>
          <section className="card chart-card">
            <Bone className="skel-section-label" />
            <Bone className="skel-chart skel-chart-sm" />
          </section>
        </div>
      </div>
    </div>
  )
}

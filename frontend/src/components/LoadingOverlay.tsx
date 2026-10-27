type Props = {
  show: boolean
  label?: string
}

/** Blur/dim host content and show a centered spinner while refetching. */
export function LoadingOverlay({ show, label = 'Loading' }: Props) {
  if (!show) return null
  return (
    <div className="loading-overlay" role="status" aria-live="polite" aria-label={label}>
      <div className="loading-panel">
        <span className="spinner" aria-hidden />
        <span className="loading-text">{label}</span>
      </div>
    </div>
  )
}

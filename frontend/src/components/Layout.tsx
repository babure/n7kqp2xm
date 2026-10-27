import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useUiStore } from '../state/uiStore'

const LOGO_FALLBACK =
  'https://photos.wellfound.com/startups/i/11073428-222f03969dfb804307de1e11d5f2cffa-medium_jpg.jpg?buster=1782640292'

export function Layout() {
  const ui = useUiStore()
  const health = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    staleTime: 60_000,
  })

  const updated = health.data?.cache_updated_at
    ? new Date(health.data.cache_updated_at).toLocaleString('en-GB', {
        timeZone: 'UTC',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      })
    : null

  const scopeLabel = ui.scope?.label ?? 'GB wind'

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-left">
          <img
            className="brand-logo"
            src="/logo.png"
            alt=""
            width={32}
            height={32}
            onError={(e) => {
              const img = e.currentTarget
              if (img.dataset.fallbackApplied === '1') return
              img.dataset.fallbackApplied = '1'
              img.src = LOGO_FALLBACK
            }}
          />
          <span className="pill">Gridbricks</span>
          <span className="pill pill-accent">{scopeLabel}</span>
          <nav className="nav" aria-label="Primary">
            <NavLink to="/" end>
              Outlook
            </NavLink>
            <NavLink to="/accuracy">Accuracy</NavLink>
          </nav>
        </div>
        {updated && <p className="updated">Updated {updated}</p>}
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}

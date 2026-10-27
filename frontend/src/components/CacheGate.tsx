import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { AccuracySkeleton, DeskSkeleton } from './Skeleton'

export function CacheGate({ children }: { children: ReactNode }) {
  const location = useLocation()
  const health = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: (q) => (q.state.data?.cache_ready ? false : 3000),
  })

  if (health.isLoading || (health.data && !health.data.cache_ready)) {
    return location.pathname.startsWith('/accuracy') ? (
      <AccuracySkeleton />
    ) : (
      <DeskSkeleton />
    )
  }

  if (health.isError) {
    return (
      <div className="card pad">
        <p className="eyebrow">Offline</p>
        <h1>API unavailable</h1>
        <p className="signal-body">Start the backend or Docker Compose, then refresh.</p>
      </div>
    )
  }

  return <>{children}</>
}

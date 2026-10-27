import { useQuery } from '@tanstack/react-query'
import { useEffect, type ReactNode } from 'react'
import { api } from '../api/client'
import { applyScope } from '../state/uiStore'
import { DeskSkeleton } from './Skeleton'

/** Loads GET /api/v1/scope and seeds the UI store before pages render. */
export function ScopeBootstrap({ children }: { children: ReactNode }) {
  const scopeQuery = useQuery({
    queryKey: ['scope'],
    queryFn: api.scope,
    staleTime: 5 * 60_000,
  })

  useEffect(() => {
    if (scopeQuery.data) applyScope(scopeQuery.data)
  }, [scopeQuery.data])

  if (scopeQuery.isPending) {
    return <DeskSkeleton />
  }

  if (scopeQuery.isError) {
    return (
      <div className="card pad">
        <p className="eyebrow">Config</p>
        <h1>Could not load analysis scope</h1>
        <p className="signal-body">{(scopeQuery.error as Error).message}</p>
      </div>
    )
  }

  return <>{children}</>
}

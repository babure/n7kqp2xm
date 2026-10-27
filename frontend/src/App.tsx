import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { CacheGate } from './components/CacheGate'
import { Layout } from './components/Layout'
import { ScopeBootstrap } from './components/ScopeBootstrap'
import { Accuracy } from './pages/Accuracy'
import { DecisionDesk } from './pages/DecisionDesk'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ScopeBootstrap>
          <Routes>
            <Route element={<Layout />}>
              <Route
                index
                element={
                  <CacheGate>
                    <DecisionDesk />
                  </CacheGate>
                }
              />
              <Route
                path="accuracy"
                element={
                  <CacheGate>
                    <Accuracy />
                  </CacheGate>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </ScopeBootstrap>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

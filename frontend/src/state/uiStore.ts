import { useSyncExternalStore } from 'react'
import type { Scope } from '../api/client'

type UiState = {
  scope: Scope | null
  deliveryDate: string
  accuracyFrom: string
  accuracyTo: string
  showActuals: boolean
  showBand: boolean
  brushStart: number | null
  brushEnd: number | null
  scopeReady: boolean
}

type Listener = () => void

let state: UiState = {
  scope: null,
  deliveryDate: '2026-01-15',
  accuracyFrom: '2026-01-01',
  accuracyTo: '2026-01-31',
  showActuals: true,
  showBand: true,
  brushStart: null,
  brushEnd: null,
  scopeReady: false,
}

const listeners = new Set<Listener>()

function emit() {
  listeners.forEach((l) => l())
}

export function getUiState() {
  return state
}

export function subscribeUi(listener: Listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Apply server scope — drives all date pickers (open for extension). */
export function applyScope(scope: Scope) {
  const sameWindow =
    state.scopeReady &&
    state.scope?.delivery_from === scope.delivery_from &&
    state.scope?.delivery_to === scope.delivery_to
  if (sameWindow) {
    state = { ...state, scope }
    emit()
    return
  }
  state = {
    ...state,
    scope,
    scopeReady: true,
    deliveryDate: scope.default_delivery_date,
    accuracyFrom: scope.delivery_from,
    accuracyTo: scope.delivery_to,
  }
  emit()
}

export function setDeliveryDate(date: string) {
  state = { ...state, deliveryDate: date, brushStart: null, brushEnd: null }
  emit()
}

export function setAccuracyRange(from: string, to: string) {
  let nextFrom = from
  let nextTo = to
  if (nextFrom > nextTo) {
    nextFrom = to
    nextTo = from
  }
  state = { ...state, accuracyFrom: nextFrom, accuracyTo: nextTo }
  emit()
}

export function setShowActuals(value: boolean) {
  state = { ...state, showActuals: value }
  emit()
}

export function setShowBand(value: boolean) {
  state = { ...state, showBand: value }
  emit()
}

export function setBrushRange(start: number | null, end: number | null) {
  state = { ...state, brushStart: start, brushEnd: end }
  emit()
}

export function useUiStore() {
  return useSyncExternalStore(subscribeUi, getUiState, getUiState)
}

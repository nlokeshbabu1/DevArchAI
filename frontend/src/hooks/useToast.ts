import { useCallback, useSyncExternalStore } from 'react'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastItem {
  id: string
  type: ToastType
  message: string
}

let toasts: ToastItem[] = []
let listeners = new Set<() => void>()
let idCounter = 0

function emit() {
  listeners.forEach((l) => l())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function getSnapshot() {
  return toasts
}

export function toast(message: string, type: ToastType = 'info') {
  const id = String(++idCounter)
  toasts = [...toasts, { id, type, message }]
  emit()
  window.setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id)
    emit()
  }, 4000)
}

toast.success = (message: string) => toast(message, 'success')
toast.error = (message: string) => toast(message, 'error')
toast.info = (message: string) => toast(message, 'info')

export function useToast() {
  const items = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
  const dismiss = useCallback((id: string) => {
    toasts = toasts.filter((t) => t.id !== id)
    emit()
  }, [])
  return { toasts, dismiss }
}

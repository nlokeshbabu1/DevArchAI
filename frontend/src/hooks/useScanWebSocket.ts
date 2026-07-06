import { useEffect, useRef, useCallback, useState } from 'react'
import { buildWebSocketUrl } from '../lib/api'

export interface WSMessage {
  type: string
  data: Record<string, any>
}

interface UseScanWebSocketOptions {
  scanId: string | null
  enabled?: boolean
  onMessage?: (message: WSMessage) => void
  onProgress?: (data: Record<string, any>) => void
  onComplete?: (data: Record<string, any>) => void
  onFailed?: (data: Record<string, any>) => void
  onAIComplete?: (data: Record<string, any>) => void
  onLog?: (message: string) => void
}

export function useScanWebSocket({
  scanId,
  enabled = true,
  onMessage,
  onProgress,
  onComplete,
  onFailed,
  onAIComplete,
  onLog,
}: UseScanWebSocketOptions) {
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'failed'>('disconnected')
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const maxRetries = 3
  const mountedRef = useRef(false)
  const enabledRef = useRef(enabled)
  const scanIdRef = useRef(scanId)

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  useEffect(() => {
    scanIdRef.current = scanId
  }, [scanId])

  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onopen = null
      wsRef.current.onmessage = null
      wsRef.current.onerror = null
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!scanIdRef.current || !enabledRef.current) return

    const token = localStorage.getItem('access_token') || ''
    const wsUrl = `${buildWebSocketUrl(`/ws/scan/${scanIdRef.current}`)}?token=${encodeURIComponent(token)}`

    cleanup()
    setConnectionStatus('connecting')
    setError(null)

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close()
        return
      }
      setConnectionStatus('connected')
      retryCountRef.current = 0
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const message = JSON.parse(event.data) as WSMessage
        const { type, data } = message

        onMessage?.(message)

        switch (type) {
          case 'progress_update':
            onProgress?.(data || {})
            break
          case 'scan_complete':
            setConnectionStatus('disconnected')
            onComplete?.(data || {})
            break
          case 'scan_failed':
            setConnectionStatus('disconnected')
            onFailed?.(data || {})
            break
          case 'ai_complete':
            onAIComplete?.(data || {})
            break
          case 'log_message':
            onLog?.(data?.message || '')
            break
        }
      } catch {
        // Ignore parse errors
      }
    }

    ws.onerror = () => {
      setError('WebSocket connection error')
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      wsRef.current = null
      if (retryCountRef.current < maxRetries && enabledRef.current && scanIdRef.current) {
        retryCountRef.current++
        const delay = Math.pow(2, retryCountRef.current) * 1000
        setTimeout(connect, delay)
      } else {
        setConnectionStatus('failed')
      }
    }
  }, [cleanup, onMessage, onProgress, onComplete, onFailed, onAIComplete, onLog])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      cleanup()
    }
  }, [connect, cleanup])

  return { connectionStatus, error }
}

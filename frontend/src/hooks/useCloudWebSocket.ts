import { useEffect, useRef, useCallback, useState } from 'react'
import { buildWebSocketUrl } from '../lib/api'
import { useCloudStore } from '../stores/cloud-store'
import type { CloudWSMessage } from '../api/endpoints/cloud'

interface UseCloudWebSocketOptions {
  connectionId: string | null
  enabled?: boolean
  onComplete?: () => void
  onFailed?: (error: string) => void
}

const HEARTBEAT_INTERVAL_MS = 15_000
const HEARTBEAT_TIMEOUT_MS = 10_000
const MAX_RECONNECT = 10
const BASE_DELAY_MS = 1000
const MAX_DELAY_MS = 30_000

export function useCloudWebSocket({
  connectionId,
  enabled = true,
  onComplete,
  onFailed,
}: UseCloudWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const callbacksRef = useRef({ onComplete, onFailed })
  callbacksRef.current = { onComplete, onFailed }

  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected' | 'failed'>('idle')

  const {
    setScanInProgress,
    setScanProgress,
    setScanStage,
    setOverview,
    setError,
  } = useCloudStore()

  const cleanup = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
    }
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
      reconnectTimeout.current = null
    }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!connectionId || !enabled) return
    cleanup()

    setConnectionStatus('connecting')
    const url = buildWebSocketUrl(`/ws/cloud/${connectionId}`)

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnectionStatus('connected')
        reconnectAttempts.current = 0

        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, HEARTBEAT_INTERVAL_MS)
      }

      ws.onmessage = (event) => {
        try {
          const msg: CloudWSMessage = JSON.parse(event.data)
          if (msg.type === 'pong') return

          const data = msg.data || {}

          switch (msg.type) {
            case 'connection_ack':
              break

            case 'stage_start':
              setScanStage((data.stage as string) || '')
              setScanProgress(0)
              setScanInProgress(true)
              break

            case 'stage_progress':
              setScanStage((data.stage as string) || '')
              setScanProgress((data.progress as number) || 0)
              break

            case 'stage_complete':
              setScanProgress(100)
              break

            case 'finding_discovered':
              break

            case 'scan_complete':
              setScanInProgress(false)
              setScanProgress(100)
              setScanStage('completed')
              callbacksRef.current.onComplete?.()
              break

            case 'scan_failed':
              setScanInProgress(false)
              setScanStage('failed')
              setError((data.error as string) || 'Scan failed')
              callbacksRef.current.onFailed?.((data.error as string) || 'Scan failed')
              break
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onerror = () => {
        setConnectionStatus('failed')
      }

      ws.onclose = () => {
        setConnectionStatus('disconnected')
        if (heartbeatRef.current) {
          clearInterval(heartbeatRef.current)
          heartbeatRef.current = null
        }

        if (reconnectAttempts.current < MAX_RECONNECT && enabled) {
          const delay = Math.min(
            BASE_DELAY_MS * Math.pow(2, reconnectAttempts.current),
            MAX_DELAY_MS,
          )
          reconnectAttempts.current += 1
          reconnectTimeout.current = setTimeout(connect, delay)
        }
      }
    } catch {
      setConnectionStatus('failed')
    }
  }, [connectionId, enabled, cleanup, setScanStage, setScanProgress, setScanInProgress, setError])

  useEffect(() => {
    connect()
    return cleanup
  }, [connect, cleanup])

  return { connectionStatus }
}

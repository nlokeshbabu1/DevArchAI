import { useState, useCallback, useRef, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { scansApi } from '../api/endpoints/scans'
import apiClient from '../api/endpoints/client'

const DEBUG = true

function debugLog(...args: any[]) {
  if (DEBUG) {
    console.warn('[ScanSync]', ...args)
  }
}

export interface ScanProgress {
  progress: number
  currentStep?: string
  status: string
  steps?: Array<{ name: string; status: string; progress: number }>
  logs?: string[]
  detected_stack?: string[]
  error_message?: string | null
}

export interface ScanState {
  isActive: boolean
  isScanning: boolean
  isComplete: boolean
  isFailed: boolean
  progress: ScanProgress
  scanId: string | null
  error: string | null
  isAiPending: boolean
  aiProgress: { current: number; total: number }
}

const initialProgress: ScanProgress = {
  progress: 0,
  status: 'idle',
  currentStep: '',
  steps: [],
  logs: [],
  detected_stack: [],
}

const initialState: ScanState = {
  isActive: false,
  isScanning: false,
  isComplete: false,
  isFailed: false,
  progress: initialProgress,
  scanId: null,
  error: null,
  isAiPending: false,
  aiProgress: { current: 0, total: 0 },
}

const POLL_INTERVAL_MS = 2000
const MAX_POLL_ERRORS = 5

interface UseRepositoryScanOptions {
  repositoryUrl: string
  repositoryId?: string
  branch?: string
  queryKeysToInvalidate?: string[][]
}

function isTerminalStatus(status: string): boolean {
  return status === 'completed' || status === 'failed' || status === 'cancelled'
}

function isScanningStatus(status: string): boolean {
  return status === 'running' || status === 'pending' || status === 'processing' || status === 'queued' || status === 'starting'
}

export function useRepositoryScan(options: UseRepositoryScanOptions) {
  const queryClient = useQueryClient()
  const [state, setState] = useState<ScanState>(initialState)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)
  const optionsRef = useRef(options)
  const statusAtLastPollRef = useRef<string>('idle')
  const pollErrorCountRef = useRef(0)

  useEffect(() => {
    optionsRef.current = options
  }, [options])

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  const startPolling = useCallback((scanId: string) => {
    stopPolling()
    pollErrorCountRef.current = 0

    pollingRef.current = setInterval(async () => {
      if (!mountedRef.current) return
      try {
        const response = await apiClient.get(`/scan/status/${scanId}`)
        const pollData = response.data as Record<string, any>
        const status: string = pollData.status || ''
        const progress: number = typeof pollData.progress === 'number' ? pollData.progress : 0
        const currentStep: string = pollData.current_step || pollData.currentStep || ''
        const steps = pollData.steps || []
        const logs = pollData.logs || []
        const detected_stack = pollData.detected_stack || []
        const error_message = pollData.error_message || null

        const prevStatus = statusAtLastPollRef.current
        statusAtLastPollRef.current = status

        const terminal = isTerminalStatus(status)
        const scanning = isScanningStatus(status)

        pollErrorCountRef.current = 0

        debugLog(
          `Poll OK: scanId=${scanId} status=${status} progress=${progress}% ` +
          `prev=${prevStatus} terminal=${terminal} scanning=${scanning} step=${currentStep}`
        )

        setState(prev => ({
          ...prev,
          progress: {
            ...prev.progress,
            progress,
            currentStep,
            status,
            steps,
            logs,
            detected_stack,
          },
          isComplete: terminal && status === 'completed',
          isFailed: terminal && (status === 'failed' || status === 'cancelled'),
          isScanning: scanning,
          isActive: scanning,
          error: error_message,
        }))

        if (terminal) {
          debugLog(`Terminal status detected (${status}), stopping polling for scan ${scanId}`)
          stopPolling()
        }
      } catch (err) {
        pollErrorCountRef.current++
        debugLog(`Poll error (${pollErrorCountRef.current}/${MAX_POLL_ERRORS}):`, err, `scanId=${scanId}`)
        if (pollErrorCountRef.current >= MAX_POLL_ERRORS) {
          debugLog(`Too many poll errors (${MAX_POLL_ERRORS}), stopping polling for scan ${scanId}`)
          stopPolling()
        }
      }
    }, POLL_INTERVAL_MS)
  }, [stopPolling])

  const invalidateRelevantQueries = useCallback(async () => {
    const opts = optionsRef.current
    const keys = [
      queryClient.invalidateQueries({ queryKey: ['repositories'] }),
      queryClient.invalidateQueries({ queryKey: ['scans'] }),
      ...(opts.queryKeysToInvalidate?.map(k => queryClient.invalidateQueries({ queryKey: k })) || []),
    ]
    debugLog('Invalidating queries:', keys.length)
    await Promise.all(keys)
  }, [queryClient])

  const startScan = useCallback(async () => {
    const opts = optionsRef.current
    if (!opts.repositoryUrl) return

    setState({
      ...initialState,
      isActive: true,
      isScanning: true,
      progress: { ...initialProgress, status: 'starting', currentStep: 'Connecting to repository...' },
    })

    try {
      const response = await scansApi.startUnifiedScan({
        repository_id: opts.repositoryId,
        repository_url: opts.repositoryUrl,
        branch: opts.branch || 'main',
      })

      const scanId = response.scan_id
      if (!scanId) throw new Error('No scan_id returned')

      debugLog('Scan created:', scanId)

      setState(prev => ({
        ...prev,
        scanId,
        progress: {
          ...prev.progress,
          status: 'running',
          progress: 0,
          currentStep: 'Initializing scan...',
          logs: [response.message || 'Scan started'],
        },
      }))

      startPolling(scanId)
      return scanId
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err.message || 'Failed to start scan'
      debugLog('Scan start failed:', errorMsg)
      setState(prev => ({
        ...prev,
        isScanning: false,
        isFailed: true,
        error: errorMsg,
      }))
      return null
    }
  }, [startPolling])

  const handleProgressUpdate = useCallback((data: Record<string, any>) => {
    setState(prev => ({
      ...prev,
      progress: {
        progress: data.progress ?? prev.progress.progress,
        currentStep: data.current_step || data.currentStep || prev.progress.currentStep,
        status: data.status || prev.progress.status,
        steps: data.steps || prev.progress.steps,
        logs: data.logs || prev.progress.logs,
        detected_stack: data.detected_stack || prev.progress.detected_stack,
      },
    }))
  }, [])

  const handleScanComplete = useCallback(async (_data?: Record<string, any>) => {
    debugLog('Scan complete handler called')
    stopPolling()
    setState(prev => ({
      ...prev,
      isScanning: false,
      isComplete: true,
      isActive: false,
      progress: { ...prev.progress, progress: 100, status: 'completed', currentStep: 'Static scan completed' },
    }))
    await invalidateRelevantQueries()
  }, [stopPolling, invalidateRelevantQueries])

  const handleScanFailed = useCallback((data?: Record<string, any>) => {
    debugLog('Scan failed handler called')
    stopPolling()
    setState(prev => ({
      ...prev,
      isScanning: false,
      isFailed: true,
      isActive: false,
      error: data?.error_message || data?.error || 'Scan failed',
    }))
  }, [stopPolling])

  const handleAIComplete = useCallback(async () => {
    debugLog('AI complete handler called')
    setState(prev => ({ ...prev, isAiPending: false }))
    await queryClient.invalidateQueries({ queryKey: ['repository-results'] })
    await queryClient.invalidateQueries({ queryKey: ['scan-result'] })
  }, [queryClient])

  const handleLog = useCallback((message: string) => {
    setState(prev => ({
      ...prev,
      progress: {
        ...prev.progress,
        logs: [...(prev.progress.logs || []), message],
      },
    }))
  }, [])

  const reset = useCallback(() => {
    debugLog('Reset')
    stopPolling()
    setState(initialState)
    statusAtLastPollRef.current = 'idle'
  }, [stopPolling])

  const retry = useCallback(() => {
    reset()
    startScan()
  }, [reset, startScan])

  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  return {
    state,
    startScan,
    reset,
    retry,
    handleProgressUpdate,
    handleScanComplete,
    handleScanFailed,
    handleAIComplete,
    handleLog,
  }
}

import { useState, useCallback, useRef, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { scansApi } from '../api/endpoints/scans'

export interface ScanState {
  isActive: boolean
  isScanning: boolean
  isComplete: boolean
  isFailed: boolean
  scanId: string | null
  error: string | null
}

const initialState: ScanState = {
  isActive: false,
  isScanning: false,
  isComplete: false,
  isFailed: false,
  scanId: null,
  error: null,
}

interface UseRepositoryScanOptions {
  repositoryUrl: string
  repositoryId?: string
  branch?: string
  queryKeysToInvalidate?: string[][]
}

export function useRepositoryScan(options: UseRepositoryScanOptions) {
  const queryClient = useQueryClient()
  const [state, setState] = useState<ScanState>(initialState)
  const mountedRef = useRef(true)
  const optionsRef = useRef(options)

  useEffect(() => {
    optionsRef.current = options
  }, [options])

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  const invalidateRelevantQueries = useCallback(async () => {
    const opts = optionsRef.current
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['repositories'] }),
      queryClient.invalidateQueries({ queryKey: ['scans'] }),
      ...(opts.queryKeysToInvalidate?.map(k => queryClient.invalidateQueries({ queryKey: k })) || []),
    ])
  }, [queryClient])

  const startScan = useCallback(async () => {
    const opts = optionsRef.current
    if (!opts.repositoryUrl) return null

    setState({
      ...initialState,
      isActive: true,
      isScanning: true,
    })

    try {
      const response = await scansApi.startUnifiedScan({
        repository_id: opts.repositoryId,
        repository_url: opts.repositoryUrl,
        branch: opts.branch || 'main',
      })

      const scanId = response.scan_id
      if (!scanId) throw new Error('No scan_id returned')

      setState(prev => ({
        ...prev,
        scanId,
        isScanning: true,
        isActive: true,
      }))
      return scanId
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err.message || 'Failed to start scan'
      setState(prev => ({
        ...prev,
        isScanning: false,
        isFailed: true,
        error: errorMsg,
      }))
      return null
    }
  }, [])

  const handleScanComplete = useCallback(async (_data?: Record<string, any>) => {
    setState(prev => ({
      ...prev,
      isScanning: false,
      isComplete: true,
      isActive: false,
    }))
    await invalidateRelevantQueries()
  }, [invalidateRelevantQueries])

  const handleScanFailed = useCallback((data?: Record<string, any>) => {
    setState(prev => ({
      ...prev,
      isScanning: false,
      isFailed: true,
      isActive: false,
      error: data?.error_message || data?.error || 'Scan failed',
    }))
  }, [])

  const handleAIComplete = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['repository-results'] })
    await queryClient.invalidateQueries({ queryKey: ['scan-results'] })
    await queryClient.invalidateQueries({ queryKey: ['scans'] })
  }, [queryClient])

  const reset = useCallback(() => {
    setState(initialState)
  }, [])

  const retry = useCallback(() => {
    reset()
    return startScan()
  }, [reset, startScan])

  const cancelScan = useCallback(async () => {
    if (!state.scanId) return
    try {
      await scansApi.cancelScan(state.scanId)
      setState(prev => ({
        ...prev,
        isScanning: false,
        isFailed: true,
        isActive: false,
        error: 'Scan cancelled',
      }))
    } catch {
      // WebSocket / state sync will reflect cancellation
    }
  }, [state.scanId])

  return {
    state,
    startScan,
    reset,
    retry,
    cancelScan,
    handleScanComplete,
    handleScanFailed,
    handleAIComplete,
  }
}

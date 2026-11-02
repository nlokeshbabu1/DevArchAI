import { useEffect, useRef, useCallback, useState } from 'react'
import { buildWebSocketUrl } from '../lib/api'
import { getAccessToken } from '../lib/auth-token'
import { buildWebSocketAuthMessage } from '../lib/ws-auth'
import type {
  ScanStage,
  ScanLifecycleState,
  ScanProgressSnapshot,
  ScannerStatus,
  LiveFinding,
  AIGenerationProgress,
  StageTransition,
  SeverityCounts,
  ScanEvent,
  ScanEventType,
  TechnologyResult,
} from '../types'
import { normalizeLifecycleStage } from '../lib/scanLifecycle'

export interface WSMessage {
  type: string
  data: Record<string, any>
}

interface UseScanWebSocketOptions {
  scanId: string | null
  sessionToken?: string | null
  enabled?: boolean
  onComplete?: (data: Record<string, any>) => void
  onFailed?: (data: Record<string, any>) => void
  onStageChange?: (stage: ScanStage) => void
  onAIComplete?: (data: Record<string, any>) => void
}

const BASE_DELAY_MS = 1000
const MAX_DELAY_MS = 30000
const HEARTBEAT_INTERVAL_MS = 15000
const MAX_RECONNECT_ATTEMPTS = 50
const MAX_LIVE_FINDINGS = 50

export function useScanWebSocket({
  scanId,
  sessionToken,
  enabled = true,
  onComplete,
  onFailed,
  onStageChange,
  onAIComplete,
}: UseScanWebSocketOptions) {
  const [lifecycleState, setLifecycleState] = useState<ScanLifecycleState>('idle')
  const [scanState, setScanState] = useState<ScanProgressSnapshot | null>(null)
  const [completedStages, setCompletedStages] = useState<ScanStage[]>([])
  const [stageMessages, setStageMessages] = useState<Partial<Record<ScanStage, string>>>({})
  const [failedStage, setFailedStage] = useState<ScanStage | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const mountedRef = useRef(false)
  const enabledRef = useRef(enabled)
  const scanIdRef = useRef(scanId)
  const sessionTokenRef = useRef(sessionToken)
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastPongRef = useRef<number>(Date.now())
  const currentStageRef = useRef<ScanStage | null>(null)
  const onCompleteRef = useRef(onComplete)
  const onFailedRef = useRef(onFailed)
  const onStageChangeRef = useRef(onStageChange)
  const onAICompleteRef = useRef(onAIComplete)
  const eventCounterRef = useRef(0)

  useEffect(() => { enabledRef.current = enabled }, [enabled])
  useEffect(() => { scanIdRef.current = scanId }, [scanId])
  useEffect(() => { sessionTokenRef.current = sessionToken }, [sessionToken])
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])
  useEffect(() => { onFailedRef.current = onFailed }, [onFailed])
  useEffect(() => { onStageChangeRef.current = onStageChange }, [onStageChange])
  useEffect(() => { onAICompleteRef.current = onAIComplete }, [onAIComplete])

  const cleanup = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.onopen = null
      wsRef.current.onmessage = null
      wsRef.current.onerror = null
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const buildInitialSnapshot = useCallback(
    (overrides?: Partial<ScanProgressSnapshot>): ScanProgressSnapshot => ({
      scanId: scanIdRef.current || '',
      status: 'running',
      currentStage: null,
      progress: null,
      detectedStack: [],
      technologies: {},
      isTerminal: false,
      scanners: {},
      liveFindings: [],
      aiProgress: null,
      stageTransitions: [],
      filesScanned: 0,
      totalFiles: 0,
      severityCounts: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
      logs: [],
      events: [],
      ...overrides,
    }),
    [],
  )

  const mergeTechnology = useCallback((tech: TechnologyResult & { id?: string; name?: string }) => {
    const key = (tech.id || tech.technology).toLowerCase().replace(/\s+/g, '_')
    const normalized: TechnologyResult = {
      id: tech.id || key,
      technology: tech.name || tech.technology,
      name: tech.name || tech.technology,
      icon: tech.icon,
      status: tech.status || 'detected',
      detected: tech.detected ?? true,
      findings: tech.findings ?? 0,
      severity_counts: tech.severity_counts,
    }
    setScanState(prev => {
      const base = prev ?? buildInitialSnapshot()
      return {
        ...base,
        technologies: {
          ...base.technologies,
          [key]: { ...base.technologies[key], ...normalized },
        },
      }
    })
  }, [buildInitialSnapshot])

  const technologiesFromPayload = useCallback((items: any[]): Record<string, TechnologyResult> => {
    return items.reduce((acc: Record<string, TechnologyResult>, raw: any) => {
      const id = raw.id || raw.technology
      const key = String(id).toLowerCase().replace(/\s+/g, '_')
      acc[key] = {
        id: key,
        technology: raw.name || raw.technology || key,
        name: raw.name || raw.technology || key,
        icon: raw.icon,
        status: raw.status || 'detected',
        detected: raw.detected ?? true,
        findings: raw.findings ?? 0,
        severity_counts: raw.severity_counts,
      }
      return acc
    }, {})
  }, [])

  const applyServerState = useCallback((state: Record<string, any>) => {
    if (!mountedRef.current) return
    const lifecycleStage = normalizeLifecycleStage(state.stage || state.current_stage)
    const techList = state.technologies || state.technology_results || []
    const serverTechs = technologiesFromPayload(techList)

    setScanState(prev => {
      const base = prev ?? buildInitialSnapshot()
      // Merge technologies additively: preserve individual technology_detected
      // updates that arrived before this scan_state event
      const mergedTechs = { ...base.technologies }
      for (const [key, tech] of Object.entries(serverTechs)) {
        const existing = mergedTechs[key]
        if (!existing || (existing.status !== 'scanning' && existing.status !== 'completed')) {
          mergedTechs[key] = tech
        } else {
          // Preserve richer in-flight state (scanning/completed) from individual events
          mergedTechs[key] = { ...tech, status: existing.status, findings: existing.findings || tech.findings }
        }
      }

      return {
        ...base,
        scanId: state.scan_id || base.scanId,
        status: state.status || base.status,
        currentStage: lifecycleStage || base.currentStage,
        progress: state.progress ?? base.progress,
        currentStep: state.message || state.current_operation || state.stage || state.status || base.currentStep,
        currentOperation: state.message || state.current_operation || base.currentOperation,
        detectedStack: state.detected_stack || base.detectedStack,
        technologies: mergedTechs,
        isTerminal: state.is_terminal ?? base.isTerminal,
        errorMessage: state.error_message ?? base.errorMessage,
        startedAt: state.started_at || base.startedAt,
        completedAt: state.completed_at || base.completedAt,
        filesScanned: state.files_scanned || base.filesScanned,
        totalFiles: state.total_files || base.totalFiles,
        severityCounts: state.severity_counts || base.severityCounts,
        logs: state.logs || base.logs,
      }
    })
    if (state.message && lifecycleStage) {
      setStageMessages(prev => ({ ...prev, [lifecycleStage]: state.message }))
    }
    if (state.is_terminal) {
      setLifecycleState(state.status === 'completed' ? 'completed' : state.status === 'cancelled' ? 'cancelled' : 'failed')
    } else {
      setLifecycleState('running')
    }
  }, [technologiesFromPayload, buildInitialSnapshot])

  const fetchScanState = useCallback(async (id: string) => {
    try {
      const token = getAccessToken() || ''
      const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || window.location.origin
      const url = `${baseUrl}/api/v1/scan/state/${id}`
      const headers: Record<string, string> = {}
      if (token) headers['Authorization'] = `Bearer ${token}`

      const response = await fetch(url, { headers })
      if (!response.ok) return null
      return await response.json()
    } catch {
      return null
    }
  }, [])

  const connect = useCallback(async () => {
    if (!scanIdRef.current || !enabledRef.current) return

    const token = getAccessToken() || ''
    const st = sessionTokenRef.current || ''
    const wsUrl = buildWebSocketUrl(`/ws/scan/${scanIdRef.current}`)

    cleanup()
    setLifecycleState('reconnecting')
    setError(null)

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close()
        return
      }
      try {
        ws.send(
          buildWebSocketAuthMessage({
            accessToken: token || null,
            sessionToken: st || null,
          }),
        )
      } catch {
        ws.close()
        return
      }
      setLifecycleState('running')
      retryCountRef.current = 0
      lastPongRef.current = Date.now()

      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({ type: 'ping', scan_id: scanIdRef.current }))
          } catch {
            // Connection may be dead
          }
          if (Date.now() - lastPongRef.current > HEARTBEAT_INTERVAL_MS * 2) {
            ws.close()
          }
        }
      }, HEARTBEAT_INTERVAL_MS)
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const message = JSON.parse(event.data) as WSMessage
        const { type, data } = message

        if (type === 'pong') {
          lastPongRef.current = Date.now()
          return
        }

        const mapEventType = (t: string): ScanEventType => {
          const mapping: Record<string, ScanEventType> = {
            connecting: 'connecting',
            cloning: 'cloning',
            cloned: 'cloned',
            indexed: 'indexed',
            dockerfile_found: 'dockerfile_found',
            terraform_found: 'terraform_found',
            helm_found: 'helm_found',
            k8s_found: 'k8s_found',
            github_actions_found: 'github_actions_found',
            tech_detection_complete: 'tech_detection_complete',
            running_docker_rules: 'running_docker_rules',
            running_terraform_rules: 'running_terraform_rules',
            running_k8s_rules: 'running_k8s_rules',
            running_secret_detection: 'running_secret_detection',
            finding_discovered: 'finding_discovered',
            ai_suggestion_generation: 'ai_suggestion_generation',
            creating_pull_request: 'creating_pull_request',
            uploading_report: 'uploading_report',
            scan_completed: 'scan_completed',
            scan_complete: 'scan_completed',
            scan_failed: 'scan_failed',
            progress_update: 'progress_update',
            scanner_start: 'scanner_start',
            scanner_complete: 'scanner_complete',
            stack_detected: 'stack_detected',
            log_message: 'log_message',
            ai_progress: 'ai_progress',
            ai_started: 'ai_analysis_started',
            ai_completed: 'ai_completed',
            'ai.analysis.started': 'ai_analysis_started',
            'ai.finding.completed': 'ai_finding_completed',
            'ai.analysis.completed': 'ai_analysis_completed',
            'ai.analysis.failed': 'ai_analysis_failed',
            stage_transition: 'stage_transition',
            connection_ack: 'connection_ack',
          }
          return mapping[t] || 'unknown'
        }

        const pushEvent = (t: string, overrides?: Partial<ScanEvent>) => {
          eventCounterRef.current++
          const evt: ScanEvent = {
            id: eventCounterRef.current,
            type: mapEventType(t),
            timestamp: data.timestamp || new Date().toISOString(),
            progress: data.progress ?? 0,
            stage: data.stage || data.current_step || t,
            message: data.message || data.stage_label || '',
            metadata: { ...data },
            ...overrides,
          }
          setScanState(prev => {
            const base = prev ?? buildInitialSnapshot()
            return { ...base, events: [...base.events, evt] }
          })
        }

        switch (type) {
          case 'progress_update': {
            const newStage = data.current_step as ScanStage | undefined
            if (newStage && newStage !== currentStageRef.current) {
              currentStageRef.current = newStage
              onStageChangeRef.current?.(newStage)
            }

            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return {
                ...base,
                scanId: data.scan_id || base.scanId,
                status: data.status || base.status,
                currentStage: (data.current_step as ScanStage) || base.currentStage,
                progress: data.progress ?? base.progress,
                currentStep: data.current_step ?? base.currentStep,
                detectedStack: data.detected_stack ?? base.detectedStack,
                isTerminal: data.status === 'completed' || data.status === 'failed',
                errorMessage: data.error_message ?? base.errorMessage,
                startedAt: data.started_at ?? base.startedAt,
                completedAt: data.completed_at ?? base.completedAt,
                filesScanned: data.files_scanned ?? base.filesScanned,
                totalFiles: data.total_files ?? base.totalFiles,
                logs: data.logs ?? base.logs,
              }
            })
            pushEvent(type)
            break
          }

          case 'scan_completed':
          case 'scan_complete': {
            const completedStage = normalizeLifecycleStage('scan_completed')
            setCompletedStages(prev =>
              completedStage && !prev.includes(completedStage) ? [...prev, completedStage] : prev,
            )
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return {
                ...base,
                scanId: data.scan_id || base.scanId,
                status: 'completed',
                currentStage: completedStage,
                progress: data.progress ?? 100,
                isTerminal: true,
                completedAt: data.completed_at || new Date().toISOString(),
              }
            })
            pushEvent(type, {
              progress: data.progress ?? 100,
              stage: 'scan_completed',
              message: data.message || 'Scan completed successfully',
            })
            setLifecycleState('completed')
            onCompleteRef.current?.(data || {})
            break
          }

          case 'scan_failed': {
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return {
                ...base,
                scanId: data.scan_id || base.scanId,
                status: 'failed',
                isTerminal: true,
                errorMessage: data.error || 'Scan failed',
              }
            })
            pushEvent(type, { stage: 'failed', message: data.error || 'Scan failed' })
            setLifecycleState('failed')
            onFailedRef.current?.(data || {})
            break
          }

          case 'scanner_start': {
            const scannerId: string = data.scanner_id
            if (!scannerId) break
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const scanner: ScannerStatus = {
                scanner_id: scannerId,
                scanner_name: data.scanner_name || scannerId,
                status: 'running',
                rules_count: data.rules_count,
                findings_count: 0,
                started_at: data.timestamp || new Date().toISOString(),
              }
              return {
                ...base,
                scanners: { ...base.scanners, [scannerId]: scanner },
              }
            })
            pushEvent(type, { stage: scannerId, message: `Starting ${data.scanner_name || scannerId}` })
            break
          }

          case 'scanner_complete': {
            const scannerId: string = data.scanner_id
            if (!scannerId) break
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const existing = base.scanners[scannerId]
              const scanner: ScannerStatus = {
                ...(existing || {
                  scanner_id: scannerId,
                  scanner_name: data.scanner_name || scannerId,
                  findings_count: 0,
                }),
                status: data.status || 'completed',
                findings_count: data.findings_count ?? existing?.findings_count ?? 0,
                completed_at: data.timestamp || new Date().toISOString(),
                duration_ms: data.duration_ms,
                error: data.error,
              }
              return {
                ...base,
                scanners: { ...base.scanners, [scannerId]: scanner },
              }
            })
            pushEvent(type, {
              stage: scannerId,
              message: `${data.scanner_name || scannerId} completed — ${data.findings_count || 0} findings`,
            })
            break
          }

          case 'finding_added':
          case 'finding_detected': {
            const finding: LiveFinding = {
              rule_id: data.finding?.rule_id || data.rule_id || '',
              rule_name: data.finding?.rule_name || data.rule_name || '',
              severity: data.finding?.severity || data.severity || 'info',
              category: data.finding?.category || data.category || '',
              file_path: data.finding?.file_path || data.file_path,
              line_number: data.finding?.line_number || data.line_number,
              description: data.finding?.description || data.description || '',
              timestamp: data.timestamp || new Date().toISOString(),
            }
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const updatedFindings = [...base.liveFindings, finding]
              if (updatedFindings.length > MAX_LIVE_FINDINGS) {
                updatedFindings.splice(0, updatedFindings.length - MAX_LIVE_FINDINGS)
              }
              const sev = finding.severity
              const counts = { ...base.severityCounts }
              if (sev in counts) {
                counts[sev as keyof SeverityCounts]++
              }
              return {
                ...base,
                liveFindings: updatedFindings,
                severityCounts: counts,
              }
            })
            if (data.technology) {
              const key = String(data.technology).toLowerCase().replace(/\s+/g, '_')
              mergeTechnology({
                id: key,
                technology: data.technology,
                name: data.technology,
                detected: true,
                findings: data.total_findings ?? 0,
              })
            }
            pushEvent(type, {
              stage: 'finding',
              message: `[${finding.severity?.toUpperCase() || 'INFO'}] ${finding.rule_name || finding.rule_id}`,
            })
            break
          }

          case 'ai_progress': {
            const progress: AIGenerationProgress = {
              phase: data.phase || '',
              message: data.message || '',
              progress: data.progress ?? 0,
              findings_processed: data.findings_processed ?? 0,
              findings_total: data.findings_total ?? 0,
              timestamp: data.timestamp || new Date().toISOString(),
            }
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return { ...base, aiProgress: progress }
            })
            pushEvent(type, {
              stage: 'ai_generation',
              progress: data.progress ?? 0,
              message: data.message || `AI: ${data.phase || 'processing'}`,
            })
            break
          }

          case 'ai_completed': {
            const completed: AIGenerationProgress = {
              phase: data.phase || 'completed',
              message: data.message || 'AI analysis complete',
              progress: 100,
              findings_processed: data.findings_processed ?? 0,
              findings_total: data.findings_total ?? 0,
              timestamp: data.timestamp || new Date().toISOString(),
            }
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return { ...base, aiProgress: completed }
            })
            pushEvent(type, {
              stage: 'ai_generation',
              progress: 100,
              message: data.message || 'AI analysis complete',
            })
            onAICompleteRef.current?.(data || {})
            break
          }

          case 'ai_started':
          case 'ai.analysis.started': {
            const progress: AIGenerationProgress = {
              phase: data.phase || 'started',
              message: data.message || 'Building AI recommendations…',
              progress: 0,
              findings_processed: data.findings_processed ?? 0,
              findings_total: data.findings_total ?? 0,
              timestamp: data.timestamp || new Date().toISOString(),
            }
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return { ...base, aiProgress: progress }
            })
            pushEvent('ai_analysis_started', {
              stage: 'ai_generation',
              progress: 0,
              message: progress.message,
            })
            break
          }

          case 'ai.finding.completed': {
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const findings_total = data.findings_total ?? base.aiProgress?.findings_total ?? 0
              const findings_processed = data.findings_processed ?? base.aiProgress?.findings_processed ?? 0
              const progress: AIGenerationProgress = {
                phase: 'generating',
                message: `AI recommendation ${findings_processed} of ${findings_total}`,
                progress: findings_total ? Math.round((findings_processed / findings_total) * 100) : 100,
                findings_processed,
                findings_total,
                timestamp: data.timestamp || new Date().toISOString(),
              }
              return { ...base, aiProgress: progress }
            })
            pushEvent('ai_finding_completed', {
              stage: 'ai_generation',
              progress: data.findings_total ? Math.round((data.findings_processed / data.findings_total) * 100) : 100,
              message: `AI recommendation ${data.findings_processed ?? 0} of ${data.findings_total ?? 0}`,
            })
            break
          }

          case 'ai.analysis.completed': {
            const completed: AIGenerationProgress = {
              phase: data.phase || 'completed',
              message: data.message || 'AI analysis complete',
              progress: 100,
              findings_processed: data.findings_processed ?? 0,
              findings_total: data.findings_total ?? 0,
              timestamp: data.timestamp || new Date().toISOString(),
            }
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return { ...base, aiProgress: completed }
            })
            pushEvent('ai_analysis_completed', {
              stage: 'ai_generation',
              progress: 100,
              message: completed.message,
            })
            onAICompleteRef.current?.(data || {})
            break
          }

          case 'ai.analysis.failed': {
            const failed: AIGenerationProgress = {
              phase: 'failed',
              message: data.message || data.error || 'AI analysis failed',
              progress: 0,
              findings_processed: data.findings_processed ?? 0,
              findings_total: data.findings_total ?? 0,
              timestamp: data.timestamp || new Date().toISOString(),
            }
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return { ...base, aiProgress: failed }
            })
            pushEvent('ai_analysis_failed', {
              stage: 'ai_generation',
              progress: 0,
              message: failed.message,
            })
            onAICompleteRef.current?.(data || {})
            break
          }

          case 'ai.rag.completed': {
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const current = base.aiProgress || { phase: 'rag', message: '', progress: 0, findings_processed: 0, findings_total: 0, timestamp: '' }
              return {
                ...base,
                aiProgress: {
                  ...current,
                  phase: 'rag',
                  message: `DevArchAI knowledge loaded (${data.documents_found || 0} documents)`,
                  timestamp: data.timestamp || new Date().toISOString(),
                },
              }
            })
            pushEvent('ai_rag_completed', {
              stage: 'ai_generation',
              progress: 0,
              message: `RAG: ${data.documents_found || 0} docs via ${data.method || 'unknown'}`,
            })
            break
          }

          case 'ai.mcp.decision': {
            const mcpRequired = data.required ?? false
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const current = base.aiProgress || { phase: 'mcp_decision', message: '', progress: 0, findings_processed: 0, findings_total: 0, timestamp: '' }
              return {
                ...base,
                aiProgress: {
                  ...current,
                  phase: 'mcp_decision',
                  message: mcpRequired
                    ? `Checking current ${data.technology || ''} documentation`
                    : `Internal knowledge sufficient for ${data.rule_id || ''}`,
                  timestamp: data.timestamp || new Date().toISOString(),
                },
              }
            })
            pushEvent('ai_mcp_decision', {
              stage: 'ai_generation',
              progress: 0,
              message: mcpRequired ? `MCP required: ${data.technology}` : `MCP skipped: ${data.rule_id}`,
            })
            break
          }

          case 'ai.mcp.completed': {
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const current = base.aiProgress || { phase: 'mcp', message: '', progress: 0, findings_processed: 0, findings_total: 0, timestamp: '' }
              return {
                ...base,
                aiProgress: {
                  ...current,
                  phase: 'mcp',
                  message: `Current ${data.technology || ''} docs: ${data.status || 'completed'}`,
                  timestamp: data.timestamp || new Date().toISOString(),
                },
              }
            })
            pushEvent('ai_mcp_completed', {
              stage: 'ai_generation',
              progress: 0,
              message: `MCP: ${data.technology} (${data.status})`,
            })
            break
          }

          case 'ai.llm.started': {
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const current = base.aiProgress || { phase: 'llm', message: '', progress: 0, findings_processed: 0, findings_total: 0, timestamp: '' }
              return {
                ...base,
                aiProgress: {
                  ...current,
                  phase: 'llm',
                  message: 'Generating AI recommendation',
                  timestamp: data.timestamp || new Date().toISOString(),
                },
              }
            })
            break
          }

          case 'ai.llm.completed': {
            const aiGen = data.ai_generated ?? false
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const current = base.aiProgress || { phase: 'llm_done', message: '', progress: 0, findings_processed: 0, findings_total: 0, timestamp: '' }
              return {
                ...base,
                aiProgress: {
                  ...current,
                  phase: 'llm_done',
                  message: aiGen ? 'AI recommendation generated' : 'Using static recommendation',
                  timestamp: data.timestamp || new Date().toISOString(),
                },
              }
            })
            break
          }

          case 'ai.cache.hit': {
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const current = base.aiProgress || { phase: 'cache_hit', message: '', progress: 0, findings_processed: 0, findings_total: 0, timestamp: '' }
              return {
                ...base,
                aiProgress: {
                  ...current,
                  phase: 'cache_hit',
                  message: `Cache hit (${data.layer || 'redis'}): ${data.rule_id || ''}`,
                  timestamp: data.timestamp || new Date().toISOString(),
                },
              }
            })
            pushEvent('ai_cache_hit', {
              stage: 'ai_generation',
              progress: 0,
              message: `Cache hit: ${data.rule_id}`,
            })
            break
          }

          case 'ai.recommendation.updated': {
            const findingId = data.finding_id || ''
            const recStatus = data.status || 'completed'
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const updatedFindings = base.liveFindings.map((f) =>
                f.rule_id === data.rule_id
                  ? { ...f, ai_status: recStatus, ai_source: data.source }
                  : f,
              )
              return {
                ...base,
                liveFindings: updatedFindings,
                aiProgress: {
                  phase: recStatus === 'completed' ? 'llm_done' : 'llm',
                  message: data.source
                    ? `Recommendation ready (${data.source})`
                    : 'Recommendation ready',
                  progress: base.aiProgress?.progress ?? 0,
                  findings_processed: (base.aiProgress?.findings_processed ?? 0) + 1,
                  findings_total: base.aiProgress?.findings_total ?? 0,
                  timestamp: data.timestamp || new Date().toISOString(),
                },
              }
            })
            pushEvent('ai_completed', {
              stage: 'ai_generation',
              progress: 0,
              message: `AI recommendation updated for finding ${findingId}`,
            })
            onAICompleteRef.current?.(data || {})
            break
          }

          case 'stage_transition':
          case 'scan_stage': {
            const rawStage = (data.stage || data.current_step) as ScanStage
            const lifecycleStage = normalizeLifecycleStage(rawStage)
            const stageStatus = data.status || 'running'
            const message = data.message || data.stage_label || ''

            if (lifecycleStage) {
              if (stageStatus === 'completed') {
                setCompletedStages(prev =>
                  prev.includes(lifecycleStage) ? prev : [...prev, lifecycleStage],
                )
              } else if (stageStatus === 'failed') {
                setFailedStage(lifecycleStage)
              } else {
                // When a new running stage starts, mark the previous stage as completed
                const prevStage = currentStageRef.current
                if (prevStage && prevStage !== lifecycleStage) {
                  setCompletedStages(prev =>
                    prev.includes(prevStage) ? prev : [...prev, prevStage],
                  )
                }
                currentStageRef.current = lifecycleStage
                onStageChangeRef.current?.(lifecycleStage)
              }
              if (message) {
                setStageMessages(prev => ({ ...prev, [lifecycleStage]: message }))
              }
            }

            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return {
                ...base,
                currentStage: lifecycleStage || base.currentStage,
                progress: data.progress ?? base.progress,
                currentStep: message || base.currentStep,
                stageTransitions: type === 'stage_transition'
                  ? [...base.stageTransitions, {
                      stage: rawStage,
                      stage_label: message,
                      progress: data.progress ?? 0,
                      status: stageStatus,
                      timestamp: data.timestamp || new Date().toISOString(),
                    }]
                  : base.stageTransitions,
              }
            })
            pushEvent(type, {
              stage: lifecycleStage || rawStage,
              progress: data.progress ?? 0,
              message,
            })
            break
          }

          case 'technology_detected': {
            const techObj = data.technology
            if (techObj && typeof techObj === 'object') {
              mergeTechnology({
                id: techObj.id,
                technology: techObj.name || techObj.id,
                name: techObj.name,
                icon: techObj.icon,
                status: techObj.status || 'detected',
                detected: data.detected ?? true,
                findings: data.findings ?? techObj.findings ?? 0,
                severity_counts: data.severity_counts,
              })
            } else if (data.technology) {
              mergeTechnology({
                technology: data.technology,
                detected: data.detected ?? true,
                findings: data.findings ?? 0,
                severity_counts: data.severity_counts,
              })
            }
            pushEvent(type, {
              stage: 'detecting_technologies',
              message: `${data.technology?.name || data.technology}: detected`,
            })
            break
          }

          case 'technology_scan_started': {
            const name = data.technology
            const key = String(name).toLowerCase().replace(/\s+/g, '_')
            mergeTechnology({
              id: key,
              technology: name,
              name,
              status: 'scanning',
              detected: true,
              findings: 0,
            })
            const techStage = `tech:${key}` as ScanStage
            currentStageRef.current = techStage
            if (data.message) setStageMessages(prev => ({ ...prev, [techStage]: data.message }))
            pushEvent(type, { stage: techStage, message: data.message || `Analyzing ${name}` })
            break
          }

          case 'technology_scan_completed': {
            const name = data.technology
            const key = String(name).toLowerCase().replace(/\s+/g, '_')
            mergeTechnology({
              id: key,
              technology: name,
              name,
              status: data.status === 'failed' ? 'failed' : 'completed',
              detected: true,
              findings: data.findings_count ?? 0,
            })
            setCompletedStages(prev => {
              const techStage = `tech:${key}` as ScanStage
              return prev.includes(techStage) ? prev : [...prev, techStage]
            })
            pushEvent(type, {
              stage: `tech:${key}` as ScanStage,
              message: `${name}: ${data.findings_count ?? 0} findings`,
            })
            break
          }

          case 'scan_cancelled': {
            setLifecycleState('cancelled')
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return {
                ...base,
                status: 'cancelled',
                isTerminal: true,
                errorMessage: data.message || 'Scan cancelled',
              }
            })
            pushEvent(type, { stage: 'cancelled', message: data.message || 'Scan cancelled' })
            break
          }

          case 'stack_detected': {
            const stack: string[] = data.stack || data.detected_stack || []
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              return { ...base, detectedStack: stack }
            })
            pushEvent(type, {
              stage: 'technology_detection',
              message: `Detected: ${stack.join(', ') || 'Technologies identified'}`,
            })
            break
          }

          case 'log_message': {
            const msg: string = data.message || ''
            if (!msg) break
            setScanState(prev => {
              const base = prev ?? buildInitialSnapshot()
              const logs = [...base.logs, msg]
              if (logs.length > 50) logs.splice(0, logs.length - 50)
              return { ...base, logs }
            })
            break
          }

          case 'connection_ack':
            pushEvent(type, { message: 'Connected to scan server' })
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
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current)
        heartbeatRef.current = null
      }

      const syncAndReconnect = async () => {
        const id = scanIdRef.current
        if (!id) return

        const state = await fetchScanState(id)
        if (state && mountedRef.current) {
          applyServerState(state)

          if (state.is_terminal) {
            if (state.status === 'completed') {
              onCompleteRef.current?.(state as Record<string, any>)
            } else if (state.status === 'failed') {
              onFailedRef.current?.(state as Record<string, any>)
            }
            return
          }
        }

        if (enabledRef.current && scanIdRef.current && retryCountRef.current < MAX_RECONNECT_ATTEMPTS) {
          retryCountRef.current++
          const delay = Math.min(
            BASE_DELAY_MS * Math.pow(2, retryCountRef.current - 1),
            MAX_DELAY_MS,
          )
          setTimeout(connect, delay)
        } else {
          setLifecycleState('failed')
          setError('Failed to reconnect after multiple attempts')
        }
      }

      syncAndReconnect()
    }
  }, [cleanup, fetchScanState, buildInitialSnapshot, applyServerState, mergeTechnology])

  useEffect(() => {
    mountedRef.current = true
    if (enabled && scanId) {
      connect()
    }

    return () => {
      mountedRef.current = false
      cleanup()
    }
  }, [connect, cleanup, enabled, scanId])

  const connectionStatus: 'connected' | 'connecting' | 'disconnected' =
    lifecycleState === 'running' ? 'connected' :
    lifecycleState === 'reconnecting' ? 'connecting' :
    'disconnected'

  return {
    lifecycleState,
    scanState,
    completedStages,
    stageMessages,
    failedStage,
    error,
    connectionStatus,
  }
}

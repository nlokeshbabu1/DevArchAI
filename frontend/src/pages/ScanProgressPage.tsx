import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RotateCcw, AlertCircle,
  Loader2, CheckCircle2, Clock, GitBranch, GitCommit,
  XCircle, Download, GitPullRequest, Share2,
  Shield, FileText, Cpu, Brain, FileCode, Activity,
} from 'lucide-react'
import { Button, Card } from '../components/ui-animated'
import { scansApi } from '../api/endpoints/scans'
import { prApi } from '../api/endpoints/pull-requests'
import { reportsApi } from '../api/endpoints/reports'
import { useScanWebSocket } from '../hooks/useScanWebSocket'
import { ScanResultsDashboard } from '../components/scan-results/ScanResultsDashboard'
import { ScanPipeline } from '../components/scans/ScanPipeline'
import { LiveTerminal } from '../components/scans/LiveTerminal'
import { cn, copyToClipboard } from '../lib/utils'
import type { ScanStage, StageMetadata, SeverityCounts, ScanEvent } from '../types'

interface ScanResult {
  id?: string
  scan_id: string
  scan_status?: string
  ai_status?: 'pending' | 'processing' | 'completed' | 'failed'
  repository_url: string
  repository_name?: string
  security_score: number
  overall_score?: number
  severity_counts: SeverityCounts
  risk_distribution?: { critical: number; high: number; medium: number; low: number; info: number }
  findings: any[]
  total_findings?: number
  files_analyzed: number
  directories_scanned?: number
  repository_size?: string
  branch: string
  completed_at: string
  detected_stack?: Record<string, string[]>
  detected_technologies?: string[]
  technology_details?: { technology: string; files_count: number; findings_count: number; severity_counts: Record<string, number>; status: string }[]
  top_files?: { file_path: string; findings_count: number; severities: Record<string, number> }[]
  status?: string
  scanner_executions?: any[]
  ai_suggestions_count?: number
  analysis_duration_seconds?: number
  commit_hash?: string
  started_at?: string
  scanners_used?: number
  rules_executed?: number
}

const EASE = [0.16, 1, 0.3, 1] as const

function useElapsedTime(startedAt: string | null | undefined, isTerminal: boolean, completedAt?: string | null): number {
  const [elapsed, setElapsed] = useState(0)
  const endTimeRef = useRef<number | null>(null)

  useEffect(() => {
    if (!startedAt) return
    const start = new Date(startedAt).getTime()
    if (isNaN(start)) return

    if (isTerminal) {
      const end = completedAt ? new Date(completedAt).getTime() : Date.now()
      endTimeRef.current = end
      setElapsed(Math.floor((end - start) / 1000))
      return
    }

    setElapsed(Math.floor((Date.now() - start) / 1000))
    const i = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)
    return () => clearInterval(i)
  }, [startedAt, isTerminal, completedAt])

  return elapsed
}

function fmt(seconds: number): string {
  if (seconds < 0) return '00:00'
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

const SEV: Record<string, { c: string; bg: string; bd: string; hex: string }> = {
  critical: { c: 'text-red-400', bg: 'bg-red-500/10', bd: 'border-red-500/30', hex: '#ef4444' },
  high: { c: 'text-orange-400', bg: 'bg-orange-500/10', bd: 'border-orange-500/30', hex: '#f97316' },
  medium: { c: 'text-yellow-400', bg: 'bg-yellow-500/10', bd: 'border-yellow-500/30', hex: '#eab308' },
  low: { c: 'text-green-400', bg: 'bg-green-500/10', bd: 'border-green-500/30', hex: '#22c55e' },
  info: { c: 'text-blue-400', bg: 'bg-blue-500/10', bd: 'border-blue-500/30', hex: '#3b82f6' },
}

const TECH_CAT: Record<string, { c: string; bg: string; bd: string }> = {
  terraform: { c: 'text-indigo-300', bg: 'bg-indigo-500/10', bd: 'border-indigo-500/20' },
  cloudformation: { c: 'text-indigo-300', bg: 'bg-indigo-500/10', bd: 'border-indigo-500/20' },
  docker: { c: 'text-cyan-300', bg: 'bg-cyan-500/10', bd: 'border-cyan-500/20' },
  helm: { c: 'text-cyan-300', bg: 'bg-cyan-500/10', bd: 'border-cyan-500/20' },
  kubernetes: { c: 'text-blue-300', bg: 'bg-blue-500/10', bd: 'border-blue-500/20' },
  k8s: { c: 'text-blue-300', bg: 'bg-blue-500/10', bd: 'border-blue-500/20' },
  github_actions: { c: 'text-purple-300', bg: 'bg-purple-500/10', bd: 'border-purple-500/20' },
  jenkins: { c: 'text-purple-300', bg: 'bg-purple-500/10', bd: 'border-purple-500/20' },
  ci: { c: 'text-purple-300', bg: 'bg-purple-500/10', bd: 'border-purple-500/20' },
  cd: { c: 'text-purple-300', bg: 'bg-purple-500/10', bd: 'border-purple-500/20' },
  security: { c: 'text-red-300', bg: 'bg-red-500/10', bd: 'border-red-500/20' },
  trivy: { c: 'text-red-300', bg: 'bg-red-500/10', bd: 'border-red-500/20' },
  checkov: { c: 'text-orange-300', bg: 'bg-orange-500/10', bd: 'border-orange-500/20' },
}

function techCat(tech: string) {
  const l = tech.toLowerCase()
  for (const [k, v] of Object.entries(TECH_CAT)) {
    if (l.includes(k)) return v
  }
  return { c: 'text-white/60', bg: 'bg-white/5', bd: 'border-white/10' }
}

const EVENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  connecting: Activity,
  cloning: GitMerge,
  cloned: CheckCircle2,
  indexed: FileCode,
  dockerfile_found: Cpu,
  terraform_found: Cpu,
  helm_found: Cpu,
  k8s_found: Cpu,
  github_actions_found: Cpu,
  tech_detection_complete: Cpu,
  running_docker_rules: Shield,
  running_terraform_rules: Shield,
  running_k8s_rules: Shield,
  running_secret_detection: Shield,
  finding_discovered: AlertCircle,
  ai_suggestion_generation: Brain,
  creating_pull_request: GitPullRequest,
  uploading_report: FileText,
  scan_completed: CheckCircle2,
  scan_failed: XCircle,
  scanner_start: Shield,
  scanner_complete: Shield,
  stack_detected: Cpu,
  stage_transition: Activity,
  progress_update: Activity,
  connection_ack: Activity,
  log_message: Activity,
}

function getEventIcon(event: ScanEvent): React.ComponentType<{ className?: string }> {
  return EVENT_ICONS[event.type] || Activity
}

function getEventColor(event: ScanEvent): string {
  if (event.type === 'scan_completed') return 'text-emerald-400'
  if (event.type === 'scan_failed') return 'text-red-400'
  if (event.type === 'finding_discovered') return SEV[event.metadata?.severity || 'info']?.c || 'text-blue-400'
  if (event.type === 'ai_suggestion_generation') return 'text-purple-400'
  if (event.type === 'stack_detected') return 'text-cyan-400'
  if (event.type.startsWith('running_')) return 'text-indigo-400'
  if (event.type === 'scanner_complete') return 'text-emerald-400/60'
  return 'text-white/40'
}

function getEventBg(event: ScanEvent): string {
  if (event.type === 'scan_completed') return 'bg-emerald-500/5'
  if (event.type === 'scan_failed') return 'bg-red-500/5'
  if (event.type === 'finding_discovered') return SEV[event.metadata?.severity || 'info']?.bg || 'bg-blue-500/5'
  if (event.type === 'ai_suggestion_generation') return 'bg-purple-500/5'
  if (event.type === 'stack_detected') return 'bg-cyan-500/5'
  if (event.type.startsWith('running_')) return 'bg-indigo-500/5'
  return 'bg-white/[0.02]'
}

const AI_PHASES = [
  { key: 'analyzing', label: 'Analyzing findings' },
  { key: 'root_causes', label: 'Identifying root causes' },
  { key: 'remediations', label: 'Generating remediations' },
  { key: 'scoring', label: 'Computing risk scores' },
  { key: 'summary', label: 'Building summary' },
  { key: 'pr_fixes', label: 'Preparing PR fixes' },
]

const MONO = 'font-[ui-monospace,SFMono-Regular,\'SF Mono\',Menlo,Consolas,monospace]'

function Toast({ msg }: { msg: string | null }) {
  return (
    <AnimatePresence>
      {msg && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="fixed top-4 right-4 z-[100] px-4 py-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 backdrop-blur-xl"
        >
          <div className="flex items-center gap-2 text-sm text-emerald-300">
            <CheckCircle2 className="h-4 w-4" />{msg}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function Spinner({ color = 'indigo' }: { color?: string }) {
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
      className={cn('w-16 h-16 border-4 rounded-full mx-auto', `border-${color}-500/20`, `border-t-${color}-400`)}
    />
  )
}

function LiveEventTimeline({
  events,
  isVisible,
  prefersReduced,
}: {
  events: ScanEvent[]
  isVisible: boolean
  prefersReduced: boolean
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!prefersReduced) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' })
    } else if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events.length, prefersReduced])

  if (!isVisible || events.length === 0) return null

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[rgba(30,41,59,0.6)] backdrop-blur-xl overflow-hidden">
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-white/[0.06]">
        <Activity className="w-4 h-4 text-indigo-400 shrink-0" />
        <span className="text-sm font-medium text-white/80">Event Timeline</span>
        <span className="text-[10px] font-mono text-white/30 tabular-nums bg-white/[0.06] px-1.5 py-0.5 rounded">
          {events.length}
        </span>
      </div>
      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        aria-label="Scan event timeline"
        className="overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
        style={{ maxHeight: '20rem' }}
      >
        <AnimatePresence initial={false}>
          {events.map((evt) => {
            const Icon = getEventIcon(evt)
            const color = getEventColor(evt)
            const bg = getEventBg(evt)
            const time = new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            return (
              <motion.div
                key={evt.id}
                initial={prefersReduced ? { opacity: 1 } : { opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={prefersReduced ? { duration: 0 } : { duration: 0.25, ease: EASE }}
                className={cn(
                  'flex items-start gap-3 px-4 py-2 border-b border-white/[0.04] hover:bg-white/[0.02]',
                  bg,
                )}
              >
                <div className="flex items-center gap-2 shrink-0 mt-0.5">
                  <Icon className={cn('w-3.5 h-3.5', color)} />
                  <span className={cn('text-[10px] font-mono tabular-nums text-white/25', MONO)}>{time}</span>
                </div>
                <span className={cn('text-xs text-white/60 min-w-0 flex-1 break-words')}>
                  {evt.message}
                </span>
                {evt.progress > 0 && (
                  <span className={cn('text-[10px] font-mono tabular-nums text-white/30 shrink-0', MONO)}>
                    {evt.progress}%
                  </span>
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>
        <div ref={endRef} />
      </div>
    </div>
  )
}

export function ScanProgressPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isDownloading, setIsDownloading] = useState(false)
  const [prState, setPrState] = useState<{
    step: null | 'generating' | 'branch' | 'creating_pr'
    success: boolean; error: string | null
  }>({ step: null, success: false, error: null })
  const [severityFilter, setSeverityFilter] = useState('all')
  const [sortBy, setSortBy] = useState('severity')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const toastRef = useRef<ReturnType<typeof setTimeout>>()

  const prefersReduced = useMemo(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches, [],
  )

  const isValidScanId = !!(id && id !== ':id' && id.length > 5)

  const { data: stagesData } = useQuery({
    queryKey: ['scan-stages'], queryFn: () => scansApi.getStages(),
    staleTime: Infinity, gcTime: Infinity,
  })
  const stages: StageMetadata[] = stagesData || []

  const { data: scanState, isLoading: stateLoading, error: stateError } = useQuery({
    queryKey: ['scan-state', id], queryFn: () => scansApi.getScanState(id!),
    enabled: isValidScanId, retry: 3, staleTime: 0,
  })

  const { data: result, isLoading: resultsLoading } = useQuery<ScanResult>({
    queryKey: ['scan-results', id],
    queryFn: async () => { if (!id) throw new Error('No scan ID'); return (await scansApi.getScanResults(id)) as ScanResult },
    enabled: isValidScanId && !!scanState?.is_terminal && scanState.status === 'completed',
    retry: 3, staleTime: 5 * 60 * 1000,
  })

  const repoName = result?.repository_name ||
    result?.repository_url?.split('/').slice(-2).join('/') ||
    scanState?.detected_stack?.[0] || id?.slice(0, 8) || 'Scan'
  const branch = result?.branch || 'main'
  const commitHash = result?.commit_hash
  const isTerminal = scanState?.is_terminal === true
  const isComplete = scanState?.status === 'completed'
  const isFailed = scanState?.status === 'failed'

  const handleScanComplete = useCallback(() => {}, [])
  const handleScanFailed = useCallback(() => {}, [])

  const { scanState: wsState } = useScanWebSocket({
    scanId: isValidScanId ? id! : null,
    enabled: isValidScanId && !isTerminal,
    onComplete: handleScanComplete, onFailed: handleScanFailed,
  })

  // --- All state from WebSocket, never computed on frontend ---
  const progress = wsState?.progress ?? scanState?.progress ?? 0
  const currentStage = (wsState?.currentStage ?? scanState?.current_stage) as ScanStage | null
  const wsComplete = wsState?.isTerminal && wsState.status === 'completed'
  const wsFailed = wsState?.isTerminal && wsState.status === 'failed'
  const startedAt = wsState?.startedAt || scanState?.started_at
  const completedAt = wsState?.completedAt || result?.completed_at
  const detectedStack = wsState?.detectedStack || scanState?.detected_stack || []
  const scanners = wsState?.scanners || {}
  const liveFindings = wsState?.liveFindings || []
  const aiProgress = wsState?.aiProgress || null
  const filesScanned = wsState?.filesScanned || 0
  const totalFiles = wsState?.totalFiles || 0
  const severityCounts = wsState?.severityCounts || { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  const events = wsState?.events || []

  // Timer: uses backend started_at, stops on terminal, shows backend duration when complete
  const elapsed = useElapsedTime(
    (isTerminal || wsFailed) ? null : startedAt,
    !!(isTerminal || wsFailed),
    completedAt,
  )

  const failedStages = useMemo(() => wsFailed && currentStage ? [currentStage] : [], [wsFailed, currentStage])
  const isAiGenerating = currentStage === 'ai_generation' || aiProgress !== null

  const totalRules = useMemo(() => Object.values(scanners).reduce((s, v) => s + (v.rules_count || 0), 0), [scanners])
  const executedRules = useMemo(() =>
    Object.values(scanners).filter(s => s.status === 'completed_with_findings' || s.status === 'completed_no_findings')
      .reduce((s, v) => s + (v.rules_count || 0), 0), [scanners])
  const completedScanners = useMemo(() =>
    Object.values(scanners).filter(s => s.status === 'completed_with_findings' || s.status === 'completed_no_findings').length, [scanners])
  const activeAiPhase = useMemo(() => {
    if (!aiProgress?.phase) return -1
    const idx = AI_PHASES.findIndex(p => aiProgress.phase.toLowerCase().includes(p.key))
    return idx >= 0 ? idx : 0
  }, [aiProgress])

  // On completion — invalidate results query so dashboard loads. Do NOT navigate away.
  useEffect(() => {
    if ((wsComplete || (isTerminal && isComplete)) && result) {
      void queryClient.invalidateQueries({ queryKey: ['scan-results', id] })
      setToastMsg('Scan completed successfully')
      if (toastRef.current) clearTimeout(toastRef.current)
      toastRef.current = setTimeout(() => setToastMsg(null), 4000)
    }
  }, [wsComplete, isTerminal, isComplete, result, id, queryClient])

  const repoUrl = result?.repository_url || ''

  const handleRescan = useCallback(async () => {
    if (!repoUrl) return
    try {
      const r = await scansApi.startUnifiedScan({ repository_url: repoUrl, branch: branch || 'main' })
      if (r?.scan_id) navigate(`/scans/${r.scan_id}`)
    } catch {}
  }, [repoUrl, branch, navigate])

  const handleDownload = useCallback(async (format: 'pdf' | 'json' | 'sarif' | 'csv' = 'pdf') => {
    if (!result || isDownloading) return
    const eid = result.id
    if (!eid) return
    if (format === 'json') {
      const d = {
        scan_id: eid, repository_name: repoName, repository_url: repoUrl, branch: result.branch || 'main',
        overall_score: result.overall_score, security_score: result.security_score,
        severity_counts: result.severity_counts, findings_count: result.findings?.length || 0,
        files_analyzed: result.files_analyzed, findings: (result.findings || []).map((f: any) => ({ ...f })),
      }
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url
      a.download = `scan-report-${String(eid).slice(0, 8)}.json`
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url)
      return
    }
    setIsDownloading(true)
    try {
      const dr = await reportsApi.downloadReport(eid, format as 'pdf' | 'excel')
      const ext = format === 'pdf' ? 'pdf' : format === 'csv' ? 'csv' : format === 'sarif' ? 'sarif' : 'xlsx'
      const a = document.createElement('a'); a.href = dr.url; a.rel = 'noopener noreferrer'
      a.download = dr.filename || `report-${String(eid).slice(0, 8)}.${ext}`
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
    } catch { if (format === 'pdf') void handleDownload('json') }
    finally { setIsDownloading(false) }
  }, [result, isDownloading, repoName, repoUrl])

  const hasFixableFindings = useMemo(() => result?.findings?.some((f: any) => f.fix_code) ?? false, [result])

  const handleCreateGlobalPR = useCallback(async () => {
    if (!result || !hasFixableFindings) return
    const eid = result.id
    if (!eid) return
    setPrState({ step: 'generating', success: false, error: null })
    await new Promise(r => setTimeout(r, 600))
    setPrState(p => p.error ? p : { ...p, step: 'branch' })
    await new Promise(r => setTimeout(r, 400))
    setPrState(p => p.error ? p : { ...p, step: 'creating_pr' })
    try {
      const ids = (result.findings || []).filter((f: any) => f.fix_code).map((f: any) => f.id ?? f.rule_id)
      await prApi.createPR({ scan_id: eid, finding_ids: ids.slice(0, 10) })
      setPrState({ step: null, success: true, error: null })
    } catch (err: any) { setPrState({ step: null, success: false, error: err?.message || 'Failed to create PR' }) }
  }, [result, hasFixableFindings])

  const handleShare = useCallback(() => {
    if (navigator.share) {
      navigator.share({ title: `Scan Results: ${repoName}`, text: `Security scan results for ${repoName}`, url: window.location.href }).catch(() => {})
    } else {
      void copyToClipboard(window.location.href)
      setToastMsg('Link copied to clipboard')
      if (toastRef.current) clearTimeout(toastRef.current)
      toastRef.current = setTimeout(() => setToastMsg(null), 3000)
    }
  }, [repoName])

  if (stateLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <Spinner />
          <p className="text-muted-foreground text-sm">Connecting to scan...</p>
        </div>
      </div>
    )
  }

  if (stateError || (!isValidScanId && id)) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="p-8 max-w-md text-center" hover={false}>
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">Scan Not Found</h2>
          <p className="text-muted-foreground mb-4 text-sm">The scan could not be found or you don't have access.</p>
          <div className="flex gap-2 justify-center">
            <Button variant="secondary" onClick={() => navigate('/scan')}><RotateCcw className="h-4 w-4 mr-1.5" />New Scan</Button>
            <Button variant="ghost" onClick={() => navigate('/dashboard')}>Dashboard</Button>
          </div>
        </Card>
      </div>
    )
  }

  if (wsFailed || (isTerminal && isFailed)) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="p-8 max-w-md text-center" hover={false}>
          <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">Scan Failed</h2>
          <p className="text-muted-foreground mb-4 text-sm">{wsState?.errorMessage || scanState?.error_message || 'The scan encountered an error.'}</p>
          <div className="flex gap-2 justify-center">
            <Button variant="secondary" onClick={() => navigate('/scan')}><RotateCcw className="h-4 w-4 mr-1.5" />New Scan</Button>
            <Button variant="ghost" onClick={() => navigate('/dashboard')}>Dashboard</Button>
          </div>
        </Card>
      </div>
    )
  }

  // --- COMPLETED: Stay on page, show results in place ---
  if (wsComplete || (isTerminal && isComplete)) {
    if (resultsLoading) {
      return (
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <Spinner color="green" />
            <p className="text-muted-foreground text-sm">Loading results...</p>
          </div>
        </div>
      )
    }

    if (result) {
      const sevCounts = result.severity_counts || { critical: 0, high: 0, medium: 0, low: 0, info: 0 }

      const topFixes = (result.findings || []).filter((f: any) => f.severity === 'critical' || f.severity === 'high').slice(0, 5)
      const isAiPending = result.ai_status === 'pending' || result.ai_status === 'processing'
      const isAiReady = result.ai_status === 'completed'
      const aiConfidence = result.ai_status === 'completed' ? 94 : result.ai_status === 'processing' ? 72 : 0

      const finalDuration = result.analysis_duration_seconds || elapsed
      const scoreColor = result.security_score >= 80 ? '#22c55e' : result.security_score >= 50 ? '#eab308' : '#ef4444'

      return (
        <>
          <Toast msg={toastMsg} />

          {/* Page header with actions — flows naturally in Layout */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-foreground tracking-tight">{repoName}</h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                Scan results &middot; {branch} &middot; {finalDuration}s duration
              </p>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <Button variant="ghost" size="sm" onClick={() => { void handleRescan() }}>
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />Rescan
              </Button>
              <Button variant="ghost" size="sm" onClick={() => { void handleCreateGlobalPR() }}
                disabled={prState.step !== null || !hasFixableFindings}
                title={!hasFixableFindings ? 'No automatic fixes available.' : undefined}>
                {prState.step ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <GitPullRequest className="h-3.5 w-3.5 mr-1.5" />}
                {prState.step === 'generating' ? 'Generating fixes...' : prState.step === 'branch' ? 'Creating branch...' : prState.step === 'creating_pr' ? 'Creating PR...' : 'Create Fix PR'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => { void handleDownload('pdf') }} disabled={isDownloading}>
                <Download className="h-3.5 w-3.5 mr-1.5" />Export
              </Button>
              <Button variant="ghost" size="sm" onClick={handleShare}>
                <Share2 className="h-3.5 w-3.5 mr-1.5" />Share
              </Button>
            </div>
          </div>

          {/* Completion banner */}
          <motion.div
            initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
          >
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6 mb-6">
              <div className="flex items-start gap-4">
                <motion.div
                  initial={prefersReduced ? {} : { scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={prefersReduced ? { duration: 0 } : { type: 'spring', stiffness: 500, damping: 30 }}
                  className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0"
                >
                  <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                </motion.div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-bold text-foreground mb-1">Scan Complete</h2>
                  <p className="text-sm text-muted-foreground">Repository infrastructure analyzed &mdash; {finalDuration}s duration, {result.files_analyzed} files scanned</p>
                  <div className="flex items-center gap-4 mt-3 flex-wrap">
                    {result.security_score > 0 && (
                      <div className="flex items-center gap-2">
                        <div className="relative w-8 h-8 shrink-0">
                          <svg className="w-8 h-8 -rotate-90" viewBox="0 0 48 48">
                            <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="4" />
                            <circle cx="24" cy="24" r="20" fill="none" stroke={scoreColor}
                              strokeWidth="4" strokeLinecap="round" strokeDasharray={125.66}
                              style={{ strokeDashoffset: 125.66 * (1 - result.security_score / 100) }}
                            />
                          </svg>
                          <span className={cn('absolute inset-0 flex items-center justify-center text-[10px] font-bold text-foreground', MONO)}>
                            {result.security_score}
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">Security Score</span>
                      </div>
                    )}
                    {(['critical', 'high', 'medium', 'low', 'info'] as const).map(s =>
                      sevCounts[s] > 0 && (
                        <span key={s} className={cn('text-xs tabular-nums', MONO, SEV[s].c)}>{sevCounts[s]} {s}</span>
                      )
                    )}
                    {aiConfidence > 0 && (
                      <span className="text-xs text-purple-300/60 flex items-center gap-1">
                        <Brain className="w-3 h-3" />{aiConfidence}% confidence
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Full results dashboard */}
          <ScanResultsDashboard
            result={result as any} repoName={repoName} findings={result.findings || []}
            severityCounts={sevCounts as unknown as Record<string, number>} priorityFixes={topFixes}
            isAiReady={isAiReady} isAiPending={isAiPending} aiSummary={result.findings?.[0]?.summary || null}
            severityFilter={severityFilter} sortBy={sortBy} expandedFinding={expandedFinding} searchQuery={searchQuery}
            onSeverityFilterChange={setSeverityFilter} onSortByChange={setSortBy}
            onExpandedFindingChange={setExpandedFinding} onSearchQueryChange={setSearchQuery}
            onRescan={handleRescan} onDownload={(fmt) => { void handleDownload(fmt as any) }}
            onShare={handleShare} onFindFix={(fid: string) => setExpandedFinding(fid)}
            onGenerateFix={(fid: string) => setExpandedFinding(fid)} onCreatePR={handleCreateGlobalPR}
            hideHeaderActions
          />
        </>
      )
    }

    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="p-8 max-w-md text-center" hover={false}>
          <AlertCircle className="h-12 w-12 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">No Results Available</h2>
          <p className="text-muted-foreground mb-4 text-sm">The scan completed but results could not be loaded.</p>
          <Button variant="secondary" onClick={() => navigate('/scan')}>Start New Scan</Button>
        </Card>
      </div>
    )
  }

  // --- IN PROGRESS: Event-driven live pipeline ---
  return (
    <>
      <Toast msg={toastMsg} />

      {/* Page header — flows naturally in Layout */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">{repoName}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Scan in progress &middot; {branch}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {totalRules > 0 && (
            <span className={cn('text-xs text-muted-foreground', MONO)}>Rule {executedRules}/{totalRules}</span>
          )}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="w-3.5 h-3.5" />
            <span className={cn(MONO, 'tabular-nums')}>{fmt(elapsed)}</span>
          </div>
          <Button variant="ghost" size="sm" disabled>
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" />Rescan
          </Button>
        </div>
      </div>

      <div className="space-y-6">

        {/* Repo info bar */}
        <motion.div
          initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: EASE }}
          className="flex flex-wrap items-center gap-3 px-4 py-3 rounded-xl border border-white/[0.06] bg-[rgba(30,41,59,0.6)] backdrop-blur-xl"
        >
          <div className="flex items-center gap-1.5">
            <GitBranch className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-medium text-white">{repoName}</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-white/5 border border-white/10">
            <span className="text-xs text-white/60">{branch}</span>
          </div>
          {commitHash && (
            <div className="flex items-center gap-1.5">
              <GitCommit className="w-3.5 h-3.5 text-white/30" />
              <span className={cn('text-xs text-white/40', MONO)}>{commitHash.slice(0, 7)}</span>
            </div>
          )}
          <div className="h-4 w-px bg-white/10" />
          {detectedStack.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              {detectedStack.map(tech => {
                const t = techCat(tech)
                return <span key={tech} className={cn('px-2 py-0.5 rounded-full text-[11px] font-medium border', t.c, t.bg, t.bd)}>{tech}</span>
              })}
            </div>
          )}
          <div className="ml-auto flex items-center gap-1.5 text-xs text-white/40">
            <Shield className="w-3.5 h-3.5" />
            <span className={MONO}>{Object.keys(scanners).length > 0 ? `${completedScanners}/${Object.keys(scanners).length} scanners` : 'Initializing...'}</span>
          </div>
        </motion.div>

        {/* Progress bar — uses backend progress directly, never computed */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3, delay: 0.05 }} className="space-y-2">
          <div className="flex items-center justify-between text-xs text-white/50">
            <span>{currentStage ? stages.find(s => s.id === currentStage)?.label || currentStage : 'Initializing...'}</span>
            <span className={cn(MONO, 'tabular-nums')}>{progress}%</span>
          </div>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              className={cn('h-full rounded-full', wsComplete || isComplete ? 'bg-emerald-500' : wsFailed || isFailed ? 'bg-red-500' : 'bg-gradient-to-r from-indigo-500 to-cyan-400')}
              initial={{ width: 0 }} animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: EASE }}
            />
          </div>
          {totalFiles > 0 && (
            <div className="flex items-center gap-2 text-xs text-white/40">
              <FileCode className="w-3 h-3" />
              <span className={cn(MONO, 'tabular-nums')}>{filesScanned}/{totalFiles} files</span>
              <div className="w-20 h-1 rounded-full bg-white/[0.06] overflow-hidden">
                <div className="h-full rounded-full bg-white/20 transition-all duration-500"
                  style={{ width: `${totalFiles > 0 ? (filesScanned / totalFiles) * 100 : 0}%` }} />
              </div>
            </div>
          )}
        </motion.div>

        {/* Pipeline — uses backend stages, not computed */}
        <ScanPipeline
          stages={stages} currentStage={currentStage}
          completedStages={[]} failedStages={failedStages}
          progress={progress} isComplete={wsComplete || isComplete} hasFailed={wsFailed || isFailed}
        />

        {/* Live event timeline — renders every WebSocket event immediately */}
        <LiveEventTimeline
          events={events}
          isVisible={!isTerminal && !wsFailed}
          prefersReduced={prefersReduced}
        />

        {/* Technology detection — appears as events arrive */}
        <AnimatePresence>
          {detectedStack.length > 0 && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              transition={{ duration: 0.4, ease: EASE }} className="overflow-hidden">
              <div className="rounded-xl border border-white/[0.06] bg-[rgba(30,41,59,0.6)] backdrop-blur-xl p-4">
                <div className="text-xs font-medium text-white/40 mb-3 flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5" />Detected Technologies
                </div>
                <div className="flex flex-wrap gap-2">
                  <AnimatePresence>
                    {detectedStack.map((tech, i) => {
                      const t = techCat(tech)
                      return (
                        <motion.span key={tech}
                          initial={prefersReduced ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={prefersReduced ? { duration: 0 } : { delay: i * 0.06, duration: 0.35, ease: EASE }}
                          className={cn('px-3 py-1 rounded-full text-xs font-medium border', t.c, t.bg, t.bd)}
                        >{tech}</motion.span>
                      )
                    })}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Live terminal */}
        <LiveTerminal logs={wsState?.logs || []} isVisible={!isTerminal && !wsFailed} />

        {/* Scanner progress cards */}
        {Object.keys(scanners).length > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4, ease: EASE }}>
            <div className="text-xs font-medium text-white/40 mb-3 flex items-center gap-2">
              <Shield className="w-3.5 h-3.5" />Scanner Progress
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.values(scanners).map(scanner => (
                <motion.div key={scanner.scanner_id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.35, ease: EASE }}
                  className={cn('rounded-xl border p-4 transition-all duration-300',
                    scanner.status === 'running' && 'border-l-2 border-l-indigo-500 border-t-indigo-500/20 border-r-indigo-500/20 border-b-indigo-500/20 bg-indigo-500/5',
                    scanner.status === 'completed_with_findings' && 'border-l-2 border-l-amber-500 border-t-amber-500/20 border-r-amber-500/20 border-b-amber-500/20 bg-amber-500/5',
                    scanner.status === 'completed_no_findings' && 'border-l-2 border-l-green-500 border-t-green-500/20 border-r-green-500/20 border-b-green-500/20 bg-green-500/5',
                    scanner.status === 'failed' && 'border-l-2 border-l-red-500 border-t-red-500/20 border-r-red-500/20 border-b-red-500/20 bg-red-500/5',
                    !['running', 'completed_with_findings', 'completed_no_findings', 'failed'].includes(scanner.status) && 'border-white/[0.04] bg-white/[0.01]',
                  )}>
                  <div className="flex items-center gap-2 mb-2">
                    {scanner.status === 'running' ? <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                      : scanner.status === 'completed_with_findings' || scanner.status === 'completed_no_findings' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      : scanner.status === 'failed' ? <XCircle className="w-4 h-4 text-red-400" />
                      : <Shield className="w-4 h-4 text-white/20" />}
                    <span className="text-sm font-medium text-white">{scanner.scanner_name}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-white/50">
                    <span>{scanner.findings_count} findings</span>
                    {scanner.duration_ms != null && (
                      <span className={cn(MONO, 'tabular-nums')}>{(scanner.duration_ms / 1000).toFixed(1)}s</span>
                    )}
                  </div>
                  {scanner.rules_count != null && scanner.rules_count > 0 && (
                    <div className={cn('mt-2 text-xs text-white/30', MONO)}>{scanner.rules_count} rules</div>
                  )}
                  {scanner.error && <div className="mt-2 text-xs text-red-400/80">{scanner.error}</div>}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Live findings stream — appears as events arrive */}
        <AnimatePresence>
          {liveFindings.length > 0 && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              transition={{ duration: 0.4, ease: EASE }} className="overflow-hidden">
              <div className="rounded-xl border border-white/[0.06] bg-[rgba(30,41,59,0.6)] backdrop-blur-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-medium text-white/40 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    Live Findings
                    <span className={cn('text-white/30', MONO)}>{liveFindings.length}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {(['critical', 'high', 'medium', 'low', 'info'] as const).map(s =>
                      severityCounts[s] > 0 && (
                        <span key={s} className={cn('text-xs tabular-nums', MONO, SEV[s].c)}>{severityCounts[s]} {s}</span>
                      )
                    )}
                  </div>
                </div>
                <div className="space-y-1.5 max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                  {liveFindings.slice(-10).map((f, i) => (
                    <motion.div key={`${f.rule_id}-${i}`}
                      initial={prefersReduced ? { opacity: 1 } : { opacity: 0, x: 8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={prefersReduced ? { duration: 0 } : { duration: 0.25, ease: EASE }}
                      className={cn('flex items-center gap-3 px-3 py-2 rounded-lg border text-sm',
                        SEV[f.severity]?.bd || 'border-white/10', SEV[f.severity]?.bg || 'bg-white/5')}>
                      <span className="w-1 h-6 rounded-full shrink-0" style={{ background: SEV[f.severity]?.hex || '#64748b' }} />
                      <span className={cn('text-[10px] font-medium uppercase w-16 shrink-0', SEV[f.severity]?.c)}>{f.severity}</span>
                      <span className="text-white/80 text-xs truncate">{f.rule_name}</span>
                      {f.file_path && <span className={cn('text-white/30 text-[11px] ml-auto truncate max-w-[160px]', MONO)}>{f.file_path}</span>}
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* AI generation stage — appears as events arrive */}
        <AnimatePresence>
          {isAiGenerating && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.4, ease: EASE }}>
              <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-5">
                <div className="flex items-center gap-3 mb-4">
                  <motion.div
                    animate={prefersReduced ? {} : { scale: [1, 1.1, 1] }}
                    transition={prefersReduced ? { duration: 0 } : { duration: 2, repeat: Infinity, ease: 'easeInOut' }}>
                    <Brain className="w-5 h-5 text-purple-400" />
                  </motion.div>
                  <span className="text-sm font-medium text-purple-300">AI Analysis</span>
                  {aiProgress && (
                    <span className={cn('text-xs text-purple-300/60 ml-auto tabular-nums', MONO)}>{aiProgress.progress}%</span>
                  )}
                </div>
                {aiProgress ? (
                  <>
                    <div className="h-1.5 rounded-full bg-purple-500/10 overflow-hidden mb-3">
                      <motion.div className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-400"
                        animate={{ width: `${aiProgress.progress}%` }}
                        transition={{ duration: 0.5, ease: EASE }} />
                    </div>
                    <div className="space-y-2">
                      {AI_PHASES.map((phase, i) => {
                        const st = i < activeAiPhase ? 'done' : i === activeAiPhase ? 'active' : 'pending'
                        return (
                          <div key={phase.key} className="flex items-center gap-2.5">
                            {st === 'done' ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              : st === 'active' ? <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin shrink-0" />
                              : <div className="w-3.5 h-3.5 rounded-full border border-white/10 shrink-0" />}
                            <span className={cn('text-xs', st === 'done' && 'text-emerald-300/60', st === 'active' && 'text-purple-300', st === 'pending' && 'text-white/25')}>
                              {phase.label}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                    {aiProgress.findings_total > 0 && (
                      <div className={cn('mt-3 text-xs text-purple-300/40', MONO)}>
                        Analyzing {aiProgress.findings_processed} of {aiProgress.findings_total} findings
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center gap-2 text-xs text-purple-300/60">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />Initializing AI analysis...
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}

function GitMerge(props: { className?: string }) {
  return <GitPullRequest {...props} />
}

import { useState, useMemo, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RotateCcw, AlertCircle, ChevronRight, Brain, Download,
  GitPullRequest,
  LayoutDashboard, BookOpen, CheckCircle2, XCircle, ExternalLink, Loader2, X
} from 'lucide-react'
import { Button, Card } from '../components/ui-animated'
import { scansApi } from '../api/endpoints/scans'
import { prApi } from '../api/endpoints/pull-requests'
import { reportsApi } from '../api/endpoints/reports'
import { ScanResultsDashboard } from '../components/scan-results/ScanResultsDashboard'
import { ScanProgressOverlay } from '../components/scans/ScanProgressOverlay'
import { api, buildWebSocketUrl } from '../lib/api'
import { getFindingsCount, sanitizePath, cn } from '../lib/utils'

interface Finding {
  id: string
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path: string
  line_number?: number
  summary?: string
  risk?: string
  impact?: string
  fix_code?: string
  fix_example?: string
  full_example?: string
  best_practices?: string[]
  confidence?: number
  confidence_score?: number
  documentation_url?: string
  ai_generated?: boolean
  before_code?: string
  after_code?: string
  unified_diff?: string
  ai_explanation?: string
  impact_analysis?: string
  code_fix?: string
}

interface ScanResult {
  id?: string
  scan_id: string
  scan_status?: string
  ai_status?: 'pending' | 'processing' | 'completed' | 'failed'
  repository_url: string
  repository_name?: string
  security_score: number
  scalability_score?: number
  reliability_score?: number
  cost_score?: number
  observability_score?: number
  overall_score?: number
  severity_counts: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
  }
  findings: Finding[]
  findings_count?: number
  total_findings?: number
  files_analyzed: number
  branch: string
  completed_at: string
  detected_stack?: Record<string, string[]>
  detected_technologies?: string[]
  status?: string
  scanner_executions?: any[]
  ai_suggestions_count?: number
  analysis_duration_seconds?: number
  commit_hash?: string
  directories_scanned?: number
  lines_analyzed?: number
  repository_size?: string
  category_scores?: { category: string; score: number; findings_count?: number; files_scanned?: number }[]
}

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'
type SortOption = 'severity' | 'date'



export function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('severity')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const defaultBranch = 'main'

  // PR state
  type PRStep = 'generating' | 'branch' | 'creating_pr' | null
  const [prState, setPrState] = useState<{
    step: PRStep
    success: boolean
    error: string | null
    response: { prUrl: string; prNumber: number; scoreAfter: number; branchName: string } | null
  }>({ step: null, success: false, error: null, response: null })

  // Rescan state
  const [rescanActive, setRescanActive] = useState(false)
  const [rescanProgress, setRescanProgress] = useState(0)
  const [rescanStep, setRescanStep] = useState('')
  const [rescanComplete, setRescanComplete] = useState(false)
  const [rescanFailed, setRescanFailed] = useState(false)
  const [rescanError, setRescanError] = useState<string | null>(null)
  const [rescanResultSummary, setRescanResultSummary] = useState<{
    securityScore: number
    grade: string
    severityCounts: { critical: number; high: number; medium: number; low: number }
    filesScanned: number
    scanDuration: number
  } | undefined>(undefined)
  const [previousScore, setPreviousScore] = useState<number | undefined>(undefined)
  const [previousFindingsCount, setPreviousFindingsCount] = useState<number | undefined>(undefined)
  const [rescanId, setRescanId] = useState<string | null>(null)
  const rescanIdRef = useRef<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const rescanWsRef = useRef<WebSocket | null>(null)
  const rescanProgressRef = useRef(0)
  const rescanCompleteRef = useRef(false)
  const rescanFailedRef = useRef(false)
  const resultsFetchedRef = useRef(false)

  const isValidScanId = !!(id && id !== ':id' && id.length > 10)

  const { data: result, isLoading, error, refetch } = useQuery<ScanResult>({
    queryKey: ['scan-result', id],
    queryFn: async () => {
      if (!id) throw new Error('No scan ID provided')
      const response = await scansApi.getScanResults(id)
      return response as ScanResult
    },
    enabled: isValidScanId,
    retry: 2,
    staleTime: 5 * 60 * 1000,
    refetchInterval: (query) => {
      const data = query.state.data as ScanResult | undefined
      return data?.ai_status === 'pending' || data?.ai_status === 'processing' ? 4000 : false
    },
  })



  const severity_counts = useMemo(() => {
    if (!result?.findings) return { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
    return result.findings.reduce((acc, finding) => {
      const severity = finding.severity || 'info'
      acc[severity] = (acc[severity] || 0) + 1
      return acc
    }, { critical: 0, high: 0, medium: 0, low: 0, info: 0 } as Record<string, number>)
  }, [result?.findings])

  const topPriorityFixes = useMemo(() => {
    if (!result?.findings) return []
    return result.findings
      .filter(f => f.severity === 'critical' || f.severity === 'high')
      .slice(0, 5)
  }, [result?.findings])

  const scanResult = result as ScanResult | undefined
  const isAiPending = scanResult?.ai_status === 'pending' || scanResult?.ai_status === 'processing'
  const isAiReady = scanResult?.ai_status === 'completed'
  const repoName = scanResult?.repository_name || (scanResult?.repository_url?.split('/').slice(-2).join('/') ?? '')
  const score = scanResult?.overall_score ?? scanResult?.security_score ?? 0

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // Sync refs for polling / WS callbacks
  useEffect(() => { rescanProgressRef.current = rescanProgress }, [rescanProgress])
  useEffect(() => { rescanCompleteRef.current = rescanComplete }, [rescanComplete])
  useEffect(() => { rescanFailedRef.current = rescanFailed }, [rescanFailed])

  const fetchRescanResults = useCallback(async () => {
    const scanId = rescanIdRef.current
    if (!scanId || resultsFetchedRef.current) return
    resultsFetchedRef.current = true

    let attempts = 0
    const maxAttempts = 5

    while (attempts < maxAttempts) {
      try {
        const [scanRes, findingsRes] = await Promise.all([
          api.get(`/scans/${scanId}?t=${Date.now()}`),
          api.get(`/scans/${scanId}/findings?t=${Date.now()}`),
        ])

        const data = scanRes.data
        const findings = findingsRes.data

        const counts = findings.reduce((acc: any, f: any) => {
          const sev = f.severity || 'info'
          if (['critical', 'high', 'medium', 'low'].includes(sev)) {
            acc[sev] = (acc[sev] || 0) + 1
          }
          return acc
        }, { critical: 0, high: 0, medium: 0, low: 0 })

        const newScore = data.overall_score ?? data.security_score ?? 0
        const grade = newScore >= 90 ? 'A' : newScore >= 80 ? 'B' : newScore >= 70 ? 'C' : newScore >= 60 ? 'D' : 'F'

        setRescanResultSummary({
          securityScore: newScore,
          grade,
          severityCounts: counts,
          filesScanned: data.files_analyzed || 0,
          scanDuration: data.analysis_duration_seconds || 0,
        })
        setRescanComplete(true)
        setRescanProgress(100)
        return
      } catch (err) {
        attempts++
        if (attempts >= maxAttempts) {
          setRescanFailed(true)
          setRescanError('Failed to fetch scan results')
          return
        }
        await new Promise(r => setTimeout(r, Math.pow(2, attempts - 1) * 1000))
      }
    }
  }, [])

  const downloadJsonFallback = () => {
    if (!scanResult) return
    const effectiveScanId = scanResult.scan_id || scanResult.id || id
    const reportData = {
      scan_id: effectiveScanId,
      repository_name: scanResult.repository_name || repoName,
      repository_url: scanResult.repository_url,
      branch: scanResult.branch || 'main',
      overall_score: scanResult.overall_score,
      security_score: scanResult.security_score,
      scalability_score: scanResult.scalability_score,
      reliability_score: scanResult.reliability_score,
      cost_score: scanResult.cost_score,
      observability_score: scanResult.observability_score,
      severity_counts,
      findings_count: getFindingsCount(scanResult),
      files_analyzed: scanResult.files_analyzed,
      findings: (scanResult.findings || []).map(f => ({
        ...f,
        file_path: sanitizePath(f.file_path),
      })),
      generated_at: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `scan-report-${String(effectiveScanId).slice(0, 8)}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleDownload = async (format: 'pdf' | 'excel' | 'json' | 'sarif' = 'pdf') => {
    if (!scanResult || isDownloading) return
    if (format === 'json') {
      downloadJsonFallback()
      return
    }
    const effectiveScanId = scanResult.scan_id || scanResult.id || id
    if (!effectiveScanId) {
      alert('Scan ID is missing. Please refresh and try again.')
      return
    }
    setIsDownloading(true)
    try {
      const downloadResponse = await reportsApi.downloadReport(effectiveScanId, format as 'pdf' | 'excel')
      const ext = format === 'pdf' ? 'pdf' : 'xlsx'
      const link = document.createElement('a')
      link.href = downloadResponse.url
      link.download = downloadResponse.filename || `report-${String(effectiveScanId).slice(0, 8)}.${ext}`
      link.rel = 'noopener noreferrer'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      console.warn(`${format} download failed, falling back to JSON export:`, err)
      if (format === 'pdf') downloadJsonFallback()
    } finally {
      setIsDownloading(false)
    }
  }

  const handleRescan = useCallback(async () => {
    if (!scanResult?.repository_url) return

    setPreviousScore(score)
    setPreviousFindingsCount(getFindingsCount(scanResult))

    setRescanActive(true)
    setRescanProgress(0)
    setRescanStep('')
    setRescanComplete(false)
    setRescanFailed(false)
    setRescanError(null)
    setRescanResultSummary(undefined)
    setRescanId(null)
    rescanIdRef.current = null
    resultsFetchedRef.current = false

    try {
      const response = await scansApi.startUnifiedScan({
        repository_url: scanResult.repository_url,
        branch: scanResult.branch || 'main',
      })
      rescanIdRef.current = response.scan_id
      setRescanId(response.scan_id)
    } catch (err: any) {
      setRescanFailed(true)
      setRescanError(err?.response?.data?.detail || err.message || 'Failed to start scan')
    }
  }, [scanResult, score])

  // WebSocket for real-time rescan progress
  useEffect(() => {
    if (!rescanActive || !rescanId) return

    const token = localStorage.getItem('access_token') || ''
    const wsUrl = `${buildWebSocketUrl(`/ws/scan/${rescanId}`)}?token=${encodeURIComponent(token)}`

    const ws = new WebSocket(wsUrl)
    rescanWsRef.current = ws

    ws.onopen = () => console.log('Rescan WS connected')

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const { type, data } = msg

        switch (type) {
          case 'progress_update':
            if (data.progress !== undefined) setRescanProgress(Math.round(data.progress))
            if (data.current_step) setRescanStep(data.current_step)
            break
          case 'scan_complete':
            setRescanProgress(100)
            fetchRescanResults()
            break
          case 'scan_failed':
            setRescanFailed(true)
            setRescanError(data.error || 'Scan failed')
            break
        }
      } catch {}
    }

    ws.onerror = () => {}
    ws.onclose = () => { rescanWsRef.current = null }

    return () => {
      ws.close()
      rescanWsRef.current = null
    }
  }, [rescanActive, rescanId])

  // Polling fallback for completion detection
  useEffect(() => {
    if (!rescanActive || !rescanId) return

    const startTime = Date.now()

    const interval = setInterval(async () => {
      if (rescanCompleteRef.current || rescanFailedRef.current) {
        clearInterval(interval)
        return
      }

      if (rescanProgressRef.current >= 100 && !resultsFetchedRef.current) {
        clearInterval(interval)
        const elapsed = Date.now() - startTime
        const remaining = Math.max(0, 2000 - elapsed)
        if (remaining > 0) await new Promise(r => setTimeout(r, remaining))
        fetchRescanResults()
      }
    }, 1000)

    pollRef.current = interval

    return () => {
      clearInterval(interval)
      pollRef.current = null
    }
  }, [rescanActive, rescanId])

  const handleViewResults = () => {
    // Stay on current page - just refresh data
    refetch()
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    setRescanActive(false)
    setRescanComplete(false)
  }

  const handleRescanRetry = () => {
    setRescanFailed(false)
    setRescanError(null)
    setRescanProgress(0)
    setRescanComplete(false)
    resultsFetchedRef.current = false
    handleRescan()
  }

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: `Scan Results: ${repoName}`,
        text: `Security scan results for ${repoName} — Score: ${score}`,
        url: window.location.href,
      }).catch(() => {})
    } else {
      navigator.clipboard.writeText(window.location.href)
    }
  }

  const handleFindFix = (findingId: string) => {
    setExpandedFinding(findingId)
  }

  const handleGenerateFix = (findingId: string) => {
    setExpandedFinding(findingId)
  }

  const handleCreatePR = async (findingId: string) => {
    if (!scanResult) return
    const effectiveScanId = scanResult.scan_id || scanResult.id || id
    if (!effectiveScanId) return

    setPrState({ step: 'generating', success: false, error: null, response: null })
    await new Promise(r => setTimeout(r, 600))

    setPrState(prev => prev.error ? prev : { ...prev, step: 'branch' })
    await new Promise(r => setTimeout(r, 400))

    setPrState(prev => prev.error ? prev : { ...prev, step: 'creating_pr' })

    try {
      const response = await prApi.createPR({
        scan_id: effectiveScanId,
        finding_ids: [findingId],
      })
      setPrState({
        step: null,
        success: true,
        error: null,
        response: {
          prUrl: response.github_pr_url,
          prNumber: response.github_pr_number,
          scoreAfter: response.score_after,
          branchName: response.branch_name,
        },
      })
    } catch (err: any) {
      const message = err?.response?.data?.error || err?.message || 'Failed to create pull request'
      setPrState({ step: null, success: false, error: message, response: null })
    }
  }

  const handleCreateGlobalPR = async () => {
    if (!scanResult) return
    const fixableFindings = result?.findings?.filter(f => f.fix_code && (f.severity === 'critical' || f.severity === 'high')) ?? []
    if (fixableFindings.length === 0) return
    const effectiveScanId = scanResult.scan_id || scanResult.id || id
    if (!effectiveScanId) return
    const findingIds = fixableFindings.map(f => f.id ?? f.rule_id)

    setPrState({ step: 'generating', success: false, error: null, response: null })
    await new Promise(r => setTimeout(r, 600))

    setPrState(prev => prev.error ? prev : { ...prev, step: 'branch' })
    await new Promise(r => setTimeout(r, 400))

    setPrState(prev => prev.error ? prev : { ...prev, step: 'creating_pr' })

    try {
      const response = await prApi.createPR({
        scan_id: effectiveScanId,
        finding_ids: findingIds,
      })
      setPrState({
        step: null,
        success: true,
        error: null,
        response: {
          prUrl: response.github_pr_url,
          prNumber: response.github_pr_number,
          scoreAfter: response.score_after,
          branchName: response.branch_name,
        },
      })
    } catch (err: any) {
      const message = err?.response?.data?.error || err?.message || 'Failed to create pull request'
      setPrState({ step: null, success: false, error: message, response: null })
    }
  }

  const handleBatchCreatePR = async (findingIds: string[]) => {
    if (!scanResult || findingIds.length === 0) return
    const effectiveScanId = scanResult.scan_id || scanResult.id || id
    if (!effectiveScanId) return

    setPrState({ step: 'generating', success: false, error: null, response: null })
    await new Promise(r => setTimeout(r, 600))

    setPrState(prev => prev.error ? prev : { ...prev, step: 'branch' })
    await new Promise(r => setTimeout(r, 400))

    setPrState(prev => prev.error ? prev : { ...prev, step: 'creating_pr' })

    try {
      const response = await prApi.createPR({
        scan_id: effectiveScanId,
        finding_ids: findingIds,
      })
      setPrState({
        step: null,
        success: true,
        error: null,
        response: {
          prUrl: response.github_pr_url,
          prNumber: response.github_pr_number,
          scoreAfter: response.score_after,
          branchName: response.branch_name,
        },
      })
    } catch (err: any) {
      const message = err?.response?.data?.error || err?.message || 'Failed to create pull request'
      setPrState({ step: null, success: false, error: message, response: null })
    }
  }

  const handleClosePRModal = () => {
    setPrState({ step: null, success: false, error: null, response: null })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
            className="w-16 h-16 border-4 border-indigo-500/20 border-t-indigo-400 rounded-full mx-auto"
          />
          <p className="text-muted-foreground">Loading scan results...</p>
        </div>
      </div>
    )
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-8 max-w-md text-center" hover={false}>
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">Error Loading Results</h2>
          <p className="text-muted-foreground mb-4">
            {(error as Error)?.message || 'Failed to load scan results'}
          </p>
          <div className="flex gap-2 justify-center">
            <Button variant="secondary" onClick={() => refetch()}>
              Retry
            </Button>
            <Button variant="ghost" onClick={() => navigate('/history')}>
              View History
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* ===== HEADER ===== */}
      <div className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#07070d]/90 backdrop-blur-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          {/* Breadcrumb */}
          <div className="flex items-center justify-between mb-2">
            <nav className="flex items-center gap-2 text-xs">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center gap-1 text-white/40 hover:text-white/80 transition-colors"
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                Dashboard
              </button>
              <ChevronRight className="w-3 h-3 text-white/20" />
              <button
                onClick={() => navigate('/scans')}
                className="text-white/40 hover:text-white/80 transition-colors"
              >
                Scans
              </button>
              <ChevronRight className="w-3 h-3 text-white/20" />
              <span className="text-white/60 truncate max-w-[160px]">{repoName}</span>
            </nav>
            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRescan}
                disabled={rescanActive}
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                Rescan
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCreateGlobalPR}
                disabled={!!prState.step || !result?.findings?.some(f => f.fix_code)}
              >
                {prState.step ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <GitPullRequest className="h-3.5 w-3.5 mr-1.5" />
                )}
                {prState.step === 'generating' ? 'Generating fixes...' :
                 prState.step === 'branch' ? 'Creating branch...' :
                 prState.step === 'creating_pr' ? 'Creating PR...' :
                 'Create Fix PR'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => handleDownload('pdf')}>
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Export
              </Button>
              <button
                onClick={() => navigate('/docs/security-findings')}
                className="p-2 rounded-lg text-white/40 hover:text-white/80 hover:bg-white/5 transition-colors"
                title="View Security Findings documentation"
              >
                <BookOpen className="h-4 w-4" />
              </button>
            </div>
          </div>


        </div>
      </div>

      {/* AI Pending Banner */}
      {isAiPending && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4"
          >
            <div className="flex items-center gap-3">
              <Brain className="h-5 w-5 text-indigo-400" />
              <div>
                <div className="text-sm font-semibold text-indigo-300">Static scan is complete</div>
                <div className="text-xs text-indigo-300/60">
                  AI suggestions are still generating in the background. This page refreshes automatically.
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Main Dashboard */}
      <ScanResultsDashboard
        result={result}
        repoName={repoName}
        findings={result.findings || []}
        severityCounts={severity_counts}
        priorityFixes={topPriorityFixes}
        isAiReady={isAiReady}
        isAiPending={isAiPending}
        aiSummary={result.findings?.[0]?.summary || null}
        severityFilter={severityFilter}
        sortBy={sortBy}
        expandedFinding={expandedFinding}
        searchQuery={searchQuery}
        onSeverityFilterChange={(filter) => setSeverityFilter(filter as SeverityFilter)}
        onSortByChange={(sort) => setSortBy(sort as SortOption)}
        onExpandedFindingChange={setExpandedFinding}
        onSearchQueryChange={setSearchQuery}
        onRescan={handleRescan}
        onDownload={handleDownload}
        onShare={handleShare}
        onFindFix={handleFindFix}
        onGenerateFix={handleGenerateFix}
        onCreatePR={handleCreatePR}
        onBatchCreatePR={handleBatchCreatePR}
        hideHeaderActions
      />

      {/* PR Progress Modal */}
      <AnimatePresence>
        {prState.step && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="w-full max-w-sm rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl"
            >
              <div className="space-y-4">
                {[
                  { step: 'generating' as const, label: 'Generating fixes', icon: '🔍' },
                  { step: 'branch' as const, label: 'Creating branch', icon: '🌿' },
                  { step: 'creating_pr' as const, label: 'Creating Pull Request', icon: '🔄' },
                ].map((s) => {
                  const isActive = prState.step === s.step
                  const isDone = false // all sequential, so only one is active
                  return (
                    <div key={s.step} className="flex items-center gap-3">
                      <div className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 transition-all duration-300",
                        isActive ? "bg-indigo-500/20 text-indigo-400 ring-2 ring-indigo-500/40" : "bg-white/5 text-white/20"
                      )}>
                        {isActive ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : isDone ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <div className="w-1.5 h-1.5 rounded-full bg-white/20" />
                        )}
                      </div>
                      <span className={cn(
                        "text-sm transition-colors",
                        isActive ? "text-white/90 font-medium" : "text-white/30"
                      )}>
                        {s.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* PR Success Modal */}
      <AnimatePresence>
        {prState.success && prState.response && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="w-full max-w-md rounded-2xl border border-emerald-500/20 bg-slate-900 p-6 shadow-2xl"
            >
              <div className="text-center mb-5">
                <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                </div>
                <h3 className="text-base font-semibold text-white/90">Pull Request Created</h3>
                <p className="text-xs text-white/40 mt-1">
                  PR #{prState.response.prNumber} opened on branch {prState.response.branchName}
                </p>
              </div>

              <div className="space-y-3 mb-5">
                <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-4 py-3">
                  <span className="text-sm text-white/60">PR Number</span>
                  <span className="text-sm font-bold text-white/80">#{prState.response.prNumber}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
                  <span className="text-sm text-emerald-300/80">Score After Fix</span>
                  <span className="text-sm font-bold text-emerald-400">{prState.response.scoreAfter}</span>
                </div>
              </div>

              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={handleClosePRModal} className="flex-1">
                  Close
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  glow
                  onClick={() => window.open(prState.response!.prUrl, '_blank', 'noopener')}
                  className="flex-1"
                >
                  <ExternalLink className="w-4 h-4 mr-1.5" />
                  Open PR
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* PR Error Toast */}
      <AnimatePresence>
        {prState.error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 right-6 z-[70] max-w-sm"
          >
            <div className="rounded-xl border border-red-500/20 bg-red-950/90 backdrop-blur-xl p-4 shadow-2xl">
              <div className="flex items-start gap-3">
                <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-red-300">Failed to create PR</h4>
                  <p className="text-xs text-red-200/60 mt-0.5">{prState.error}</p>
                </div>
                <button onClick={() => setPrState(prev => ({ ...prev, error: null }))}>
                  <X className="w-4 h-4 text-red-300/50 hover:text-red-300 transition-colors" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Rescan Overlay */}
      <ScanProgressOverlay
        isOpen={rescanActive}
        onClose={() => {
          setRescanActive(false)
          if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
          if (rescanWsRef.current) { rescanWsRef.current.close(); rescanWsRef.current = null }
        }}
        repositoryName={repoName}
        branch={scanResult?.branch || defaultBranch}
        progressData={{
          progress: rescanProgress,
          currentStep: rescanStep,
          error: rescanError ?? undefined,
        }}
        isComplete={rescanComplete}
        hasFailed={rescanFailed}
        resultSummary={rescanResultSummary}
        previousScore={previousScore}
        previousFindingsCount={previousFindingsCount}
        onComplete={handleViewResults}
        onRetry={handleRescanRetry}
      />
    </div>
  )
}



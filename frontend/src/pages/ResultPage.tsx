import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  RotateCcw, AlertCircle, ChevronRight, Brain, Download,
  GitBranch, GitPullRequest, Clock, FileCode, Shield,
  Star, Home, LayoutDashboard
} from 'lucide-react'
import { Button, Card, ScoreCircle } from '../components/ui-animated'
import api from '../lib/api'
import { reportsApi } from '../api/endpoints/reports'
import { scansApi } from '../api/endpoints/scans'
import { ScanResultsDashboard } from '../components/scan-results/ScanResultsDashboard'
import { ScanProgressOverlay } from '../components/scans/ScanProgressOverlay'

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
}

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'
type SortOption = 'severity' | 'date'

function getGrade(score: number): string {
  if (score >= 90) return 'A'
  if (score >= 80) return 'B'
  if (score >= 70) return 'C'
  if (score >= 60) return 'D'
  return 'F'
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-400'
  if (score >= 60) return 'text-yellow-400'
  return 'text-red-400'
}

function relativeTime(dateStr: string): string {
  if (!dateStr) return 'N/A'
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  if (isNaN(then)) return 'N/A'
  const diff = Math.max(0, Math.floor((now - then) / 1000))
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('severity')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const defaultBranch = 'main'

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
  const rescanIdRef = useRef<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

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

  const filteredFindings = useMemo(() => {
    if (!result?.findings) return []
    let filtered = [...result.findings]
    if (severityFilter !== 'all') {
      filtered = filtered.filter(f => f.severity === severityFilter)
    }
    const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    filtered.sort((a, b) => {
      if (sortBy === 'severity') {
        return severityOrder[a.severity] - severityOrder[b.severity]
      }
      return 0
    })
    return filtered
  }, [result?.findings, severityFilter, sortBy])

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
  const grade = getGrade(score)
  const findingsCount = scanResult?.total_findings ?? scanResult?.findings_count ?? scanResult?.findings?.length ?? 0
  const filesScanned = scanResult?.files_analyzed ?? 0
  const techStack = scanResult?.detected_technologies ?? []
  const lastScanTime = relativeTime(scanResult?.completed_at ?? '')

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
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
      findings_count: scanResult.total_findings || scanResult.findings_count || scanResult.findings?.length || 0,
      files_analyzed: scanResult.files_analyzed,
      findings: scanResult.findings || [],
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

    const prevScore = score
    const prevFindings = findingsCount
    setPreviousScore(prevScore)
    setPreviousFindingsCount(prevFindings)

    setRescanActive(true)
    setRescanProgress(0)
    setRescanComplete(false)
    setRescanFailed(false)
    setRescanError(null)
    setRescanResultSummary(undefined)

    try {
      const response = await scansApi.startUnifiedScan({
        repository_url: scanResult.repository_url,
        branch: scanResult.branch || 'main',
      })

      const newScanId = response.scan_id
      rescanIdRef.current = newScanId

      pollRef.current = setInterval(async () => {
        try {
          const statusData = await scansApi.getScanProgress(newScanId)

          if (statusData.status === 'completed' || statusData.progress >= 100) {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setRescanProgress(100)
            setRescanComplete(true)

            // Use unified results endpoint (works for both guest and auth scans)
            const resultsResponse = await api.get(`/scan/results/${newScanId}`)
            const results = resultsResponse.data

            const unifiedResults: Partial<ScanResult> = {
              scan_id: results.scan_id || newScanId,
              repository_url: scanResult!.repository_url,
              repository_name: scanResult!.repository_name,
              branch: scanResult!.branch || 'main',
              security_score: results.security_score || results.overall_score || 0,
              overall_score: results.overall_score || results.security_score || 0,
              files_analyzed: results.files_analyzed || results.filesAnalyzed || 0,
              completed_at: results.completed_at || new Date().toISOString(),
              severity_counts: results.severity_counts || { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
              findings: results.findings || [],
              total_findings: results.findings_count || results.findings?.length || 0,
              detected_technologies: results.detected_technologies || [],
              status: results.status || 'completed',
              ai_status: results.ai_status || (results.findings ? 'completed' : 'pending'),
            }

            const newScore = unifiedResults.overall_score ?? unifiedResults.security_score ?? 0
            setRescanResultSummary({
              securityScore: newScore,
              grade: getGrade(newScore),
              severityCounts: {
                critical: unifiedResults.severity_counts?.critical ?? 0,
                high: unifiedResults.severity_counts?.high ?? 0,
                medium: unifiedResults.severity_counts?.medium ?? 0,
                low: unifiedResults.severity_counts?.low ?? 0,
              },
              filesScanned: unifiedResults.files_analyzed ?? 0,
              scanDuration: 0,
            })

            // Update query cache for the current scan ID (same page, no navigation)
            queryClient.setQueryData(['scan-result', id], unifiedResults)
          } else if (statusData.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setRescanFailed(true)
            setRescanError((statusData as any).error_message || 'Scan failed to complete')
          } else {
            setRescanProgress(statusData.progress)
            setRescanStep(statusData.current_step || '')
          }
        } catch (err) {
          console.error('Rescan polling error:', err)
        }
      }, 1000)
    } catch (err: any) {
      setRescanFailed(true)
      setRescanError(err.message || 'Failed to start rescan')
    }
  }, [scanResult?.repository_url, scanResult?.branch, score, findingsCount, id, queryClient])

  const handleViewResults = () => {
    setRescanActive(false)
    setRescanComplete(false)
    setRescanFailed(false)
    setRescanProgress(0)
    setRescanResultSummary(undefined)
    refetch()
  }

  const handleRescanRetry = () => {
    setRescanFailed(false)
    setRescanError(null)
    setRescanProgress(0)
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

  const handleCreatePR = (findingId: string) => {
    const finding = result?.findings?.find(f => f.id === findingId)
    if (finding?.fix_code && scanResult) {
      const effectiveScanId = scanResult.scan_id || scanResult.id || id
      const prWindow = window.open('', '_blank')
      if (prWindow) {
        prWindow.document.write(`<pre>${finding.fix_code}</pre>`)
        prWindow.document.close()
      }
    }
  }

  const handleCreateGlobalPR = () => {
    const fixableFindings = result?.findings?.filter(f => f.fix_code && (f.severity === 'critical' || f.severity === 'high')) ?? []
    const target = fixableFindings[0]
    if (target) {
      handleCreatePR(target.id ?? target.rule_id)
    }
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
                disabled={!result?.findings?.some(f => f.fix_code)}
              >
                <GitPullRequest className="h-3.5 w-3.5 mr-1.5" />
                Create Fix PR
              </Button>
              <Button variant="ghost" size="sm" onClick={() => handleDownload('pdf')}>
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Export
              </Button>
            </div>
          </div>

          {/* Header Info Card */}
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              {/* Left: Repo name */}
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 shrink-0">
                  <GitBranch className="h-4 w-4 text-indigo-400" />
                </div>
                <div className="min-w-0">
                  <h1 className="text-sm font-semibold text-white/90 truncate">{repoName}</h1>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] font-mono px-1.5 py-0.5 rounded border border-white/[0.08] bg-white/[0.04] text-indigo-300/80">
                      {scanResult?.branch || defaultBranch}
                    </span>
                    <span className="text-[11px] text-white/30 hidden sm:inline">{lastScanTime}</span>
                  </div>
                </div>
              </div>

              {/* Divider */}
              <div className="hidden sm:block w-px h-8 bg-white/[0.06]" />

              {/* Center: Score + Stats */}
              <div className="flex flex-wrap items-center gap-3">
                {/* Score + Grade */}
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'text-lg font-bold font-mono tabular-nums',
                    getScoreColor(score)
                  )}>
                    {score}
                  </div>
                  <div className={cn(
                    'text-[10px] font-bold px-1.5 py-0.5 rounded',
                    grade === 'A' ? 'bg-emerald-500/15 text-emerald-400' :
                    grade === 'B' ? 'bg-emerald-500/10 text-emerald-300' :
                    grade === 'C' ? 'bg-yellow-500/10 text-yellow-400' :
                    grade === 'D' ? 'bg-orange-500/10 text-orange-400' :
                    'bg-red-500/10 text-red-400'
                  )}>
                    {grade}
                  </div>
                </div>

                <div className="w-px h-4 bg-white/[0.06]" />

                {/* Stats */}
                <div className="flex items-center gap-3 text-[11px] text-white/50">
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-3 w-3 text-white/30" />
                    <span>{findingsCount} findings</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <FileCode className="h-3 w-3 text-white/30" />
                    <span>{filesScanned} files</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Technology Badges */}
            {techStack.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-3 border-t border-white/[0.04]">
                {techStack.map((tech) => (
                  <span
                    key={tech}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-white/50"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            )}
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
        hideHeaderActions
      />

      {/* Rescan Overlay */}
      <ScanProgressOverlay
        isOpen={rescanActive}
        onClose={() => {
          setRescanActive(false)
          if (pollRef.current) clearInterval(pollRef.current)
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
        onViewResults={handleViewResults}
        onRetry={handleRescanRetry}
      />
    </div>
  )
}

function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(' ')
}

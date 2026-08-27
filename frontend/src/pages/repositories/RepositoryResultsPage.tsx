import { useState, useMemo, useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RotateCcw, AlertCircle, ChevronRight, Brain, Download,
  GitPullRequest, LayoutDashboard, BookOpen, CheckCircle2,
  XCircle, ExternalLink, Loader2, X, CheckCheck
} from 'lucide-react'
import { Button, Card } from '../../components/ui-animated'
import { ErrorState } from '../../components/ui/error-state'
import { prApi } from '../../api/endpoints/pull-requests'
import { reportsApi } from '../../api/endpoints/reports'
import { ScanResultsDashboard } from '../../components/scan-results/ScanResultsDashboard'
import { ScanProgressOverlay } from '../../components/scans/ScanProgressOverlay'
import { AIProgressBanner } from '../../components/scans/AIProgressBanner'
import apiClient from '../../api/endpoints/client'
import { useScanWebSocket } from '../../hooks/useScanWebSocket'
import { useRepositoryScan } from '../../hooks/useRepositoryScan'
import { scansApi } from '../../api/endpoints/scans'
import { resolveSecurityScore } from '../../lib/security-score'
import { normalizeLifecycleStage } from '../../lib/scanLifecycle'
import type { ScanStage, StageMetadata } from '../../types'
import { getFindingsCount, sanitizePath, cn, copyToClipboard } from '../../lib/utils'

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'
type SortOption = 'severity' | 'date'

export function RepositoryResultsPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>()
  const navigate = useNavigate()
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('severity')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [scanStarted, setScanStarted] = useState(false)
  const [scanCompleteToast, setScanCompleteToast] = useState<{ score: number; findings: number } | null>(null)

  // Fetch repository results
  const { data: repoData, isLoading, error, refetch } = useQuery({
    queryKey: ['repository-results', repositoryId],
    queryFn: async () => {
      if (!repositoryId) throw new Error('No repository ID')
      const response = await apiClient.get(`/repositories/${repositoryId}/results`)
      return response.data
    },
    enabled: !!repositoryId,
    retry: 2,
    staleTime: 30 * 1000,
    refetchInterval: (query) => {
      const data = query.state.data as any
      // Poll while AI is still running
      if (data?.scan?.ai_status === 'pending' || data?.scan?.ai_status === 'queued' || data?.scan?.ai_status === 'processing') {
        return 4000
      }
      return false
    },
  })

  const scanResult = repoData?.scan
  const scanId = scanResult?.id as string | undefined

  const { data: unifiedScanResult } = useQuery({
    queryKey: ['scan-results', scanId],
    queryFn: () => scansApi.getScanResults(scanId!),
    enabled: !!scanId,
    staleTime: 30_000,
    refetchInterval: (query) => {
      const data = query.state.data as { ai_status?: string } | undefined
      const status = data?.ai_status ?? scanResult?.ai_status
      if (status === 'pending' || status === 'queued' || status === 'processing') return 4000
      return false
    },
  })

  const displayResult = unifiedScanResult ?? scanResult
  const repoName = repoData?.repository_name || ''
  const repoUrl = repoData?.repository_url || ''
  const defaultBranch = repoData?.default_branch || 'main'

  const severityCounts = useMemo(() => {
    if (!displayResult?.findings) return { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
    return displayResult.findings.reduce((acc: Record<string, number>, f: any) => {
      const sev = f.severity || 'info'
      acc[sev] = (acc[sev] || 0) + 1
      return acc
    }, { critical: 0, high: 0, medium: 0, low: 0, info: 0 })
  }, [displayResult?.findings])

  const topPriorityFixes = useMemo(() => {
    if (!displayResult?.findings) return []
    return displayResult.findings
      .filter((f: any) => f.severity === 'critical' || f.severity === 'high')
      .slice(0, 5)
  }, [displayResult?.findings])

  const isAiPending = displayResult?.ai_status === 'pending' || displayResult?.ai_status === 'queued' || displayResult?.ai_status === 'processing'
  const isAiReady = displayResult?.ai_status === 'completed'
  const resolvedScore = resolveSecurityScore(displayResult)?.value ?? 0

  const { data: stagesData } = useQuery({
    queryKey: ['scan-stages'],
    queryFn: () => scansApi.getStages(),
    staleTime: Infinity,
  })
  const stages: StageMetadata[] = stagesData || []

  // Scan management hook
  const { state: scanState, startScan, retry: retryScan, cancelScan, handleScanComplete, handleScanFailed, handleAIComplete } = useRepositoryScan({
    repositoryUrl: repoUrl,
    repositoryId,
    branch: defaultBranch,
    queryKeysToInvalidate: repositoryId ? [['repository-results', repositoryId]] : undefined,
  })

  // Canonical scan results live at /scans/:id — redirect when viewing a completed scan
  useEffect(() => {
    if (!scanId || scanStarted || scanState.isScanning) return
    const status = displayResult?.status ?? scanResult?.status
    if (status === 'completed') {
      navigate(`/scans/${scanId}`, { replace: true })
    }
  }, [scanId, scanStarted, scanState.isScanning, displayResult?.status, scanResult?.status, navigate])

  // WebSocket for real-time updates during scan
  const { scanState: wsState, completedStages, stageMessages, failedStage } = useScanWebSocket({
    scanId: scanState.scanId,
    enabled: scanState.isScanning || isAiPending,
    onComplete: (data) => {
      void handleScanComplete(data)
    },
    onFailed: (data) => {
      handleScanFailed(data)
    },
    onAIComplete: () => {
      void handleAIComplete()
    },
  })

  const wsAiProgress = wsState?.aiProgress || null

  // Auto-refresh on scan complete
  useEffect(() => {
    if (scanState.isComplete) {
      void refetch()
    }
  }, [scanState.isComplete, refetch])

  // PR state
  type PRStep = 'generating' | 'branch' | 'creating_pr' | null
  const [prState, setPrState] = useState<{
    step: PRStep
    success: boolean
    error: string | null
    response: { prUrl: string; prNumber: number; scoreAfter: number; branchName: string } | null
  }>({ step: null, success: false, error: null, response: null })

  const handleStartScan = useCallback(async () => {
    if (!repoUrl) {
      return
    }
    setScanStarted(true)
    await startScan()
  }, [startScan, repoUrl])

  const handleRescan = useCallback(async () => {
    if (!repoUrl) {
      return
    }
    setScanStarted(true)
    await startScan()
  }, [startScan, repoUrl])

  const handleRetry = useCallback(() => {
    retryScan()
  }, [retryScan])

  const handleCloseOverlay = useCallback(() => {
    // Only allow closing on complete/failed
    if (scanState.isComplete || scanState.isFailed) {
      setScanStarted(false)
    }
  }, [scanState.isComplete, scanState.isFailed])

  const handleDownload = async (format: 'pdf' | 'excel' | 'json' | 'sarif' = 'pdf') => {
    if (!scanResult || isDownloading) return
    const effectiveScanId = scanResult.id
    if (!effectiveScanId) return

    if (format === 'json') {
      const reportData = {
        scan_id: effectiveScanId,
        repository_name: repoName,
        repository_url: repoUrl,
        branch: scanResult.branch || 'main',
        overall_score: scanResult.overall_score,
        security_score: scanResult.security_score,
        severity_counts: severityCounts,
        findings_count: getFindingsCount(scanResult),
        files_analyzed: scanResult.files_analyzed,
        findings: (scanResult.findings || []).map((f: any) => ({
          ...f,
          file_path: sanitizePath(f.file_path),
        })),
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
    } catch {
      if (format === 'pdf') {
        void handleDownload('json')
      }
    } finally {
      setIsDownloading(false)
    }
  }

  const handleCreatePR = async (findingId: string) => {
    if (!scanResult) return
    const effectiveScanId = scanResult.id
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
    const fixableFindings = scanResult?.findings?.filter((f: any) => f.fix_code && (f.severity === 'critical' || f.severity === 'high')) ?? []
    if (fixableFindings.length === 0) return
    const effectiveScanId = scanResult.id
    if (!effectiveScanId) return
    const findingIds = fixableFindings.map((f: any) => f.id ?? f.rule_id)

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
    const effectiveScanId = scanResult.id
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

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: `Scan Results: ${repoName}`,
        text: `Security scan results for ${repoName} — Score: ${resolvedScore}`,
        url: window.location.href,
      }).catch(() => {})
    } else {
      void copyToClipboard(window.location.href)
    }
  }

  if (isLoading && !repoData) {
    return (
      <div className="min-h-screen bg-background">
        <div className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#07070d]/90 backdrop-blur-2xl">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center gap-2 text-xs mb-2">
              <div className="h-3 w-16 bg-white/10 rounded animate-pulse" />
              <div className="h-3 w-3 bg-white/5 rounded" />
              <div className="h-3 w-20 bg-white/10 rounded animate-pulse" />
            </div>
            <div className="h-3 w-24 bg-white/10 rounded animate-pulse" />
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5 space-y-3">
                <div className="h-3 w-20 bg-white/10 rounded animate-pulse" />
                <div className="h-8 w-12 bg-white/10 rounded animate-pulse" />
                <div className="h-3 w-16 bg-white/10 rounded animate-pulse" />
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-4">
            <div className="h-6 w-40 bg-white/10 rounded animate-pulse" />
            <div className="h-4 w-full bg-white/10 rounded animate-pulse" />
            <div className="h-4 w-3/4 bg-white/10 rounded animate-pulse" />
            <div className="grid grid-cols-2 gap-3 pt-4">
              <div className="h-12 bg-white/[0.04] rounded-lg border border-white/[0.06] animate-pulse" />
              <div className="h-12 bg-white/[0.04] rounded-lg border border-white/[0.06] animate-pulse" />
            </div>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-3">
            <div className="h-5 w-32 bg-white/10 rounded animate-pulse" />
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-3 py-2">
                <div className="h-6 w-6 rounded-full bg-white/10 animate-pulse" />
                <div className="h-4 flex-1 bg-white/10 rounded animate-pulse" />
                <div className="h-4 w-12 bg-white/10 rounded animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error && !repoData) {
    const errorMessage = (error as Error)?.message || 'Failed to load repository results'
    const isNotFound = /404|not found/i.test(errorMessage)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <ErrorState
          title={isNotFound ? 'Repository not found' : 'Unable to load scan results'}
          message={
            isNotFound
              ? 'This repository may have been removed or you may not have access. Check the repository URL and try again.'
              : `Could not fetch results for this repository. ${errorMessage}`
          }
          onRetry={isNotFound ? undefined : () => { void refetch() }}
          className="py-8"
        />
      </div>
    )
  }

  // Empty state - no scan yet
  if (!scanResult && repoData && !repoData.has_scan) {
    return (
      <div className="min-h-screen bg-background">
        <div className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#07070d]/90 backdrop-blur-2xl">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center justify-between mb-2">
            <nav className="flex items-center gap-2 text-xs min-w-0">
                <button onClick={() => navigate('/dashboard')} className="flex items-center gap-1 text-white/40 hover:text-white/80 transition-colors">
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  Dashboard
                </button>
                <ChevronRight className="w-3 h-3 text-white/20" />
                <button onClick={() => navigate('/repositories')} className="text-white/40 hover:text-white/80 transition-colors">
                  Repositories
                </button>
                <ChevronRight className="w-3 h-3 text-white/20" />
                <span className="text-white/60 truncate max-w-[160px]">{repoName}</span>
              </nav>
              <Button variant="primary" size="sm" glow onClick={() => { void handleStartScan(); }} disabled={scanState.isScanning}>
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                Start Scan
              </Button>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <Card className="p-12 text-center" hover={false}>
            <Brain className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="mb-2 text-lg font-semibold text-foreground">No scan results yet</h3>
            <p className="mb-6 text-muted-foreground">
              This repository hasn't been scanned. Start a scan to analyze its infrastructure.
            </p>
            <Button variant="primary" glow onClick={() => { void handleStartScan(); }} disabled={scanState.isScanning}>
              <RotateCcw className="h-4 w-4 mr-2" />
              Start Scan
            </Button>
          </Card>
        </div>

        <ScanProgressOverlay
          isOpen={scanState.isActive || scanStarted || scanState.isFailed}
          onClose={handleCloseOverlay}
          onCancel={() => { void cancelScan() }}
          repositoryName={repoName}
          branch={defaultBranch}
          stages={stages}
          currentStage={normalizeLifecycleStage(wsState?.currentStage ?? null)}
          completedStages={completedStages}
          failedStage={failedStage}
          stageMessages={stageMessages}
          technologies={wsState?.technologies}
          startedAt={wsState?.startedAt}
          progressData={{
            currentStep: wsState?.currentStep,
            error: scanState.error || wsState?.errorMessage || undefined,
          }}
          isComplete={!!(scanState.isComplete || (wsState?.isTerminal && wsState.status === 'completed'))}
          hasFailed={!!(scanState.isFailed || (wsState?.isTerminal && wsState.status === 'failed'))}
          onComplete={() => {
            void refetch()
            handleCloseOverlay()
            if (scanResult) {
              const total = (scanResult.severityCounts?.critical || 0) +
                (scanResult.severityCounts?.high || 0) +
                (scanResult.severityCounts?.medium || 0) +
                (scanResult.severityCounts?.low || 0)
              setScanCompleteToast({
                score: resolveSecurityScore({
                  overall_score: scanResult.overall_score,
                  security_score: scanResult.security_score,
                })?.value ?? 0,
                findings: total,
              })
              setTimeout(() => setScanCompleteToast(null), 5000)
            }
          }}
          onRetry={handleRetry}
        />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* ===== HEADER ===== */}
      <div className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#07070d]/90 backdrop-blur-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between mb-2">
            <nav className="flex items-center gap-2 text-xs min-w-0">
              <button onClick={() => navigate('/dashboard')} className="flex items-center gap-1 text-white/40 hover:text-white/80 transition-colors">
                <LayoutDashboard className="w-3.5 h-3.5" />
                Dashboard
              </button>
              <ChevronRight className="w-3 h-3 text-white/20" />
              <button onClick={() => navigate('/repositories')} className="text-white/40 hover:text-white/80 transition-colors">
                Repositories
              </button>
              <ChevronRight className="w-3 h-3 text-white/20" />
              <span className="text-white/60 truncate max-w-[160px]">{repoName}</span>
            </nav>
            <div className="flex items-center gap-1.5 flex-wrap justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { void handleRescan(); }}
                disabled={scanState.isScanning}
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                Rescan
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { void handleCreateGlobalPR(); }}
                disabled={!!prState.step || !scanResult?.findings?.some((f: any) => f.fix_code)}
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
               <Button variant="ghost" size="sm" onClick={() => { void handleDownload('pdf'); }}>
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Export
              </Button>
              <button onClick={() => navigate('/docs/security-findings')} className="p-2 rounded-lg text-white/40 hover:text-white/80 hover:bg-white/5 transition-colors" title="Documentation">
                <BookOpen className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* AI Pending Banner */}
      <AnimatePresence>
        {isAiPending && !scanState.isScanning && (
          <AIProgressBanner
            aiStatus={displayResult?.ai_status}
            aiProgress={wsAiProgress}
            onAIComplete={handleAIComplete}
          />
        )}
      </AnimatePresence>

      {/* Main Dashboard */}
      <div className={cn(scanState.isScanning && 'opacity-40 pointer-events-none transition-opacity duration-300')}>
        <ScanResultsDashboard
          result={displayResult || {}}
          repoName={repoName}
          findings={displayResult?.findings || []}
          severityCounts={severityCounts}
          priorityFixes={topPriorityFixes}
          isAiReady={isAiReady}
          isAiPending={isAiPending}
          aiSummary={displayResult?.findings?.[0]?.summary || null}
          severityFilter={severityFilter}
          sortBy={sortBy}
          expandedFinding={expandedFinding}
          searchQuery={searchQuery}
          onSeverityFilterChange={(filter: string) => setSeverityFilter(filter as SeverityFilter)}
          onSortByChange={(sort: string) => setSortBy(sort as SortOption)}
          onExpandedFindingChange={setExpandedFinding}
          onSearchQueryChange={setSearchQuery}
          onRescan={handleRescan}
          onDownload={handleDownload}
          onShare={handleShare}
          onFindFix={(id: string) => setExpandedFinding(id)}
          onGenerateFix={(id: string) => setExpandedFinding(id)}
          onCreatePR={handleCreatePR}
          onBatchCreatePR={handleBatchCreatePR}
          hideHeaderActions
        />
      </div>

      {/* Scan Progress Overlay - slide-in panel, keeps results visible */}
      <ScanProgressOverlay
        slideIn
        isOpen={scanState.isActive || scanStarted || scanState.isFailed}
        onClose={handleCloseOverlay}
        onCancel={() => { void cancelScan() }}
        repositoryName={repoName}
        branch={defaultBranch}
        stages={stages}
        currentStage={normalizeLifecycleStage(wsState?.currentStage ?? null)}
        completedStages={completedStages}
        failedStage={failedStage}
        stageMessages={stageMessages}
        technologies={wsState?.technologies}
        startedAt={wsState?.startedAt}
        progressData={{
          currentStep: wsState?.currentStep,
          error: scanState.error || wsState?.errorMessage || undefined,
        }}
        isComplete={!!(scanState.isComplete || (wsState?.isTerminal && wsState.status === 'completed'))}
        hasFailed={!!(scanState.isFailed || (wsState?.isTerminal && wsState.status === 'failed'))}
        onComplete={() => {
          void refetch()
          handleCloseOverlay()
          if (scanResult) {
            const total = (scanResult.severityCounts?.critical || 0) +
              (scanResult.severityCounts?.high || 0) +
              (scanResult.severityCounts?.medium || 0) +
              (scanResult.severityCounts?.low || 0)
            setScanCompleteToast({
              score: resolveSecurityScore({
                overall_score: scanResult.overall_score,
                security_score: scanResult.security_score,
              })?.value ?? 0,
              findings: total,
            })
            setTimeout(() => setScanCompleteToast(null), 5000)
          }
        }}
        onRetry={handleRetry}
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
                  { step: 'generating' as const, label: 'Generating fixes' },
                  { step: 'branch' as const, label: 'Creating branch' },
                  { step: 'creating_pr' as const, label: 'Creating Pull Request' },
                ].map((s) => {
                  const isActive = prState.step === s.step
                  return (
                    <div key={s.step} className="flex items-center gap-3">
                      <div className={cn(
                        'w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 transition-all duration-300',
                        isActive ? 'bg-indigo-500/20 text-indigo-400 ring-2 ring-indigo-500/40' : 'bg-white/5 text-white/20'
                      )}>
                        {isActive ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <div className="w-1.5 h-1.5 rounded-full bg-white/20" />
                        )}
                      </div>
                      <span className={cn(
                        'text-sm transition-colors',
                        isActive ? 'text-white/90 font-medium' : 'text-white/30'
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
                <Button variant="ghost" size="sm" onClick={() => setPrState({ step: null, success: false, error: null, response: null })} className="flex-1">
                  Close
                </Button>
                <Button variant="primary" size="sm" glow onClick={() => window.open(prState.response!.prUrl, '_blank', 'noopener')} className="flex-1">
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

      {/* Scan Complete Toast */}
      <AnimatePresence>
        {scanCompleteToast && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-6 right-6 z-[70] max-w-sm"
          >
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/90 backdrop-blur-xl p-4 shadow-2xl">
              <div className="flex items-start gap-3">
                <CheckCheck className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-emerald-300">Scan Complete</h4>
                  <p className="text-xs text-emerald-200/60 mt-0.5">
                    Score: {scanCompleteToast.score} &middot; {scanCompleteToast.findings} findings
                  </p>
                </div>
                <button onClick={() => setScanCompleteToast(null)}>
                  <X className="w-4 h-4 text-emerald-300/50 hover:text-emerald-300 transition-colors" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

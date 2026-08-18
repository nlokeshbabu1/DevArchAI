import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle, Clock, GitBranch,
  Shield, Activity, Search, FileText,
  Loader2, X, AlertCircle, TrendingUp, TrendingDown,
  CheckCheck, Brain, Filter, Layers, Download
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { formatDuration } from '../../lib/utils'
import { Button } from '../ui-animated'
import type { StageMetadata, ScanStage } from '../../types'

interface ScanProgressData {
  progress: number
  currentStep?: string
  status?: string
  findingsCount?: number
  filesScanned?: number
  error?: string
}

interface ScanResultSummary {
  securityScore: number
  grade: string
  severityCounts: {
    critical: number
    high: number
    medium: number
    low: number
  }
  filesScanned: number
  scanDuration: number
}

interface ScanProgressOverlayProps {
  isOpen: boolean
  onClose: () => void
  repositoryName: string
  branch: string
  progressData: ScanProgressData
  isComplete: boolean
  hasFailed: boolean
  resultSummary?: ScanResultSummary
  previousScore?: number
  previousFindingsCount?: number
  onComplete: () => void
  onRetry?: () => void
  slideIn?: boolean
  stages?: StageMetadata[]
  currentStage?: ScanStage | null
  startedAt?: string
}

const ICON_MAP: Record<string, React.ComponentType<any>> = {
  'git-branch': GitBranch,
  'download': Download,
  'search': Search,
  'layers': Layers,
  'shield': Shield,
  'filter': Filter,
  'check-circle': CheckCircle,
  'brain': Brain,
  'file-text': FileText,
}

function useElapsedTime(startedAt: string | undefined, isRunning: boolean) {
  const [elapsed, setElapsed] = useState(0)
  const frozenRef = useRef(0)

  useEffect(() => {
    if (!isRunning) {
      frozenRef.current = elapsed
      return
    }

    // Compute initial elapsed from backend started_at
    if (startedAt) {
      const startMs = new Date(startedAt).getTime()
      const nowMs = Date.now()
      if (!isNaN(startMs) && startMs > 0) {
        setElapsed(Math.floor((nowMs - startMs) / 1000))
      }
    }

    const interval = setInterval(() => {
      if (startedAt) {
        const startMs = new Date(startedAt).getTime()
        const nowMs = Date.now()
        if (!isNaN(startMs) && startMs > 0) {
          setElapsed(Math.floor((nowMs - startMs) / 1000))
        }
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [startedAt, isRunning])

  return isRunning ? elapsed : frozenRef.current
}

export function ScanProgressOverlay({
  isOpen,
  onClose,
  repositoryName,
  branch,
  progressData,
  isComplete,
  hasFailed,
  resultSummary,
  previousScore,
  previousFindingsCount,
  onComplete,
  onRetry,
  slideIn = false,
  stages = [],
  currentStage = null,
  startedAt,
}: ScanProgressOverlayProps) {
  const isRunning = isOpen && !isComplete && !hasFailed
  const elapsed = useElapsedTime(startedAt, isRunning)
  const completeHandledRef = useRef(false)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  useEffect(() => {
    if (isComplete && !completeHandledRef.current) {
      completeHandledRef.current = true
      const timer = setTimeout(() => {
        onCompleteRef.current()
      }, 3000)
      return () => clearTimeout(timer)
    }
    if (!isComplete) {
      completeHandledRef.current = false
    }
  }, [isComplete])

  // Compute completed stages from backend current_stage
  const completedStageIds = useMemo(() => {
    const ids = new Set<string>()
    if (!currentStage || stages.length === 0) return ids

    const currentOrder = stages.find(s => s.id === currentStage)?.order ?? -1
    for (const stage of stages) {
      if (stage.order < currentOrder) {
        ids.add(stage.id)
      }
    }
    if (isComplete || progressData.progress >= 100) {
      stages.forEach(s => ids.add(s.id))
    }
    return ids
  }, [currentStage, stages, isComplete, progressData.progress])

  const activeStageId = useMemo(() => {
    if (isComplete || hasFailed) return null
    return currentStage || null
  }, [currentStage, isComplete, hasFailed])

  const currentStepLabel = useMemo(() => {
    if (isComplete) return 'Scan completed'
    if (hasFailed) return 'Scan Failed'
    if (currentStage) {
      const meta = stages.find(s => s.id === currentStage)
      return meta?.label || currentStage
    }
    return progressData.currentStep || 'Initializing...'
  }, [currentStage, stages, progressData.currentStep, isComplete, hasFailed])

  const allStagesDone = completedStageIds.size >= stages.length

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400'
    if (score >= 60) return 'text-yellow-400'
    return 'text-red-400'
  }

  const scoreDelta = previousScore !== undefined && resultSummary
    ? resultSummary.securityScore - previousScore
    : undefined

  const findingsDelta = previousFindingsCount !== undefined && resultSummary
    ? (resultSummary.severityCounts.critical + resultSummary.severityCounts.high +
       resultSummary.severityCounts.medium + resultSummary.severityCounts.low) - previousFindingsCount
    : undefined

  const handleAutoClose = useCallback(() => {
    if (isComplete) {
      onComplete()
    }
  }, [isComplete, onComplete])

  const content = (
    <div className="p-6 sm:p-8">
      {/* ===== HEADER ===== */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className={cn(
            'p-3 rounded-xl border',
            isComplete
              ? 'bg-emerald-500/10 border-emerald-500/20'
              : hasFailed
                ? 'bg-red-500/10 border-red-500/20'
                : 'bg-indigo-500/10 border-indigo-500/20'
          )}>
            {isComplete ? (
              <CheckCircle className="h-6 w-6 text-emerald-400" />
            ) : hasFailed ? (
              <AlertCircle className="h-6 w-6 text-red-400" />
            ) : (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}
              >
                <Loader2 className="h-6 w-6 text-indigo-400" />
              </motion.div>
            )}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white/90">
              {isComplete ? 'Scan Complete' : hasFailed ? 'Scan Failed' : 'Scan in Progress'}
            </h2>
            <p className="text-sm text-white/40 mt-0.5">
              {isComplete
                ? 'Analysis finished. AI recommendations may follow.'
                : hasFailed
                  ? progressData.error || 'An error occurred during the scan'
                  : 'Running infrastructure analysis'
              }
            </p>
          </div>
        </div>
      </div>

      {/* ===== METADATA BAR ===== */}
      {!isComplete && !hasFailed && (
        <div className="flex flex-wrap items-center gap-3 mb-6 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="flex items-center gap-2 text-sm">
            <GitBranch className="h-3.5 w-3.5 text-indigo-400/70" />
            <span className="text-white/60">{repositoryName}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-white/40 text-xs font-mono border border-white/[0.08] rounded px-1.5 py-0.5">{branch}</span>
          </div>
          <div className="w-px h-4 bg-white/[0.08]" />
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-3.5 w-3.5 text-indigo-400/70" />
            <span className="text-white/60 font-mono tabular-nums">{formatDuration(elapsed)}</span>
          </div>
        </div>
      )}

      {/* ===== SUCCESS STATE ===== */}
      {isComplete && resultSummary && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-6 space-y-4"
        >
          <div className="flex flex-col items-center gap-3 p-6 rounded-xl bg-gradient-to-br from-indigo-500/[0.08] to-emerald-500/[0.04] border border-white/[0.06]">
            <CheckCheck className="h-10 w-10 text-emerald-400" />
            <div className="text-center">
              <div className="text-xl font-bold text-white/90">Scan Complete</div>
              <div className="text-sm text-white/40 mt-0.5">Repository infrastructure analyzed</div>
            </div>

            {scoreDelta !== undefined && (
              <div className="flex items-center gap-4 mt-2">
                {previousScore !== undefined && (
                  <div className="text-center">
                    <div className="text-xs text-white/30 mb-1">Previous Score</div>
                    <div className={cn('text-lg font-bold font-mono', getScoreColor(previousScore))}>
                      {previousScore}
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  {scoreDelta >= 0 ? (
                    <TrendingUp className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <TrendingDown className="h-5 w-5 text-red-400" />
                  )}
                  <span className={cn(
                    'text-sm font-bold font-mono',
                    scoreDelta >= 0 ? 'text-emerald-400' : 'text-red-400'
                  )}>
                    {scoreDelta >= 0 ? '+' : ''}{scoreDelta}
                  </span>
                </div>
                <div className="text-center">
                  <div className="text-xs text-white/30 mb-1">New Score</div>
                  <div className={cn('text-lg font-bold font-mono', getScoreColor(resultSummary.securityScore))}>
                    {resultSummary.securityScore}
                  </div>
                </div>
              </div>
            )}

            {findingsDelta !== undefined && (
              <div className="flex items-center gap-4 mt-1">
                {previousFindingsCount !== undefined && (
                  <div className="text-center">
                    <div className="text-xs text-white/30 mb-1">Previous Findings</div>
                    <div className="text-lg font-bold font-mono text-white/70">{previousFindingsCount}</div>
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <span className={cn(
                    'text-sm font-bold',
                    findingsDelta <= 0 ? 'text-emerald-400' : 'text-red-400'
                  )}>
                    {findingsDelta <= 0 ? '↓' : '↑'}
                  </span>
                  <span className={cn(
                    'text-sm font-bold font-mono',
                    findingsDelta <= 0 ? 'text-emerald-400' : 'text-red-400'
                  )}>
                    {Math.abs(findingsDelta)}
                  </span>
                </div>
                <div className="text-center">
                  <div className="text-xs text-white/30 mb-1">Current Findings</div>
                  <div className="text-lg font-bold font-mono text-white/90">
                    {resultSummary.severityCounts.critical + resultSummary.severityCounts.high +
                     resultSummary.severityCounts.medium + resultSummary.severityCounts.low}
                  </div>
                </div>
              </div>
            )}

            {!scoreDelta && !findingsDelta && (
              <div className="grid grid-cols-4 gap-3 w-full mt-2">
                {(['critical', 'high', 'medium', 'low'] as const).map((sev) => (
                  <div key={sev} className="text-center p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                    <div className={cn(
                      'text-lg font-bold font-mono',
                      sev === 'critical' ? 'text-red-400' :
                      sev === 'high' ? 'text-orange-400' :
                      sev === 'medium' ? 'text-yellow-400' : 'text-blue-400'
                    )}>
                      {resultSummary.severityCounts[sev]}
                    </div>
                    <div className="text-[10px] text-white/40 mt-0.5 capitalize">{sev}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* ===== FAILED STATE ===== */}
      {hasFailed && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/[0.06] border border-red-500/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 shrink-0" />
            <div className="space-y-1.5">
              <p className="text-sm font-medium text-red-300">Scan failed to complete</p>
              <p className="text-sm text-red-400/70">
                {progressData.error || 'An unexpected error occurred during the scan.'}
              </p>
              <p className="text-xs text-red-400/50">
                Common causes: repository access issues, unsupported file formats, or a temporary server error.
                You can retry the scan or check that the repository is accessible.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ===== PROGRESS BAR ===== */}
      {!isComplete && !hasFailed && (
        <div className="mb-6" aria-live="polite" aria-atomic="true">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
              <span className="text-sm text-white/70">{currentStepLabel}</span>
            </div>
            <span className="text-sm font-semibold text-white/80 font-mono tabular-nums">
              {Math.round(progressData.progress)}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-indigo-400 to-cyan-400"
              initial={{ width: '0%' }}
              animate={{ width: `${Math.round(progressData.progress)}%` }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
        </div>
      )}

      {/* ===== STAGES TIMELINE ===== */}
      {!isComplete && !hasFailed && stages.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="h-3.5 w-3.5 text-white/30" />
            <span className="text-xs font-medium text-white/30 uppercase tracking-wider">Scan Stages</span>
            <span className="text-[10px] text-white/20 ml-auto font-mono">
              Stage {Math.min(completedStageIds.size + 1, stages.length)}/{stages.length}
            </span>
          </div>
          <div className="space-y-0">
            {stages.map((stage, i) => {
              const isDone = completedStageIds.has(stage.id)
              const isActive = stage.id === activeStageId && !isDone
              const isPending = !isDone && !isActive
              const Icon = ICON_MAP[stage.icon] || Activity

              return (
                <motion.div
                  key={stage.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.03 }}
                  className={cn(
                    'flex items-center gap-3 py-2.5 px-3 rounded-lg transition-all duration-300',
                    isActive && 'bg-indigo-500/[0.06] border border-indigo-500/20',
                    isDone && 'opacity-90',
                    isPending && 'opacity-40'
                  )}
                >
                  <div className={cn(
                    'relative w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all duration-300',
                    isDone && 'bg-emerald-500/20 text-emerald-400',
                    isActive && 'bg-indigo-500/20 text-indigo-400',
                    isPending && 'bg-white/[0.04] text-white/30'
                  )}>
                    {isDone ? (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                      >
                        <CheckCircle className="h-3.5 w-3.5" />
                      </motion.div>
                    ) : isActive ? (
                      <div className="relative">
                        <Icon className="h-3.5 w-3.5" />
                        <span className="absolute inset-0 rounded-full animate-ping bg-indigo-400/30" />
                      </div>
                    ) : (
                      <Icon className="h-3.5 w-3.5" />
                    )}
                  </div>

                  <span className={cn(
                    'text-sm transition-colors duration-300',
                    isDone && 'text-emerald-300/90',
                    isActive && 'text-white/90 font-medium',
                    isPending && 'text-white/30'
                  )}>
                    {stage.label}
                  </span>

                  {isActive && (
                    <motion.div
                      className="ml-auto flex items-center gap-1.5"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    >
                      <span className="text-[10px] font-mono text-indigo-400/70 tabular-nums">
                        {Math.round(progressData.progress)}%
                      </span>
                      <div className="flex gap-0.5">
                        {[0, 1, 2].map((dot) => (
                          <motion.div
                            key={dot}
                            className="w-1 h-1 rounded-full bg-indigo-400"
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{
                              duration: 1.2,
                              repeat: Infinity,
                              delay: dot * 0.2,
                            }}
                          />
                        ))}
                      </div>
                    </motion.div>
                  )}
                </motion.div>
              )
            })}
          </div>
        </div>
      )}

      {/* ===== ACTIONS ===== */}
      <div className="flex gap-2">
        {hasFailed && onRetry && (
          <Button variant="primary" size="sm" onClick={onRetry} className="flex-1">
            Retry Scan
          </Button>
        )}
        {isComplete && (
          <Button variant="primary" size="sm" onClick={onComplete} className="flex-1">
            View Results
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )

  if (slideIn) {
    return (
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-[#0a0a14] border-l border-white/[0.06] shadow-2xl overflow-y-auto"
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    )
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="w-full max-w-lg rounded-2xl border border-white/[0.08] bg-[#0a0a14] shadow-2xl max-h-[85vh] overflow-y-auto"
          >
            {content}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

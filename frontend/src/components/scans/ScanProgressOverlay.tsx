import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle, Clock, GitBranch, FileCode, Layers,
  Shield, Activity, Search, Brain, FileText,
  Loader2, X, AlertCircle, TrendingUp, TrendingDown
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { formatDuration } from '../../lib/utils'
import { Button } from '../ui-animated'

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
  onViewResults: () => void
  onRetry?: () => void
}

const SCAN_STAGES = [
  { id: 'clone', label: 'Cloning Repository', icon: GitBranch, threshold: 11 },
  { id: 'detect', label: 'Detecting Technologies', icon: Search, threshold: 22 },
  { id: 'terraform', label: 'Running Terraform Rules', icon: FileCode, threshold: 33 },
  { id: 'k8s', label: 'Running Kubernetes Rules', icon: Layers, threshold: 44 },
  { id: 'docker', label: 'Running Docker Rules', icon: Layers, threshold: 55 },
  { id: 'cicd', label: 'Running CI/CD Rules', icon: Activity, threshold: 66 },
  { id: 'secrets', label: 'Running Secrets Scan', icon: Shield, threshold: 77 },
  { id: 'ai', label: 'Generating AI Recommendations', icon: Brain, threshold: 88 },
  { id: 'finalize', label: 'Finalizing Report', icon: FileText, threshold: 96 },
]

function useElapsedTime(startedAt: number, isRunning: boolean) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!isRunning) {
      setElapsed(0)
      return
    }
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [startedAt, isRunning])

  return elapsed
}

function useStepStates(progress: number, isComplete: boolean) {
  return useMemo(() => {
    return SCAN_STAGES.map((stage) => {
      if (isComplete || progress >= 100) return 'completed' as const
      if (progress >= stage.threshold) return 'completed' as const
      const prevThreshold = SCAN_STAGES[SCAN_STAGES.indexOf(stage) - 1]?.threshold ?? 0
      if (progress >= prevThreshold && progress < stage.threshold) return 'running' as const
      return 'pending' as const
    })
  }, [progress, isComplete])
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
  onViewResults,
  onRetry,
}: ScanProgressOverlayProps) {
  const [startedAt] = useState(Date.now())
  const isRunning = isOpen && !isComplete && !hasFailed
  const elapsed = useElapsedTime(startedAt, isRunning)
  const stepStates = useStepStates(progressData.progress, isComplete)
  const activeStepIndex = stepStates.indexOf('running')

  // Estimated time remaining
  const estimatedRemaining = useMemo(() => {
    if (!isRunning || progressData.progress === 0) return undefined
    const elapsedSec = elapsed
    const ratio = progressData.progress / 100
    if (ratio <= 0) return undefined
    const estimatedTotal = elapsedSec / ratio
    return Math.max(0, Math.round(estimatedTotal - elapsedSec))
  }, [elapsed, progressData.progress, isRunning])

  const currentStepLabel = useMemo(() => {
    if (isComplete) return 'Scan Complete'
    if (hasFailed) return 'Scan Failed'
    if (activeStepIndex >= 0) return SCAN_STAGES[activeStepIndex]?.label ?? 'Processing...'
    return 'Initializing...'
  }, [activeStepIndex, isComplete, hasFailed])

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

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/70 backdrop-blur-2xl"
        >
          <motion.div
            initial={{ scale: 0.92, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.92, opacity: 0, y: 20 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-white/[0.08] bg-[#0a0a10]/95 backdrop-blur-2xl shadow-2xl shadow-black/60"
          >
            {/* Close button - only when complete or failed */}
            {(isComplete || hasFailed) && (
              <button
                onClick={onClose}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/5 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            )}

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
                        ? 'All checks passed successfully'
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
                  {estimatedRemaining !== undefined && (
                    <>
                      <div className="w-px h-4 bg-white/[0.08]" />
                      <div className="flex items-center gap-2 text-sm">
                        <Clock className="h-3.5 w-3.5 text-cyan-400/70" />
                        <span className="text-white/50 font-mono tabular-nums">
                          ~{formatDuration(estimatedRemaining)} remaining
                        </span>
                      </div>
                    </>
                  )}
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
                  {/* Score & Grade */}
                  <div className="flex flex-col items-center gap-3 p-6 rounded-xl bg-gradient-to-br from-indigo-500/[0.08] to-emerald-500/[0.04] border border-white/[0.06]">
                    <CheckCircle className="h-10 w-10 text-emerald-400" />
                    <div className="text-center">
                      <div className="text-xl font-bold text-white/90">Scan Complete</div>
                      <div className="text-sm text-white/40 mt-0.5">Repository has been re-scanned</div>
                    </div>

                    {/* Score Comparison */}
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

                    {/* Findings Comparison */}
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

                    {/* Severity Breakdown */}
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
                    <div>
                      <p className="text-sm font-medium text-red-300">Scan failed to complete</p>
                      <p className="text-sm text-red-400/70 mt-1">
                        {progressData.error || 'An unexpected error occurred. Please try again.'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* ===== PROGRESS BAR ===== */}
              {!isComplete && !hasFailed && (
                <div className="mb-6">
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
              {!isComplete && !hasFailed && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Activity className="h-3.5 w-3.5 text-white/30" />
                    <span className="text-xs font-medium text-white/30 uppercase tracking-wider">Scan Stages</span>
                    <span className="text-[10px] text-white/20 ml-auto font-mono">
                      Stage {Math.min(activeStepIndex + 1, SCAN_STAGES.length)}/{SCAN_STAGES.length}
                    </span>
                  </div>
                  <div className="space-y-0">
                    {SCAN_STAGES.map((stage, i) => {
                      const state = stepStates[i]
                      const isActive = state === 'running'
                      const isDone = state === 'completed'
                      const Icon = stage.icon

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
                            !isActive && !isDone && 'opacity-40'
                          )}
                        >
                          {/* Stage icon */}
                          <div className={cn(
                            'relative w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all duration-300',
                            isDone && 'bg-emerald-500/20 text-emerald-400',
                            isActive && 'bg-indigo-500/20 text-indigo-400',
                            !isActive && !isDone && 'bg-white/[0.04] text-white/30'
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

                          {/* Stage label */}
                          <span className={cn(
                            'text-sm transition-colors duration-300',
                            isDone && 'text-emerald-300/90',
                            isActive && 'text-white/90 font-medium',
                            !isActive && !isDone && 'text-white/30'
                          )}>
                            {stage.label}
                          </span>

                          {/* Stage progress indicator */}
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

                          {/* Done indicator */}
                          {isDone && (
                            <span className="ml-auto text-[10px] text-emerald-400/60 font-mono">Done</span>
                          )}
                        </motion.div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* ===== FOOTER ACTIONS ===== */}
              <div className="flex items-center gap-3 pt-4 border-t border-white/[0.06]">
                {isComplete && (
                  <>
                    <Button
                      variant="primary"
                      size="md"
                      onClick={onViewResults}
                      glow
                      className="flex-1"
                    >
                      <CheckCircle className="h-4 w-4" />
                      View Updated Results
                    </Button>
                    <Button
                      variant="ghost"
                      size="md"
                      onClick={onClose}
                    >
                      Close
                    </Button>
                  </>
                )}
                {hasFailed && (
                  <>
                    <Button
                      variant="primary"
                      size="md"
                      onClick={onRetry}
                      glow
                      className="flex-1"
                    >
                      <AlertCircle className="h-4 w-4" />
                      Retry Scan
                    </Button>
                    <Button
                      variant="ghost"
                      size="md"
                      onClick={onClose}
                    >
                      Dismiss
                    </Button>
                  </>
                )}
                {!isComplete && !hasFailed && (
                  <div className="flex items-center gap-2 text-xs text-white/30">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Scanning repository — this typically takes 1-3 minutes</span>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle, Clock, GitBranch,
  Loader2, X, AlertCircle, TrendingUp, TrendingDown,
  CheckCheck,
} from 'lucide-react'
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'

import { cn , formatDuration } from '../../lib/utils'
import type { ScanStage, StageMetadata, TechnologyResult } from '../../types'
import { Button } from '../ui-animated'

import { ScanLifecycleSteps, normalizeLifecycleStage } from './ScanLifecycleSteps'


interface ScanProgressData {
  progress?: number
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
  onCancel?: () => void
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
  completedStages?: ScanStage[]
  failedStage?: ScanStage | null
  stageMessages?: Partial<Record<ScanStage, string>>
  technologies?: Record<string, TechnologyResult>
  startedAt?: string
  showProgressPercent?: boolean
}

function useElapsedTime(startedAt: string | undefined, isRunning: boolean) {
  const [elapsed, setElapsed] = useState(0)
  const frozenRef = useRef(0)

  useEffect(() => {
    if (!isRunning) {
      frozenRef.current = elapsed
      return
    }

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
  onCancel,
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
  completedStages = [],
  failedStage = null,
  stageMessages = {},
  technologies = {},
  startedAt,
  showProgressPercent = false,
}: ScanProgressOverlayProps) {
  const isRunning = isOpen && !isComplete && !hasFailed
  const elapsed = useElapsedTime(startedAt, isRunning)
  const completeHandledRef = useRef(false)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  const normalizedCurrent = normalizeLifecycleStage(currentStage)
  const derivedCompleted = useMemo(() => {
    if (completedStages.length > 0) {return completedStages}
    if (!normalizedCurrent || stages.length === 0) {return []}
    const currentOrder = stages.find(s => s.id === normalizedCurrent)?.order ?? -1
    return stages.filter(s => s.order < currentOrder).map(s => s.id)
  }, [completedStages, normalizedCurrent, stages])

  const derivedMessages = useMemo(() => {
    const msgs = { ...stageMessages }
    if (progressData.currentStep && normalizedCurrent) {
      msgs[normalizedCurrent] = progressData.currentStep
    }
    if (hasFailed && progressData.error && failedStage) {
      msgs[failedStage] = progressData.error
    }
    return msgs
  }, [stageMessages, progressData.currentStep, progressData.error, normalizedCurrent, hasFailed, failedStage])

  useEffect(() => {
    if (isComplete && !completeHandledRef.current) {
      completeHandledRef.current = true
      const timer = setTimeout(() => {
        onCompleteRef.current()
      }, 2500)
      return () => clearTimeout(timer)
    }
    if (!isComplete) {
      completeHandledRef.current = false
    }
  }, [isComplete])

  const subtitle = useMemo(() => {
    if (isComplete) {return 'Scan completed. AI remediation may continue in the background.'}
    if (hasFailed) {return progressData.error || 'An error occurred during the scan'}
    const active = normalizedCurrent
      ? stages.find(s => s.id === normalizedCurrent)?.label
      : progressData.currentStep
    return active || 'Initializing scan...'
  }, [isComplete, hasFailed, progressData.error, progressData.currentStep, normalizedCurrent, stages])

  const technologiesCount = useMemo(
    () => Object.keys(technologies).length,
    [technologies],
  )

  const findingsCount = useMemo(() => {
    if (typeof progressData.findingsCount === 'number') {return progressData.findingsCount}
    return Object.values(technologies).reduce((sum, t) => sum + (t.findings ?? 0), 0)
  }, [progressData.findingsCount, technologies])

  const currentOperation = useMemo(() => {
    if (normalizedCurrent && derivedMessages[normalizedCurrent]) {
      return derivedMessages[normalizedCurrent]
    }
    return progressData.currentStep || subtitle
  }, [normalizedCurrent, derivedMessages, progressData.currentStep, subtitle])

  const showProgressBar = showProgressPercent && typeof progressData.progress === 'number'

  const getScoreColor = (score: number) => {
    if (score >= 80) {return 'text-emerald-400'}
    if (score >= 60) {return 'text-yellow-400'}
    return 'text-red-400'
  }

  const scoreDelta = previousScore !== undefined && resultSummary
    ? resultSummary.securityScore - previousScore
    : undefined

  const findingsDelta = previousFindingsCount !== undefined && resultSummary
    ? (resultSummary.severityCounts.critical + resultSummary.severityCounts.high +
       resultSummary.severityCounts.medium + resultSummary.severityCounts.low) - previousFindingsCount
    : undefined

  const content = (
    <div className="p-6 sm:p-8">
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
            <p className="text-sm text-white/40 mt-0.5">{subtitle}</p>
          </div>
        </div>
        {isRunning && onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="p-2 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/5"
            aria-label="Cancel scan"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

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
          {showProgressPercent && typeof progressData.progress === 'number' && progressData.progress > 0 && (
            <>
              <div className="w-px h-4 bg-white/[0.08]" />
              <span className="text-xs font-mono text-white/50 tabular-nums">{Math.round(progressData.progress)}%</span>
            </>
          )}
        </div>
      )}

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
                <div className="text-center">
                  <div className="text-xs text-white/30 mb-1">Current Findings</div>
                  <div className="text-lg font-bold font-mono text-white/90">
                    {resultSummary.severityCounts.critical + resultSummary.severityCounts.high +
                     resultSummary.severityCounts.medium + resultSummary.severityCounts.low}
                  </div>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {hasFailed && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/[0.06] border border-red-500/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 shrink-0" />
            <div className="space-y-1.5">
              <p className="text-sm font-medium text-red-300">Scan failed to complete</p>
              <p className="text-sm text-red-400/70">
                {progressData.error || 'An unexpected error occurred during the scan.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {!isComplete && !hasFailed && stages.length > 0 && (
        <div className="mb-6 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
          <ScanLifecycleSteps
            stages={stages}
            currentStage={normalizedCurrent}
            completedStages={isComplete ? stages.map(s => s.id) : derivedCompleted}
            failedStage={failedStage}
            stageMessages={derivedMessages}
            technologies={technologies}
          />

          {currentOperation && (
            <p className="mt-4 text-sm text-white/50 border-t border-white/[0.06] pt-4">
              <span className="text-white/30">Current operation: </span>
              {currentOperation}
            </p>
          )}

          {showProgressBar && (
            <div className="mt-4 space-y-2">
              <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.round(progressData.progress!)}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>
            </div>
          )}

          {(technologiesCount > 0 || findingsCount > 0) && (
            <div className="mt-4 flex items-center gap-6 text-sm border-t border-white/[0.06] pt-4">
              <div>
                <span className="text-white/30">Technologies</span>
                <span className="ml-2 font-mono tabular-nums text-white/70">{technologiesCount}</span>
              </div>
              <div>
                <span className="text-white/30">Findings</span>
                <span className="ml-2 font-mono tabular-nums text-white/70">{findingsCount}</span>
              </div>
            </div>
          )}
        </div>
      )}

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

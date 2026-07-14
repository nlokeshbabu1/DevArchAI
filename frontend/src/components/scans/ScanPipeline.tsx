import React, { useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircle2, XCircle, Circle, Loader2, Globe, GitMerge,
  Cpu, Search, Shield, FileCode, Zap, Brain, FileText,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import type { ScanStage, StageMetadata } from '../../types'

interface ScanPipelineProps {
  stages: StageMetadata[]
  currentStage: ScanStage | null
  completedStages: ScanStage[]
  failedStages: ScanStage[]
  progress: number
  isComplete: boolean
  hasFailed: boolean
}

const STAGE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  connecting: Globe,
  cloning: GitMerge,
  technology_detection: Cpu,
  scanner_selection: Search,
  scanning: Shield,
  normalization: FileCode,
  deduplication: Zap,
  ai_generation: Brain,
  report_generation: FileText,
}

const EASE = [0.16, 1, 0.3, 1] as const

function getStageState(
  id: ScanStage, props: Pick<ScanPipelineProps, 'currentStage' | 'completedStages' | 'failedStages' | 'isComplete'>
): 'completed' | 'running' | 'failed' | 'pending' {
  if (props.completedStages.includes(id) || props.isComplete) return 'completed'
  if (props.failedStages.includes(id)) return 'failed'
  if (id === props.currentStage) return 'running'
  return 'pending'
}

function StageRow({
  stage, state, index,
}: { stage: StageMetadata; state: 'completed' | 'running' | 'failed' | 'pending'; index: number }) {
  const Icon = STAGE_ICONS[stage.id] ?? Circle
  return (
    <motion.div
      role="listitem"
      aria-current={state === 'running' ? 'step' : undefined}
      className="flex items-center gap-3"
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.04, ease: EASE }}
    >
      <div className="relative flex items-center justify-center w-8 h-8 shrink-0">
        <div
          className={cn(
            'absolute inset-0 rounded-full transition-colors duration-500',
            state === 'completed' && 'bg-emerald-500/10',
            state === 'running' && 'bg-indigo-500/10',
            state === 'failed' && 'bg-red-500/10',
          )}
        />
        {state === 'completed' && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 500, damping: 28 }}
          >
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          </motion.div>
        )}
        {state === 'running' && (
          <div className="relative">
            <span className="absolute inset-0 rounded-full animate-ping bg-indigo-400/30" />
            <Circle className="h-5 w-5 text-indigo-400 fill-indigo-400/20" />
          </div>
        )}
        {state === 'failed' && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 500, damping: 28 }}
          >
            <XCircle className="h-5 w-5 text-red-400" />
          </motion.div>
        )}
        {state === 'pending' && (
          <Circle className="h-5 w-5 text-white/20" />
        )}
      </div>

      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className={cn(
            'h-3.5 w-3.5 shrink-0',
            state === 'completed' && 'text-emerald-400/60',
            state === 'running' && 'text-indigo-400/60',
            state === 'failed' && 'text-red-400/60',
            state === 'pending' && 'text-white/15',
          )} />
          <span className={cn(
            'text-sm font-medium truncate',
            state === 'completed' && 'text-emerald-300/90',
            state === 'running' && 'text-white',
            state === 'failed' && 'text-red-400',
            state === 'pending' && 'text-white/30',
          )}>
            {stage.label}
          </span>
        </div>
        <div className="flex-1" />
        {state === 'running' && (
          <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin shrink-0" />
        )}
      </div>
    </motion.div>
  )
}

function ConnectorLine({ state }: { state: 'completed' | 'running' | 'failed' | 'pending' }) {
  return (
    <div className="flex items-center pl-[15px] h-5">
      <div
        className={cn(
          'w-px h-full transition-colors duration-500',
          state === 'completed' && 'bg-emerald-400/60',
          state === 'running' && 'bg-indigo-400/60',
          state === 'failed' && 'bg-red-400/60',
          state === 'pending' && 'bg-white/[0.08]',
        )}
      />
    </div>
  )
}

export const ScanPipeline = React.memo(function ScanPipeline({
  stages, currentStage, completedStages, failedStages, progress, isComplete, hasFailed,
}: ScanPipelineProps) {
  const sortedStages = useMemo(
    () => [...stages].sort((a, b) => a.order - b.order),
    [stages],
  )

  const clampedProgress = Math.max(0, Math.min(100, Math.round(progress)))
  const props = { currentStage, completedStages, failedStages, isComplete }

  return (
    <motion.div
      aria-label="Scan pipeline progress"
      role="list"
      className="w-full rounded-xl border border-white/[0.06] bg-[rgba(30,41,59,0.6)] p-4 sm:p-5"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: EASE }}
    >
      <div className="space-y-0">
        {sortedStages.map((stage, i) => {
          const state = getStageState(stage.id, props)
          return (
            <React.Fragment key={stage.id}>
              <StageRow stage={stage} state={state} index={i} />
              {i < sortedStages.length - 1 && (
                <ConnectorLine state={getStageState(sortedStages[i].id, props)} />
              )}
            </React.Fragment>
          )
        })}
      </div>

      <div className="mt-5 flex items-center gap-3">
        <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <motion.div
            className={cn(
              'h-full rounded-full',
              isComplete
                ? 'bg-emerald-400'
                : hasFailed
                  ? 'bg-red-400'
                  : 'bg-gradient-to-r from-indigo-500 to-cyan-400',
            )}
            initial={{ width: '0%' }}
            animate={{ width: `${clampedProgress}%` }}
            transition={{ duration: 0.6, ease: EASE }}
          />
        </div>
        <span className="text-xs font-mono tabular-nums text-white/40 shrink-0">
          {clampedProgress}%
        </span>
      </div>
    </motion.div>
  )
})

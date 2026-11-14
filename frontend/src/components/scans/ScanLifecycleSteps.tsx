import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, Circle, Loader2 } from 'lucide-react'
import { useMemo } from 'react'

import { buildDynamicScanSteps, normalizeLifecycleStage } from '../../lib/scanLifecycle'
import { cn } from '../../lib/utils'
import type { ScanStage, StageMetadata, TechnologyResult } from '../../types'

export type LifecycleStepState = 'completed' | 'running' | 'failed' | 'pending'

export interface ScanLifecycleStepsProps {
  stages: StageMetadata[]
  currentStage: ScanStage | null
  completedStages: ScanStage[]
  failedStage?: ScanStage | null
  stageMessages?: Partial<Record<ScanStage, string>>
  technologies?: Record<string, TechnologyResult>
  repositoryName?: string
  branch?: string
}

export { normalizeLifecycleStage }

function getStepState(
  stageId: ScanStage,
  props: Pick<ScanLifecycleStepsProps, 'currentStage' | 'completedStages' | 'failedStage'>,
  tech?: TechnologyResult,
): LifecycleStepState {
  const id = normalizeLifecycleStage(stageId) ?? stageId
  const current = normalizeLifecycleStage(props.currentStage)
  const failed = normalizeLifecycleStage(props.failedStage ?? null)
  const completed = props.completedStages.map(s => normalizeLifecycleStage(s) ?? s)

  if (tech?.status === 'failed') {return 'failed'}
  if (tech?.status === 'completed' || (tech && tech.findings > 0 && completed.includes(id))) {return 'completed'}
  if (failed === id) {return 'failed'}
  if (completed.includes(id)) {return 'completed'}
  if (tech?.status === 'scanning' || current === id) {return 'running'}
  if (tech?.status === 'detected' && !completed.includes(id) && current !== id) {return 'pending'}
  return 'pending'
}

function StatusIcon({ state }: { state: LifecycleStepState }) {
  if (state === 'completed') {return <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
  if (state === 'failed') {return <XCircle className="h-4 w-4 text-red-400" />}
  if (state === 'running') {
    return (
      <div className="relative">
        <Circle className="h-4 w-4 text-indigo-400 fill-indigo-400/25" />
        <span className="absolute inset-0 rounded-full animate-ping bg-indigo-400/25" />
      </div>
    )
  }
  return <Circle className="h-4 w-4 text-white/25" />
}

export function ScanLifecycleSteps({
  stages,
  currentStage,
  completedStages,
  failedStage = null,
  stageMessages = {},
  technologies = {},
  repositoryName,
  branch,
}: ScanLifecycleStepsProps) {
  const dynamicStages = useMemo(
    () => buildDynamicScanSteps(stages, technologies),
    [stages, technologies],
  )

  return (
    <div className="space-y-1" role="list" aria-label="Scan lifecycle">
      {(repositoryName || branch) && (
        <div className="mb-4 text-xs text-white/40 flex flex-wrap gap-2">
          {repositoryName && <span className="text-white/60">{repositoryName}</span>}
          {branch && (
            <span className="font-mono border border-white/[0.08] rounded px-1.5 py-0.5">{branch}</span>
          )}
        </div>
      )}

      {dynamicStages.map((stage, index) => {
        const techId = stage.technology_id
        const tech = techId
          ? Object.values(technologies).find(t => (t.id || t.technology) === techId)
          : undefined
        const state = getStepState(stage.id, { currentStage, completedStages, failedStage }, tech)
        const message =
          stageMessages[stage.id] ||
          (tech && tech.findings > 0
            ? `${tech.findings} finding${tech.findings === 1 ? '' : 's'}`
            : state === 'pending'
              ? 'Waiting...'
              : state === 'running'
                ? stage.kind === 'technology'
                  ? `Analyzing ${stage.label}...`
                  : 'In progress...'
                : state === 'completed' && stage.kind === 'technology'
                  ? 'Detected'
                  : '')

        return (
          <motion.div
            key={stage.id}
            role="listitem"
            aria-current={state === 'running' ? 'step' : undefined}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.03 }}
            className={cn(
              'flex gap-3 py-2.5 px-3 rounded-lg',
              state === 'running' && 'bg-indigo-500/[0.06] border border-indigo-500/20',
              state === 'failed' && 'bg-red-500/[0.05] border border-red-500/20',
            )}
          >
            <div className="w-5 pt-0.5 shrink-0 flex justify-center">
              <StatusIcon state={state} />
            </div>
            <div className="flex-1 min-w-0">
              <div
                className={cn(
                  'text-sm font-medium',
                  state === 'completed' && 'text-emerald-300/90',
                  state === 'running' && 'text-white',
                  state === 'failed' && 'text-red-300',
                  state === 'pending' && 'text-white/35',
                )}
              >
                {stage.label}
              </div>
              {message && (
                <div
                  className={cn(
                    'text-xs mt-0.5',
                    state === 'failed' ? 'text-red-400/80' : 'text-white/40',
                  )}
                >
                  {message}
                </div>
              )}
            </div>
            {state === 'running' && (
              <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin shrink-0 mt-1" />
            )}
          </motion.div>
        )
      })}
    </div>
  )
}

import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Sparkles, Loader2, CheckCircle2, Database, Globe, Cpu, Zap } from 'lucide-react'

import { cn } from '../../lib/utils'
import type { AIGenerationProgress } from '../../types'

const AI_PHASES = [
  { id: 'rag', label: 'Loading DevArchAI knowledge', icon: <Database className="w-4 h-4" />, description: 'Retrieving rule knowledge from internal docs' },
  { id: 'mcp_decision', label: 'Checking documentation needs', icon: <Globe className="w-4 h-4" />, description: 'Determining if current external docs are needed' },
  { id: 'mcp', label: 'Fetching current documentation', icon: <Globe className="w-4 h-4" />, description: 'Retrieving official documentation' },
  { id: 'llm', label: 'Generating AI recommendation', icon: <Cpu className="w-4 h-4" />, description: 'Creating production-grade remediation guidance' },
  { id: 'llm_done', label: 'AI recommendation ready', icon: <Zap className="w-4 h-4" />, description: 'Recommendation generated and cached' },
  { id: 'cache_hit', label: 'Using cached recommendation', icon: <Zap className="w-4 h-4" />, description: 'Retrieved from cache (no LLM call needed)' },
]

interface AIGenerationPanelProps {
  aiProgress: AIGenerationProgress | null
  isGenerating: boolean
}

function getPhaseStatus(currentPhase: string, phaseIndex: number): 'completed' | 'current' | 'pending' {
  const currentPhaseIndex = AI_PHASES.findIndex(p => p.id === currentPhase)
  if (currentPhaseIndex === -1) {
    return 'pending'
  }
  if (phaseIndex < currentPhaseIndex) {
    return 'completed'
  }
  if (phaseIndex === currentPhaseIndex) {
    return 'current'
  }
  return 'pending'
}

export function AIGenerationPanel({ aiProgress, isGenerating }: AIGenerationPanelProps) {
  if (!isGenerating && !aiProgress) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="rounded-xl border border-purple-500/20 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-purple-500/10 p-5"
    >
      <div className="flex items-center gap-3 mb-4">
        <motion.div
          animate={isGenerating ? { scale: [1, 1.1, 1] } : {}}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        >
          <Brain className="h-5 w-5 text-purple-400" />
        </motion.div>
        <h3 className="text-sm font-semibold text-purple-300">AI Analysis</h3>
        {!aiProgress && isGenerating && (
          <Loader2 className="h-4 w-4 text-purple-400 animate-spin ml-auto" />
        )}
      </div>

      {!aiProgress && isGenerating && (
        <div className="flex items-center gap-2 text-sm text-purple-300/70">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Initializing AI analysis...</span>
        </div>
      )}

      <AnimatePresence>
        {aiProgress && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-purple-300/70">{aiProgress.message}</span>
                <span className="text-purple-300/50">{Math.round(aiProgress.progress)}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-purple-500/10 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-purple-500 to-blue-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${aiProgress.progress}%` }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              {AI_PHASES.map((phase, index) => {
                const status = getPhaseStatus(aiProgress.phase, index)
                return (
                  <div
                    key={phase.id}
                    className={cn(
                      'flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-xs transition-colors',
                      status === 'current' && 'bg-purple-500/10 text-purple-300',
                      status === 'completed' && 'text-emerald-400/70',
                      status === 'pending' && 'text-gray-500',
                    )}
                  >
                    {status === 'completed' && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    )}
                    {status === 'current' && (
                      <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin shrink-0" />
                    )}
                    {status === 'pending' && (
                      <div className="w-3.5 h-3.5 rounded-full border border-gray-600 shrink-0" />
                    )}
                    <span className="shrink-0">{phase.icon}</span>
                    <span className="font-medium">{phase.label}</span>
                    {status === 'current' && (
                      <span className="text-purple-300/50 ml-auto hidden sm:inline">
                        {phase.description}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>

            {aiProgress.findings_total > 0 && (
              <div className="text-xs text-purple-300/50">
                Analyzing {aiProgress.findings_processed} of {aiProgress.findings_total} findings...
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

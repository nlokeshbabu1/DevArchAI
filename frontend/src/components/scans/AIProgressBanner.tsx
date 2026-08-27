import { motion } from 'framer-motion'
import { Brain, Loader2, CheckCircle, AlertCircle, Database, Globe, Cpu } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { AIGenerationProgress } from '../../types'

interface AIProgressBannerProps {
  aiStatus?: 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | null
  aiProgress?: AIGenerationProgress | null
  onAIComplete?: () => void
}

const STAGE_ICONS: Record<string, typeof Brain> = {
  rag: Database,
  mcp_decision: Globe,
  mcp: Globe,
  llm: Cpu,
  llm_done: Brain,
  cache_hit: Brain,
}

export function AIProgressBanner({ aiStatus, aiProgress }: AIProgressBannerProps) {
  const status = aiStatus || 'processing'
  const StageIcon = STAGE_ICONS[aiProgress?.phase || ''] || Brain

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6"
    >
      <div className={cn(
        'rounded-xl border p-4',
        status === 'processing' && 'border-indigo-500/30 bg-indigo-500/10',
        status === 'queued' && 'border-indigo-500/20 bg-indigo-500/5',
        status === 'completed' && 'border-emerald-500/30 bg-emerald-500/10',
        status === 'failed' && 'border-red-500/30 bg-red-500/10',
        status === 'pending' && 'border-gray-500/30 bg-gray-500/10',
      )}>
        <div className="flex items-center gap-3">
          {status === 'pending' && (
            <>
              <Brain className="h-5 w-5 text-gray-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-gray-300">Scan complete</div>
                <div className="text-xs text-gray-300/60">
                  Preparing AI analysis pipeline…
                </div>
              </div>
              <Loader2 className="h-4 w-4 text-gray-400 animate-spin shrink-0" />
            </>
          )}
          {status === 'queued' && (
            <>
              <Brain className="h-5 w-5 text-indigo-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-indigo-300">AI analysis queued</div>
                <div className="text-xs text-indigo-300/60">
                  {aiProgress?.message || 'Waiting for background worker — checking knowledge cache next…'}
                </div>
              </div>
              <Loader2 className="h-4 w-4 text-indigo-400 animate-spin shrink-0" />
            </>
          )}
          {status === 'processing' && (
            <>
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              >
                <StageIcon className="h-5 w-5 text-indigo-400" />
              </motion.div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-indigo-300">
                  {aiProgress?.message || 'AI recommendations generating...'}
                </div>
                <div className="text-xs text-indigo-300/60">
                  {aiProgress?.phase === 'rag' && 'Retrieving DevArchAI internal knowledge'}
                  {aiProgress?.phase === 'mcp_decision' && 'Determining if current documentation is needed'}
                  {aiProgress?.phase === 'mcp' && 'Fetching official documentation'}
                  {aiProgress?.phase === 'llm' && 'Generating production-grade remediation guidance'}
                  {aiProgress?.phase === 'cache_hit' && 'Using cached recommendation (fast path)'}
                  {!aiProgress?.phase && 'Building grounded context and generating recommendations'}
                  {aiProgress && aiProgress.findings_total > 0 && (
                    <span className="ml-1 tabular-nums">
                      ({aiProgress.findings_processed}/{aiProgress.findings_total} findings)
                    </span>
                  )}
                </div>
              </div>
              <Loader2 className="h-4 w-4 text-indigo-400 animate-spin shrink-0" />
            </>
          )}
          {status === 'completed' && (
            <>
              <CheckCircle className="h-5 w-5 text-emerald-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-emerald-300">AI analysis complete</div>
                <div className="text-xs text-emerald-300/60">
                  AI-powered suggestions and recommendations are now available.
                </div>
              </div>
            </>
          )}
          {status === 'failed' && (
            <>
              <AlertCircle className="h-5 w-5 text-red-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-red-300">AI analysis failed</div>
                <div className="text-xs text-red-300/60">
                  AI-powered suggestions could not be generated. Static scan results are still available.
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </motion.div>
  )
}

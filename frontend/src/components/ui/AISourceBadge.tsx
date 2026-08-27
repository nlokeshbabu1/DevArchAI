import { BookOpen, Database, Globe, Sparkles } from 'lucide-react'
import { cn } from '../../lib/utils'

/** Backend `source` / `source_display` values from AI job telemetry */
export type AISourceKind = 'rag' | 'rag_mcp' | 'mcp' | 'cache' | 'llm' | string | null | undefined

function normalizeSource(source: AISourceKind): string {
  return String(source ?? '').toLowerCase().replace(/[\s-]+/g, '_')
}

export function getAISourceLabel(source: AISourceKind, sourceDisplay?: string | null): string | null {
  if (sourceDisplay?.trim()) return sourceDisplay.trim()
  const key = normalizeSource(source)
  if (!key) return null
  if (key === 'rag' || key === 'rag_mcp') return 'DevArchAI security knowledge'
  if (key === 'mcp') return 'Current official documentation'
  if (key === 'cache' || key.includes('cache')) return 'Cached recommendation'
  if (key === 'llm') return 'AI-generated guidance'
  return null
}

interface AISourceBadgeProps {
  source?: AISourceKind
  sourceDisplay?: string | null
  technology?: string | null
  className?: string
  compact?: boolean
}

export function AISourceBadge({ source, sourceDisplay, technology, className, compact }: AISourceBadgeProps) {
  const key = normalizeSource(source)
  const label = getAISourceLabel(source, sourceDisplay)
  if (!label && !key) return null

  const usedRag = key === 'rag' || key === 'rag_mcp' || key.includes('rag')
  const usedMcp = key === 'mcp' || key === 'rag_mcp' || key.includes('mcp')
  const tech = technology?.replace(/_/g, ' ')

  return (
    <div className={cn('flex flex-wrap gap-1.5', className)} role="list" aria-label="AI recommendation sources">
      {usedRag && (
        <span
          role="listitem"
          className="inline-flex items-center gap-1 rounded-md border border-indigo-500/20 bg-indigo-500/10 px-2 py-0.5 text-[10px] text-indigo-300"
        >
          <Database className="h-3 w-3 shrink-0" aria-hidden />
          {compact ? 'DevArchAI knowledge' : 'Based on DevArchAI security knowledge'}
        </span>
      )}
      {usedMcp && (
        <span
          role="listitem"
          className="inline-flex items-center gap-1 rounded-md border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300"
        >
          <Globe className="h-3 w-3 shrink-0" aria-hidden />
          {compact
            ? 'Current docs'
            : tech
              ? `Based on current ${tech} documentation`
              : 'Based on current official documentation'}
        </span>
      )}
      {!usedRag && !usedMcp && label && (
        <span
          role="listitem"
          className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-white/60"
        >
          <Sparkles className="h-3 w-3 shrink-0" aria-hidden />
          {label}
        </span>
      )}
      {key.includes('cache') && !usedRag && !usedMcp && (
        <span
          role="listitem"
          className="inline-flex items-center gap-1 rounded-md border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-300"
        >
          <BookOpen className="h-3 w-3 shrink-0" aria-hidden />
          Fast path — cached
        </span>
      )}
    </div>
  )
}

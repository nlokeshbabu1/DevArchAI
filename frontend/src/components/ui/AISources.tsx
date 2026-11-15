import { Database, ExternalLink, Globe, ShieldAlert } from 'lucide-react'

import { cn } from '../../lib/utils'
import type { FindingAISource } from '../../types'

interface AISourcesProps {
  sources?: FindingAISource[] | null
  documentationStatus?: string | null
  documentationStatusDisplay?: string | null
  className?: string
}

const EMPTY_STATE: Record<string, string> = {
  no_relevant_document: 'No matching documentation was found for this finding.',
  retrieval_unavailable: 'Documentation retrieval was unavailable when this was generated.',
  not_attempted: 'Static remediation guidance (no documentation lookup performed).',
}

function safeHref(url?: string): string | null {
  if (!url) {return null}
  try {
    const parsed = new URL(url)
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {return parsed.toString()}
  } catch {
    return null
  }
  return null
}

function formatRetrievedAt(value?: string): string | null {
  if (!value) {return null}
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {return null}
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export function AISources({
  sources,
  documentationStatus,
  documentationStatusDisplay,
  className,
}: AISourcesProps) {
  const items = (sources ?? []).filter((source) => source?.title)
  const statusKey = String(documentationStatus ?? '')
  const explicitMessage = documentationStatusDisplay?.trim()
  const fallbackMessage =
    explicitMessage || EMPTY_STATE[statusKey] || (items.length === 0 ? EMPTY_STATE.not_attempted : '')

  if (items.length === 0) {
    if (!fallbackMessage) {return null}
    return (
      <div
        className={cn(
          'flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-200/80',
          className,
        )}
        role="status"
      >
        <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        <span>{fallbackMessage}</span>
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <ul className="space-y-1.5" aria-label="Documentation sources used by this recommendation">
        {items.map((source, index) => {
          const href = safeHref(source.url)
          const isMcp = source.kind === 'mcp'
          const Icon = isMcp ? Globe : Database
          const retrievedAt = formatRetrievedAt(source.retrieved_at)
          return (
            <li
              key={`${source.kind}-${source.title}-${index}`}
              className="flex items-start gap-2 rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5"
            >
              <Icon
                className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', isMcp ? 'text-cyan-300' : 'text-indigo-300')}
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  {href ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex min-w-0 items-center gap-1 text-xs font-medium text-white/90 hover:text-white hover:underline"
                    >
                      <span className="truncate">{source.title}</span>
                      <ExternalLink className="h-3 w-3 shrink-0 opacity-70" aria-hidden />
                    </a>
                  ) : (
                    <span className="text-xs font-medium text-white/90">{source.title}</span>
                  )}
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-[9px] uppercase tracking-wide',
                      isMcp
                        ? 'bg-cyan-500/10 text-cyan-300'
                        : 'bg-indigo-500/10 text-indigo-300',
                    )}
                  >
                    {isMcp ? 'Live docs' : 'Knowledge base'}
                  </span>
                  {source.version && (
                    <span className="text-[9px] text-white/40">v{source.version}</span>
                  )}
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-white/50">
                  {source.publisher && <span className="truncate">{source.publisher}</span>}
                  {retrievedAt && <span>Retrieved {retrievedAt}</span>}
                  {source.supplied_to_llm === false && source.status && (
                    <span className="text-amber-300/80">Not used ({source.status})</span>
                  )}
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

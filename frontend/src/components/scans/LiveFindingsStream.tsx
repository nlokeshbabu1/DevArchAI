import { useMemo } from 'react'

import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, AlertCircle, Info, Shield, ChevronRight } from 'lucide-react'

import { cn } from '../../lib/utils'
import type { LiveFinding } from '../../types'

interface LiveFindingsStreamProps {
  findings: LiveFinding[]
  isVisible: boolean
}

const SEVERITY_CONFIG = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', borderColor: '#ef4444', icon: <AlertTriangle className="w-4 h-4" />, label: 'Critical' },
  high: { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30', borderColor: '#f97316', icon: <AlertCircle className="w-4 h-4" />, label: 'High' },
  medium: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', borderColor: '#eab308', icon: <Shield className="w-4 h-4" />, label: 'Medium' },
  low: { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', borderColor: '#3b82f6', icon: <Info className="w-4 h-4" />, label: 'Low' },
  info: { color: 'text-gray-400', bg: 'bg-gray-500/10', border: 'border-gray-500/30', borderColor: '#6b7280', icon: <Info className="w-4 h-4" />, label: 'Info' },
}

function getSeverityConfig(severity: LiveFinding['severity']): (typeof SEVERITY_CONFIG)[keyof typeof SEVERITY_CONFIG] {
  return SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.info
}

function truncate(text: string, max: number): string {
  if (text.length <= max) {
    return text
  }
  return text.slice(0, max).trimEnd() + '…'
}

const MAX_VISIBLE = 20

export function LiveFindingsStream({ findings, isVisible }: LiveFindingsStreamProps): React.JSX.Element | null {
  const visibleFindings = useMemo(
    () => findings.slice(-MAX_VISIBLE),
    [findings],
  )

  if (!isVisible) {
    return null
  }

  return (
    <div className="flex flex-col rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-white/[0.06]">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
        </span>
        <span className="text-sm font-medium text-white/80">Live Findings</span>
        {findings.length > 0 && (
          <span className="ml-auto text-xs font-mono text-white/30 tabular-nums">
            {findings.length}
          </span>
        )}
      </div>

      {/* List */}
      <div className="max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        {visibleFindings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-white/20"
                  animate={{ opacity: [0.2, 0.6, 0.2] }}
                  transition={{
                    duration: 1.4,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
              ))}
            </div>
            <span className="text-xs text-white/30">Waiting for findings…</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {visibleFindings.map((finding, idx) => {
              const config = getSeverityConfig(finding.severity)
              const animKey = `${finding.rule_id}-${finding.file_path ?? ''}-${finding.line_number ?? ''}`

              return (
                <motion.div
                  key={animKey}
                  initial={{ opacity: 0, x: 40 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 40 }}
                  transition={{
                    duration: 0.3,
                    delay: Math.min(idx * 0.04, 0.4),
                    ease: [0.25, 0.46, 0.45, 0.94],
                  }}
                  className={cn(
                    'group relative flex items-start gap-3 px-4 py-3 border-b border-white/[0.04]',
                    'bg-card rounded-lg p-3 mb-2 transition-colors duration-150',
                    'hover:bg-white/[0.04]',
                  )}
                  style={{ borderLeft: `2px solid ${config.borderColor}` }}
                >
                  {/* Severity icon */}
                  <div className={cn(
                    'shrink-0 mt-0.5 p-1.5 rounded-md',
                    config.bg,
                    config.border,
                    'border',
                  )}>
                    <span className={config.color}>{config.icon}</span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-white/90 truncate">
                        {finding.rule_name}
                      </span>
                      <span className={cn(
                        'inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded',
                        config.bg,
                        config.color,
                      )}>
                        {config.label}
                      </span>
                    </div>

                    {finding.file_path !== undefined && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-white/40 font-mono truncate">
                        <ChevronRight className="w-3 h-3 shrink-0 opacity-50" />
                        <span className="truncate">{finding.file_path}</span>
                        {finding.line_number !== undefined && (
                          <span className="text-white/25 shrink-0">:{finding.line_number}</span>
                        )}
                      </div>
                    )}

                    <p className="text-xs text-white/50 mt-1 line-clamp-2 leading-relaxed">
                      {truncate(finding.description, 100)}
                    </p>
                  </div>

                  {/* Timestamp */}
                  <span className="shrink-0 text-[10px] text-white/25 font-mono mt-0.5">
                    Just now
                  </span>
                </motion.div>
              )
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}

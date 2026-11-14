
import { motion, AnimatePresence } from 'framer-motion'
import { Terminal, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'

import { cn } from '../../lib/utils'

interface LiveTerminalProps {
  logs: string[]
  isVisible: boolean
  maxHeight?: string
}

type LogLevel = 'ERROR' | 'WARN' | 'INFO' | 'DEBUG' | 'SUCCESS'

interface ParsedLog {
  timestamp: string | null
  level: LogLevel
  message: string
}

const LEVEL_COLORS: Record<LogLevel, string> = {
  ERROR: '#ef4444',
  WARN: '#eab308',
  INFO: '#3b82f6',
  DEBUG: '#64748b',
  SUCCESS: '#22c55e',
}

const TIMESTAMP_RE = /^(\d{1,2}:\d{2}:\d{2}(?:\.\d+)?|\[[^\]]+\])\s*/

const LEVEL_PATTERNS: [LogLevel, RegExp][] = [
  ['ERROR', /\b(error|failed?|fatal|exception)\b/i],
  ['WARN', /\b(warn(?:ing)?)\b/i],
  ['DEBUG', /\b(debug|verbose)\b/i],
  ['SUCCESS', /\b(success|completed?|done|finished)\b/i],
  ['INFO', /\b(info|starting|initialized)\b/i],
]

function parseLog(raw: string): ParsedLog {
  let rest = raw
  const tsMatch = raw.match(TIMESTAMP_RE)
  const timestamp = tsMatch?.[1] ?? null
  if (tsMatch) {
    rest = raw.slice(tsMatch[0].length)
  }

  let level: LogLevel = 'INFO'
  for (const [lvl, re] of LEVEL_PATTERNS) {
    if (re.test(rest)) {
      level = lvl
      break
    }
  }

  return { timestamp, level, message: rest }
}

const EASE = [0.16, 1, 0.3, 1] as const
const REDUCED_TRANSITION = { duration: 0 }

function BouncingDots(): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-white/20"
            animate={{ opacity: [0.2, 0.6, 0.2], y: [0, -4, 0] }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              delay: i * 0.2,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
      <span className="text-xs text-white/30 font-mono">Waiting for scan logs...</span>
    </div>
  )
}

export const LiveTerminal = function LiveTerminal({
  logs,
  isVisible,
  maxHeight = '24rem',
}: LiveTerminalProps): React.JSX.Element | null {
  const scrollRef = useRef<HTMLDivElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const parsed = useMemo(() => logs.map(parseLog), [logs])

  const prefersReduced = useMemo(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    [],
  )

  useEffect(() => {
    if (!prefersReduced) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' })
    } else {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      }
    }
  }, [parsed.length, prefersReduced])

  if (!isVisible) {
    return null
  }

  return (
    <motion.div
      initial={prefersReduced ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={prefersReduced ? REDUCED_TRANSITION : { duration: 0.35, ease: EASE }}
      className="flex flex-col rounded-xl border border-white/[0.06] overflow-hidden"
      style={{ background: '#0a0f1e' }}
      aria-label="Live analysis terminal"
    >
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-white/[0.06]">
        <Terminal className="w-4 h-4 text-[#6366f1] shrink-0" />
        <span className="text-sm font-medium text-white/80">Live Analysis</span>
        {logs.length > 0 && (
          <span className="text-[10px] font-mono text-white/30 tabular-nums bg-white/[0.06] px-1.5 py-0.5 rounded">
            {logs.length}
          </span>
        )}
        <button
          onClick={() => { /* clear handled by parent via logs=[] */ }}
          className={cn(
            'ml-auto p-1 rounded-md text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-colors',
            'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#6366f1]/50',
          )}
          aria-label="Clear logs"
          disabled={logs.length === 0}
          tabIndex={0}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        className="overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
        style={{ maxHeight }}
      >
        {parsed.length === 0 ? (
          <BouncingDots />
        ) : (
          <AnimatePresence initial={false}>
            {parsed.map((log, idx) => {
              const color = LEVEL_COLORS[log.level]
              return (
                <motion.div
                  key={`${idx}-${log.level}`}
                  initial={prefersReduced ? false : { opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={
                    prefersReduced
                      ? REDUCED_TRANSITION
                      : { duration: 0.25, ease: EASE, delay: Math.min(idx * 0.02, 0.3) }
                  }
                  className="flex items-start gap-2 px-4 py-1.5 border-b border-white/[0.04] hover:bg-white/[0.02]"
                >
                  {log.timestamp !== null && (
                    <span className="shrink-0 text-[11px] font-mono text-white/25 tabular-nums mt-px">
                      {log.timestamp}
                    </span>
                  )}
                  <span className="shrink-0 flex items-center gap-1.5 mt-px">
                    <span
                      className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: color }}
                    />
                    <span
                      className="text-[10px] font-mono font-medium uppercase tracking-wider"
                      style={{ color }}
                    >
                      {log.level}
                    </span>
                  </span>
                  <span className="flex-1 min-w-0 text-[12px] font-mono text-white/60 leading-relaxed break-all">
                    {log.message}
                  </span>
                </motion.div>
              )
            })}
          </AnimatePresence>
        )}
        <div ref={endRef} />
      </div>
    </motion.div>
  )
}

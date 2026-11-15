import { motion, useReducedMotion } from 'framer-motion'
import { useEffect, useState } from 'react'

import {
  formatSecurityScore,
  resolveSecurityScore,
  type ResolvedSecurityScore,
  type ScoreSource,
} from '../../lib/security-score'
import { cn, isValidScore } from '../../lib/utils'

export interface SecurityScoreProps {
  data: ScoreSource | null | undefined
  /** Override resolved value (rare — prefer `data`) */
  score?: number | null
  size?: 'xs' | 'sm' | 'md' | 'lg'
  showGrade?: boolean
  showLabel?: boolean
  label?: string
  animated?: boolean
  className?: string
  /** Accessible live region for score updates */
  live?: boolean
}

const SIZE = {
  xs: { ring: 40, stroke: 3, score: 'text-sm', grade: 'text-[9px]', label: 'text-[9px]' },
  sm: { ring: 56, stroke: 4, score: 'text-lg', grade: 'text-[10px]', label: 'text-[10px]' },
  md: { ring: 72, stroke: 5, score: 'text-2xl', grade: 'text-xs', label: 'text-[10px]' },
  lg: { ring: 96, stroke: 6, score: 'text-4xl', grade: 'text-sm', label: 'text-xs' },
} as const

function strokeColor(value: number): string {
  if (value >= 80) {return '#22c55e'}
  if (value >= 60) {return '#eab308'}
  if (value >= 40) {return '#f97316'}
  return '#ef4444'
}

export function SecurityScore({
  data,
  score: scoreOverride,
  size = 'md',
  showGrade = true,
  showLabel = false,
  label,
  animated = true,
  className,
  live = false,
}: SecurityScoreProps) {
  const reducedMotion = useReducedMotion()
  const resolved: ResolvedSecurityScore | null = scoreOverride != null && isValidScore(scoreOverride)
    ? {
        value: Math.round(scoreOverride * 10) / 10,
        grade: resolveSecurityScore({ security_score: scoreOverride })?.grade ?? 'F',
        gradeColor: resolveSecurityScore({ security_score: scoreOverride })?.gradeColor ?? 'text-red-400',
        source: 'security_score',
        label: 'Security Score',
      }
    : resolveSecurityScore(data)

  const [display, setDisplay] = useState(0)
  const cfg = SIZE[size]

  useEffect(() => {
    if (!resolved) {
      setDisplay(0)
      return
    }
    if (!animated || reducedMotion) {
      setDisplay(resolved.value)
      return
    }
    const start = performance.now()
    const duration = 900
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(resolved.value * eased)
      if (t < 1) {requestAnimationFrame(tick)}
    }
    requestAnimationFrame(tick)
  }, [resolved?.value, animated, reducedMotion])

  if (!resolved) {
    return (
      <div className={cn('text-muted-foreground text-sm', className)} aria-label="Security score unavailable">
        —
      </div>
    )
  }

  const radius = (cfg.ring - cfg.stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (resolved.value / 100) * circumference
  const displayLabel = label ?? resolved.label

  return (
    <div
      className={cn('inline-flex items-center gap-3', className)}
      role="img"
      aria-label={`${displayLabel}: ${formatSecurityScore(resolved.value)}, grade ${resolved.grade}`}
      {...(live ? { 'aria-live': 'polite' as const } : {})}
    >
      <div className="relative shrink-0" style={{ width: cfg.ring, height: cfg.ring }}>
        <svg className="w-full h-full -rotate-90" viewBox={`0 0 ${cfg.ring} ${cfg.ring}`}>
          <circle
            cx={cfg.ring / 2}
            cy={cfg.ring / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={cfg.stroke}
          />
          <motion.circle
            cx={cfg.ring / 2}
            cy={cfg.ring / 2}
            r={radius}
            fill="none"
            stroke={strokeColor(resolved.value)}
            strokeWidth={cfg.stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={false}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: reducedMotion ? 0 : 0.8, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <span
          className={cn(
            'absolute inset-0 flex items-center justify-center font-bold font-mono tabular-nums',
            cfg.score,
            resolved.gradeColor,
          )}
        >
          {formatSecurityScore(Math.round(display * 10) / 10)}
        </span>
      </div>
      {(showGrade || showLabel) && (
        <div className="flex flex-col min-w-0">
          {showLabel && (
            <span className={cn('text-muted-foreground font-medium uppercase tracking-wide', cfg.label)}>
              {displayLabel}
            </span>
          )}
          {showGrade && (
            <span
              className={cn(
                'font-bold px-1.5 py-0.5 rounded w-fit mt-0.5',
                cfg.grade,
                resolved.grade === 'A' || resolved.grade === 'B'
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : resolved.grade === 'C'
                    ? 'bg-yellow-500/10 text-yellow-400'
                    : resolved.grade === 'D'
                      ? 'bg-orange-500/10 text-orange-400'
                      : 'bg-red-500/10 text-red-400',
              )}
            >
              Grade {resolved.grade}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

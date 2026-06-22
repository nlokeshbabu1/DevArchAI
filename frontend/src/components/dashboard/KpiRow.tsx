import { motion } from 'framer-motion'
import {
  FolderGit2, Activity, AlertTriangle, Brain,
  TrendingUp, ArrowUp, ArrowDown
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useEffect, useState, useRef } from 'react'

interface KpiCardProps {
  title: string
  value: string
  subtitle?: string
  icon: React.ElementType
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  severity?: { critical: number; high: number; medium: number; low: number }
  accentColor?: string
  index: number
}

function AnimatedCounter({ value, duration = 1200 }: { value: string; duration?: number }) {
  const [display, setDisplay] = useState('0')
  const [isAnimating, setIsAnimating] = useState(true)
  const targetNum = parseInt(value.replace(/,/g, ''), 10)
  const isNumeric = !Number.isNaN(targetNum)
  const prevValue = useRef(0)

  useEffect(() => {
    if (!isNumeric) {
      setDisplay(value)
      setIsAnimating(false)
      return
    }

    const start = prevValue.current || 0
    const diff = targetNum - start
    const startTime = Date.now()

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 4)
      const current = Math.round(start + diff * eased)
      setDisplay(current.toLocaleString())
      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        setIsAnimating(false)
      }
    }

    requestAnimationFrame(animate)
    prevValue.current = targetNum
  }, [value, isNumeric, duration])

  return (
    <span className={cn(
      'tabular-nums',
      isAnimating && isNumeric ? 'animate-counter-rise' : ''
    )}>
      {display}
    </span>
  )
}

function SeverityStack({ severity }: { severity: { critical: number; high: number; medium: number; low: number } }) {
  const total = severity.critical + severity.high + severity.medium + severity.low
  if (total === 0) return null

  const items = [
    { key: 'critical', value: severity.critical, color: 'severity-bar-critical' },
    { key: 'high', value: severity.high, color: 'severity-bar-high' },
    { key: 'medium', value: severity.medium, color: 'severity-bar-medium' },
    { key: 'low', value: severity.low, color: 'severity-bar-low' },
  ]

  return (
    <div className="flex h-1.5 gap-0.5 rounded-full overflow-hidden bg-white/5">
      {items.map((item) => {
        const pct = total > 0 ? (item.value / total) * 100 : 0
        if (pct === 0) return null
        return (
          <div
            key={item.key}
            className={cn('h-full rounded-full transition-all duration-700', item.color)}
            style={{ width: `${pct}%` }}
          />
        )
      })}
    </div>
  )
}

function KpiCard({ title, value, subtitle, icon: Icon, trend, trendValue, severity, accentColor, index }: KpiCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      className={cn(
        'relative overflow-hidden rounded-2xl',
        'bg-card/60 backdrop-blur-xl border border-white/10',
        'shadow-2xl shadow-black/30',
        'hover:border-white/20 hover:shadow-2xl hover:shadow-black/40',
        'transition-all duration-300 group'
      )}
    >
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
            {title}
          </p>
          <div className={cn(
            'p-2 rounded-lg border border-white/10 bg-white/5 transition-colors duration-200',
            'group-hover:bg-white/[0.08]'
          )}>
            <Icon className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors duration-200" />
          </div>
        </div>

        <div className="flex items-baseline gap-1.5 mb-1">
          <span className={cn(
            'text-2xl font-bold tracking-tight',
            accentColor || 'text-foreground'
          )}>
            <AnimatedCounter value={value} />
          </span>
          {trend && trendValue && (
            <span className={cn(
              'inline-flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded-full',
              trend === 'up' ? 'text-green-400 bg-green-500/10' :
              trend === 'down' ? 'text-red-400 bg-red-500/10' :
              'text-muted-foreground bg-white/5'
            )}>
              {trend === 'up' ? <ArrowUp className="h-3 w-3" /> :
               trend === 'down' ? <ArrowDown className="h-3 w-3" /> : null}
              {trendValue}
            </span>
          )}
        </div>

        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}

        {severity && severity.critical + severity.high + severity.medium + severity.low > 0 && (
          <div className="mt-3 space-y-1.5">
            <SeverityStack severity={severity} />
            <div className="flex gap-3 text-[10px] text-muted-foreground">
              {severity.critical > 0 && (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full severity-bar-critical" />
                  <span>{severity.critical} critical</span>
                </span>
              )}
              {severity.high > 0 && (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full severity-bar-high" />
                  <span>{severity.high} high</span>
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

export interface KpiData {
  title: string
  value: string
  subtitle?: string
  icon: React.ElementType
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  severity?: { critical: number; high: number; medium: number; low: number }
  accentColor?: string
}

interface KpiRowProps {
  items: KpiData[]
  className?: string
}

export function KpiRow({ items, className }: KpiRowProps) {
  return (
    <div className={cn(
      'grid gap-4 sm:grid-cols-2 lg:grid-cols-4',
      className
    )}>
      {items.map((item, i) => (
        <KpiCard key={item.title} {...item} index={i} />
      ))}
    </div>
  )
}

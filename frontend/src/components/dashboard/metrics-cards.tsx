import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

import { cn } from '../../lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: number
  icon?: React.ReactNode
  delay?: number
  className?: string
}

export function MetricsCards({ metrics }: { metrics: MetricCardProps[] }) {
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric, index) => (
        <MetricCard key={metric.title} {...metric} delay={index * 0.1} />
      ))}
    </div>
  )
}

function MetricCard({
  title,
  value,
  trend,
  trendValue,
  icon,
  delay = 0,
  className,
}: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
    >
      <div className={cn(
        'bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30',
        'rounded-2xl p-6',
        'transition-all duration-300 hover:border-white/20 hover:shadow-2xl hover:shadow-black/40',
        className
      )}>
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold text-foreground">{value}</p>
            {trend && (
              <div className={cn(
                'flex items-center gap-1 text-sm',
                trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-muted-foreground'
              )}>
                {trend === 'up' && <TrendingUp className="h-4 w-4" />}
                {trend === 'down' && <TrendingDown className="h-4 w-4" />}
                {trend === 'neutral' && <Minus className="h-4 w-4" />}
                {trendValue && <span>{trendValue}%</span>}
              </div>
            )}
          </div>
          {icon && (
            <div className="p-3 bg-white/5 rounded-xl border border-white/10">
              {icon}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

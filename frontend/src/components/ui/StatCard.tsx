import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

import { cn } from '../../lib/utils'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: number
  delay?: number
}

export function StatCard({
  title,
  value,
  icon: Icon,
  trend = 'neutral',
  trendValue,
  delay = 0,
}: StatCardProps) {
  return (
    <motion.div
      className="rounded-xl border border-white/10 bg-card/50 p-6 backdrop-blur-sm"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ scale: 1.02, borderColor: 'rgba(255,255,255,0.2)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="p-2.5 rounded-lg bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        {trendValue && (
          <div className={cn(
            'flex items-center gap-1 text-sm font-medium px-2 py-1 rounded-full',
            trend === 'up'
              ? 'text-green-400 bg-green-500/10 border border-green-500/30'
              : trend === 'down'
              ? 'text-red-400 bg-red-500/10 border border-red-500/30'
              : 'text-muted-foreground bg-white/5'
          )}>
            {trend === 'up' && <TrendingUp className="h-3 w-3" />}
            {trend === 'down' && <TrendingDown className="h-3 w-3" />}
            <span>{trendValue}%</span>
          </div>
        )}
      </div>
      <div className="space-y-1">
        <motion.p
          className="text-3xl font-bold text-foreground"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.2 }}
        >
          {value}
        </motion.p>
        <p className="text-sm text-muted-foreground">{title}</p>
      </div>
    </motion.div>
  )
}

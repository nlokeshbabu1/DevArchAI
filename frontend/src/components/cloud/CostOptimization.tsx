import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { DollarSign, TrendingDown, ArrowDown, Filter } from 'lucide-react'
import { cn } from '@/lib/utils'
import { cloudApi, type CloudCostRecommendation } from '@/api/endpoints/cloud'
import { useCloudStore } from '@/stores/cloud-store'

interface Props {
  connectionId: string
}

const PRIORITY_CONFIG: Record<string, { color: string; bg: string }> = {
  high: { color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
  medium: { color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  low: { color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30' },
}

export function CostOptimization({ connectionId }: Props) {
  const { costs, setCosts } = useCloudStore()
  const [loading, setLoading] = useState(true)
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await cloudApi.costs(connectionId)
      setCosts(data.recommendations)
    } catch {
      // ignore
    }
    setLoading(false)
  }, [connectionId, setCosts])

  useEffect(() => {
    load()
  }, [load])

  const filtered = costs.filter((c) => priorityFilter === 'all' || c.priority === priorityFilter)
  const totalSavings = costs.reduce((sum, c) => sum + (c.monthly_savings || 0), 0)

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-card/60 border border-white/10 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Total Savings Card */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/20">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-green-500/20 border border-green-500/30">
            <TrendingDown className="h-6 w-6 text-green-400" />
          </div>
          <div>
            <p className="text-xs text-green-400/80 font-medium">Estimated Monthly Savings</p>
            <p className="text-3xl font-bold text-green-400">${totalSavings.toFixed(2)}</p>
            <p className="text-xs text-muted-foreground mt-1">{costs.length} recommendation{costs.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
      </div>

      {/* Priority Filter */}
      <div className="flex gap-2">
        {['all', 'high', 'medium', 'low'].map((p) => (
          <button
            key={p}
            onClick={() => setPriorityFilter(p)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-all border',
              priorityFilter === p
                ? p === 'all'
                  ? 'bg-white/10 border-white/20 text-foreground'
                  : `${PRIORITY_CONFIG[p]?.bg} ${PRIORITY_CONFIG[p]?.color}`
                : 'bg-white/5 border-white/10 text-muted-foreground hover:bg-white/[0.05]',
            )}
          >
            {p === 'all' ? 'All' : p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>

      {/* Recommendations */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground text-sm">
            {costs.length === 0
              ? 'No cost recommendations yet. Run a scan to identify savings opportunities.'
              : 'No recommendations match your filter.'}
          </div>
        ) : (
          filtered.map((c) => {
            const pConfig = PRIORITY_CONFIG[c.priority] || PRIORITY_CONFIG.low
            const isExpanded = expandedId === c.id
            return (
              <motion.div
                key={c.id}
                layout
                className={cn(
                  'rounded-xl border transition-all',
                  isExpanded ? 'bg-white/[0.05] border-white/20' : 'bg-white/5 border-white/10 hover:bg-white/[0.03]',
                )}
              >
                <button
                  onClick={() => setExpandedId(isExpanded ? null : c.id)}
                  className="w-full flex items-center gap-4 p-4 text-left"
                >
                  <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
                    <DollarSign className="h-4 w-4 text-green-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-foreground truncate">{c.title}</span>
                      <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full font-medium border', pConfig.bg, pConfig.color)}>
                        {c.priority}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{c.service} &middot; {c.region}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-lg font-bold text-green-400">${(c.monthly_savings || 0).toFixed(2)}</p>
                    <p className="text-[10px] text-muted-foreground">/month</p>
                  </div>
                </button>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="px-4 pb-4 border-t border-white/5 pt-3"
                  >
                    <p className="text-xs text-muted-foreground mb-3">{c.description}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Category</p>
                        <p className="text-xs text-foreground">{c.category}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Type</p>
                        <p className="text-xs text-foreground">{c.recommendation_type}</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )
          })
        )}
      </div>
    </motion.div>
  )
}

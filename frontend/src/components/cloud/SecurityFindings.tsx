import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Search, Shield, AlertTriangle, AlertCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { cloudApi, type CloudFinding } from '@/api/endpoints/cloud'
import { useCloudStore } from '@/stores/cloud-store'

interface Props {
  connectionId: string
}

const SEVERITY_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  critical: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
  high: { icon: AlertCircle, color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' },
  medium: { icon: Info, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  low: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30' },
}

export function SecurityFindings({ connectionId }: Props) {
  const { findings, setFindings } = useCloudStore()
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await cloudApi.findings(connectionId)
      setFindings(data.findings)
    } catch {
      // ignore
    }
    setLoading(false)
  }, [connectionId, setFindings])

  useEffect(() => {
    load()
  }, [load])

  const filtered = findings.filter((f) => {
    if (severityFilter !== 'all' && f.severity !== severityFilter) return false
    if (search) {
      const q = search.toLowerCase()
      return f.title.toLowerCase().includes(q) || f.description.toLowerCase().includes(q)
    }
    return true
  })

  const severityCounts = findings.reduce(
    (acc, f) => {
      acc[f.severity] = (acc[f.severity] || 0) + 1
      return acc
    },
    {} as Record<string, number>,
  )

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
      {/* Severity Summary */}
      <div className="grid grid-cols-4 gap-3">
        {['critical', 'high', 'medium', 'low'].map((sev) => {
          const config = SEVERITY_CONFIG[sev]
          const count = severityCounts[sev] || 0
          return (
            <button
              key={sev}
              onClick={() => setSeverityFilter(severityFilter === sev ? 'all' : sev)}
              className={cn(
                'p-3 rounded-xl border text-left transition-all',
                severityFilter === sev ? config.bg : 'bg-white/5 border-white/10 hover:bg-white/[0.05]',
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <config.icon className={cn('h-3.5 w-3.5', severityFilter === sev ? config.color : 'text-muted-foreground')} />
                <span className="text-xs font-medium capitalize text-muted-foreground">{sev}</span>
              </div>
              <span className="text-lg font-bold text-foreground">{count}</span>
            </button>
          )
        })}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search findings..."
          className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
        />
      </div>

      {/* Findings List */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground text-sm">
            {findings.length === 0 ? 'No findings detected yet. Run a scan to identify issues.' : 'No findings match your filter.'}
          </div>
        ) : (
          filtered.map((f) => {
            const config = SEVERITY_CONFIG[f.severity] || SEVERITY_CONFIG.low
            const isExpanded = expandedId === f.id
            return (
              <motion.div
                key={f.id}
                layout
                className={cn('rounded-xl border transition-all', isExpanded ? config.bg : 'bg-white/5 border-white/10 hover:bg-white/[0.03]')}
              >
                <button
                  onClick={() => setExpandedId(isExpanded ? null : f.id)}
                  className="w-full flex items-start gap-3 p-4 text-left"
                >
                  <config.icon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', config.color)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-foreground truncate">{f.title}</span>
                      <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full font-medium border', config.bg, config.color)}>
                        {f.severity}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{f.description}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-[10px] text-muted-foreground font-mono uppercase">{f.service}</span>
                      <span className="text-[10px] text-muted-foreground">{f.region}</span>
                      {f.rule_id && <span className="text-[10px] text-muted-foreground font-mono">{f.rule_id}</span>}
                    </div>
                  </div>
                </button>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="px-4 pb-4 border-t border-white/5 pt-3"
                  >
                    <p className="text-xs text-muted-foreground mb-3">{f.description}</p>
                    {f.remediation && (
                      <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Remediation</p>
                        <p className="text-xs text-foreground">{f.remediation}</p>
                      </div>
                    )}
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

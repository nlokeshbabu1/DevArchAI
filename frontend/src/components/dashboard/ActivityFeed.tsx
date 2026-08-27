import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { FolderGit2, CheckCircle, ArrowRight, Clock, Search, AlertTriangle, Brain, Download, Shield } from 'lucide-react'
import { cn } from '../../lib/utils'
import { resolveSecurityScore } from '../../lib/security-score'
import { Button } from '../ui-animated'
import type { RecentScan } from '../../api/endpoints/dashboard'
import { useState, useDeferredValue, memo } from 'react'

interface ActivityFeedProps {
  scans: RecentScan[]
  searchQuery?: string
  onSearchChange?: (query: string) => void
  onClearSearch?: () => void
  isLoading?: boolean
}

const getActivityIcon = (status: string) => {
  switch (status) {
    case 'completed': return CheckCircle
    case 'processing': case 'pending': return Clock
    case 'failed': case 'error': return AlertTriangle
    default: return Shield
  }
}

const getActivityColor = (status: string) => {
  switch (status) {
    case 'completed': return 'text-green-400 border-green-500/30 bg-green-500/15'
    case 'processing': case 'pending': return 'text-blue-400 border-blue-500/30 bg-blue-500/15'
    case 'failed': case 'error': return 'text-red-400 border-red-500/30 bg-red-500/15'
    default: return 'text-muted-foreground border-white/10 bg-white/5'
  }
}

const getScoreColor = (score: number | null) => {
  if (score === null) return 'text-muted-foreground'
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-yellow-400'
  return 'text-red-400'
}

export const ActivityFeed = memo(function ActivityFeed({ scans, searchQuery, onSearchChange, onClearSearch, isLoading }: ActivityFeedProps) {
  const navigate = useNavigate()
  const [localSearch, setLocalSearch] = useState(searchQuery || '')
  const deferredSearch = useDeferredValue(localSearch.toLowerCase())

  const handleSearchChange = (val: string) => {
    setLocalSearch(val)
    onSearchChange?.(val)
  }

  const filteredScans = scans.filter((scan) => {
    if (!deferredSearch) return true
    const name = (scan.repository_name || scan.repository_url || '').toLowerCase()
    const status = (scan.status || '').toLowerCase()
    return name.includes(deferredSearch) || status.includes(deferredSearch)
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.4 }}
    >
      <div className="rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 overflow-hidden">
        <div className="p-5 pb-0">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Recent Scan Activity</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {localSearch
                  ? `${filteredScans.length} of ${scans.length} scans`
                  : 'Latest security scan results'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Filter scans..."
                  value={localSearch}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="w-36 pl-8 pr-2.5 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/30 transition-all"
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/scans')}
                icon={<ArrowRight className="h-3.5 w-3.5" />}
              >
                <span className="text-xs">All Scans</span>
              </Button>
            </div>
          </div>
        </div>

        <div className="hidden md:block overflow-x-auto max-h-[480px] overflow-y-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Activity</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Status</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Score</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Time</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Duration</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <div className="flex justify-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </td>
                </tr>
              ) : filteredScans.length > 0 ? (
                filteredScans.map((scan, i) => {
                  const validScore = resolveSecurityScore(scan)?.value ?? null
                  const ActivityIcon = getActivityIcon(scan.status)
                  const activityColor = getActivityColor(scan.status)

                  return (
                    <motion.tr
                      key={scan.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, delay: i * 0.03 }}
                      className="border-b border-white/5 transition-colors hover:bg-white/[0.04] cursor-pointer"
                      onClick={() => navigate(`/scans/${scan.id}`)}
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className={cn(
                            'p-1.5 rounded-lg border',
                            activityColor
                          )}>
                            <ActivityIcon className="h-3 w-3" />
                          </div>
                          <span className="text-sm font-medium text-foreground truncate max-w-[220px]">
                            {scan.repository_name || scan.repository_url?.split('/').pop() || 'Unknown'}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <span className={cn(
                          'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium capitalize',
                          activityColor
                        )}>
                          {scan.status === 'completed' && <CheckCircle className="h-2.5 w-2.5" />}
                          {scan.status}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        {validScore !== null ? (
                          <span className={cn('text-sm font-semibold tabular-nums', getScoreColor(validScore))}>
                            {validScore.toFixed(1)}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3 w-3 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">
                            {new Date(scan.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-xs text-muted-foreground">
                        {typeof scan.analysis_duration_seconds === 'number'
                          ? `${scan.analysis_duration_seconds.toFixed(0)}s`
                          : '—'}
                      </td>
                    </motion.tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <div className="p-2 rounded-full bg-white/5 border border-white/10">
                        <Search className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <p className="text-sm font-medium text-foreground">
                        {localSearch ? 'No scans match this search' : 'No scans yet'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {localSearch ? 'Try a different keyword' : 'Recent scans will appear here'}
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="md:hidden max-h-[480px] overflow-y-auto px-4 pb-4 space-y-3">
          {isLoading ? (
            <div className="py-12 flex justify-center gap-1">
              <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          ) : filteredScans.length > 0 ? (
            filteredScans.map((scan, i) => {
              const validScore = resolveSecurityScore(scan)?.value ?? null
              const ActivityIcon = getActivityIcon(scan.status)
              const activityColor = getActivityColor(scan.status)

              return (
                <motion.button
                  key={scan.id}
                  type="button"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.03 }}
                  onClick={() => navigate(`/scans/${scan.id}`)}
                  className="w-full text-left rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-3 hover:bg-white/[0.05] transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className={cn('p-1.5 rounded-lg border shrink-0', activityColor)}>
                        <ActivityIcon className="h-3 w-3" />
                      </div>
                      <span className="text-sm font-medium text-foreground truncate">
                        {scan.repository_name || scan.repository_url?.split('/').pop() || 'Unknown'}
                      </span>
                    </div>
                    <span className={cn(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium capitalize shrink-0',
                      activityColor
                    )}>
                      {scan.status === 'completed' && <CheckCircle className="h-2.5 w-2.5" />}
                      {scan.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className={cn('font-semibold tabular-nums', validScore !== null ? getScoreColor(validScore) : '')}>
                      {validScore !== null ? `${validScore.toFixed(1)} score` : 'No score'}
                    </span>
                    <span>
                      {typeof scan.analysis_duration_seconds === 'number'
                        ? `${scan.analysis_duration_seconds.toFixed(0)}s`
                        : '—'}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>
                      {new Date(scan.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </motion.button>
              )
            })
          ) : (
            <div className="py-12 text-center">
              <div className="flex flex-col items-center gap-2">
                <div className="p-2 rounded-full bg-white/5 border border-white/10">
                  <Search className="h-4 w-4 text-muted-foreground" />
                </div>
                <p className="text-sm font-medium text-foreground">
                  {localSearch ? 'No scans match this search' : 'No scans yet'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {localSearch ? 'Try a different keyword' : 'Recent scans will appear here'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
})

import { memo } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { FolderGit2, ArrowRight, CheckCircle, AlertTriangle } from 'lucide-react'
import { cn } from '../../lib/utils'
import { Button } from '../ui-animated'
import type { Repository } from '../../api/endpoints/repositories'

interface RiskTableProps {
  repositories: Repository[]
  isLoading?: boolean
  getScore: (repo: Repository) => number | null
  getCritical: (repo: Repository) => number
  getHigh: (repo: Repository) => number
  formatDate: (value?: string | null) => string
}

export const RiskTable = memo(function RiskTable({ repositories, isLoading, getScore, getCritical, getHigh, formatDate }: RiskTableProps) {
  const navigate = useNavigate()

  const sorted = [...repositories]
    .filter((repo) => repo.scan_count || repo.last_scan_at || getScore(repo) !== null || repo.issues)
    .sort((a, b) => {
      const aScore = getScore(a) ?? 101
      const bScore = getScore(b) ?? 101
      const aRisk = getCritical(a) * 100 + getHigh(a) * 25 + Math.max(0, 100 - aScore)
      const bRisk = getCritical(b) * 100 + getHigh(b) * 25 + Math.max(0, 100 - bScore)
      return bRisk - aRisk
    })
    .slice(0, 5)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.35 }}
    >
      <div className="rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 overflow-hidden">
        <div className="p-5 pb-0">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Top Risk Repositories</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Ranked by critical, high, and low score</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/repositories')}
              icon={<ArrowRight className="h-3.5 w-3.5" />}
            >
              <span className="text-xs">All Repos</span>
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto pb-1">
          <table className="w-full min-w-[600px]">
            <thead>
              <tr className="border-b border-white/5">
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Repository</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Score</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Critical</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">High</th>
                <th className="px-5 py-2.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Last Scan</th>
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
              ) : sorted.length > 0 ? (
                sorted.map((repo, i) => {
                  const score = getScore(repo)
                  const critical = getCritical(repo)
                  const high = getHigh(repo)

                  return (
                    <motion.tr
                      key={repo.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: i * 0.04 }}
                      className="border-b border-white/5 transition-colors hover:bg-white/[0.04] cursor-pointer"
                      onClick={() => navigate(`/repositories?id=${repo.id}`)}
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="p-1.5 rounded-lg bg-white/5 border border-white/10">
                            <FolderGit2 className="h-3.5 w-3.5 text-muted-foreground" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground truncate max-w-[200px]">{repo.name}</p>
                            <p className="text-[10px] text-muted-foreground">{repo.default_branch || 'main'}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        {score !== null ? (
                          <div className="flex items-center gap-2">
                            <div className={cn(
                              'h-6 w-6 rounded-full flex items-center justify-center text-[10px] font-bold border',
                              score >= 80 ? 'border-green-500/30 bg-green-500/10 text-green-400' :
                              score >= 60 ? 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400' :
                              'border-red-500/30 bg-red-500/10 text-red-400'
                            )}>
                              {score.toFixed(0)}
                            </div>
                            <div className="h-1 w-16 rounded-full bg-white/5 overflow-hidden">
                              <div
                                className={cn(
                                  'h-full rounded-full transition-all duration-700',
                                  score >= 80 ? 'bg-green-400' : score >= 60 ? 'bg-yellow-400' : 'bg-red-400'
                                )}
                                style={{ width: `${score}%` }}
                              />
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <span className={cn(
                          'inline-flex items-center justify-center min-w-[24px] h-5 px-1.5 rounded text-[10px] font-bold',
                          critical > 0
                            ? 'severity-glow-critical bg-red-500/15 text-red-400 border border-red-500/30'
                            : 'bg-white/5 text-muted-foreground border border-white/10'
                        )}>
                          {critical}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <span className={cn(
                          'inline-flex items-center justify-center min-w-[24px] h-5 px-1.5 rounded text-[10px] font-bold',
                          high > 0
                            ? 'severity-glow-high bg-orange-500/15 text-orange-400 border border-orange-500/30'
                            : 'bg-white/5 text-muted-foreground border border-white/10'
                        )}>
                          {high}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-[11px] text-muted-foreground whitespace-nowrap">
                        {formatDate(repo.last_scan_at)}
                      </td>
                    </motion.tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <CheckCircle className="h-6 w-6 text-green-400" />
                      <p className="text-sm font-medium text-foreground">No risky repositories</p>
                      <p className="text-xs text-muted-foreground">Repositories with findings will appear here</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  )
})

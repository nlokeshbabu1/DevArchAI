import { motion } from 'framer-motion'
import {
  AlertCircle, CheckCircle, Clock, ExternalLink, Github, Gitlab, Loader2, Play, Trash2,
} from 'lucide-react'
import { memo } from 'react'

import type { Repository } from '../../api/endpoints/repositories'
import {
  formatRepositoryActivity,
  inferRepositoryProvider,
  repositoryStatusLabel,
  scanActionLabel,
  type RepositoryDisplayStatus,
} from '../../lib/repository-display'
import { cn } from '../../lib/utils'
import { Badge } from '../ui'
import { SecurityScore } from '../ui/SecurityScore'
import { Button, Card } from '../ui-animated'

export type RepositoryCardModel = Repository & {
  displayStatus: RepositoryDisplayStatus
  source?: ReturnType<typeof inferRepositoryProvider>
}

type RepositoryListCardProps = {
  repo: RepositoryCardModel
  index?: number
  isStartPending?: boolean
  isLocallyScanning?: boolean
  onScan: () => void
  onViewResults: () => void
  onDelete: () => void
}

export const RepositoryListCard = memo(function RepositoryListCard({
  repo,
  index = 0,
  isStartPending = false,
  isLocallyScanning = false,
  onScan,
  onViewResults,
  onDelete,
}: RepositoryListCardProps) {
  const source = repo.source ?? inferRepositoryProvider(repo.url)
  const isRepoScanning = repo.displayStatus === 'scanning' || isLocallyScanning
  const hasScore = repo.overall_score !== undefined && repo.overall_score !== null
  const scanButtonLabel = scanActionLabel(repo.displayStatus)
  const activityLabel = formatRepositoryActivity(repo, repo.displayStatus)

  return (
    <motion.div
      className="h-full"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.12 + index * 0.06 }}
    >
      <Card className="flex h-full flex-col overflow-hidden" hover>
        <div className="flex flex-1 flex-col gap-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 flex-1 items-start gap-3">
              <div className="rounded-xl border border-white/10 bg-white/5 p-2.5">
                {source === 'gitlab' ? (
                  <Gitlab className="h-5 w-5 text-muted-foreground" aria-hidden />
                ) : (
                  <Github className="h-5 w-5 text-muted-foreground" aria-hidden />
                )}
              </div>
              <div className="min-w-0 flex-1 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate text-lg font-semibold text-foreground">{repo.name}</h3>
                  {source === 'github' && (
                    <Badge variant="secondary" className="border-blue-500/30 bg-blue-500/10 text-xs text-blue-400">
                      GitHub
                    </Badge>
                  )}
                  {source === 'gitlab' && (
                    <Badge variant="secondary" className="border-orange-500/30 bg-orange-500/10 text-xs text-orange-400">
                      GitLab
                    </Badge>
                  )}
                </div>
                <p className="line-clamp-2 text-sm leading-6 text-muted-foreground">
                  {repo.description || repo.url}
                </p>
                <p className="text-xs text-muted-foreground">
                  Branch: <span className="text-foreground/80">{repo.default_branch || 'main'}</span>
                </p>
              </div>
            </div>
            <div
              className={cn(
                'inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium',
                repo.displayStatus === 'completed'
                  ? 'border-green-500/30 bg-green-500/15 text-green-400'
                  : repo.displayStatus === 'scanning'
                  ? 'border-blue-500/30 bg-blue-500/15 text-blue-400'
                  : repo.displayStatus === 'failed'
                  ? 'border-red-500/30 bg-red-500/15 text-red-400'
                  : 'border-gray-500/30 bg-gray-500/15 text-gray-400',
              )}
            >
              {repo.displayStatus === 'scanning' && <Loader2 className="h-3 w-3 animate-spin" aria-hidden />}
              {repo.displayStatus === 'completed' && <CheckCircle className="h-3 w-3" aria-hidden />}
              {repo.displayStatus === 'failed' && <AlertCircle className="h-3 w-3" aria-hidden />}
              <span>{repositoryStatusLabel(repo.displayStatus)}</span>
            </div>
          </div>

          {repo.tech_stack && repo.tech_stack.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {repo.tech_stack.slice(0, 4).map((tech) => (
                <Badge key={tech} variant="secondary" className="text-xs">
                  {tech}
                </Badge>
              ))}
              {repo.tech_stack.length > 4 && (
                <Badge variant="secondary" className="text-xs">
                  +{repo.tech_stack.length - 4}
                </Badge>
              )}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Security Score
              </div>
              {hasScore ? (
                <div className="mt-3">
                  <SecurityScore
                    data={{ overall_score: repo.overall_score }}
                    size="sm"
                    showLabel={false}
                    animated={false}
                  />
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  {repo.displayStatus === 'scanning' ? 'Refreshing after scan…' : 'No score available yet'}
                </p>
              )}
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Latest Activity
              </div>
              <div className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden />
                <span className="leading-6">{activityLabel}</span>
              </div>
            </div>
          </div>

          {repo.issues && Object.values(repo.issues).some((value) => value > 0) && (
            <div className="flex flex-wrap gap-2">
              {repo.issues.critical > 0 && (
                <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400">
                  Critical {repo.issues.critical}
                </span>
              )}
              {repo.issues.high > 0 && (
                <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-2.5 py-1 text-xs font-medium text-orange-400">
                  High {repo.issues.high}
                </span>
              )}
              {repo.issues.medium > 0 && (
                <span className="rounded-full border border-yellow-500/30 bg-yellow-500/10 px-2.5 py-1 text-xs font-medium text-yellow-400">
                  Medium {repo.issues.medium}
                </span>
              )}
              {repo.issues.low > 0 && (
                <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-400">
                  Low {repo.issues.low}
                </span>
              )}
            </div>
          )}

          <div className="mt-auto border-t border-white/10 pt-5">
            <div className="flex flex-col gap-2 sm:flex-row">
              {repo.displayStatus === 'completed' && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="sm:flex-1"
                  onClick={onViewResults}
                  icon={<ExternalLink className="h-3.5 w-3.5" />}
                >
                  View Results
                </Button>
              )}

              {isRepoScanning ? (
                <Button
                  variant="secondary"
                  size="sm"
                  className="sm:flex-1"
                  disabled
                  icon={<Loader2 className="h-3.5 w-3.5 animate-spin" />}
                >
                  {isStartPending ? 'Starting Scan…' : 'Scanning…'}
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  className="sm:flex-1"
                  onClick={onScan}
                  disabled={isStartPending}
                  icon={isStartPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                >
                  {isStartPending ? 'Starting Scan…' : scanButtonLabel}
                </Button>
              )}

              <Button
                variant="ghost"
                size="sm"
                className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                onClick={onDelete}
                disabled={isRepoScanning || isStartPending}
                icon={<Trash2 className="h-3.5 w-3.5" />}
                aria-label={`Remove ${repo.name}`}
              >
                <span className="sr-only">Remove</span>
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  )
})
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'
import { Github, CheckCircle, RefreshCw, Clock, AlertCircle, Play, Eye } from 'lucide-react'
import { Button } from '../ui'

interface RepositoryCardProps {
  name: string
  description?: string
  lastScan?: string
  score?: number
  status: 'scanned' | 'scanning' | 'pending' | 'error'
  onScan?: () => void
  onView?: () => void
  delay?: number
}

export function RepositoryCard({
  name,
  description,
  lastScan,
  score,
  status,
  onScan,
  onView,
  delay = 0,
}: RepositoryCardProps) {
  const statusConfig = {
    scanned: { color: 'text-green-400', bg: 'bg-green-500/15', icon: CheckCircle, label: 'Scanned' },
    scanning: { color: 'text-blue-400', bg: 'bg-blue-500/15', icon: RefreshCw, label: 'Scanning' },
    pending: { color: 'text-yellow-400', bg: 'bg-yellow-500/15', icon: Clock, label: 'Pending' },
    error: { color: 'text-red-400', bg: 'bg-red-500/15', icon: AlertCircle, label: 'Error' },
  }

  const StatusIcon = statusConfig[status].icon
  const statusInfo = statusConfig[status]

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 50) return 'text-orange-400'
    return 'text-red-400'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      whileHover={{ y: -4 }}
    >
      <div className={cn(
        'bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30',
        'rounded-2xl p-6',
        'transition-all duration-300 hover:border-white/20 hover:shadow-2xl hover:shadow-black/40'
      )}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="p-2.5 bg-white/5 rounded-xl border border-white/10">
              <Github className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-foreground truncate">{name}</h3>
              {description && (
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{description}</p>
              )}
            </div>
          </div>
          <div className={cn(
            'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
            statusInfo.bg,
            statusInfo.color
          )}>
            <StatusIcon className="h-3.5 w-3.5" />
            <span className="capitalize">{statusInfo.label}</span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-white/10">
          <div className="flex items-center gap-4">
            {score !== undefined && (
              <div>
                <div className="text-xs text-muted-foreground">Score</div>
                <div className={cn('text-lg font-bold', getScoreColor(score))}>
                  {score.toFixed(1)}
                </div>
              </div>
            )}
            {lastScan && (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">{lastScan}</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {onView && (
              <Button variant="ghost" size="sm" onClick={onView}>
                <Eye className="h-3.5 w-3.5 mr-1" />
                View
              </Button>
            )}
            {onScan && status !== 'scanning' && (
              <Button variant="primary" size="sm" onClick={onScan}>
                <Play className="h-3.5 w-3.5 mr-1" />
                Scan
              </Button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

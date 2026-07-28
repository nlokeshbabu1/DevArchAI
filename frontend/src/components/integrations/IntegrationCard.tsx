import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { CheckCircle, Clock, Zap } from 'lucide-react'
import { ProviderLogo } from './ProviderLogo'
import { ConnectionBadge } from './ConnectionBadge'
import { ProviderActionButton } from './ProviderActionButton'
import type { IntegrationMeta } from './types'

interface IntegrationCardProps {
  integration: IntegrationMeta
  index?: number
  onClick?: () => void
  className?: string
}

export function IntegrationCard({ integration, index = 0, onClick, className }: IntegrationCardProps) {
  const {
    name,
    description,
    icon,
    status,
    features,
    connectedAccount,
    lastScan,
    extraStats,
  } = integration

  const isConnected = status === 'connected'
  const isSyncing = status === 'syncing'

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className={cn(
        'group relative rounded-2xl border transition-all duration-200',
        'bg-card/60 backdrop-blur-xl border-white/10 hover:border-white/20',
        'hover:shadow-lg hover:shadow-black/20',
        isConnected && 'border-emerald-500/20 hover:border-emerald-500/30',
        isSyncing && 'border-blue-500/20 hover:border-blue-500/30',
        className,
      )}
    >
      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <ProviderLogo icon={icon} size="lg" className="h-10 w-10" />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-foreground truncate">{name}</h3>
              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{description}</p>
            </div>
          </div>
        </div>

        {/* Status badge */}
        <div className="mb-3">
          <ConnectionBadge status={status} />
        </div>

        {/* Connected metadata */}
        {isConnected && connectedAccount && (
          <div className="mb-3 px-3 py-2 rounded-lg bg-white/5 border border-white/5">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
              Account
            </div>
            <div className="text-xs font-medium text-foreground font-mono truncate">
              {connectedAccount}
            </div>
          </div>
        )}

        {/* Stats */}
        {isConnected && extraStats && (
          <div className="grid grid-cols-2 gap-2 mb-3">
            {Object.entries(extraStats).map(([key, value]) => (
              <div key={key} className="px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/5">
                <div className="text-[10px] text-muted-foreground">{key}</div>
                <div className="text-xs font-semibold text-foreground">{String(value)}</div>
              </div>
            ))}
          </div>
        )}

        {/* Last scan */}
        {isConnected && lastScan && (
          <div className="flex items-center gap-1.5 mb-3 text-[10px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            Last scan {lastScan}
          </div>
        )}

        {/* Features */}
        {features && !isConnected && (
          <div className="flex flex-wrap gap-1 mb-3">
            {features.slice(0, 3).map((f) => (
              <span
                key={f}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-[10px] text-muted-foreground"
              >
                <CheckCircle className="h-2.5 w-2.5 text-emerald-400/60" />
                {f}
              </span>
            ))}
            {features.length > 3 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-[10px] text-muted-foreground">
                +{features.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Action button */}
        <ProviderActionButton status={status} onClick={onClick} />
      </div>
    </motion.div>
  )
}

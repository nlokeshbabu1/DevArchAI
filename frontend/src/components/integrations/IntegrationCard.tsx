import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { CheckCircle, Clock, Zap, ArrowRight } from 'lucide-react'
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
    connectionId,
    healthStatus,
    kubernetesVersion,
    lastVerified,
    providerLabel,
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
              {providerLabel || 'Cluster'}
            </div>
            <div className="text-xs font-medium text-foreground font-mono truncate">
              {connectedAccount}
            </div>
            {kubernetesVersion && (
              <div className="text-[10px] text-muted-foreground mt-1">{kubernetesVersion}</div>
            )}
            {healthStatus && (
              <div className="text-[10px] mt-1 capitalize text-emerald-400">
                {healthStatus === 'connected' ? '✓ Healthy' : healthStatus.replace(/_/g, ' ')}
              </div>
            )}
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

        {/* Last scan / verified */}
        {isConnected && (lastScan || lastVerified) && (
          <div className="flex items-center gap-1.5 mb-3 text-[10px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            {lastVerified ? `Last verified ${lastVerified}` : `Last scan ${lastScan}`}
          </div>
        )}

        {/* Open cluster for K8s */}
        {isConnected && connectionId && (
          <Link
            to="/kubernetes"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-2 w-full justify-center mb-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition-all"
          >
            Open Cluster
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
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

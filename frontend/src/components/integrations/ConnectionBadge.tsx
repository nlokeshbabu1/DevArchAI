import { Check, X, Loader2, AlertCircle, Clock, Construction } from 'lucide-react'

import { cn } from '@/lib/utils'

import type { ConnectionStatus } from './types'


const STATUS_CONFIG: Record<ConnectionStatus, { label: string; dot: string; bg: string; icon: React.ComponentType<{ className?: string }> }> = {
  connected: {
    label: 'Connected',
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    icon: Check,
  },
  syncing: {
    label: 'Syncing',
    dot: 'bg-blue-500',
    bg: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    icon: Loader2,
  },
  connecting: {
    label: 'Connecting',
    dot: 'bg-blue-500',
    bg: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    icon: Loader2,
  },
  verifying: {
    label: 'Verifying',
    dot: 'bg-amber-500',
    bg: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    icon: Loader2,
  },
  error: {
    label: 'Error',
    dot: 'bg-red-500',
    bg: 'bg-red-500/10 border-red-500/20 text-red-400',
    icon: AlertCircle,
  },
  not_connected: {
    label: 'Not Connected',
    dot: 'bg-zinc-500',
    bg: 'bg-zinc-500/10 border-zinc-500/20 text-zinc-400',
    icon: X,
  },
  coming_soon: {
    label: 'Coming Soon',
    dot: 'bg-amber-500',
    bg: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    icon: Construction,
  },
}

interface ConnectionBadgeProps {
  status: ConnectionStatus
  className?: string
}

export function ConnectionBadge({ status, className }: ConnectionBadgeProps) {
  const config = STATUS_CONFIG[status]
  const Icon = config.icon

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
        config.bg,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dot, (status === 'syncing' || status === 'connecting' || status === 'verifying') && 'animate-pulse')} />
      <Icon className={cn('h-3 w-3', (status === 'syncing' || status === 'connecting' || status === 'verifying') && 'animate-spin')} />
      {config.label}
    </span>
  )
}

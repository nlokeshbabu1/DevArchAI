import { cn } from '@/lib/utils'
import { Plug, Settings, ExternalLink, ArrowRight, Loader2 } from 'lucide-react'
import type { ConnectionStatus } from './types'

interface ProviderActionButtonProps {
  status: ConnectionStatus
  onClick?: () => void
  className?: string
}

export function ProviderActionButton({ status, onClick, className }: ProviderActionButtonProps) {
  const config = {
    connected: {
      label: 'Manage',
      icon: Settings,
      style: 'bg-white/10 hover:bg-white/15 text-foreground border border-white/10',
    },
    syncing: {
      label: 'Scanning...',
      icon: Loader2,
      style: 'bg-blue-500/20 hover:bg-blue-500/25 text-blue-400 border border-blue-500/20 cursor-wait',
    },
    error: {
      label: 'Retry',
      icon: ArrowRight,
      style: 'bg-red-500/20 hover:bg-red-500/25 text-red-400 border border-red-500/20',
    },
    not_connected: {
      label: 'Connect',
      icon: Plug,
      style: 'bg-white/5 hover:bg-white/10 text-muted-foreground border border-white/10 hover:text-foreground',
    },
    coming_soon: {
      label: 'Coming Soon',
      icon: ExternalLink,
      style: 'bg-white/5 border border-white/5 text-muted-foreground/50 cursor-not-allowed',
    },
  }

  const { label, icon: Icon, style } = config[status]

  return (
    <button
      onClick={status === 'coming_soon' ? undefined : onClick}
      disabled={status === 'coming_soon'}
      className={cn(
        'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
        style,
        className,
      )}
    >
      <Icon className={cn('h-3.5 w-3.5', status === 'syncing' && 'animate-spin')} />
      {label}
    </button>
  )
}

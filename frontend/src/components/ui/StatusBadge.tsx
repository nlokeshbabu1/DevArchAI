import { cn } from '../../lib/utils'

export type ProductStatus =
  | 'available'
  | 'connected'
  | 'not_connected'
  | 'coming_soon'
  | 'enterprise'
  | 'beta'
  | 'running'
  | 'failed'
  | 'completed'
  | 'queued'
  | 'processing'
  | 'pending'

const STYLES: Record<ProductStatus, string> = {
  available: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  connected: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  not_connected: 'bg-white/5 text-white/40 border-white/10',
  coming_soon: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/25',
  enterprise: 'bg-purple-500/10 text-purple-300 border-purple-500/25',
  beta: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25',
  running: 'bg-blue-500/10 text-blue-300 border-blue-500/25',
  processing: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/25',
  queued: 'bg-indigo-500/5 text-indigo-300/80 border-indigo-500/20',
  pending: 'bg-white/5 text-white/50 border-white/10',
  completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  failed: 'bg-red-500/10 text-red-400 border-red-500/25',
}

const LABELS: Record<ProductStatus, string> = {
  available: 'Available',
  connected: 'Connected',
  not_connected: 'Not Connected',
  coming_soon: 'Coming Soon',
  enterprise: 'Enterprise',
  beta: 'Beta',
  running: 'Running',
  processing: 'Processing',
  queued: 'Queued',
  pending: 'Pending',
  completed: 'Completed',
  failed: 'Failed',
}

interface StatusBadgeProps {
  status: ProductStatus
  label?: string
  className?: string
  dot?: boolean
}

export function StatusBadge({ status, label, className, dot = false }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
        STYLES[status],
        className,
      )}
    >
      {dot && (
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            status === 'failed' ? 'bg-red-400' : status === 'completed' || status === 'connected' ? 'bg-emerald-400' : 'bg-current',
          )}
          aria-hidden
        />
      )}
      {label ?? LABELS[status]}
    </span>
  )
}

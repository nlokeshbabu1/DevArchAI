import { cn } from '../../lib/utils'
import { AlertTriangle, AlertCircle, CheckCircle, Info } from 'lucide-react'

interface SeverityBadgeProps {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  className?: string
}

export function SeverityBadge({
  severity,
  size = 'md',
  showIcon = true,
  className,
}: SeverityBadgeProps) {
  const config = {
    critical: {
      bg: 'bg-red-500/15',
      text: 'text-red-400',
      border: 'border-red-500/40',
      icon: AlertTriangle,
    },
    high: {
      bg: 'bg-orange-500/15',
      text: 'text-orange-400',
      border: 'border-orange-500/40',
      icon: AlertTriangle,
    },
    medium: {
      bg: 'bg-yellow-500/15',
      text: 'text-yellow-400',
      border: 'border-yellow-500/40',
      icon: AlertCircle,
    },
    low: {
      bg: 'bg-green-500/15',
      text: 'text-green-400',
      border: 'border-green-500/40',
      icon: CheckCircle,
    },
    info: {
      bg: 'bg-blue-500/15',
      text: 'text-blue-400',
      border: 'border-blue-500/40',
      icon: Info,
    },
  }

  const sizeConfig = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  }

  const iconSize = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }

  const { bg, text, border, icon: Icon } = config[severity]
  const IconComponent = Icon

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full font-medium border',
      'backdrop-blur-sm',
      bg, text, border,
      sizeConfig[size],
      className
    )}>
      {showIcon && <IconComponent className={iconSize[size]} />}
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  )
}

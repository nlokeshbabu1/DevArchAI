import type { ReactNode } from 'react'

import { cn } from '../../lib/utils'

interface PageHeaderProps {
  title: string
  description?: string
  breadcrumb?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, description, breadcrumb, actions, className }: PageHeaderProps) {
  return (
    <header className={cn('flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-6', className)}>
      <div className="min-w-0 space-y-1">
        {breadcrumb && <div className="text-xs text-muted-foreground mb-1">{breadcrumb}</div>}
        <h1 className="text-2xl font-bold text-foreground tracking-tight font-display">{title}</h1>
        {description && <p className="text-sm text-muted-foreground max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap shrink-0">{actions}</div>}
    </header>
  )
}

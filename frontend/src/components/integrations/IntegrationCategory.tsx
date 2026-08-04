import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import {
  GitBranch,
  Cloud,
  Workflow,
  Container,
  FileCode,
  Bell,
  type LucideIcon,
} from 'lucide-react'
import { IntegrationCard } from './IntegrationCard'
import type { IntegrationCategory as IntegrationCategoryType, IntegrationMeta } from './types'

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  repositories: GitBranch,
  cloud: Cloud,
  cicd: Workflow,
  containers: Container,
  iac: FileCode,
  notifications: Bell,
}

interface IntegrationCategoryProps {
  category: IntegrationCategoryType
  onConnect?: (id: string) => void
  onManage?: (id: string) => void
  className?: string
}

export function IntegrationCategory({
  category,
  onConnect,
  onManage,
  className,
}: IntegrationCategoryProps) {
  const Icon = CATEGORY_ICONS[category.id] || Cloud

  const handleProviderClick = (integration: IntegrationMeta) => {
    if (integration.status === 'connected') {
      onManage?.(integration.id)
    } else if (integration.status === 'not_connected') {
      onConnect?.(integration.id)
    }
  }

  const connectedCount = category.providers.filter((p) => p.status === 'connected').length
  const totalCount = category.providers.length

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={cn('space-y-4', className)}
    >
      {/* Category header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center h-9 w-9 rounded-xl bg-white/5 border border-white/10">
            <Icon className="h-4.5 w-4.5 text-muted-foreground" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-foreground">{category.title}</h2>
              {connectedCount > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-medium text-emerald-400">
                  {connectedCount} connected
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{category.description}</p>
          </div>
        </div>
        <div className="text-[10px] text-muted-foreground font-medium">
          {connectedCount}/{totalCount}
        </div>
      </div>

      {/* Cards grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {category.providers.map((integration, index) => (
          <IntegrationCard
            key={integration.id}
            integration={integration}
            index={index}
            onClick={() => handleProviderClick(integration)}
          />
        ))}
      </div>
    </motion.section>
  )
}

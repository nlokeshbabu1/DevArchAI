import { motion } from 'framer-motion'
import { useState, type ReactNode } from 'react'

import { cn } from '../../lib/utils'

interface Tab {
  id: string
  label: string
  icon?: ReactNode
  count?: number
}

interface TabsProps {
  tabs: Tab[]
  children: ReactNode[]
  className?: string
}

export function Tabs({ tabs, children, className }: TabsProps) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.id)

  return (
    <div className={cn('w-full', className)}>
      {/* Tab Bar */}
      <div className="flex items-center gap-1 p-1 rounded-lg bg-white/5 border border-white/10">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'relative flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors',
                isActive
                  ? 'text-foreground'
                  : 'text-muted-foreground hover:text-foreground/80'
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-white/10 rounded-md"
                  transition={{ type: 'spring', duration: 0.5 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-2">
                {tab.icon}
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className={cn(
                    'px-1.5 py-0.5 text-xs rounded-full',
                    isActive ? 'bg-primary/20 text-primary' : 'bg-white/10 text-muted-foreground'
                  )}>
                    {tab.count}
                  </span>
                )}
              </span>
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="mt-4">
        {tabs.map((tab, index) => {
          const isActive = activeTab === tab.id
          return (
            <div
              key={tab.id}
              className={cn('transition-opacity duration-200', isActive ? 'opacity-100' : 'opacity-0 hidden')}
            >
              {children[index]}
            </div>
          )
        })}
      </div>
    </div>
  )
}

import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface SectionHeaderProps {
  badge?: string
  badgeIcon?: LucideIcon
  title: string
  description: string
  className?: string
}

export function SectionHeader({
  badge,
  badgeIcon: BadgeIcon,
  title,
  description,
  className = '',
}: SectionHeaderProps) {
  return (
    <div className={`text-center mb-12 md:mb-16 space-y-4 ${className}`}>
      {badge && BadgeIcon && (
        <motion.div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <BadgeIcon className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-primary">{badge}</span>
        </motion.div>
      )}
      <motion.h2
        className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight"
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        {title}
      </motion.h2>
      <motion.p
        className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed"
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        {description}
      </motion.p>
    </div>
  )
}

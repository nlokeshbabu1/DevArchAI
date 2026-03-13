import { cn } from '../../lib/utils'
import { motion } from 'framer-motion'

interface AnimatedCardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
  delay?: number
  onClick?: () => void
}

export function AnimatedCard({
  children,
  className,
  hover = true,
  delay = 0,
  onClick,
}: AnimatedCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      whileHover={hover ? { y: -4, scale: 1.02 } : {}}
      onClick={onClick}
      className={cn(
        'bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 rounded-2xl p-6',
        hover && 'transition-all duration-300 hover:border-white/20 hover:shadow-2xl hover:shadow-black/40',
        onClick && 'cursor-pointer',
        className
      )}
    >
      {children}
    </motion.div>
  )
}

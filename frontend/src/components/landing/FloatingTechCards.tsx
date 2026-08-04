import { memo, useMemo, useState, useEffect } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  Box, Hexagon, Layers, Cloud, Shield, GitBranch,
} from 'lucide-react'

function useIsDesktop(breakpoint = 1024) {
  const [isDesktop, setIsDesktop] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${breakpoint}px)`)
    setIsDesktop(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])
  return isDesktop
}

interface FloatingCard {
  id: number
  icon: React.ElementType
  label: string
  color: string
  borderColor: string
  x: string
  y: string
  delay: number
  duration: number
  driftX: number
  driftY: number
}

const allCards: FloatingCard[] = [
  { id: 0, icon: Box, label: 'Docker', color: 'text-blue-400', borderColor: 'border-blue-500/15', x: '3%', y: '18%', delay: 0, duration: 9, driftX: 4, driftY: -5 },
  { id: 1, icon: Hexagon, label: 'K8s', color: 'text-cyan-400', borderColor: 'border-cyan-500/15', x: '94%', y: '15%', delay: 0.5, duration: 10, driftX: -4, driftY: -4 },
  { id: 2, icon: Layers, label: 'Terraform', color: 'text-purple-400', borderColor: 'border-purple-500/15', x: '5%', y: '75%', delay: 1, duration: 11, driftX: 5, driftY: -3 },
  { id: 3, icon: Shield, label: 'Helm', color: 'text-indigo-400', borderColor: 'border-indigo-500/15', x: '93%', y: '72%', delay: 1.5, duration: 9.5, driftX: -5, driftY: -5 },
  { id: 4, icon: GitBranch, label: 'GitHub Actions', color: 'text-slate-400', borderColor: 'border-slate-500/15', x: '2%', y: '50%', delay: 2, duration: 10.5, driftX: 3, driftY: -4 },
  { id: 5, icon: Cloud, label: 'AWS', color: 'text-amber-400', borderColor: 'border-amber-500/15', x: '95%', y: '48%', delay: 0.8, duration: 8.5, driftX: -3, driftY: -6 },
]

const FloatingCardItem = memo(function FloatingCardItem({
  card, reduced,
}: {
  card: FloatingCard; reduced: boolean
}) {
  const Icon = card.icon

  return (
    <motion.div
      className="absolute hidden lg:flex"
      style={{ left: card.x, top: card.y }}
      initial={{ opacity: 0, scale: 0.7 }}
      animate={reduced ? { opacity: 0.45, scale: 1 } : {
        opacity: [0, 0.45, 0.45],
        scale: [0.7, 1, 1],
        x: [0, card.driftX, 0],
        y: [0, card.driftY, 0],
      }}
      transition={reduced ? { duration: 0.5, delay: card.delay } : {
        opacity: { duration: 0.8, delay: card.delay },
        scale: { duration: 0.8, delay: card.delay },
        x: { duration: card.duration, repeat: Infinity, ease: 'easeInOut', delay: card.delay },
        y: { duration: card.duration, repeat: Infinity, ease: 'easeInOut', delay: card.delay },
      }}
    >
      <div className={`glass-card-premium rounded-lg px-2.5 py-1.5 flex items-center gap-1.5 ${card.borderColor}`}>
        <Icon className={`w-3 h-3 ${card.color}`} />
        <span className="text-[9px] font-medium text-white/40 whitespace-nowrap">{card.label}</span>
      </div>
    </motion.div>
  )
})

export const FloatingTechCards = memo(function FloatingTechCards() {
  const prefersReducedMotion = useReducedMotion()
  const isDesktop = useIsDesktop()

  const visibleCards = useMemo(() => {
    if (!isDesktop) {
      return []
    }
    return allCards
  }, [isDesktop])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {visibleCards.map((card) => (
        <FloatingCardItem
          key={card.id}
          card={card}
          reduced={!!prefersReducedMotion}
        />
      ))}
    </div>
  )
})

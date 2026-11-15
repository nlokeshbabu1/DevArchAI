import { motion, useReducedMotion } from 'framer-motion'
import {
  Box, Hexagon, Layers, Cloud, Shield, GitBranch, Github,
  Server, Workflow, Rocket, Activity, LineChart, Search, Radar,
} from 'lucide-react'
import { memo, useMemo, useState, useEffect } from 'react'

import { MARQUEE_TECHNOLOGIES } from '../../lib/supported-capabilities'

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
  sub: string
  color: string
  glow: string
  borderColor: string
  x: string
  y: string
  delay: number
  duration: number
  driftX: number
  driftY: number
  rotate: number
}

const allCards: FloatingCard[] = [
  { id: 0, icon: Box, label: 'Docker', sub: 'Container', color: 'text-[#4f8dff]', glow: 'rgba(79,141,255,0.35)', borderColor: 'border-blue-500/20', x: '2%', y: '16%', delay: 0, duration: 9, driftX: 5, driftY: -5, rotate: -2 },
  { id: 1, icon: Hexagon, label: 'Kubernetes', sub: 'Orchestration', color: 'text-[#00e5ff]', glow: 'rgba(0,229,255,0.35)', borderColor: 'border-cyan-500/20', x: '94%', y: '12%', delay: 0.5, duration: 10, driftX: -4, driftY: -4, rotate: 2 },
  { id: 2, icon: Layers, label: 'Terraform', sub: 'IaC', color: 'text-[#7c5cff]', glow: 'rgba(124,92,255,0.35)', borderColor: 'border-purple-500/20', x: '3%', y: '78%', delay: 1, duration: 11, driftX: 5, driftY: -3, rotate: 1.5 },
  { id: 3, icon: Cloud, label: 'AWS', sub: 'Cloud', color: 'text-amber-400', glow: 'rgba(255,181,71,0.3)', borderColor: 'border-amber-500/20', x: '94%', y: '74%', delay: 1.5, duration: 9.5, driftX: -5, driftY: -5, rotate: -1 },
  { id: 4, icon: Github, label: 'GitHub Actions', sub: 'CI/CD', color: 'text-slate-300', glow: 'rgba(148,163,184,0.3)', borderColor: 'border-slate-500/20', x: '1.5%', y: '47%', delay: 2, duration: 10.5, driftX: 3, driftY: -4, rotate: 0.5 },
  { id: 5, icon: Radar, label: 'Trivy', sub: 'Scanner', color: 'text-emerald-400', glow: 'rgba(0,217,126,0.3)', borderColor: 'border-emerald-500/20', x: '95%', y: '45%', delay: 0.8, duration: 8.5, driftX: -3, driftY: -6, rotate: -1.5 },
  { id: 6, icon: Cloud, label: 'Azure', sub: 'Cloud', color: 'text-[#4f8dff]', glow: 'rgba(79,141,255,0.3)', borderColor: 'border-blue-500/20', x: '6%', y: '30%', delay: 0.9, duration: 12, driftX: 4, driftY: -6, rotate: 1 },
  { id: 7, icon: Cloud, label: 'GCP', sub: 'Cloud', color: 'text-red-400', glow: 'rgba(255,91,107,0.28)', borderColor: 'border-red-500/20', x: '90%', y: '28%', delay: 1.2, duration: 11, driftX: -4, driftY: -5, rotate: -1 },
  { id: 8, icon: GitBranch, label: 'GitLab CI', sub: 'CI/CD', color: 'text-orange-400', glow: 'rgba(255,181,71,0.28)', borderColor: 'border-orange-500/20', x: '4%', y: '62%', delay: 1.7, duration: 10, driftX: 4, driftY: -5, rotate: 1.5 },
  { id: 9, icon: Rocket, label: 'Jenkins', sub: 'CI/CD', color: 'text-red-400', glow: 'rgba(255,91,107,0.3)', borderColor: 'border-red-500/20', x: '92%', y: '60%', delay: 2.2, duration: 9, driftX: -4, driftY: -4, rotate: -0.5 },
  { id: 10, icon: Shield, label: 'Helm', sub: 'Charts', color: 'text-[#7c5cff]', glow: 'rgba(124,92,255,0.3)', borderColor: 'border-purple-500/20', x: '7%', y: '8%', delay: 0.4, duration: 13, driftX: 3, driftY: -6, rotate: 2 },
  { id: 11, icon: Server, label: 'Ansible', sub: 'Config', color: 'text-slate-300', glow: 'rgba(148,163,184,0.28)', borderColor: 'border-slate-500/20', x: '90%', y: '8%', delay: 1.4, duration: 12, driftX: -3, driftY: -6, rotate: -1.5 },
  { id: 12, icon: Workflow, label: 'ArgoCD', sub: 'GitOps', color: 'text-[#00e5ff]', glow: 'rgba(0,229,255,0.3)', borderColor: 'border-cyan-500/20', x: '1%', y: '33%', delay: 2.6, duration: 9.5, driftX: 4, driftY: -3, rotate: 1 },
  { id: 13, icon: Activity, label: 'Prometheus', sub: 'Metrics', color: 'text-orange-400', glow: 'rgba(255,181,71,0.28)', borderColor: 'border-orange-500/20', x: '96%', y: '33%', delay: 3, duration: 11, driftX: -4, driftY: -5, rotate: 0.5 },
  { id: 14, icon: LineChart, label: 'Grafana', sub: 'Dashboards', color: 'text-[#4f8dff]', glow: 'rgba(79,141,255,0.28)', borderColor: 'border-blue-500/20', x: '5%', y: '90%', delay: 0.6, duration: 10.5, driftX: 5, driftY: -4, rotate: -1 },
  { id: 16, icon: Shield, label: 'Checkov', sub: 'IaC policy', color: 'text-violet-400', glow: 'rgba(139,92,246,0.28)', borderColor: 'border-violet-500/20', x: '91%', y: '88%', delay: 2.4, duration: 12.5, driftX: -5, driftY: -4, rotate: 1 },
  { id: 17, icon: Search, label: 'Gitleaks', sub: 'Secrets', color: 'text-rose-400', glow: 'rgba(244,63,94,0.28)', borderColor: 'border-rose-500/20', x: '50%', y: '6%', delay: 1.1, duration: 11.5, driftX: 3, driftY: -4, rotate: 0.5 },
]

const heroLabelSet = new Set<string>(MARQUEE_TECHNOLOGIES)

const FloatingCardItem = memo(function FloatingCardItem({
  card, reduced,
}: {
  card: FloatingCard; reduced: boolean
}) {
  const Icon = card.icon

  return (
    <motion.div
      className="absolute hidden lg:block"
      style={{ left: card.x, top: card.y }}
      initial={{ opacity: 0, scale: 0.7 }}
      animate={reduced ? { opacity: 0.55, scale: 1, rotate: 0 } : {
        opacity: [0, 0.55, 0.55],
        scale: [0.7, 1, 1],
        rotate: [card.rotate, card.rotate * -1, card.rotate],
        x: [0, card.driftX, 0],
        y: [0, card.driftY, 0],
      }}
      transition={reduced ? { duration: 0.5, delay: card.delay } : {
        opacity: { duration: 0.8, delay: card.delay },
        scale: { duration: 0.8, delay: card.delay },
        rotate: { duration: card.duration, repeat: Infinity, ease: 'easeInOut', delay: card.delay },
        x: { duration: card.duration, repeat: Infinity, ease: 'easeInOut', delay: card.delay },
        y: { duration: card.duration, repeat: Infinity, ease: 'easeInOut', delay: card.delay },
      }}
    >
      <motion.div
        className="group relative"
        whileHover={reduced ? undefined : { scale: 1.06, transition: { duration: 0.25 } }}
      >
        {/* Glow halo */}
        <div
          className="absolute -inset-2 rounded-xl opacity-50 group-hover:opacity-90 transition-opacity duration-300"
          style={{ background: `radial-gradient(circle, ${card.glow} 0%, transparent 70%)`, filter: 'blur(10px)' }}
        />
        <div
          className="relative rounded-lg px-3.5 py-2.5 flex items-center gap-2.5 animate-glow-breathe hover:-translate-y-1"
          style={{
            background: 'rgba(18, 24, 45, 0.92)',
            border: '1px solid rgba(130, 140, 255, 0.35)',
            backdropFilter: 'blur(20px) saturate(160%)',
            WebkitBackdropFilter: 'blur(20px) saturate(160%)',
            ['--chip-glow' as string]: card.glow,
            transition: 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.3s ease, box-shadow 0.3s ease',
          }}
        >
          <div className="p-1.5 rounded-md bg-white/[0.06] border border-white/[0.1]" style={{ filter: 'brightness(1.15)' }}>
            <Icon className={`w-4 h-4 ${card.color}`} style={{ filter: 'brightness(1.4)' }} />
          </div>
          <div className="leading-tight">
            <span className="block text-[11px] font-semibold text-white/90 whitespace-nowrap font-display">{card.label}</span>
            <span className="block text-[9px] text-white/40 whitespace-nowrap font-mono">{card.sub}</span>
          </div>
        </div>
      </motion.div>
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
    return allCards.filter((card) => heroLabelSet.has(card.label))
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

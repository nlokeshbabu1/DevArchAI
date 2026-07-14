import { memo, useState, useEffect } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Box, GitBranch, Github, Layers, Cloud, Server, Shield, Hexagon } from 'lucide-react'
import { cn } from '../../lib/utils'

interface TechItem {
  name: string
  icon: React.ElementType
  category: string
  color: string
}

const technologies: TechItem[] = [
  { name: 'Docker', icon: Box, category: 'Containers', color: 'from-blue-500/20 to-cyan-500/20' },
  { name: 'Docker Compose', icon: Layers, category: 'Containers', color: 'from-blue-500/20 to-cyan-500/20' },
  { name: 'Kubernetes', icon: Hexagon, category: 'Orchestration', color: 'from-indigo-500/20 to-blue-500/20' },
  { name: 'Helm', icon: Shield, category: 'Orchestration', color: 'from-indigo-500/20 to-blue-500/20' },
  { name: 'Terraform', icon: Layers, category: 'Infrastructure', color: 'from-purple-500/20 to-indigo-500/20' },
  { name: 'GitHub Actions', icon: Github, category: 'CI/CD', color: 'from-slate-500/20 to-gray-500/20' },
  { name: 'Jenkins', icon: GitBranch, category: 'CI/CD', color: 'from-orange-500/20 to-red-500/20' },
  { name: 'GitLab CI', icon: GitBranch, category: 'CI/CD', color: 'from-orange-500/20 to-amber-500/20' },
  { name: 'AWS', icon: Cloud, category: 'Cloud', color: 'from-amber-500/20 to-orange-500/20' },
  { name: 'EKS', icon: Server, category: 'Cloud', color: 'from-amber-500/20 to-orange-500/20' },
  { name: 'AKS', icon: Server, category: 'Cloud', color: 'from-blue-500/20 to-cyan-500/20' },
  { name: 'GKE', icon: Server, category: 'Cloud', color: 'from-green-500/20 to-emerald-500/20' },
]

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`)
    setIsMobile(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])
  return isMobile
}

const TechChip = memo(function TechChip({ tech, index }: { tech: TechItem; index: number }) {
  const Icon = tech.icon
  const [isHovered, setIsHovered] = useState(false)
  const prefersReducedMotion = useReducedMotion()

  return (
    <motion.div
      className={cn(
        'tech-chip flex items-center gap-2.5 px-4 py-2.5 rounded-xl',
        'bg-white/[0.03] border border-white/[0.06]',
        'cursor-default select-none',
        'transition-all duration-300',
        isHovered && 'border-primary/30 bg-primary/[0.05]'
      )}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: index * 0.04, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      whileHover={prefersReducedMotion ? undefined : { y: -3, scale: 1.02 }}
    >
      {/* Icon with animated glow on hover */}
      <div className={cn(
        'relative p-1.5 rounded-lg border border-white/[0.06]',
        'transition-all duration-300',
        isHovered ? 'bg-primary/15 border-primary/30' : 'bg-white/[0.04]'
      )}>
        <Icon className={cn(
          'h-4 w-4 transition-colors duration-300',
          isHovered ? 'text-primary' : 'text-white/60'
        )} />
        {/* Glow effect on hover */}
        {isHovered && !prefersReducedMotion && (
          <motion.div
            className="absolute inset-0 rounded-lg bg-primary/20 blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
        )}
      </div>

      {/* Name */}
      <span className={cn(
        'text-sm font-medium whitespace-nowrap transition-colors duration-300',
        isHovered ? 'text-white' : 'text-white/70'
      )}>
        {tech.name}
      </span>

      {/* Scanning pulse line on hover */}
      {isHovered && !prefersReducedMotion && (
        <motion.div
          className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div
            className="absolute inset-0 animate-scan-pulse"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.08), transparent)',
              backgroundSize: '200% 100%',
            }}
          />
        </motion.div>
      )}
    </motion.div>
  )
})

export function TechnologyMarquee() {
  const isMobile = useIsMobile()
  const prefersReducedMotion = useReducedMotion()

  // On mobile: static grid (no marquee animation). On desktop: infinite marquee.
  const allTechs = isMobile
    ? technologies
    : [...technologies, ...technologies, ...technologies]

  return (
    <section className="py-12 lg:py-16 overflow-hidden" aria-label="Supported technologies">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 mb-8">
        <div className="text-center space-y-3">
          <h2 className="display-lg text-white">
            Scan Across Your Entire Stack
          </h2>
          <p className="text-base text-slate-400 max-w-2xl mx-auto">
            Comprehensive security scanning for containers, orchestrators, CI/CD pipelines, and cloud platforms
          </p>
        </div>
      </div>

      {isMobile ? (
        /* Static grid on mobile — no horizontal scroll */
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-2">
            {technologies.map((tech, index) => (
              <TechChip key={`${tech.name}-mobile`} tech={tech} index={index} />
            ))}
          </div>
        </div>
      ) : (
        /* Marquee on desktop */
        <div className="relative">
          {/* Fade edges */}
          <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-[#0B1020] to-transparent z-10 pointer-events-none" />
          <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-[#0B1020] to-transparent z-10 pointer-events-none" />

          {/* Marquee */}
          <div
            className={cn(
              'flex gap-3',
              !prefersReducedMotion && 'animate-marquee'
            )}
            style={{ width: 'max-content' }}
          >
            {allTechs.map((tech, index) => (
              <TechChip key={`${tech.name}-${index}`} tech={tech} index={index} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

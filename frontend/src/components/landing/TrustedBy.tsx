import { motion, useReducedMotion } from 'framer-motion'
import { memo, useState, useEffect } from 'react'

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

const logos = [
  { name: 'Terraform', abbr: 'TF' },
  { name: 'Kubernetes', abbr: 'K8s' },
  { name: 'Docker', abbr: 'DK' },
  { name: 'GitHub Actions', abbr: 'GH' },
  { name: 'AWS', abbr: 'AWS' },
  { name: 'Azure', abbr: 'AZ' },
  { name: 'GitLab', abbr: 'GL' },
  { name: 'Helm', abbr: 'HM' },
]

export const TrustedBy = memo(function TrustedBy() {
  const prefersReducedMotion = useReducedMotion()
  const isMobile = useIsMobile()

  const allLogos = isMobile ? logos : [...logos, ...logos, ...logos]

  return (
    <section className="py-12 border-y border-white/[0.04] overflow-hidden" aria-label="Trusted by leading platforms">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <motion.p
          className="text-center text-sm text-slate-400 mb-8"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Supports the tools you already use
        </motion.p>
      </div>

      {isMobile ? (
        /* Static grid on mobile */
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {logos.map((logo, index) => (
              <motion.div
                key={logo.name}
                className="flex items-center gap-2 text-slate-400/60 hover:text-slate-400 transition-colors duration-200"
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05, duration: 0.4 }}
              >
                <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-xs font-mono font-medium">
                  {logo.abbr}
                </div>
                <span className="text-sm font-medium">{logo.name}</span>
              </motion.div>
            ))}
          </div>
        </div>
      ) : (
        /* Infinite scroll marquee on desktop */
        <div className="relative">
          {/* Fade edges */}
          <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-[#0B1020] to-transparent z-10 pointer-events-none" />
          <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-[#0B1020] to-transparent z-10 pointer-events-none" />

          <div
            className={`flex items-center gap-12 ${!prefersReducedMotion ? 'animate-infinite-scroll' : ''}`}
            style={{ width: 'max-content' }}
          >
            {allLogos.map((logo, index) => (
              <div
                key={`${logo.name}-${index}`}
                className="flex items-center gap-2.5 text-slate-400/50 hover:text-slate-300 transition-colors duration-300 cursor-default"
              >
                <div className="w-9 h-9 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center justify-center text-xs font-mono font-medium hover:border-primary/20 hover:bg-primary/[0.05] transition-all duration-300">
                  {logo.abbr}
                </div>
                <span className="text-sm font-medium whitespace-nowrap">{logo.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
})

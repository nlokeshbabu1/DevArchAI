import { Fragment, memo, useMemo, useState, useEffect } from 'react'
import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion'

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

function generateParticles(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: 1 + Math.random() * 1.2,
    opacity: 0.02 + Math.random() * 0.025,
    duration: 55 + Math.random() * 35,
    delay: Math.random() * 30,
    driftX: (Math.random() - 0.5) * 30,
    driftY: (Math.random() - 0.5) * 20,
  }))
}

function generateOrbs(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    x: 10 + Math.random() * 80,
    y: 10 + Math.random() * 80,
    size: 350 + Math.random() * 450,
    opacity: 0.012 + Math.random() * 0.018,
    duration: 40 + Math.random() * 25,
    driftX: (Math.random() - 0.5) * 80,
    driftY: (Math.random() - 0.5) * 50,
    hue: i % 2 === 0 ? '239' : '220',
  }))
}

const Particle = memo(function Particle({
  x, y, size, opacity, duration, delay, driftX, driftY, reduced,
}: {
  x: number; y: number; size: number; opacity: number; duration: number;
  delay: number; driftX: number; driftY: number; reduced: boolean;
}) {
  return (
    <motion.div
      className="absolute rounded-full bg-white"
      style={{ left: `${x}%`, top: `${y}%`, width: size, height: size, opacity }}
      animate={reduced ? undefined : { x: [0, driftX, 0], y: [0, driftY, 0] }}
      transition={{ duration, delay, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
})

const RadialOrb = memo(function RadialOrb({
  x, y, size, opacity, duration, driftX, driftY, hue, reduced,
}: {
  x: number; y: number; size: number; opacity: number; duration: number;
  driftX: number; driftY: number; hue: string; reduced: boolean;
}) {
  return (
    <motion.div
      className="absolute rounded-full blur-[140px]"
      style={{
        left: `${x}%`, top: `${y}%`, width: size, height: size,
        backgroundColor: `hsla(${hue}, 84%, 67%, ${opacity})`,
      }}
      animate={reduced ? undefined : { x: [0, driftX, 0], y: [0, driftY, 0] }}
      transition={{ duration, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
})

export const BackgroundGrid = memo(function BackgroundGrid() {
  const prefersReducedMotion = useReducedMotion()
  const isMobile = useIsMobile()

  const particleCount = isMobile ? 4 : 12
  const orbCount = isMobile ? 2 : 5

  const particles = useMemo(() => generateParticles(particleCount), [particleCount])
  const orbs = useMemo(() => generateOrbs(orbCount), [orbCount])

  const { scrollY } = useScroll()
  const parallaxY = useTransform(scrollY, [0, 800], [0, 80])

  return (
    <motion.div
      className="absolute inset-0 overflow-hidden pointer-events-none"
      style={{ y: prefersReducedMotion ? 0 : parallaxY }}
      aria-hidden="true"
    >
      {/* SVG noise filter for grain texture */}
      <svg className="absolute" style={{ width: 0, height: 0 }}>
        <defs>
          <filter id="noiseFilter">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.65"
              numOctaves="3"
              stitchTiles="stitch"
            />
            <feColorMatrix type="saturate" values="0" />
          </filter>
        </defs>
      </svg>

      {/* Fine dot grid overlay */}
      <div
        className="absolute inset-0"
        style={{
          opacity: isMobile ? 0.2 : 0.35,
          backgroundImage: 'radial-gradient(circle, rgba(148, 163, 184, 0.08) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Slow-moving ambient gradient */}
      <motion.div
        className="absolute inset-0"
        animate={prefersReducedMotion ? undefined : {
          background: [
            'radial-gradient(ellipse 60% 50% at 20% 40%, hsla(239, 84%, 67%, 0.03) 0%, transparent 70%)',
            'radial-gradient(ellipse 60% 50% at 70% 60%, hsla(239, 84%, 67%, 0.03) 0%, transparent 70%)',
            'radial-gradient(ellipse 60% 50% at 40% 30%, hsla(220, 80%, 60%, 0.025) 0%, transparent 70%)',
            'radial-gradient(ellipse 60% 50% at 20% 40%, hsla(239, 84%, 67%, 0.03) 0%, transparent 70%)',
          ],
        }}
        transition={{ duration: 28, repeat: Infinity, ease: 'linear' }}
      />

      {/* Aurora bands — Northern Lights effect */}
      {!isMobile && !prefersReducedMotion && (
        <Fragment>
          <motion.div
            className="absolute top-[8%] left-0 right-0 h-[35%] pointer-events-none"
            style={{
              background: 'linear-gradient(180deg, transparent 0%, hsla(239, 84%, 67%, 0.025) 30%, hsla(262, 83%, 58%, 0.02) 50%, transparent 100%)',
              filter: 'blur(60px)',
            }}
            animate={{
              opacity: [0.4, 0.8, 0.4],
              scaleY: [0.8, 1.1, 0.8],
              x: ['-5%', '5%', '-5%'],
            }}
            transition={{ duration: 24, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            className="absolute top-[12%] left-0 right-0 h-[25%] pointer-events-none"
            style={{
              background: 'linear-gradient(180deg, transparent 0%, hsla(189, 100%, 56%, 0.02) 40%, transparent 100%)',
              filter: 'blur(80px)',
            }}
            animate={{
              opacity: [0.3, 0.6, 0.3],
              scaleY: [1, 0.7, 1],
              x: ['5%', '-5%', '5%'],
            }}
            transition={{ duration: 30, repeat: Infinity, ease: 'easeInOut', delay: 4 }}
          />
        </Fragment>
      )}

      {/* Gradient mesh — multi-color ambient glow */}
      <div
        className="absolute inset-0 opacity-40"
        style={{
          background: `
            radial-gradient(ellipse 40% 30% at 15% 25%, hsla(239, 84%, 67%, 0.04) 0%, transparent 70%),
            radial-gradient(ellipse 35% 35% at 75% 70%, hsla(220, 80%, 60%, 0.03) 0%, transparent 70%),
            radial-gradient(ellipse 30% 25% at 50% 50%, hsla(262, 83%, 58%, 0.02) 0%, transparent 70%)
          `,
        }}
      />

      {/* Light beams — subtle diagonal sweep */}
      {!isMobile && !prefersReducedMotion && (
        <Fragment>
          <motion.div
            className="absolute top-0 left-0 w-[200px] h-[120%] -rotate-12 origin-top-left"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.03), transparent)',
            }}
            animate={{ x: ['-200px', 'calc(100vw + 200px)'] }}
            transition={{ duration: 18, repeat: Infinity, ease: 'linear', delay: 0 }}
          />
          <motion.div
            className="absolute top-0 left-0 w-[150px] h-[120%] -rotate-12 origin-top-left"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.02), transparent)',
            }}
            animate={{ x: ['calc(100vw + 200px)', '-200px'] }}
            transition={{ duration: 22, repeat: Infinity, ease: 'linear', delay: 6 }}
          />
        </Fragment>
      )}

      {/* Radial gradient orbs for depth */}
      {orbs.map((orb) => (
        <RadialOrb key={orb.id} {...orb} reduced={!!prefersReducedMotion} />
      ))}

      {/* Floating particles */}
      {particles.map((p) => (
        <Particle key={p.id} {...p} reduced={!!prefersReducedMotion} />
      ))}

      {/* Top-down gradient for depth */}
      <div
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(180deg, transparent 0%, rgba(3, 0, 20, 0.25) 50%, rgba(3, 0, 20, 0.5) 100%)',
        }}
      />

      {/* Layered radial vignette */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 80% 60% at 50% 50%, transparent 0%, rgba(3, 0, 20, 0.4) 100%)',
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 100% 100% at 50% 0%, transparent 30%, rgba(3, 0, 20, 0.6) 100%)',
        }}
      />

      {/* Grain texture overlay — SVG noise filter */}
      <div
        className="absolute inset-0 opacity-30 mix-blend-overlay"
        style={{ filter: 'url(#noiseFilter)' }}
      />

      {/* Decorative subtle lines */}
      {!isMobile && (
        <Fragment>
          <div className="absolute left-1/4 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-white/[0.02] to-transparent" />
          <div className="absolute right-1/4 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-white/[0.02] to-transparent" />
        </Fragment>
      )}
    </motion.div>
  )
})

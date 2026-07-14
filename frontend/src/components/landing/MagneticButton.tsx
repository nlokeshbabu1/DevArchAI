import { useRef, useCallback, type ReactNode, type MouseEvent } from 'react'
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from 'framer-motion'

interface MagneticButtonProps {
  children: ReactNode
  className?: string
  onClick?: () => void
  strength?: number
}

const springConfig = { stiffness: 300, damping: 20, mass: 0.5 }

export function MagneticButton({
  children,
  className = '',
  onClick,
  strength = 0.3,
}: MagneticButtonProps) {
  const ref = useRef<HTMLButtonElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const prefersReducedMotion = useReducedMotion()

  const springX = useSpring(x, springConfig)
  const springY = useSpring(y, springConfig)

  const glowOpacity = useTransform(
    [springX, springY],
    ([vx, vy]: number[]) => {
      const dist = Math.sqrt(vx * vx + vy * vy)
      return dist > 0.5 ? 1 : 0
    }
  )

  const handleMouseMove = useCallback((e: MouseEvent<HTMLButtonElement>) => {
    if (prefersReducedMotion || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    x.set((e.clientX - centerX) * strength)
    y.set((e.clientY - centerY) * strength)
  }, [x, y, strength, prefersReducedMotion])

  const handleMouseLeave = useCallback(() => {
    x.set(0)
    y.set(0)
  }, [x, y])

  return (
    <motion.button
      ref={ref}
      type="button"
      className={`relative focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 ${className}`}
      style={prefersReducedMotion ? undefined : { x: springX, y: springY }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      whileTap={prefersReducedMotion ? undefined : { scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
    >
      {/* Glow that follows cursor position */}
      {!prefersReducedMotion && (
        <motion.div
          className="absolute inset-0 rounded-[inherit] pointer-events-none"
          style={{
            opacity: glowOpacity,
            background: 'radial-gradient(circle at 50% 50%, hsl(239 84% 67% / 0.15), transparent 70%)',
          }}
        />
      )}
      <span className="relative z-10 flex items-center justify-center">{children}</span>
    </motion.button>
  )
}
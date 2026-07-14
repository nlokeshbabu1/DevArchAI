import { memo, useEffect, useState, useRef } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'

interface StatItem {
  label: string
  value: number
  suffix: string
}

const stats: StatItem[] = [
  { label: 'Repositories Analyzed', value: 10000, suffix: '+' },
  { label: 'Security Rules', value: 500, suffix: '+' },
  { label: 'Technologies', value: 40, suffix: '+' },
  { label: 'Avg. Scan Time', value: 30, suffix: 's' },
]

function formatValue(value: number, suffix: string): string {
  if (suffix === 's') return `< ${value}${suffix}`
  return `${value.toLocaleString()}${suffix}`
}

function AnimatedCounter({ value, suffix, inView }: { value: number; suffix: string; inView: boolean }) {
  const prefersReducedMotion = useReducedMotion()
  const [displayValue, setDisplayValue] = useState(0)

  useEffect(() => {
    if (!inView) return
    if (prefersReducedMotion) {
      setDisplayValue(value)
      return
    }

    const duration = 2000
    const startTime = Date.now()
    const startValue = 0

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 4)

      setDisplayValue(Math.floor(startValue + (value - startValue) * eased))

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [inView, value, prefersReducedMotion])

  return (
    <span className="tabular-nums">
      {suffix === 's' ? `< ${displayValue}` : displayValue.toLocaleString()}{suffix}
    </span>
  )
}

export const StatsSection = memo(function StatsSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section className="py-16 lg:py-20" ref={ref} aria-label="Key statistics">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-5xl mx-auto">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              className="text-center"
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: index * 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <p className="text-3xl md:text-4xl font-bold text-white tracking-tight">
                <AnimatedCounter value={stat.value} suffix={stat.suffix} inView={inView} />
              </p>
              <p className="text-sm text-slate-400 mt-2">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
})
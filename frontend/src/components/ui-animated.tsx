import { motion, AnimatePresence } from 'framer-motion'
import { Github, ChevronRight, CheckCircle, AlertCircle, RefreshCw, Clock, Play, Terminal } from 'lucide-react'
import { useEffect, useState } from 'react'

import { cn } from '../lib/utils'

// Re-export only used UI components
export { Skeleton, SkeletonCard } from './ui/Skeleton'
export { SeverityBadge } from './ui/severity-badge'

// ============================================================================
// Animated Score Circle with Framer Motion
// ============================================================================

interface ScoreCircleProps {
  score: number
  size?: 'sm' | 'md' | 'lg' | 'xl'
  showLabel?: boolean
  label?: string
  animated?: boolean
  delay?: number
}

export function ScoreCircle({
  score,
  size = 'lg',
  showLabel = true,
  label = 'Score',
  animated = true,
  delay = 0
}: ScoreCircleProps) {
  const [displayScore, setDisplayScore] = useState(0)

  const sizeConfig = {
    sm: { dim: 80, stroke: 6, text: 'text-2xl' },
    md: { dim: 120, stroke: 8, text: 'text-3xl' },
    lg: { dim: 180, stroke: 10, text: 'text-5xl' },
    xl: { dim: 220, stroke: 12, text: 'text-6xl' },
  }

  const { dim, stroke, text } = sizeConfig[size]
  const radius = (dim - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (score / 100) * circumference

  const getColor = (score: number) => {
    if (score >= 90) {return { text: 'text-green-400', stroke: 'stroke-green-400', glow: 'shadow-green-500/30', gradient: 'from-green-500 to-emerald-500' }}
    if (score >= 80) {return { text: 'text-blue-400', stroke: 'stroke-blue-400', glow: 'shadow-blue-500/30', gradient: 'from-blue-500 to-cyan-500' }}
    if (score >= 70) {return { text: 'text-yellow-400', stroke: 'stroke-yellow-400', glow: 'shadow-yellow-500/30', gradient: 'from-yellow-500 to-orange-500' }}
    if (score >= 60) {return { text: 'text-orange-400', stroke: 'stroke-orange-400', glow: 'shadow-orange-500/30', gradient: 'from-orange-500 to-red-500' }}
    return { text: 'text-red-400', stroke: 'stroke-red-400', glow: 'shadow-red-500/30', gradient: 'from-red-500 to-pink-500' }
  }

  const getGrade = (score: number) => {
    if (score >= 90) {return 'A'}
    if (score >= 80) {return 'B'}
    if (score >= 70) {return 'C'}
    if (score >= 60) {return 'D'}
    return 'F'
  }

  const colorClass = getColor(score)

  useEffect(() => {
    const timer = setTimeout(() => {
      if (animated) {
        const duration = 1500
        const startTime = Date.now()
        const startScore = 0

        const animateScore = () => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          const eased = 1 - Math.pow(1 - progress, 4)

          setDisplayScore(startScore + (score - startScore) * eased)

          if (progress < 1) {
            requestAnimationFrame(animateScore)
          }
        }

        requestAnimationFrame(animateScore)
      } else {
        setDisplayScore(score)
      }
    }, delay)

    return () => clearTimeout(timer)
  }, [score, animated, delay])

  return (
    <motion.div
      className="flex flex-col items-center gap-4"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay }}
    >
      <div className="relative" style={{ width: dim, height: dim }}>
        <motion.div
          className={cn(
            'absolute inset-0 rounded-full blur-2xl',
            colorClass.glow
          )}
          animate={{
            opacity: [0.3, 0.5, 0.3],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />

        <svg
          width={dim}
          height={dim}
          className="relative transform -rotate-90"
        >
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={stroke}
            fill="transparent"
            className="text-white/5"
          />
          <motion.circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={stroke}
            fill="transparent"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, ease: "easeOut", delay }}
            strokeLinecap="round"
            className={cn(colorClass.stroke)}
            style={{
              filter: `drop-shadow(0 0 6px currentColor)`,
            }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className={cn(text, 'font-bold', colorClass.text, 'drop-shadow-lg')}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: delay + 0.3 }}
          >
            {displayScore.toFixed(1)}
          </motion.span>
          <span className="text-sm text-muted-foreground mt-1">{label}</span>
        </div>
      </div>
      {showLabel && (
        <motion.div
          className={cn(
            'px-4 py-1.5 rounded-full text-sm font-bold',
            colorClass.text,
            'bg-white/10 border border-white/20',
            'backdrop-blur-sm'
          )}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: delay + 0.5 }}
        >
          Grade: {getGrade(score)}
        </motion.div>
      )}
    </motion.div>
  )
}

// ============================================================================
// Animated Card with Framer Motion
// ============================================================================

interface CardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
  glass?: boolean
  animate?: boolean
}

export function Card({ children, className, hover = true, padding = 'md', glass = true, animate = false }: CardProps) {
  const paddingConfig = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }

  const CardComponent = animate ? motion.div : 'div'

  const commonProps = {
    className: cn(
      glass
        ? 'bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30'
        : 'bg-card rounded-2xl border border-border/50 shadow-lg shadow-black/20',
      hover && 'transition-all duration-300 hover:border-white/20 hover:shadow-2xl hover:shadow-black/40 hover:-translate-y-1',
      'rounded-2xl',
      paddingConfig[padding],
      className
    ),
    ...(animate && {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      whileHover: hover ? { y: -4, scale: 1.02 } : {},
      transition: { duration: 0.3 }
    })
  }

  return (
    <CardComponent {...commonProps}>
      {children}
    </CardComponent>
  )
}

// ============================================================================
// Animated Button with Framer Motion
// ============================================================================

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: React.ReactNode
  glow?: boolean
  icon?: React.ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  children,
  className,
  disabled,
  glow = true,
  icon,
  ...props
}: ButtonProps) {
  const variantConfig = {
    primary: 'bg-primary text-primary-foreground shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/50 hover:scale-[1.02] active:scale-[0.98]',
    secondary: 'bg-white/5 text-foreground border border-white/10 hover:bg-white/10 hover:border-white/20 hover:scale-[1.02] active:scale-[0.98]',
    ghost: 'hover:bg-white/5 hover:text-foreground active:scale-[0.98]',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-lg shadow-destructive/30 hover:scale-[1.02] active:scale-[0.98]',
  }

  const sizeConfig = {
    sm: 'px-3 py-1.5 text-sm rounded-xl',
    md: 'px-4 py-2.5 text-base rounded-xl',
    lg: 'px-6 py-3 text-lg rounded-xl',
  }

  return (
    <button
      className={cn(
        'group relative inline-flex items-center justify-center gap-2 font-medium',
        'transition-all duration-300 ease-out',
        'will-change-transform',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
        variantConfig[variant],
        sizeConfig[size],
        glow && variant === 'primary' && 'pulse-glow',
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.svg
            key="spinner"
            className="animate-spin h-4 w-4"
            viewBox="0 0 24 24"
            initial={{ opacity: 0, rotate: 0 }}
            animate={{ opacity: 1, rotate: 360 }}
            exit={{ opacity: 0, rotate: 0 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </motion.svg>
        ) : (
          <>
            {icon && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              >
                {icon}
              </motion.span>
            )}
            <motion.span
              key="text"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {children}
            </motion.span>
          </>
        )}
      </AnimatePresence>
    </button>
  )
}

// ============================================================================
// Code Block with Syntax Highlighting Style
// ============================================================================

interface CodeBlockProps {
  code: string
  language?: string
  title?: string
  showLineNumbers?: boolean
}

export function CodeBlock({ code, language = 'terraform', title, showLineNumbers = true }: CodeBlockProps) {
  const lines = code.split('\n')

  return (
    <motion.div
      className="rounded-xl overflow-hidden border border-white/10 bg-black/40 backdrop-blur-sm"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {title && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-white/5">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium text-muted-foreground">{title}</span>
          </div>
          <span className="text-xs text-muted-foreground uppercase">{language}</span>
        </div>
      )}
      <div className="p-4 overflow-x-auto">
        <pre className="text-sm font-mono">
          <code>
            {lines.map((line, index) => (
              <motion.div
                key={index}
                className="flex"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: index * 0.02 }}
              >
                {showLineNumbers && (
                  <span className="text-muted-foreground select-none w-8 text-right pr-4 flex-shrink-0">
                    {index + 1}
                  </span>
                )}
                <span className="text-foreground">{line}</span>
              </motion.div>
            ))}
          </code>
        </pre>
      </div>
    </motion.div>
  )
}

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import { cn } from '../lib/utils'
import { AlertTriangle, AlertCircle, CheckCircle, Info, Shield, Zap, GitBranch, Brain, Rocket, FileCode, ArrowRight, Check, Github, BarChart3, Sparkles, Code, Layers, Lock, Bell, Settings, LogOut, User, ChevronRight, Search, Filter, Download, RefreshCw, Play, Clock, TrendingUp, Activity, Server, Database, Cloud, Terminal } from 'lucide-react'

// Re-export UI components
export { Skeleton, SkeletonCard, SkeletonTable, SkeletonChart, SkeletonStatCard } from './ui/Skeleton'
export { ScanningAnimation, LoadingDots, PulseGlow } from './ui/LoadingAnimation'
export { StatCard } from './ui/StatCard'

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
    if (score >= 90) return { text: 'text-green-400', stroke: 'stroke-green-400', glow: 'shadow-green-500/30', gradient: 'from-green-500 to-emerald-500' }
    if (score >= 80) return { text: 'text-blue-400', stroke: 'stroke-blue-400', glow: 'shadow-blue-500/30', gradient: 'from-blue-500 to-cyan-500' }
    if (score >= 70) return { text: 'text-yellow-400', stroke: 'stroke-yellow-400', glow: 'shadow-yellow-500/30', gradient: 'from-yellow-500 to-orange-500' }
    if (score >= 60) return { text: 'text-orange-400', stroke: 'stroke-orange-400', glow: 'shadow-orange-500/30', gradient: 'from-orange-500 to-red-500' }
    return { text: 'text-red-400', stroke: 'stroke-red-400', glow: 'shadow-red-500/30', gradient: 'from-red-500 to-pink-500' }
  }

  const getGrade = (score: number) => {
    if (score >= 90) return 'A'
    if (score >= 80) return 'B'
    if (score >= 70) return 'C'
    if (score >= 60) return 'D'
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
        {/* Animated glow effect */}
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

        {/* SVG Ring */}
        <svg
          width={dim}
          height={dim}
          className="relative transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={stroke}
            fill="transparent"
            className="text-white/5"
          />
          {/* Animated progress circle */}
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

        {/* Center content */}
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
// Animated Severity Badge
// ============================================================================

interface SeverityBadgeProps {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  animated?: boolean
}

export function SeverityBadge({ severity, size = 'md', showIcon = true, animated = false }: SeverityBadgeProps) {
  const config = {
    critical: {
      bg: 'bg-red-500/15',
      text: 'text-red-400',
      border: 'border-red-500/40',
      icon: AlertTriangle,
      glow: 'shadow-red-500/25'
    },
    high: {
      bg: 'bg-orange-500/15',
      text: 'text-orange-400',
      border: 'border-orange-500/40',
      icon: AlertCircle,
      glow: 'shadow-orange-500/25'
    },
    medium: {
      bg: 'bg-yellow-500/15',
      text: 'text-yellow-400',
      border: 'border-yellow-500/40',
      icon: AlertCircle,
      glow: 'shadow-yellow-500/25'
    },
    low: {
      bg: 'bg-green-500/15',
      text: 'text-green-400',
      border: 'border-green-500/40',
      icon: CheckCircle,
      glow: 'shadow-green-500/25'
    },
    info: {
      bg: 'bg-blue-500/15',
      text: 'text-blue-400',
      border: 'border-blue-500/40',
      icon: Info,
      glow: 'shadow-blue-500/25'
    },
  }

  const sizeConfig = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  }

  const iconSize = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }

  const { bg, text, border, icon: Icon, glow } = config[severity]

  return (
    <motion.span 
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium border',
        'backdrop-blur-sm',
        bg, text, border,
        `shadow-lg ${glow}`,
        sizeConfig[size]
      )}
      initial={animated ? { opacity: 0, scale: 0.8 } : {}}
      animate={animated ? { opacity: 1, scale: 1 } : {}}
      transition={{ duration: 0.2 }}
      whileHover={{ scale: 1.05 }}
    >
      {showIcon && <Icon className={iconSize[size]} />}
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </motion.span>
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
    primary: 'bg-primary text-primary-foreground shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/40',
    secondary: 'bg-white/5 text-foreground border border-white/10 hover:bg-white/10 hover:border-white/20',
    ghost: 'hover:bg-white/5 hover:text-foreground',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-lg shadow-destructive/30',
  }

  const sizeConfig = {
    sm: 'px-3 py-1.5 text-sm rounded-xl',
    md: 'px-4 py-2.5 text-base rounded-xl',
    lg: 'px-6 py-3 text-lg rounded-xl',
  }

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium',
        'transition-all duration-300',
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
// Feature Card with Icon
// ============================================================================

interface FeatureCardProps {
  icon: React.ElementType
  title: string
  description: string
  gradient: string
  borderColor: string
  iconBg: string
  delay?: number
}

export function FeatureCard({ icon: Icon, title, description, gradient, borderColor, iconBg, delay = 0 }: FeatureCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <Card
        className={cn(
          'p-6 bg-gradient-to-br h-full',
          gradient,
          borderColor,
          'hover:border-white/30'
        )}
        hover
        animate
      >
        <div className="space-y-3">
          <motion.div 
            className={cn(
              'p-3 rounded-xl w-fit border border-white/10 backdrop-blur-sm',
              iconBg
            )}
            whileHover={{ scale: 1.1, rotate: 5 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          >
            <Icon className="h-6 w-6 text-foreground" />
          </motion.div>
          <h3 className="text-lg font-semibold text-foreground">
            {title}
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {description}
          </p>
        </div>
      </Card>
    </motion.div>
  )
}

// ============================================================================
// How It Works Step
// ============================================================================

interface HowItWorksStepProps {
  step: string
  icon: React.ElementType
  title: string
  description: string
  index: number
  total: number
}

export function HowItWorksStep({ step, icon: Icon, title, description, index, total }: HowItWorksStepProps) {
  return (
    <motion.div
      className="flex items-start gap-6 p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10 hover:border-white/20 transition-all duration-300 relative"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
    >
      <div className="flex-shrink-0">
        <motion.div 
          className="relative"
          whileHover={{ scale: 1.05 }}
          transition={{ type: "spring", stiffness: 400, damping: 10 }}
        >
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center shadow-lg shadow-primary/30">
            <Icon className="h-8 w-8 text-white" />
          </div>
          <motion.div 
            className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-background border-2 border-primary flex items-center justify-center"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 15, delay: 0.2 + index * 0.1 }}
          >
            <span className="text-xs font-bold text-primary">{step}</span>
          </motion.div>
        </motion.div>
      </div>
      <div className="flex-1 pt-2">
        <h3 className="text-xl font-semibold text-foreground mb-2">
          {title}
        </h3>
        <p className="text-muted-foreground">
          {description}
        </p>
      </div>
      {index < total - 1 && (
        <motion.div 
          className="absolute left-12 top-20 w-0.5 h-8 bg-gradient-to-b from-primary/50 to-transparent hidden lg:block"
          initial={{ height: 0 }}
          animate={{ height: 32 }}
          transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
        />
      )}
    </motion.div>
  )
}

// ============================================================================
// Navigation Link Component
// ============================================================================

interface NavLinkProps {
  href: string
  icon: React.ElementType
  label: string
  active?: boolean
  onClick?: () => void
}

export function NavLink({ href, icon: Icon, label, active = false, onClick }: NavLinkProps) {
  return (
    <motion.a
      href={href}
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200',
        active 
          ? 'bg-primary/15 text-primary border border-primary/30' 
          : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
      )}
      whileHover={{ x: 4 }}
      whileTap={{ scale: 0.98 }}
    >
      <Icon className={cn("h-5 w-5", active ? 'text-primary' : 'text-muted-foreground')} />
      <span className="font-medium">{label}</span>
      {active && (
        <motion.div
          className="ml-auto"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          <ChevronRight className="h-4 w-4 text-primary" />
        </motion.div>
      )}
    </motion.a>
  )
}

// ============================================================================
// Repository Card Component
// ============================================================================

interface RepositoryCardProps {
  name: string
  description?: string
  lastScan?: string
  score?: number
  status: 'scanned' | 'scanning' | 'pending' | 'error'
  onScan?: () => void
  onView?: () => void
}

export function RepositoryCard({ name, description, lastScan, score, status, onScan, onView }: RepositoryCardProps) {
  const statusConfig = {
    scanned: { color: 'text-green-400', bg: 'bg-green-500/15', icon: CheckCircle },
    scanning: { color: 'text-blue-400', bg: 'bg-blue-500/15', icon: RefreshCw },
    pending: { color: 'text-yellow-400', bg: 'bg-yellow-500/15', icon: Clock },
    error: { color: 'text-red-400', bg: 'bg-red-500/15', icon: AlertCircle },
  }

  const StatusIcon = statusConfig[status].icon
  const scoreColor = score && score >= 80 ? 'text-green-400' : score && score >= 60 ? 'text-yellow-400' : 'text-red-400'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="p-6" hover animate={false}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="p-2.5 bg-white/5 rounded-xl border border-white/10">
              <Github className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-foreground truncate">{name}</h3>
              {description && (
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{description}</p>
              )}
            </div>
          </div>
          <div className={cn(
            'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
            statusConfig[status].bg,
            statusConfig[status].color
          )}>
            <StatusIcon className="h-3.5 w-3.5" />
            <span className="capitalize">{status}</span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-white/10">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              {lastScan || 'Never scanned'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {onView && (
              <Button variant="ghost" size="sm" onClick={onView}>
                View
              </Button>
            )}
            {onScan && status !== 'scanning' && (
              <Button variant="primary" size="sm" onClick={onScan} icon={<Play className="h-3.5 w-3.5" />}>
                Scan
              </Button>
            )}
          </div>
        </div>
      </Card>
    </motion.div>
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

// ============================================================================
// Export all icons for convenience
// ============================================================================

export {
  Shield, Zap, GitBranch, BarChart3, Sparkles, Check, ArrowRight, Github, 
  FileCode, Brain, Rocket, Code, Layers, Lock, Bell, Settings, LogOut, 
  User, ChevronRight, Search, Filter, Download, RefreshCw, Play, Clock, 
  TrendingUp, Activity, Server, Database, Cloud, Terminal,
  AlertTriangle, AlertCircle, CheckCircle, Info
}

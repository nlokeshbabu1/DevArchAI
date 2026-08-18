import { useEffect, useState } from 'react'
import { cn, sanitizePath } from '../lib/utils'
import { SeverityBadge } from './ui/severity-badge'

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
  const [isAnimating, setIsAnimating] = useState(animated)
  
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
    if (score >= 90) return { text: 'text-green-400', stroke: 'stroke-green-400', glow: 'shadow-green-500/30' }
    if (score >= 80) return { text: 'text-blue-400', stroke: 'stroke-blue-400', glow: 'shadow-blue-500/30' }
    if (score >= 70) return { text: 'text-yellow-400', stroke: 'stroke-yellow-400', glow: 'shadow-yellow-500/30' }
    if (score >= 60) return { text: 'text-orange-400', stroke: 'stroke-orange-400', glow: 'shadow-orange-500/30' }
    return { text: 'text-red-400', stroke: 'stroke-red-400', glow: 'shadow-red-500/30' }
  }
  
  const getGrade = (score: number) => {
    if (score >= 90) return 'A'
    if (score >= 80) return 'B'
    if (score >= 70) return 'C'
    if (score >= 60) return 'D'
    return 'F'
  }
  
  const colorClass = getColor(score)
  
  // Animate score counting
  useEffect(() => {
    const timer = setTimeout(() => {
      if (animated) {
        setIsAnimating(true)
        const duration = 1500
        const startTime = Date.now()
        const startScore = 0
        
        const animateScore = () => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          const eased = 1 - Math.pow(1 - progress, 4) // Ease out quart
          
          setDisplayScore(startScore + (score - startScore) * eased)
          
          if (progress < 1) {
            requestAnimationFrame(animateScore)
          } else {
            setIsAnimating(false)
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
    <div className="flex flex-col items-center gap-4" role="img" aria-label={`${label}: ${displayScore.toFixed(1)} out of 100, Grade ${getGrade(score)}`}>
      <div className="relative" style={{ width: dim, height: dim }}>
        {/* Glow effect behind */}
        <div 
          className={cn(
            'absolute inset-0 rounded-full blur-2xl transition-opacity duration-1000',
            colorClass.glow,
            isAnimating ? 'opacity-50' : 'opacity-30'
          )}
        />
        
        {/* SVG Ring */}
        <svg
          width={dim}
          height={dim}
          className="relative transform"
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
          {/* Progress circle */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={stroke}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={isAnimating ? circumference : strokeDashoffset}
            strokeLinecap="round"
            className={cn(
              colorClass.stroke,
              'transition-all duration-1000 ease-out',
              animated && 'score-ring'
            )}
            style={{
              filter: `drop-shadow(0 0 6px currentColor)`,
              animationDelay: `${delay}ms`
            }}
          />
        </svg>
        
        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn(
            text, 
            'font-bold', 
            colorClass.text,
            'score-number',
            'drop-shadow-lg'
          )}>
            {displayScore.toFixed(1)}
          </span>
          <span className="text-sm text-muted-foreground mt-1">{label}</span>
        </div>
      </div>
      {showLabel && (
        <div className={cn(
          'px-4 py-1.5 rounded-full text-sm font-bold',
          colorClass.text,
          'bg-white/10 border border-white/20',
          'backdrop-blur-sm',
          'animate-fade-in-delayed'
        )}>
          Grade: {getGrade(score)}
        </div>
      )}
    </div>
  )
}

export { SeverityBadge } from './ui/severity-badge'

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline' | 'secondary'
  className?: string
  children: React.ReactNode
}

export function Badge({ variant = 'default', className, children, ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variant === 'default' && 'bg-primary text-primary-foreground hover:bg-primary/80',
        variant === 'outline' && 'border border-white/10 bg-white/5 text-foreground',
        variant === 'secondary' && 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

interface ProgressProps {
  value?: number
  className?: string
  max?: number
}

export function Progress({ value = 0, className, max = 100 }: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))
  
  return (
    <div className={cn('relative h-4 w-full overflow-hidden rounded-full bg-white/10', className)}>
      <div
        className="h-full bg-primary transition-all duration-500 ease-in-out"
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

interface CardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
  glass?: boolean
}

export function Card({ children, className, hover = true, padding = 'md', glass = true }: CardProps) {
  const paddingConfig = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }

  return (
    <div className={cn(
      glass
        ? 'bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30'
        : 'bg-card rounded-2xl border border-border/50 shadow-lg shadow-black/20',
      hover && 'transition-all duration-300 hover:border-white/20 hover:shadow-2xl hover:shadow-black/40 hover:-translate-y-1',
      'rounded-2xl',
      paddingConfig[padding],
      className
    )}>
      {children}
    </div>
  )
}
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: React.ReactNode
  glow?: boolean
}

export function Button({ 
  variant = 'primary', 
  size = 'md', 
  loading = false, 
  children, 
  className,
  disabled,
  glow = true,
  ...props 
}: ButtonProps) {
  const variantConfig = {
    primary: 'bg-primary text-primary-foreground shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/40 hover:-translate-y-0.5',
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
        'transition-all duration-300 cubic-bezier(0.4, 0, 0.2, 1)',
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
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {children}
    </button>
  )
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  icon?: React.ReactNode
  error?: string
}

export function Input({ label, icon, error, className, ...props }: InputProps) {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-muted-foreground mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </div>
        )}
        <input
          className={cn(
            'w-full px-4 py-2.5 rounded-xl',
            'bg-white/5 border border-white/10',
            'text-foreground placeholder:text-muted-foreground',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
            'focus:bg-white/10 focus:border-primary/50',
            'transition-all duration-200',
            error && 'border-destructive focus:ring-destructive',
            icon && 'pl-10',
            className
          )}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-1.5 text-sm text-destructive">{error}</p>
      )}
    </div>
  )
}

interface FindingCardProps {
  ruleId: string
  ruleName: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  filePath?: string
  expanded?: boolean
  onToggle?: () => void
  aiExplanation?: string
  impactAnalysis?: string
  suggestedFix?: string
}

export function FindingCard({
  ruleId,
  ruleName,
  severity,
  category,
  description,
  recommendation,
  filePath,
  expanded = false,
  onToggle,
  aiExplanation,
  impactAnalysis,
  suggestedFix,
}: FindingCardProps) {
  return (
    <div className={cn(
      'border-b border-white/10 last:border-0',
      'transition-colors duration-150'
    )}>
      <div
        className={cn(
          'p-4 cursor-pointer',
          'hover:bg-white/5',
          'transition-colors duration-150'
        )}
        onClick={onToggle}
      >
        <div className="flex items-start gap-3">
          <SeverityBadge severity={severity} size="sm" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-foreground">{ruleName}</span>
              <span className="text-xs text-muted-foreground font-mono">{ruleId}</span>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">{description}</p>
            {filePath && (
              <p className="text-xs text-muted-foreground mt-2 font-mono">
                📁 {sanitizePath(filePath)}
              </p>
            )}
          </div>
          <svg
            className={cn(
              'h-5 w-5 text-muted-foreground transition-transform duration-200',
              expanded && 'rotate-180'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expandable content */}
      <div className={cn(
        'overflow-hidden transition-all duration-300 ease-in-out',
        expanded ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'
      )}>
        <div className="px-4 pb-4 pt-2 space-y-4">
          {/* Basic Info */}
          <div className="p-4 bg-white/5 rounded-lg border border-white/10">
            <div className="space-y-3">
              <div>
                <span className="text-sm font-medium text-foreground">Category: </span>
                <span className="text-sm text-muted-foreground capitalize">{category}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-foreground">Recommendation: </span>
                <p className="text-sm text-muted-foreground mt-1">{recommendation}</p>
              </div>
            </div>
          </div>

          {/* AI Explanation */}
          {aiExplanation && (
            <div className="p-4 bg-gradient-to-br from-primary/10 to-indigo-600/10 rounded-lg border border-primary/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-primary/20 rounded-lg">
                  <svg className="h-4 w-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-primary">AI Explanation</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{aiExplanation}</p>
            </div>
          )}

          {/* Impact Analysis */}
          {impactAnalysis && (
            <div className="p-4 bg-orange-500/10 rounded-lg border border-orange-500/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-orange-500/20 rounded-lg">
                  <svg className="h-4 w-4 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-orange-400">Impact Analysis</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{impactAnalysis}</p>
            </div>
          )}

          {/* Suggested Fix */}
          {suggestedFix && (
            <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-green-500/20 rounded-lg">
                  <svg className="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-green-400">Suggested Fix</span>
              </div>
              <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono bg-black/20 p-3 rounded-lg overflow-x-auto">
                {suggestedFix}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
export { StatCard } from './ui/StatCard'

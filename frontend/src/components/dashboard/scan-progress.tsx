import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'
import { CheckCircle, Loader2, AlertCircle } from 'lucide-react'

interface ScanProgressProps {
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed'
  progress?: number
  currentStep?: string
  className?: string
}

export function ScanProgress({
  status,
  progress = 0,
  currentStep,
  className,
}: ScanProgressProps) {
  const steps = [
    { id: 'queued', label: 'Queued', icon: Loader2 },
    { id: 'processing', label: 'Scanning', icon: Loader2 },
    { id: 'completed', label: 'Complete', icon: CheckCircle },
  ]

  const currentStepIndex = steps.findIndex(s => s.id === status)

  return (
    <div className={cn('space-y-6', className)}>
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Scan Progress</span>
          <span className="text-foreground font-medium">{progress}%</span>
        </div>
        <div className="relative h-2 bg-white/10 rounded-full overflow-hidden">
          <motion.div
            className="absolute inset-y-0 left-0 bg-primary rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const StepIcon = step.icon
          const isCompleted = index < currentStepIndex || status === 'completed'
          const isCurrent = index === currentStepIndex && status !== 'completed' && status !== 'failed'
          const isPending = index > currentStepIndex || status === 'failed'

          return (
            <div key={step.id} className="flex flex-col items-center gap-2">
              <div className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center border-2',
                'transition-all duration-300',
                isCompleted && 'bg-green-500/15 border-green-500/40 text-green-400',
                isCurrent && 'bg-primary/15 border-primary/40 text-primary animate-pulse',
                isPending && 'bg-white/5 border-white/10 text-muted-foreground'
              )}>
                {isCompleted ? (
                  <CheckCircle className="h-5 w-5" />
                ) : isCurrent ? (
                  <StepIcon className="h-5 w-5 animate-spin" />
                ) : (
                  <StepIcon className="h-5 w-5" />
                )}
              </div>
              <span className={cn(
                'text-xs font-medium',
                isCompleted && 'text-green-400',
                isCurrent && 'text-primary',
                isPending && 'text-muted-foreground'
              )}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Current Step */}
      {currentStep && status === 'processing' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-primary/10 border border-primary/30 rounded-xl"
        >
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-primary animate-spin" />
            <span className="text-sm text-primary">{currentStep}</span>
          </div>
        </motion.div>
      )}

      {/* Failed State */}
      {status === 'failed' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <span className="text-sm text-red-400">Scan failed. Please try again.</span>
          </div>
        </motion.div>
      )}
    </div>
  )
}

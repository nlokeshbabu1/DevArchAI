import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckCircle, 
  Loader2, 
  Circle, 
  GitBranch, 
  Server, 
  FileCode, 
  Shield, 
  Brain, 
  BarChart3,
  Terminal,
  Clock
} from 'lucide-react'
import { Card } from './ui-animated'
import { cn } from '../lib/utils'

interface ScanStep {
  key: string
  label: string
  icon: any
  estimatedDuration: number // milliseconds
}

interface ScanLog {
  message: string
  timestamp: string
  type: 'info' | 'success' | 'warning'
}

interface ScanProgressProps {
  progress: number
  currentStep: number
  isComplete: boolean
}

const SCAN_STEPS: ScanStep[] = [
  {
    key: 'clone',
    label: 'Cloning repository',
    icon: GitBranch,
    estimatedDuration: 3000
  },
  {
    key: 'detect',
    label: 'Detecting DevOps stack',
    icon: Server,
    estimatedDuration: 2000
  },
  {
    key: 'parse',
    label: 'Parsing infrastructure files',
    icon: FileCode,
    estimatedDuration: 3000
  },
  {
    key: 'rules',
    label: 'Running security rules',
    icon: Shield,
    estimatedDuration: 4000
  },
  {
    key: 'ai',
    label: 'Generating AI suggestions',
    icon: Brain,
    estimatedDuration: 3000
  },
  {
    key: 'score',
    label: 'Calculating DevOps score',
    icon: BarChart3,
    estimatedDuration: 2000
  },
]

const SAMPLE_LOGS: Record<string, string[]> = {
  clone: [
    'Connecting to GitHub...',
    'Repository found: nlokeshbabu1/Terraform',
    'Cloning main branch...',
    '✓ Repository cloned successfully',
  ],
  detect: [
    'Scanning repository structure...',
    'Found Dockerfile',
    'Found terraform/.tf files',
    'Detected: Docker, Terraform',
  ],
  parse: [
    'Parsing Dockerfile...',
    'Parsing Terraform configurations...',
    'Analyzing Kubernetes manifests...',
    '✓ 15 files parsed successfully',
  ],
  rules: [
    'Loading security rule engine...',
    'Running 39 security rules...',
    'Checking CIS benchmarks...',
    '✓ 14 issues detected',
  ],
  ai: [
    'Analyzing findings...',
    'Generating AI recommendations...',
    'Prioritizing critical issues...',
    '✓ AI suggestions generated',
  ],
  score: [
    'Calculating security score...',
    'Computing category scores...',
    '✓ Analysis complete',
  ],
}

function StepItem({ 
  step, 
  status, 
  index 
}: { 
  step: ScanStep
  status: 'completed' | 'active' | 'pending'
  index: number
}) {
  const Icon = step.icon
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border transition-all duration-500',
        status === 'completed' && 'bg-green-500/10 border-green-500/30',
        status === 'active' && 'bg-primary/15 border-primary/30 shadow-lg shadow-primary/10',
        status === 'pending' && 'bg-white/5 border-white/10'
      )}
    >
      <div className={cn(
        'p-2 rounded-lg transition-all duration-300',
        status === 'completed' && 'bg-green-500/20',
        status === 'active' && 'bg-primary/20',
        status === 'pending' && 'bg-white/10'
      )}>
        <AnimatePresence mode="wait">
          {status === 'completed' ? (
            <motion.div
              key="check"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <CheckCircle className="h-4 w-4 text-green-400" />
            </motion.div>
          ) : status === 'active' ? (
            <motion.div
              key="spinner"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <Loader2 className="h-4 w-4 text-primary animate-spin" />
            </motion.div>
          ) : (
            <motion.div
              key="circle"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <Circle className="h-4 w-4 text-muted-foreground" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      <span className={cn(
        'text-sm font-medium transition-all duration-300',
        status === 'completed' && 'text-green-400',
        status === 'active' && 'text-primary',
        status === 'pending' && 'text-muted-foreground'
      )}>
        {step.label}
      </span>
      
      {status === 'active' && (
        <motion.div
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          className="ml-auto"
        >
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>{Math.ceil(step.estimatedDuration / 1000)}s</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

function ScanLogs({ logs }: { logs: ScanLog[] }) {
  const logsEndRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])
  
  return (
    <Card className="p-4 bg-black/50 border-white/10" hover={false}>
      <div className="flex items-center gap-2 mb-3">
        <Terminal className="h-4 w-4 text-muted-foreground" />
        <h4 className="text-sm font-semibold text-foreground">Scan Logs</h4>
      </div>
      
      <div className="h-40 overflow-y-auto font-mono text-xs space-y-1">
        <AnimatePresence>
          {logs.map((log, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className={cn(
                'flex items-start gap-2',
                log.type === 'success' && 'text-green-400',
                log.type === 'warning' && 'text-yellow-400',
                log.type === 'info' && 'text-gray-400'
              )}
            >
              <span className="text-muted-foreground flex-shrink-0">
                [{log.timestamp}]
              </span>
              <span>{log.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={logsEndRef} />
      </div>
    </Card>
  )
}

export function ScanProgress({ progress, currentStep, isComplete }: ScanProgressProps) {
  const [logs, setLogs] = useState<ScanLog[]>([])
  const [estimatedTime, setEstimatedTime] = useState(10)
  
  // Generate logs based on current step
  useEffect(() => {
    if (isComplete) return
    
    const currentStepKey = SCAN_STEPS[currentStep]?.key
    if (!currentStepKey) return
    
    const stepLogs = SAMPLE_LOGS[currentStepKey] || []
    
    // Add logs one by one with delay
    stepLogs.forEach((logMessage, index) => {
      setTimeout(() => {
        const log: ScanLog = {
          message: logMessage,
          timestamp: new Date().toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          }),
          type: logMessage.startsWith('✓') ? 'success' : 'info',
        }
        
        setLogs(prev => [...prev, log])
      }, index * 800)
    })
  }, [currentStep, isComplete])
  
  // Update estimated time
  useEffect(() => {
    if (isComplete) {
      setEstimatedTime(0)
      return
    }
    
    const remainingSteps = SCAN_STEPS.slice(currentStep)
    const totalRemaining = remainingSteps.reduce(
      (acc, step) => acc + step.estimatedDuration, 
      0
    )
    
    setEstimatedTime(Math.ceil(totalRemaining / 1000))
  }, [currentStep, isComplete])
  
  const getStepStatus = (index: number): 'completed' | 'active' | 'pending' => {
    if (isComplete) return 'completed'
    if (index < currentStep) return 'completed'
    if (index === currentStep) return 'active'
    return 'pending'
  }
  
  return (
    <Card className="p-8 glow-primary animate-scale-in" hover={false}>
      <div className="space-y-6">
        {/* Header */}
        <motion.div 
          className="text-center space-y-2"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-4">
            <AnimatePresence mode="wait">
              {isComplete ? (
                <motion.div
                  key="success"
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  exit={{ scale: 0 }}
                  transition={{ type: 'spring', duration: 0.5 }}
                >
                  <CheckCircle className="h-8 w-8 text-white" />
                </motion.div>
              ) : (
                <motion.div
                  key="scanning"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                >
                  <GitBranch className="h-8 w-8 text-white animate-pulse" />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          <motion.h3 
            className="text-2xl font-bold text-foreground"
            key={isComplete ? 'complete' : 'scanning'}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {isComplete ? 'Analysis Complete!' : 'Analyzing Repository'}
          </motion.h3>
          
          <p className="text-muted-foreground">
            {isComplete
              ? 'Your security report is ready'
              : `Estimated time remaining: ${estimatedTime}s`}
          </p>
        </motion.div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium text-primary">{progress.toFixed(0)}%</span>
          </div>
          <div className="h-3 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-primary via-indigo-500 to-primary rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>
        </div>

        {/* Scan Steps */}
        <div className="space-y-2">
          {SCAN_STEPS.map((step, index) => (
            <StepItem
              key={step.key}
              step={step}
              status={getStepStatus(index)}
              index={index}
            />
          ))}
        </div>

        {/* Live Logs */}
        {!isComplete && logs.length > 0 && (
          <ScanLogs logs={logs} />
        )}

        {/* Completion Message */}
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-lg bg-green-500/10 border border-green-500/30"
          >
            <div className="flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <div>
                <p className="font-medium text-green-400">Scan completed successfully</p>
                <p className="text-sm text-muted-foreground">
                  Found {SCAN_STEPS.length} steps completed • Ready to view results
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </Card>
  )
}

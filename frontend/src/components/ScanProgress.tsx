import { useMemo, useRef, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle, GitBranch, Terminal, FileCode, Loader2,
  FileText, Cpu, Shield, Brain, Search, AlertTriangle
} from 'lucide-react'
import { cn } from '../lib/utils'

const STAGES = [
  { name: 'Connecting Repository', icon: GitBranch },
  { name: 'Cloning Repository', icon: GitBranch },
  { name: 'Detecting Technologies', icon: Cpu },
  { name: 'Scanning Files', icon: Search },
  { name: 'Running Security Rules', icon: Shield },
  { name: 'Running AI Analysis', icon: Brain },
  { name: 'Generating Reports', icon: FileText },
  { name: 'Completed', icon: CheckCircle },
]

const BACKEND_STEP_TO_STAGES: Record<number, number[]> = {
  1: [0], 2: [1], 3: [2], 4: [3, 4], 5: [5], 6: [6],
}

interface ScanLog {
  message: string
  timestamp: string
  type: 'info' | 'success' | 'warning'
}

interface FileBeingScanned {
  path: string
  type: 'docker' | 'k8s' | 'terraform' | 'cicd' | 'helm' | 'monitoring'
  status: 'pending' | 'scanning' | 'completed'
}

interface ScanProgressProps {
  progress: number
  currentStep: number
  isComplete: boolean
  detectedFiles?: FileBeingScanned[]
  detectedTechnologies?: string[]
  steps?: string[]
  backendLogs?: string[]
  filesScanned?: number
  findingsDetected?: number
}

function useStageStates(currentStep: number, isComplete: boolean) {
  return useMemo(() => {
    const states = Array(8).fill('pending') as ('pending' | 'running' | 'completed')[]
    if (isComplete || currentStep > 6) return states.fill('completed')
    if (currentStep <= 0) return states

    const active = BACKEND_STEP_TO_STAGES[currentStep] || []
    if (active.length === 0) return states

    const minActive = Math.min(...active)
    const maxActive = Math.max(...active)

    for (let i = 0; i < 8; i++) {
      if (i < minActive) states[i] = 'completed'
      else if (i >= minActive && i <= maxActive) states[i] = 'running'
    }
    return states
  }, [currentStep, isComplete])
}

export function ScanProgress({
  progress,
  currentStep,
  isComplete,
  detectedFiles = [],
  detectedTechnologies = [],
  backendLogs = [],
  filesScanned,
  findingsDetected = 0,
}: ScanProgressProps) {
  const [logs, setLogs] = useState<ScanLog[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const stageStates = useStageStates(currentStep, isComplete)

  const currentStageName = useMemo(() => {
    const idx = stageStates.findIndex(s => s === 'running')
    return idx >= 0 ? STAGES[idx].name : ''
  }, [stageStates])

  const scannedCount = filesScanned ?? detectedFiles.length
  const techCount = detectedTechnologies.length

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  useEffect(() => {
    if (!backendLogs || backendLogs.length === 0) return

    const parsedLogs = backendLogs.map(log => {
      const match = log.match(/^\[([^\]]+)\]\s+(.+)$/)
      if (match) {
        return {
          timestamp: match[1],
          message: match[2],
          type: match[2].includes('✓') || match[2].includes('success') || match[2].includes('completed') ? 'success' as const :
                match[2].includes('warning') || match[2].includes('Warning') ? 'warning' as const :
                'info' as const
        }
      }
      return {
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
        }),
        message: log,
        type: 'info' as const
      }
    })

    setLogs(parsedLogs)
  }, [backendLogs])

  const statusText = isComplete
    ? 'Your security report is ready'
    : currentStageName || 'Preparing scan...'

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      {/* Header */}
      <motion.div
        className="text-center mb-6"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="inline-flex p-3 rounded-xl bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/20 mb-3">
          <AnimatePresence mode="wait">
            {isComplete ? (
              <motion.div key="success" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                <CheckCircle className="h-8 w-8 text-green-400" />
              </motion.div>
            ) : (
              <motion.div key="scanning" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                <GitBranch className="h-8 w-8 text-primary animate-pulse" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <motion.h3
          className="text-2xl font-semibold text-foreground mb-1"
          key={isComplete ? 'complete' : 'scanning'}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {isComplete ? 'Analysis Complete' : 'Analyzing Repository'}
        </motion.h3>

        <p className="text-muted-foreground text-sm">{statusText}</p>
      </motion.div>

      {/* Stats Bar */}
      <motion.div
        className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <StatCard
          label="Current Stage"
          value={isComplete ? 'Complete' : currentStageName || 'Starting...'}
          icon={FileCode}
          highlight={!isComplete}
        />
        <StatCard label="Files Scanned" value={scannedCount} icon={Search} />
        <StatCard label="Technologies" value={techCount} icon={Cpu} />
        <StatCard label="Findings" value={findingsDetected} icon={AlertTriangle} />
      </motion.div>

      {/* Stage Timeline */}
      <motion.div
        className="mb-6 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <div className="flex items-center gap-0 min-w-[640px]">
          {STAGES.map((stage, i) => {
            const state = stageStates[i]
            const Icon = stage.icon
            const isActive = state === 'running'
            const isDone = state === 'completed'
            const isLast = i === STAGES.length - 1

            return (
              <div key={stage.name} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1.5">
                  <div className={cn(
                    'relative w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300',
                    isDone && 'bg-green-500/20 text-green-400 border border-green-400/30',
                    isActive && 'bg-primary/20 text-primary border border-primary/40 shadow-lg shadow-primary/20',
                    !isDone && !isActive && 'bg-white/5 text-muted-foreground border border-white/10'
                  )}>
                    {isDone ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : isActive ? (
                      <div className="relative">
                        <Icon className="h-4 w-4" />
                        <span className="absolute -inset-1 rounded-full animate-ping bg-primary/20" />
                      </div>
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>
                  <span className={cn(
                    'text-[10px] leading-tight text-center whitespace-nowrap transition-colors duration-300',
                    isDone && 'text-green-400/80',
                    isActive && 'text-foreground font-medium',
                    !isDone && !isActive && 'text-muted-foreground/60'
                  )}>
                    {stage.name}
                  </span>
                </div>

                {!isLast && (
                  <div className="flex-1 h-px mx-2 relative">
                    <div className="absolute inset-0 bg-white/10 rounded-full" />
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-r from-primary to-indigo-500 rounded-full"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: isDone ? 1 : 0 }}
                      style={{ transformOrigin: 'left' }}
                      transition={{ duration: 0.5, ease: 'easeOut' }}
                    />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </motion.div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-muted-foreground">Overall Progress</span>
          <span className="font-semibold text-foreground">{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary to-indigo-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Logs Panel */}
      <div className="bg-black/40 rounded-lg border border-white/10">
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5">
          <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">Live Logs</span>
          {logs.length > 0 && (
            <span className="ml-auto text-[10px] text-muted-foreground/60">{logs.length} entries</span>
          )}
        </div>
        <div className="h-56 overflow-y-auto font-mono text-xs space-y-0.5 p-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
          <AnimatePresence initial={false}>
            {logs.map((log, i) => (
              <motion.div
                key={`${log.timestamp}-${log.message}-${i}`}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15 }}
                className={cn(
                  'flex items-start gap-2 py-1 px-2 rounded hover:bg-white/[0.02]',
                  log.type === 'success' ? 'text-green-400/80' :
                  log.type === 'warning' ? 'text-yellow-400/80' :
                  'text-gray-400'
                )}
              >
                <span className="text-white/15 flex-shrink-0 text-[10px] w-16">{log.timestamp}</span>
                <span className="flex-1 truncate">{log.message}</span>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={logsEndRef} />
          {logs.length === 0 && (
            <div className="flex items-center justify-center h-full text-muted-foreground text-xs">
              <Loader2 className="h-3 w-3 animate-spin mr-2" />
              Waiting for logs...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon: Icon, highlight }: {
  label: string
  value: string | number
  icon: React.ElementType
  highlight?: boolean
}) {
  return (
    <div className={cn(
      'rounded-lg border p-3 transition-all duration-300',
      highlight
        ? 'bg-primary/[0.06] border-primary/20'
        : 'bg-white/[0.03] border-white/10'
    )}>
      <div className="flex items-center gap-2 mb-1.5">
        <Icon className={cn(
          'h-3 w-3',
          highlight ? 'text-primary' : 'text-muted-foreground'
        )} />
        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{label}</span>
      </div>
      <span className={cn(
        'text-sm font-semibold block truncate',
        highlight ? 'text-foreground' : 'text-foreground/80'
      )}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </span>
    </div>
  )
}

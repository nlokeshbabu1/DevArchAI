import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, GitBranch, Terminal } from 'lucide-react'
import { Card } from './ui-animated'

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

export function ScanProgress({ progress, currentStep, isComplete }: ScanProgressProps) {
  const [logs, setLogs] = useState<ScanLog[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Generate realistic scan logs based on progress
  useEffect(() => {
    if (isComplete) return

    const addLog = (message: string, type: 'info' | 'success' | 'warning' = 'info') => {
      const timestamp = new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
      
      setLogs(prev => {
        // Prevent duplicate logs
        const isDuplicate = prev.some(log => log.message === message)
        if (isDuplicate) return prev
        
        return [...prev, { message, timestamp, type }]
      })
    }

    // Progress-based log generation
    if (progress < 10) {
      addLog('Initializing scan...', 'info')
    } else if (progress < 20) {
      addLog('Connecting to GitHub...', 'info')
    } else if (progress < 30) {
      addLog('Repository found', 'success')
    } else if (progress < 40) {
      addLog('Cloning repository...', 'info')
    } else if (progress < 50) {
      addLog('✓ Repository cloned successfully', 'success')
    } else if (progress < 60) {
      addLog('Detecting technologies...', 'info')
    } else if (progress < 70) {
      addLog('Found Dockerfile', 'success')
    } else if (progress < 75) {
      addLog('Found Terraform files', 'success')
    } else if (progress < 80) {
      addLog('Running security rules...', 'info')
    } else if (progress < 85) {
      addLog('Analyzing findings...', 'info')
    } else if (progress < 90) {
      addLog('Generating AI suggestions...', 'info')
    } else if (progress < 95) {
      addLog('Calculating security score...', 'info')
    } else if (progress < 100) {
      addLog('Finalizing results...', 'info')
    }

  }, [progress, isComplete])

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
              : 'Please wait while we scan your infrastructure'}
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

        {/* Live Logs */}
        <Card className="p-4 bg-black/50 border-white/10" hover={false}>
          <div className="flex items-center gap-2 mb-3">
            <Terminal className="h-4 w-4 text-muted-foreground" />
            <h4 className="text-sm font-semibold text-foreground">Live Scan Logs</h4>
          </div>

          <div className="h-48 overflow-y-auto font-mono text-xs space-y-1">
            <AnimatePresence>
              {logs.map((log, index) => (
                <motion.div
                  key={`${log.timestamp}-${log.message}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`flex items-start gap-2 ${
                    log.type === 'success' ? 'text-green-400' :
                    log.type === 'warning' ? 'text-yellow-400' :
                    'text-gray-400'
                  }`}
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
                  Ready to view results
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </Card>
  )
}

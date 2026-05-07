import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, GitBranch, Terminal, FileCode, Loader2, Layers, FileText, Cpu } from 'lucide-react'
import { cn } from '../lib/utils'
import { Tabs } from './ui/Tabs'

// Helper function to convert absolute paths to relative paths
function convertToRelativePath(filePath: string): string {
  const parts = filePath.split('/')
  const repoIndex = parts.findIndex(part =>
    part.startsWith('scan-') || part === 'tmp' || part === 'repos' || part === 'workspace'
  )

  if (repoIndex !== -1 && repoIndex < parts.length - 1) {
    return parts.slice(repoIndex + 1).join('/')
  }

  const commonPatterns = [
    'terraform', 'k8s', 'kubernetes', 'helm', 'docker',
    '.github', '.gitlab', 'src', 'app', 'config',
    'Dockerfile', 'Makefile', 'README'
  ]

  for (const pattern of commonPatterns) {
    const patternIndex = parts.findIndex(part =>
      part.toLowerCase() === pattern.toLowerCase() ||
      part.toLowerCase().endsWith(pattern.toLowerCase())
    )
    if (patternIndex !== -1) {
      return parts.slice(patternIndex).join('/')
    }
  }

  const lastPart = parts[parts.length - 1]
  const commonFileNames = new Set([
    'Chart.yaml',
    'values.yaml',
    'main.tf',
    'variables.tf',
    'variable.tf',
    'outputs.tf',
    'output.tf',
    'deployment.yaml',
    'service.yaml',
    'ingress.yaml',
    'Dockerfile',
    'docker-compose.yml',
    'Jenkinsfile',
    'prometheus.yml',
  ])

  if (commonFileNames.has(lastPart) && parts.length > 1) {
    return parts.slice(-Math.min(3, parts.length)).join('/')
  }

  if (lastPart.includes('.') && !lastPart.startsWith('.')) {
    return lastPart
  }

  return parts.slice(-Math.min(3, parts.length)).join('/')
}

function dedupeFiles(files: FileBeingScanned[]): FileBeingScanned[] {
  const seen = new Set<string>()
  return files.filter((file) => {
    const key = `${file.type}:${file.path}:${file.status}`
    if (seen.has(key)) {
      return false
    }
    seen.add(key)
    return true
  })
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
}

const DEFAULT_STEPS = [
  'Connecting to GitHub',
  'Fetching repository',
  'Detecting technologies',
  'Running security rules',
  'Preparing report',
  'Calculating score',
]

export function ScanProgress({
  progress,
  currentStep,
  isComplete,
  detectedFiles = [],
  detectedTechnologies = [],
  steps = DEFAULT_STEPS,
  backendLogs = []
}: ScanProgressProps) {
  const [logs, setLogs] = useState<ScanLog[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [files, setFiles] = useState<FileBeingScanned[]>([])

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Update files when detectedFiles prop changes
  useEffect(() => {
    if (detectedFiles && detectedFiles.length > 0) {
      const processedFiles = dedupeFiles(
        detectedFiles.map(file => ({
          ...file,
          path: convertToRelativePath(file.path)
        }))
      ).sort((a, b) => a.path.localeCompare(b.path))
      setFiles(processedFiles)
    }
  }, [detectedFiles])

  // Update files when detectedTechnologies changes
  useEffect(() => {
    if (detectedTechnologies && detectedTechnologies.length > 0 && (!detectedFiles || detectedFiles.length === 0)) {
      const detected: FileBeingScanned[] = []
      const techToFileMap: Record<string, {type: FileBeingScanned['type'], path: string}> = {
        'docker': {type: 'docker', path: 'Dockerfile'},
        'Docker': {type: 'docker', path: 'Dockerfile'},
        'github_actions': {type: 'cicd', path: '.github/workflows/ci.yml'},
        'CI/CD': {type: 'cicd', path: '.github/workflows/ci.yml'},
        'cicd': {type: 'cicd', path: '.github/workflows/ci.yml'},
        'kubernetes': {type: 'k8s', path: 'k8s/deployment.yaml'},
        'Kubernetes': {type: 'k8s', path: 'k8s/deployment.yaml'},
        'K8S': {type: 'k8s', path: 'k8s/deployment.yaml'},
        'terraform': {type: 'terraform', path: 'terraform/main.tf'},
        'Terraform': {type: 'terraform', path: 'terraform/main.tf'},
        'helm': {type: 'helm', path: 'Chart.yaml'},
        'Helm': {type: 'helm', path: 'Chart.yaml'},
        'monitoring': {type: 'monitoring', path: 'prometheus.yml'},
        'Monitoring': {type: 'monitoring', path: 'prometheus.yml'},
        'prometheus': {type: 'monitoring', path: 'prometheus.yml'},
        'grafana': {type: 'monitoring', path: 'grafana/dashboards.yml'},
        'jenkins': {type: 'cicd', path: 'Jenkinsfile'},
        'Jenkins': {type: 'cicd', path: 'Jenkinsfile'},
        'gitlab_ci': {type: 'cicd', path: '.gitlab-ci.yml'},
        'GitLab CI': {type: 'cicd', path: '.gitlab-ci.yml'},
        'circleci': {type: 'cicd', path: '.circleci/config.yml'},
        'CircleCI': {type: 'cicd', path: '.circleci/config.yml'},
        'azure_devops': {type: 'cicd', path: 'azure-pipelines.yml'},
        'Azure DevOps': {type: 'cicd', path: 'azure-pipelines.yml'},
        'ansible': {type: 'cicd', path: 'ansible.cfg'},
        'Ansible': {type: 'cicd', path: 'ansible.cfg'},
      }

      detectedTechnologies.forEach(tech => {
        const mapping = techToFileMap[tech]
        if (mapping && !detected.some(f => f.path === mapping.path)) {
          detected.push({ path: mapping.path, type: mapping.type, status: 'completed' })
        } else if (!mapping && !detected.some(f => f.path === tech)) {
          detected.push({ path: `${tech}/config`, type: 'monitoring', status: 'completed' })
        }
      })

      if (detected.length > 0) {
        setFiles(detected)
      }
    }
  }, [detectedTechnologies, detectedFiles])

  // Use REAL backend logs when available, fallback to generated logs
  useEffect(() => {
    if (isComplete) return

    if (backendLogs && backendLogs.length > 0) {
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
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          }),
          message: log,
          type: 'info' as const
        }
      })

      setLogs(parsedLogs)
      return
    }

    const addLog = (message: string, type: 'info' | 'success' | 'warning' = 'info') => {
      const timestamp = new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })

      setLogs(prev => {
        const isDuplicate = prev.some(log => log.message === message)
        if (isDuplicate) return prev
        return [...prev, { message, timestamp, type }]
      })
    }

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
      if (detectedTechnologies.length > 0) {
        addLog(`Found ${detectedTechnologies.length} technologies: ${detectedTechnologies.join(', ')}`, 'success')
      }
    } else if (progress < 70) {
      if (files.length > 0) {
        files.forEach(file => {
          if (file.status === 'completed') {
            addLog(`✓ ${file.path} analyzed`, 'success')
          }
        })
      }
    } else if (progress < 80) {
      addLog('Running security rules...', 'info')
    } else if (progress < 90) {
      addLog('Analyzing findings...', 'info')
      addLog('Preparing report artifacts...', 'info')
    } else if (progress < 95) {
      addLog('Calculating security score...', 'info')
    } else if (progress < 100) {
      addLog('Finalizing results...', 'info')
    }

  }, [progress, isComplete, files, detectedTechnologies, backendLogs])

  // Current step display name
  const currentStepName = steps[currentStep - 1] || steps[0]

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      {/* Header - Clean and minimal */}
      <motion.div
        className="text-center mb-6"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="inline-flex p-3 rounded-xl bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/20 mb-3">
          <AnimatePresence mode="wait">
            {isComplete ? (
              <motion.div
                key="success"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
                <CheckCircle className="h-8 w-8 text-green-400" />
              </motion.div>
            ) : (
              <motion.div
                key="scanning"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
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

        <p className="text-muted-foreground text-sm">
          {isComplete ? 'Your security report is ready' : currentStepName}
        </p>
      </motion.div>

      {/* Progress Bar - Primary focus */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-muted-foreground">Progress</span>
          <span className="font-semibold text-foreground">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary to-indigo-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Minimal Step Tracker */}
      {!isComplete && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-6"
        >
          <div className="flex items-center justify-between text-xs">
            {steps.map((step, index) => {
              const stepNumber = index + 1
              const isCompleted = currentStep > stepNumber
              const isCurrent = currentStep === stepNumber

              return (
                <div key={step} className="flex flex-col items-center flex-1">
                  <div className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-all',
                    isCompleted && 'bg-green-500/20 text-green-400',
                    isCurrent && 'bg-primary/20 text-primary',
                    !isCompleted && !isCurrent && 'bg-white/5 text-muted-foreground'
                  )}>
                    {isCompleted ? (
                      <CheckCircle className="h-3.5 w-3.5" />
                    ) : (
                      stepNumber
                    )}
                  </div>
                  <span className={cn(
                    'mt-1 text-[10px] text-center leading-tight',
                    isCurrent && 'text-foreground font-medium',
                    !isCurrent && 'text-muted-foreground'
                  )}>
                    {step.split(' ')[0]}
                  </span>
                </div>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* Tabs: Logs, Files, Technologies */}
      <Tabs
        tabs={[
          { id: 'logs', label: 'Logs', icon: <Terminal className="h-3.5 w-3.5" />, count: logs.length },
          { id: 'files', label: 'Files', icon: <FileText className="h-3.5 w-3.5" />, count: files.length },
          { id: 'tech', label: 'Technologies', icon: <Cpu className="h-3.5 w-3.5" />, count: detectedTechnologies.length },
        ]}
      >
        {/* Logs Tab */}
        <div className="bg-black/40 rounded-lg border border-white/10 p-3">
          <div className="h-64 overflow-y-auto font-mono text-xs space-y-1.5 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            <AnimatePresence>
              {logs.map((log, index) => (
                <motion.div
                  key={`${log.timestamp}-${log.message}`}
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(
                    'flex items-start gap-2 py-1 px-2 rounded',
                    log.type === 'success' ? 'text-green-400/90' :
                    log.type === 'warning' ? 'text-yellow-400/90' :
                    'text-gray-400'
                  )}
                >
                  <span className="text-white/20 flex-shrink-0 text-[10px]">
                    {log.timestamp}
                  </span>
                  <span className="flex-1">{log.message}</span>
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

        {/* Files Tab */}
        <div className="bg-white/5 rounded-lg border border-white/10 p-3">
          <div className="h-64 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            {files.length > 0 ? (
              files.map((file, index) => (
                <motion.div
                  key={`${file.type}-${file.path}-${index}`}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className="flex items-center gap-2 py-1.5 px-2 rounded text-xs hover:bg-white/5 transition-colors"
                >
                  <FileCode className={cn(
                    'h-3.5 w-3.5 flex-shrink-0',
                    file.status === 'completed' ? 'text-green-400/70' : 'text-muted-foreground'
                  )} />
                  <span className="flex-1 font-mono text-foreground/80 truncate">
                    {file.path}
                  </span>
                  {file.status === 'completed' && (
                    <CheckCircle className="h-3 w-3 text-green-400/70 flex-shrink-0" />
                  )}
                  {file.status === 'scanning' && (
                    <Loader2 className="h-3 w-3 text-primary animate-spin flex-shrink-0" />
                  )}
                </motion.div>
              ))
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-xs">
                <Loader2 className="h-3 w-3 animate-spin mr-2" />
                Waiting for files...
              </div>
            )}
          </div>
        </div>

        {/* Technologies Tab */}
        <div className="space-y-3">
          {detectedTechnologies.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {detectedTechnologies.map((tech, index) => (
                <motion.div
                  key={`${tech}-${index}`}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.03 }}
                  className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-foreground/80 text-xs font-medium capitalize"
                >
                  {tech.replace('_', ' ')}
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-xs">
              <Loader2 className="h-3 w-3 animate-spin mr-2" />
              Detecting technologies...
            </div>
          )}
        </div>
      </Tabs>

      {/* Completion Message */}
      {isComplete && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 p-4 rounded-lg bg-green-500/10 border border-green-500/20"
        >
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0" />
            <div>
              <p className="font-medium text-green-400 text-sm">Scan completed successfully</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {files.length} files analyzed • {detectedTechnologies.length} technologies detected
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

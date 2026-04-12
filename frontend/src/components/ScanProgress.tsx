import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, GitBranch, Terminal, FileCode, FolderGit2, Loader2, Layers, FolderOpen } from 'lucide-react'
import { Card } from './ui-animated'
import { cn } from '../lib/utils'

// Helper function to convert absolute paths to relative paths
function convertToRelativePath(filePath: string): string {
  // Remove /tmp/scan-xxx/ or similar prefixes
  const parts = filePath.split('/')
  
  // Find common repository directory patterns
  // Look for patterns like: scan-xxx, repos, tmp
  const repoIndex = parts.findIndex(part => 
    part.startsWith('scan-') || 
    part === 'tmp' || 
    part === 'repos' ||
    part === 'workspace'
  )
  
  if (repoIndex !== -1 && repoIndex < parts.length - 1) {
    // Return everything after the repo directory
    return parts.slice(repoIndex + 1).join('/')
  }
  
  // If path contains common tech directories, extract from there
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
  
  // Fallback: if it looks like a file (has extension), return just the filename
  const lastPart = parts[parts.length - 1]
  if (lastPart.includes('.') && !lastPart.startsWith('.')) {
    return lastPart
  }
  
  // Last resort: return the last 2-3 parts
  return parts.slice(-Math.min(3, parts.length)).join('/')
}

// Build tree structure from flat file list
interface TreeNode {
  name: string
  type: 'file' | 'folder'
  children?: TreeNode[]
  fileData?: FileBeingScanned
}

function buildFileTree(files: FileBeingScanned[]): TreeNode[] {
  const root: TreeNode[] = []
  const folderMap = new Map<string, TreeNode>()

  // Sort files to ensure consistent ordering
  const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path))

  for (const file of sortedFiles) {
    const parts = file.path.split('/')
    let currentPath = ''
    let parentArray = root

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1
      currentPath = currentPath ? `${currentPath}/${part}` : part

      if (isFile) {
        // It's a file
        parentArray.push({
          name: part,
          type: 'file',
          fileData: file
        })
      } else {
        // It's a folder
        if (!folderMap.has(currentPath)) {
          const folderNode: TreeNode = {
            name: part,
            type: 'folder',
            children: []
          }
          folderMap.set(currentPath, folderNode)
          parentArray.push(folderNode)
        }
        parentArray = folderMap.get(currentPath)!.children!
      }
    }
  }

  return root
}

// Tree View Component to display file hierarchy
function FileTreeView({ nodes, depth = 0 }: { nodes: TreeNode[]; depth?: number }) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())

  const toggleFolder = (folderName: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(folderName)) {
        next.delete(folderName)
      } else {
        next.add(folderName)
      }
      return next
    })
  }

  return (
    <div className="space-y-1">
      {nodes.map((node, index) => {
        const isExpanded = expandedFolders.has(node.name)
        
        if (node.type === 'folder') {
          return (
            <div key={`${node.name}-${index}`}>
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.03 }}
                className="flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors"
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
                onClick={() => toggleFolder(node.name)}
              >
                <FolderOpen 
                  className={cn(
                    'h-4 w-4 flex-shrink-0 transition-transform',
                    isExpanded ? 'text-primary' : 'text-muted-foreground'
                  )} 
                />
                <span className="text-sm font-mono text-foreground flex-1">{node.name}/</span>
              </motion.div>
              {isExpanded && node.children && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <FileTreeView nodes={node.children} depth={depth + 1} />
                </motion.div>
              )}
            </div>
          )
        }

        // It's a file
        const fileData = node.fileData
        if (!fileData) return null

        const Icon = fileData.type === 'docker' ? FileCode :
                    fileData.type === 'k8s' ? FileCode :
                    fileData.type === 'terraform' ? FileCode :
                    fileData.type === 'helm' ? FileCode :
                    fileData.type === 'monitoring' ? FileCode : FileCode

        return (
          <motion.div
            key={`${node.name}-${index}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.03 }}
            className={cn(
              'flex items-center gap-2 p-2 rounded-lg transition-all',
              fileData.status === 'scanning' ? 'bg-primary/10 border border-primary/30' :
              fileData.status === 'completed' ? 'bg-green-500/10 border border-green-500/30' :
              'bg-white/5 border border-transparent hover:bg-white/10'
            )}
            style={{ paddingLeft: `${depth * 16 + 8}px` }}
          >
            <Icon className={cn(
              'h-4 w-4 flex-shrink-0',
              fileData.status === 'scanning' ? 'text-primary animate-pulse' :
              fileData.status === 'completed' ? 'text-green-400' :
              'text-muted-foreground'
            )} />
            <span className={cn(
              'text-sm font-mono flex-1',
              fileData.status === 'scanning' ? 'text-primary' :
              fileData.status === 'completed' ? 'text-green-400' :
              'text-muted-foreground'
            )}>
              {node.name}
            </span>
            {fileData.status === 'scanning' && (
              <Loader2 className="h-3 w-3 text-primary animate-spin" />
            )}
            {fileData.status === 'completed' && (
              <CheckCircle className="h-3 w-3 text-green-400" />
            )}
          </motion.div>
        )
      })}
    </div>
  )
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
  detectedFiles?: FileBeingScanned[]  // Dynamic files from scan
  detectedTechnologies?: string[]  // Technologies detected by backend
  steps?: string[]  // Custom step names
  backendLogs?: string[]  // ✅ Real logs from backend API
}

// Default pipeline steps
const DEFAULT_STEPS = [
  'Connecting to GitHub',
  'Fetching repository',
  'Detecting technologies',
  'Running security rules',
  'Generating AI suggestions',
  'Calculating score',
]

export function ScanProgress({
  progress,
  currentStep,
  isComplete,
  detectedFiles = [],  // Default to empty array
  detectedTechnologies = [],  // Default to empty array
  steps = DEFAULT_STEPS,
  backendLogs = []  // ✅ Real logs from backend
}: ScanProgressProps) {
  const [logs, setLogs] = useState<ScanLog[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [files, setFiles] = useState<FileBeingScanned[]>([])

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Update files when detectedFiles prop changes (PRIORITY - actual file paths from backend)
  useEffect(() => {
    if (detectedFiles && detectedFiles.length > 0) {
      console.log('📁 Setting files from detectedFiles prop:', detectedFiles.length, 'first file:', detectedFiles[0]?.path)
      // Convert absolute paths to relative and sort
      const processedFiles = detectedFiles.map(file => ({
        ...file,
        path: convertToRelativePath(file.path)
      })).sort((a, b) => a.path.localeCompare(b.path))
      setFiles(processedFiles)
    }
    // Removed verbose logging for empty state - it's normal during initial scan
  }, [detectedFiles])

  // Update files when detectedTechnologies changes (from API) - ONLY if no detectedFiles
  useEffect(() => {
    if (detectedTechnologies && detectedTechnologies.length > 0 && (!detectedFiles || detectedFiles.length === 0)) {
      // Convert technology names to file paths
      const detected: FileBeingScanned[] = []

      // Map backend technology names to frontend file types
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
          // Fallback: Add unknown technologies as generic files
          detected.push({
            path: `${tech}/config`,
            type: 'monitoring',
            status: 'completed'
          })
        }
      })

      if (detected.length > 0) {
        setFiles(detected)
        console.log('📁 Files detected from technologies:', detected)
      }
    }
  }, [detectedTechnologies, detectedFiles])

  // ✅ Use REAL backend logs when available, fallback to generated logs
  useEffect(() => {
    if (isComplete) return

    // If we have backend logs, use them directly
    if (backendLogs && backendLogs.length > 0) {
      const parsedLogs = backendLogs.map(log => {
        // Parse log format: "[HH:MM:SS] message"
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
        // Fallback for unparseable logs
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

    // Fallback: Generate local logs only if no backend logs
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

    // Progress-based log generation with DYNAMIC file detection
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
      // Show detected files if available from API
      if (detectedTechnologies.length > 0) {
        addLog(`Found ${detectedTechnologies.length} technologies: ${detectedTechnologies.join(', ')}`, 'success')
      }
    } else if (progress < 70) {
      // Show files as they are detected
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
      addLog('Generating AI suggestions...', 'info')
    } else if (progress < 95) {
      addLog('Calculating security score...', 'info')
    } else if (progress < 100) {
      addLog('Finalizing results...', 'info')
    }

  }, [progress, isComplete, files, detectedTechnologies, backendLogs])

  return (
    // PRODUCTION SCAN PROGRESS - Logs + File Tree ONLY (No Pipeline)
    <div className="w-full max-w-[1100px] mx-auto px-6">
      {/* Centered Header Section */}
      <motion.div
        className="text-center mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-4">
          <AnimatePresence mode="wait">
            {isComplete ? (
              <motion.div
                key="success"
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                exit={{ scale: 0 }}
                transition={{ type: 'spring', duration: 0.5 }}
              >
                <CheckCircle className="h-10 w-10 text-white" />
              </motion.div>
            ) : (
              <motion.div
                key="scanning"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
                <GitBranch className="h-10 w-10 text-white animate-pulse" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <motion.h3
          className="text-3xl font-bold text-foreground mb-2"
          key={isComplete ? 'complete' : 'scanning'}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {isComplete ? 'Analysis Complete!' : 'Analyzing Repository'}
        </motion.h3>

        <p className="text-muted-foreground text-base">
          {isComplete
            ? 'Your security report is ready'
            : 'Please wait while we scan your infrastructure'}
        </p>
      </motion.div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-muted-foreground font-medium">Progress</span>
          <span className="font-bold text-primary text-base">{progress.toFixed(0)}%</span>
        </div>
        <div className="h-4 bg-white/10 rounded-full overflow-hidden shadow-inner">
          <motion.div
            className="h-full bg-gradient-to-r from-primary via-indigo-500 to-primary rounded-full shadow-lg"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* PHASE 3B: Pipeline Steps Visualization */}
      {!isComplete && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            {steps.map((step, index) => {
              const stepNumber = index + 1
              const isCompleted = currentStep > stepNumber || (currentStep === stepNumber && progress >= 100)
              const isCurrent = currentStep === stepNumber
              const isPending = currentStep < stepNumber

              return (
                <div key={step} className="flex items-center flex-1">
                  {/* Step Circle */}
                  <div className="flex flex-col items-center">
                    <motion.div
                      className={cn(
                        'w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all',
                        isCompleted && 'bg-green-500 border-green-500 text-white',
                        isCurrent && 'bg-primary border-primary text-white animate-pulse',
                        isPending && 'bg-white/5 border-white/20 text-muted-foreground'
                      )}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      {isCompleted ? (
                        <CheckCircle className="h-5 w-5" />
                      ) : (
                        <span className="text-sm font-bold">{stepNumber}</span>
                      )}
                    </motion.div>
                    <span className={cn(
                      'text-xs mt-2 text-center max-w-[80px]',
                      isCompleted && 'text-green-400',
                      isCurrent && 'text-primary font-semibold',
                      isPending && 'text-muted-foreground'
                    )}>
                      {step}
                    </span>
                  </div>

                  {/* Connector Line */}
                  {index < steps.length - 1 && (
                    <div className={cn(
                      'flex-1 h-0.5 mx-2 mb-6',
                      isCompleted ? 'bg-green-500' : 'bg-white/10'
                    )} />
                  )}
                </div>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* PHASE 3B: Technology Badges */}
      {detectedTechnologies.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <div className="flex items-center gap-2 mb-3">
            <Layers className="h-4 w-4 text-primary" />
            <span className="text-sm font-semibold text-foreground">Detected Technologies</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {detectedTechnologies.map((tech, index) => (
              <motion.div
                key={tech}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05 }}
                className="px-3 py-1.5 rounded-full bg-primary/10 border border-primary/30 text-primary text-sm font-medium capitalize flex items-center gap-2"
              >
                <Terminal className="h-3 w-3" />
                {tech.replace('_', ' ')}
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Two Column Layout: Logs (left) + File Tree (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Live Logs (Left Column) */}
        <Card className="p-5 bg-black/50 border-white/10 hover:border-white/20 transition-colors" hover={false}>
          <div className="flex items-center gap-2 mb-4">
            <Terminal className="h-5 w-5 text-primary" />
            <h4 className="text-sm font-semibold text-foreground uppercase tracking-wide">Live Scan Logs</h4>
          </div>

          <div className="h-64 overflow-y-auto font-mono text-xs space-y-2 pr-2 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
            <AnimatePresence>
              {logs.map((log, index) => (
                <motion.div
                  key={`${log.timestamp}-${log.message}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                  className={cn(
                    'flex items-start gap-2 p-2 rounded',
                    log.type === 'success' ? 'bg-green-500/10 text-green-400' :
                    log.type === 'warning' ? 'bg-yellow-500/10 text-yellow-400' :
                    'bg-white/5 text-gray-300'
                  )}
                >
                  <span className="text-muted-foreground flex-shrink-0 font-mono text-[10px]">
                    [{log.timestamp}]
                  </span>
                  <span className="flex-1">{log.message}</span>
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={logsEndRef} />
          </div>
        </Card>

        {/* File Tree (Right Column) - DYNAMIC TREE STRUCTURE */}
        <Card className="p-5 bg-black/50 border-white/10 hover:border-white/20 transition-colors" hover={false}>
          <div className="flex items-center gap-2 mb-4">
            <FolderGit2 className="h-5 w-5 text-primary" />
            <h4 className="text-sm font-semibold text-foreground uppercase tracking-wide">Files Being Scanned</h4>
          </div>

          <div className="space-y-1">
            {files.length > 0 ? (
              <FileTreeView nodes={buildFileTree(files)} />
            ) : (
              <div className="flex items-center gap-3 p-3 rounded-lg border border-white/10 bg-white/5">
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
                <span className="text-sm text-muted-foreground">Waiting for repository clone...</span>
              </div>
            )}
          </div>

          {/* Scan Stats */}
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-lg font-bold text-primary">{files.filter(f => f.status === 'completed').length}</div>
                <div className="text-xs text-muted-foreground">Files Scanned</div>
              </div>
              <div>
                <div className="text-lg font-bold text-primary">{Math.min(currentStep + 1, 6)}/6</div>
                <div className="text-xs text-muted-foreground">Current Step</div>
              </div>
              <div>
                <div className="text-lg font-bold text-primary">{progress}%</div>
                <div className="text-xs text-muted-foreground">Complete</div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Completion Message */}
      {isComplete && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Scan Success */}
          <div className="p-5 rounded-xl bg-green-500/10 border border-green-500/30">
            <div className="flex items-center gap-3">
              <CheckCircle className="h-6 w-6 text-green-400" />
              <div>
                <p className="font-semibold text-green-400 text-base">Scan completed successfully</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Ready to view results
                </p>
              </div>
            </div>
          </div>

          {/* Detected Technologies Summary */}
          {detectedTechnologies && detectedTechnologies.length > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-5 rounded-xl bg-indigo-500/10 border border-indigo-500/30"
            >
              <div className="flex items-center gap-2 mb-3">
                <FolderGit2 className="h-5 w-5 text-indigo-400" />
                <h4 className="text-sm font-semibold text-indigo-400 uppercase tracking-wide">Technologies Detected</h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {detectedTechnologies.map((tech, index) => (
                  <motion.span
                    key={tech}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="px-3 py-1.5 rounded-lg bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-sm font-medium capitalize"
                  >
                    {tech.replace('_', ' ')}
                  </motion.span>
                ))}
              </div>
              <div className="mt-3 text-xs text-indigo-300">
                {files.filter(f => f.status === 'completed').length} file{files.filter(f => f.status === 'completed').length !== 1 ? 's' : ''} analyzed
              </div>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  )
}

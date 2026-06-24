import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Github, ArrowRight, Loader2, AlertCircle, GitBranch, ChevronDown, Lock } from 'lucide-react'
import { Button, Card } from '../components/ui-animated'
import { api, buildWebSocketUrl } from '../lib/api'
import { cn, getFindingsCount } from '../lib/utils'
import { ScanProgress } from '../components/ScanProgress'
import { ResultComponent } from '../components/ResultComponent'
import { useAuthStore } from '../stores/auth-store'

interface Finding {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path?: string
  line_number?: number
}

interface SeverityCounts {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

interface FileBeingScanned {
  path: string
  type: 'docker' | 'k8s' | 'terraform' | 'cicd' | 'helm' | 'monitoring'
  status: 'pending' | 'scanning' | 'completed'
}

// Helper function to determine file type from path
function getFileTypeFromPath(path: string): FileBeingScanned['type'] {
  const lowerPath = path.toLowerCase()
  
  if (lowerPath.includes('dockerfile') || lowerPath.includes('docker')) {
    return 'docker'
  }
  if (lowerPath.includes('k8s') || lowerPath.includes('kubernetes') || lowerPath.includes('deployment') || lowerPath.includes('service')) {
    return 'k8s'
  }
  if (lowerPath.includes('.tf') || lowerPath.includes('terraform')) {
    return 'terraform'
  }
  if (lowerPath.includes('chart') || lowerPath.includes('helm')) {
    return 'helm'
  }
  if (lowerPath.includes('.github') || lowerPath.includes('.gitlab') || lowerPath.includes('jenkins') || 
      lowerPath.includes('ci/') || lowerPath.includes('pipeline') || lowerPath.includes('azure-pipelines')) {
    return 'cicd'
  }
  if (lowerPath.includes('prometheus') || lowerPath.includes('grafana') || lowerPath.includes('monitor')) {
    return 'monitoring'
  }
  
  return 'cicd' // Default fallback
}

interface DevOpsStack {
  docker: boolean
  docker_files: string[]
  terraform: boolean
  terraform_files: string[]
  kubernetes: boolean
  kubernetes_files: string[]
  helm: boolean
  helm_files: string[]
  cicd: string | null
  cicd_files: string[]
  monitoring: boolean
  monitoring_files: string[]
  prometheus: boolean
  grafana: boolean
  ansible: boolean
  pulumi: boolean
  security_scanning: boolean
}

interface ScanResult {
  success: boolean
  scan_id: string
  security_score: number
  severity_counts: SeverityCounts
  findings: Finding[]
  total_findings: number
  files_analyzed: number
  devops_stack?: DevOpsStack
  detected_technologies?: string[]
  repository_url?: string
  repository_name?: string
  branch?: string
}

interface GitHubBranch {
  name: string
  protected: boolean
  commit_sha: string
}

export function ScanPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useAuthStore()
  
  // State management
  const initialUrl = searchParams.get('url') || ''
  const initialBranch = searchParams.get('branch') || 'main'
  const autoStart = searchParams.get('auto') === 'true'
  const [repoUrl, setRepoUrl] = useState(initialUrl)
  const [selectedBranch, setSelectedBranch] = useState<string>(initialBranch)
  const [showBranchDropdown, setShowBranchDropdown] = useState(false)
  const autoSubmittedRef = useRef(false)
  
  // Scan state
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState(0)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [scanId, setScanId] = useState<string>('')
  const [detectedTechnologies, setDetectedTechnologies] = useState<string[]>([])
  const [filesScanned, setFilesScanned] = useState(0)
  const [filesList, setFilesList] = useState<string[]>([])
  const [scanLogs, setScanLogs] = useState<string[]>([])
  const [stepsFromBackend, setStepsFromBackend] = useState<Array<{name: string; status: string}>>([])

  // Fetch branches when repo URL changes
  const { data: branchesData, isLoading: isLoadingBranches, error: branchesError, refetch, isFetching } = useQuery({
    queryKey: ['branches', repoUrl],
    queryFn: async () => {
      const trimmedUrl = repoUrl.trim()
      console.log('🔄 Fetching branches for:', trimmedUrl)
      if (!trimmedUrl || !trimmedUrl.startsWith('https://github.com/')) {
        console.log('⏭️ Skipping fetch - invalid URL')
        return { branches: [], default_branch: 'main' }
      }
      try {
        const response = await api.get('/github/branches', {
          params: { repo_url: trimmedUrl }
        })
        console.log('✅ Branches fetched:', response.data)
        console.log('✅ Branch count:', response.data?.branches?.length)
        console.log('✅ Default branch:', response.data?.default_branch)
        return response.data
      } catch (err: any) {
        console.error('❌ Failed to fetch branches:', err.response?.data || err.message)
        // Return default branch even on error so user can proceed
        return { branches: [], default_branch: 'main', error: err.response?.data?.detail || 'Failed to fetch branches' }
      }
    },
    enabled: !!repoUrl && repoUrl.trim().startsWith('https://github.com/'),
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: false, // Don't retry on failure
  })

  // Update selected branch when branches are loaded (preserve rescan branch)
  useEffect(() => {
    if (!branchesData?.default_branch) return
    if (initialUrl) return // preserve branch from rescan params
    setSelectedBranch(branchesData.default_branch)
  }, [branchesData])

  const branches: GitHubBranch[] = branchesData?.branches || []
  const isFetchingBranches = isLoadingBranches || isFetching
  const hasBranchesError = !!branchesData?.error || (branchesError && branches.length === 0)
  
  // Debug logging
  useEffect(() => {
    console.log('🔍 Branch state:', { 
      branches: branches.length, 
      isFetchingBranches, 
      hasBranchesError,
      branchesError,
      branchesData 
    })
  }, [branches, isFetchingBranches, hasBranchesError, branchesData])

  // Refs to avoid stale closures in intervals/timeouts
  const progressRef = useRef(0)
  const detectedTechRef = useRef<string[]>([])
  const stepsRef = useRef<Array<{name: string; status: string}>>([])
  useEffect(() => { progressRef.current = progress }, [progress])
  useEffect(() => { detectedTechRef.current = detectedTechnologies }, [detectedTechnologies])
  useEffect(() => { stepsRef.current = stepsFromBackend }, [stepsFromBackend])

  // Auto-submit when navigated from rescan
  useEffect(() => {
    if (autoStart && repoUrl && !autoSubmittedRef.current && !loading && !result) {
      autoSubmittedRef.current = true
      const timer = setTimeout(() => {
        const form = document.querySelector('form')
        if (form) form.requestSubmit()
      }, 800)
      return () => clearTimeout(timer)
    }
  }, [autoStart, repoUrl, loading, result])

  // Navigate to results page when rescan completes
  useEffect(() => {
    if (result && autoStart && result.scan_id) {
      navigate(`/scans/${result.scan_id}`, { replace: true })
    }
  }, [result, autoStart, navigate])

  // WebSocket connection for real-time scan progress
  const wsRef = useRef<WebSocket | null>(null)

  // Derive step index from steps array for UI
  const getStepIndex = useCallback((stepName: string | undefined | null, steps: Array<{name: string}> | undefined): number => {
    if (!stepName || !steps || steps.length === 0) return 1
    const idx = steps.findIndex(s => s.name === stepName)
    return idx >= 0 ? idx + 1 : 1
  }, [])

  // Connect to WebSocket for real-time updates
  useEffect(() => {
    if (!loading || !scanId) return

    const wsUrl = buildWebSocketUrl(`/ws/scan/${scanId}`)

    console.log('🔌 Connecting to WebSocket:', wsUrl)
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('✅ WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        const { type, data } = message

        switch (type) {
          case 'progress_update':
            if (data.progress !== undefined) {
              setProgress(Math.round(data.progress))
            }
            if (data.current_step) {
              setCurrentStep(getStepIndex(data.current_step, data.steps))
            }
            if (data.steps && data.steps.length > 0) {
              setStepsFromBackend(data.steps)
            }
            if (data.detected_stack && Array.isArray(data.detected_stack) && data.detected_stack.length > 0) {
              setDetectedTechnologies(data.detected_stack)
            }
            if (data.files_list && Array.isArray(data.files_list) && data.files_list.length > 0) {
              setFilesList(data.files_list)
            }
            if (data.logs && Array.isArray(data.logs)) {
              setScanLogs(prevLogs => {
                const logSet = new Set(prevLogs)
                let hasNew = false
                for (const log of data.logs) {
                  if (!logSet.has(log)) {
                    logSet.add(log)
                    hasNew = true
                  }
                }
                if (!hasNew) return prevLogs
                const all = Array.from(logSet)
                return all.length > 200 ? all.slice(-200) : all
              })
            }
            break

          case 'log_message':
            console.log("WS log received:", message)
            if (data.message) {
              const logEntry = data.timestamp ? `[${data.timestamp}] ${data.message}` : data.message
              setScanLogs(prev => {
                if (prev.includes(logEntry)) return prev
                const updated = [...prev, logEntry]
                return updated.length > 200 ? updated.slice(-200) : updated
              })
            }
            break

          case 'step_update':
            if (data.step_name) {
              setCurrentStep(getStepIndex(data.step_name, undefined))
            }
            break

          case 'stack_detected':
            if (data.technology) {
              setDetectedTechnologies(prev => {
                if (prev.includes(data.technology)) return prev
                return [...prev, data.technology]
              })
            }
            break

          case 'scan_complete':
            setProgress(100)
            setCurrentStep(stepsFromBackend.length || 7)
            break

          case 'scan_failed':
            setError(data.error || 'Scan failed')
            setLoading(false)
            break
        }
      } catch (err) {
        console.error('WebSocket message parse error:', err)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('🔌 WebSocket disconnected')
      wsRef.current = null
    }

    return () => {
      if (wsRef.current) {
        console.log('🔌 Closing WebSocket')
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [loading, scanId, getStepIndex, stepsFromBackend.length])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const trimmedUrl = repoUrl.trim()
    if (!trimmedUrl) {
      setError('Please enter a repository URL')
      return
    }

    // Validate URL format
    if (!trimmedUrl.startsWith('https://github.com/')) {
      setError('Please enter a valid GitHub repository URL (e.g., https://github.com/user/repo)')
      return
    }

    // Reset state
    setLoading(true)
    setProgress(0)
    setCurrentStep(0)
    setResult(null)
    setError(null)

    try {
      console.log('Starting scan for:', trimmedUrl, 'branch:', selectedBranch)

      // Minimum animation duration: 15 seconds (ensures UI shows for reasonable time)
      const MIN_ANIMATION_DURATION = 15000
      const startTime = Date.now()

      // Clear any previous state
      setProgress(0)
      setCurrentStep(0)

      // ❌ REMOVED local progress animation - Backend provides REAL progress updates
      // Progress is now updated ONLY from backend polling (no fake animation)

      // Use same endpoint for both authenticated and anonymous users
      const response = await api.post('/scan/start', {
        repository_url: trimmedUrl,
        branch: selectedBranch || 'main',
      })

      const data = response.data
      console.log('✅ Scan started:', data)

      if (!data.scan_id) {
        throw new Error('No scan_id returned from server')
      }

      // Save scan ID - WebSocket will handle real-time updates
      setScanId(data.scan_id)

      // WebSocket connection (defined in useEffect above) will handle:
      // - Progress updates
      // - Step updates  
      // - Log accumulation
      // - Technology detection
      // - Completion detection

      // Monitor completion via WebSocket and fetch results
      const completionCheck = setInterval(async () => {
        // Use ref to avoid stale closure on progress state
        if (progressRef.current >= 100) {
          clearInterval(completionCheck)
          
          // Minimum display time
          const elapsed = Date.now() - startTime
          const MIN_DISPLAY_TIME = 2000
          const remaining = Math.max(0, MIN_DISPLAY_TIME - elapsed)
          
          if (remaining > 0) {
            await new Promise(resolve => setTimeout(resolve, remaining))
          }

          // Fetch complete results with retry logic
          let attempts = 0
          const maxAttempts = 5
          let fetchSuccess = false

          while (attempts < maxAttempts && !fetchSuccess) {
            try {
              const resultsResponse = await api.get(`/scan/results/${data.scan_id}`)
              const results = resultsResponse.data

              console.log('✅ Complete results:', results)

              setProgress(100)
              setCurrentStep(stepsRef.current.length || 7)
              setLoading(false)

              const currentTechs = detectedTechRef.current
              const scanResult: ScanResult = {
                success: true,
                scan_id: results.scan_id || data.scan_id,
                security_score: results.security_score || results.overall_score || 0,
                severity_counts: results.severity_counts || {
                  critical: 0,
                  high: 0,
                  medium: 0,
                  low: 0,
                  info: 0,
                },
                findings: results.findings || [],
                total_findings: getFindingsCount(results),
                files_analyzed: results.files_analyzed || results.filesAnalyzed || 0,
                devops_stack: results.devops_stack,
                detected_technologies: currentTechs.length > 0 ? currentTechs : (results.detected_technologies || []),
                repository_url: results.repository_url || repoUrl,
                repository_name: results.repository_name || repoUrl.split('/').slice(-2).join('/'),
                branch: results.branch || selectedBranch,
              }

              setResult(scanResult)
              console.log('✅ Scan complete! Technologies:', scanResult.detected_technologies)
              console.log('✅ Scan complete! Findings:', scanResult.total_findings)

              fetchSuccess = true
            } catch (fetchError: any) {
              attempts++
              console.warn(`⚠️ Fetch attempt ${attempts}/${maxAttempts} failed:`, fetchError.response?.data?.detail || fetchError.message)

              if (attempts >= maxAttempts) {
                throw new Error(`Failed to fetch results after ${maxAttempts} attempts: ${fetchError.response?.data?.detail || fetchError.message}`)
              }

              const waitTime = Math.pow(2, attempts - 1) * 1000
              console.log(`⏳ Waiting ${waitTime}ms before retry...`)
              await new Promise(resolve => setTimeout(resolve, waitTime))
            }
          }
        }
      }, 500) // Check every 500ms

      // Timeout after 120 seconds (WebSocket should complete before this)
      const timeout = setTimeout(async () => {
        clearInterval(completionCheck)
        
        // Fallback: try to fetch results anyway
        try {
          const resultsResponse = await api.get(`/scan/results/${data.scan_id}`)
          const results = resultsResponse.data

          setProgress(100)
          setCurrentStep(stepsRef.current.length || 7)
          setLoading(false)
          const timeoutTechs = detectedTechRef.current
          setResult({
            success: true,
            scan_id: results.scan_id,
            security_score: results.security_score || 0,
            severity_counts: results.severity_counts || { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
            findings: results.findings || [],
            total_findings: getFindingsCount(results),
            files_analyzed: results.files_analyzed || results.filesAnalyzed || 0,
            devops_stack: results.devops_stack,
            detected_technologies: timeoutTechs.length > 0 ? timeoutTechs : (results.detected_technologies || []),
            repository_url: repoUrl,
            repository_name: repoUrl.split('/').slice(-2).join('/'),
            branch: selectedBranch,
          })
        } catch (fetchError: any) {
          console.error('Timeout fetch error:', fetchError)
          setError('Scan timed out. Please try again.')
          setLoading(false)
        }
      }, 120000)

      return () => {
        clearInterval(completionCheck)
        clearTimeout(timeout)
      }

    } catch (err: any) {
      console.error('Scan error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to analyze repository')
      setLoading(false)
    }
  }

  const handleNewScan = () => {
    setResult(null)
    setError(null)
    setProgress(0)
    setCurrentStep(0)
    setRepoUrl('')
  }

  // During rescan flow, show loading spinner while navigating to results page
  if (result && autoStart) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
            className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-400 rounded-full mx-auto"
          />
          <p className="text-muted-foreground">Opening results page...</p>
        </div>
      </div>
    )
  }

  // Render result if available - SHOW ON SAME PAGE (no redirect)
  if (result) {
    return (
      <div className="min-h-screen py-12">
        <div className="max-w-6xl mx-auto px-4 space-y-6">
          {/* Header with New Scan button */}
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Scan Results</h1>
              <p className="text-muted-foreground mt-1">
                {result.repository_name} • Branch: {result.branch}
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={handleNewScan}
              icon={<GitBranch className="h-4 w-4" />}
            >
              New Scan
            </Button>
          </div>

          {/* Result Component - Same as post-login */}
          <ResultComponent result={result} selectedBranch={selectedBranch} />
          
          {/* Login CTA for anonymous users */}
          {!isAuthenticated && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8"
            >
              <Card className="p-8 text-center glow-primary" hover={false}>
                <div className="max-w-2xl mx-auto space-y-6">
                  <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600">
                    <Lock className="h-8 w-8 text-white" />
                  </div>

                  <div>
                    <h2 className="text-2xl font-bold text-foreground">
                      Save Your Scan Results
                    </h2>
                    <p className="text-muted-foreground mt-2">
                      Create a free account to save this scan, track history, and get AI-powered fix recommendations.
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <Button
                      variant="primary"
                      size="lg"
                      onClick={() => navigate('/login')}
                      icon={<Github className="h-5 w-5" />}
                    >
                      Login with GitHub
                    </Button>
                    <Button
                      variant="secondary"
                      size="lg"
                      onClick={() => navigate('/register')}
                    >
                      Create Free Account
                      <ArrowRight className="h-5 w-5 ml-2" />
                    </Button>
                  </div>
                </div>
              </Card>
            </motion.div>
          )}
        </div>
      </div>
    )
  }

  // Render error if exists
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-8 max-w-md" hover={false}>
          <div className="text-center space-y-4">
            <AlertCircle className="h-12 w-12 text-red-400 mx-auto" />
            <h2 className="text-xl font-bold text-foreground">Scan Failed</h2>
            <p className="text-muted-foreground">{error}</p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={handleNewScan}
                className="flex-1"
              >
                Try Again
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate('/dashboard')}
                className="flex-1"
              >
                Go Home
              </Button>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  // Render progress if loading
  if (loading) {
    return (
      <div className="min-h-screen py-12">
        <div className="max-w-6xl w-full mx-auto px-6">
          {/* Scan Progress with Logs and File Tree */}
          <ScanProgress
            progress={progress}
            currentStep={currentStep}
            isComplete={progress >= 100}
            detectedTechnologies={detectedTechnologies}
            detectedFiles={filesList.map(path => ({
              path,
              type: getFileTypeFromPath(path),
              status: 'completed'
            }))}
            backendLogs={scanLogs}
            steps={stepsFromBackend.map(s => s.name)}
            filesScanned={filesList.length}
            findingsDetected={0}
          />
        </div>
      </div>
    )
  }

  // Render input form
  return (
    <div className="min-h-screen flex items-center justify-center py-12">
      <div className="max-w-2xl w-full mx-auto px-4 space-y-6">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-foreground">
            Analyze Your DevOps Architecture
          </h1>
          <p className="text-muted-foreground">
            Enter a GitHub repository URL to get a comprehensive security analysis
          </p>
        </div>

        <Card className="p-8" hover={false}>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-3">
                GitHub Repository URL
              </label>
              <div className="relative">
                <Github className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="url"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/organization/repository"
                  className="input pl-12 text-base py-3"
                  required
                />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Enter a public GitHub repository URL to analyze
              </p>
            </div>

            {/* Branch Selector */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-3">
                Branch
              </label>
              <div className="relative">
                <GitBranch className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <button
                  type="button"
                  onClick={() => setShowBranchDropdown(!showBranchDropdown)}
                  disabled={isFetchingBranches}
                  className="input pl-12 text-base py-3 w-full flex items-center justify-between bg-input hover:bg-input/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="text-foreground">
                    {isFetchingBranches ? (
                      <Loader2 className="h-4 w-4 animate-spin inline" />
                    ) : branches.length > 0 ? (
                      selectedBranch
                    ) : hasBranchesError ? (
                      <span className="text-yellow-400">Using default: {selectedBranch}</span>
                    ) : !repoUrl || !repoUrl.trim().startsWith('https://github.com/') ? (
                      <span className="text-muted-foreground">Enter GitHub URL</span>
                    ) : (
                      <span className="text-muted-foreground">{selectedBranch || 'main'}</span>
                    )}
                  </span>
                  <ChevronDown className={cn('h-4 w-4 transition-transform', showBranchDropdown && 'rotate-180')} />
                </button>

                {/* Branch Dropdown */}
                {showBranchDropdown && (
                  <div className="absolute z-50 w-full mt-1 max-h-60 overflow-auto rounded-lg border border-white/10 bg-card shadow-lg">
                    {isFetchingBranches ? (
                      <div className="px-4 py-3 text-sm text-muted-foreground flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Fetching branches...
                      </div>
                    ) : branches.length > 0 ? (
                      branches.map((branch) => (
                        <button
                          key={branch.name}
                          type="button"
                          onClick={() => {
                            setSelectedBranch(branch.name)
                            setShowBranchDropdown(false)
                          }}
                          className={cn(
                            'w-full px-4 py-2 text-left flex items-center gap-2 hover:bg-white/5 transition-colors',
                            selectedBranch === branch.name && 'bg-primary/10'
                          )}
                        >
                          <GitBranch className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm text-foreground">{branch.name}</span>
                          {branch.protected && (
                            <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                              Protected
                            </span>
                          )}
                        </button>
                      ))
                    ) : hasBranchesError ? (
                      <div className="px-4 py-3">
                        <div className="text-sm text-yellow-400 mb-2">⚠️ Could not fetch branches</div>
                        <div className="text-xs text-muted-foreground mb-3">
                          Using default branch. This happens with private repos or API rate limits.
                        </div>
                        <button
                          type="button"
                          onClick={() => setShowBranchDropdown(false)}
                          className="w-full px-3 py-2 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90"
                        >
                          Use {selectedBranch || 'main'}
                        </button>
                      </div>
                    ) : !repoUrl || !repoUrl.trim().startsWith('https://github.com/') ? (
                      <div className="px-4 py-3 text-sm text-muted-foreground">
                        Enter a GitHub URL to fetch branches
                      </div>
                    ) : (
                      <div className="px-4 py-3 text-sm text-muted-foreground flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading branches...
                      </div>
                    )}
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {branches.length > 0
                  ? `${branches.length} branch${branches.length !== 1 ? 'es' : ''} found • Using: ${selectedBranch}`
                  : isFetchingBranches
                    ? 'Fetching branches...'
                    : hasBranchesError
                      ? `Using default branch: ${selectedBranch}`
                      : repoUrl && repoUrl.trim().startsWith('https://github.com/')
                        ? 'Loading branches...'
                        : 'Select the branch to analyze'}
              </p>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={!repoUrl.trim()}
              className="w-full py-4 text-lg"
              glow
            >
              <GitBranch className="h-5 w-5" />
              Start Analysis
              <ArrowRight className="h-5 w-5" />
            </Button>
          </form>
        </Card>
      </div>
    </div>
  )
}

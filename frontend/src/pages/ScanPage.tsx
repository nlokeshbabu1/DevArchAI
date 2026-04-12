import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Github, ArrowRight, Loader2, AlertCircle, GitBranch, ChevronDown, Lock } from 'lucide-react'
import axios from 'axios'
import { Button, Card } from '../components/ui-animated'
import { cn } from '../lib/utils'
import { ScanProgress } from '../components/ScanProgress'
import { ResultComponent } from '../components/ResultComponent'
import { useAuthStore } from '../stores/auth-store'
import { scansApi } from '../api/endpoints/scans'

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
  const { isAuthenticated } = useAuthStore()
  
  // State management
  const [repoUrl, setRepoUrl] = useState('')
  const [selectedBranch, setSelectedBranch] = useState<string>('main')
  const [showBranchDropdown, setShowBranchDropdown] = useState(false)
  
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
  const [scanLogs, setScanLogs] = useState<string[]>([])  // Real logs from backend

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
        const response = await axios.get('/api/v1/github/branches', {
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

  // Update selected branch when branches are loaded
  useEffect(() => {
    console.log('📊 Branch data changed:', branchesData)
    if (branchesData?.default_branch) {
      setSelectedBranch(branchesData.default_branch)
      console.log('✅ Default branch set:', branchesData.default_branch)
    }
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

  // Poll real scan progress from API
  useEffect(() => {
    let pollInterval: NodeJS.Timeout
    if (loading && scanId) {
      pollInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get(`/api/v1/scan/status/${scanId}`)
          const status = statusResponse.data

          console.log('📊 Real scan status:', {
            progress: status.progress,
            status: status.status,
            current_step: status.current_step,
            logs_count: status.logs?.length || 0,
            files_list_length: status.files_list?.length || 0,
            files_scanned: status.files_scanned,
            has_files_list: 'files_list' in status,
            first_3_files: status.files_list?.slice(0, 3)
          })

          // Update progress from API
          if (status.progress) {
            setProgress(Math.round(status.progress))
          }

          // Update current step from API
          if (status.current_step) {
            // Backend returns current_step as a string, map it to a step number
            const stepMap: Record<string, number> = {
              'Connecting to GitHub': 1,
              'Fetching repository': 2,
              'Detecting technologies': 3,
              'Running security rules': 4,
              'Generating AI suggestions': 5,
              'Generating AI fixes': 5,
              'AI enrichment': 5,
              'Calculating score': 6,
              'Calculating scores': 6,
              'Saving results': 7,
              'Scan completed': 7,
              'completed': 7,
            }
            
            // If it's already a number, use it directly
            if (typeof status.current_step === 'number') {
              setCurrentStep(status.current_step)
            } else {
              // Map string to step number
              const stepStr = status.current_step.toLowerCase()
              let mappedStep = 1
              for (const [key, value] of Object.entries(stepMap)) {
                if (stepStr.includes(key.toLowerCase())) {
                  mappedStep = value
                  break
                }
              }
              setCurrentStep(mappedStep)
            }
          }

          // Update detected technologies from API (even after completion)
          if (status.detected_stack && Array.isArray(status.detected_stack) && status.detected_stack.length > 0) {
            console.log('✅ Technologies detected:', status.detected_stack)
            setDetectedTechnologies(status.detected_stack)
          }

          // Update files scanned count from API
          if (status.files_scanned !== undefined) {
            setFilesScanned(status.files_scanned)
          }

          // Update files list from API
          if (status.files_list && Array.isArray(status.files_list) && status.files_list.length > 0) {
            console.log('📁 Files detected:', status.files_list.length, 'First files:', status.files_list.slice(0, 3))
            setFilesList(status.files_list)
          }

          // ✅ CRITICAL: Accumulate REAL logs from backend (don't replace)
          if (status.logs && Array.isArray(status.logs)) {
            setScanLogs(prevLogs => {
              // Use Set to prevent duplicates while preserving order
              const logSet = new Set(prevLogs)
              let hasNewLogs = false
              
              for (const log of status.logs) {
                if (!logSet.has(log)) {
                  logSet.add(log)
                  hasNewLogs = true
                }
              }
              
              // Only update if there are new logs
              if (!hasNewLogs) return prevLogs
              
              // Performance optimization: Limit to last 200 logs to prevent memory issues
              const allLogs = Array.from(logSet)
              return allLogs.length > 200 ? allLogs.slice(-200) : allLogs
            })
          }

        } catch (error) {
          console.error('Polling error:', error)
        }
      }, 1000) // Poll every 1 second for faster updates
    }
    return () => clearInterval(pollInterval)
  }, [loading, scanId])

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
      const response = await axios.post('/api/v1/scan/start', {
        repository_url: trimmedUrl,
        branch: selectedBranch || 'main',
      })

      const data = response.data
      console.log('✅ Scan started:', data)

      if (!data.scan_id) {
        throw new Error('No scan_id returned from server')
      }

      // Save scan ID for polling
      setScanId(data.scan_id)

      // Wait for scan to complete on backend (poll every 1000ms)
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get(`/api/v1/scan/status/${data.scan_id}`)
          const status = statusResponse.data

          console.log('📊 Scan status:', status.status, 'progress:', status.progress)

          // ✅ Update progress from REAL backend API
          if (status.progress !== undefined) {
            setProgress(Math.round(status.progress))
          }

          // ✅ Update current step from REAL backend API
          if (status.current_step !== undefined) {
            // Backend returns current_step as a string, map it to a step number
            const stepMap: Record<string, number> = {
              'Connecting to GitHub': 1,
              'Fetching repository': 2,
              'Detecting technologies': 3,
              'Running security rules': 4,
              'Generating AI suggestions': 5,
              'Generating AI fixes': 5,
              'AI enrichment': 5,
              'Calculating score': 6,
              'Calculating scores': 6,
              'Saving results': 7,
              'Scan completed': 7,
              'completed': 7,
            }
            
            if (typeof status.current_step === 'number') {
              setCurrentStep(status.current_step)
            } else {
              const stepStr = String(status.current_step).toLowerCase()
              let mappedStep = 1
              for (const [key, value] of Object.entries(stepMap)) {
                if (stepStr.includes(key.toLowerCase())) {
                  mappedStep = value
                  break
                }
              }
              setCurrentStep(mappedStep)
            }
          }

          // ✅ Update detected technologies from backend
          if (status.detected_stack && Array.isArray(status.detected_stack)) {
            console.log('✅ Technologies detected:', status.detected_stack)
            setDetectedTechnologies(status.detected_stack)
            setFilesScanned(status.files_scanned || status.detected_stack.length)
          }

          // Only complete if BOTH backend is done AND minimum animation time has passed
          const elapsed = Date.now() - startTime
          const canComplete = status.status === 'completed' || status.progress >= 100
          const minTimePassed = elapsed >= MIN_ANIMATION_DURATION

          if (canComplete && minTimePassed) {
            clearInterval(pollInterval)

            // Fetch complete results with retry logic for race condition
            let attempts = 0
            const maxAttempts = 5
            let fetchSuccess = false

            while (attempts < maxAttempts && !fetchSuccess) {
              try {
                const resultsResponse = await axios.get(`/api/v1/scan/results/${data.scan_id}`)
                const results = resultsResponse.data

                console.log('✅ Complete results:', results)

                // Show 100% and complete
                setProgress(100)
                setCurrentStep(6)
                setLoading(false)

                // Create result object with detected technologies
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
                  total_findings: results.findings_count || results.findings?.length || 0,
                  files_analyzed: results.files_analyzed || results.filesAnalyzed || 0,  // Use backend value
                  devops_stack: results.devops_stack,
                  detected_technologies: detectedTechnologies.length > 0 ? detectedTechnologies : (results.detected_technologies || []),  // Use real data from polling
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
                
                // Wait before retrying (exponential backoff: 1s, 2s, 4s)
                const waitTime = Math.pow(2, attempts - 1) * 1000
                console.log(`⏳ Waiting ${waitTime}ms before retry...`)
                await new Promise(resolve => setTimeout(resolve, waitTime))
              }
            }

            // ✅ PHASE 3A: DO NOT navigate away - show results on same page
            // Results are already displayed inline via the `result` state
            // User can click "New Scan" button to start another scan
          } else if (canComplete && !minTimePassed) {
            // Backend is done but keep animation running
            console.log('⏳ Backend done, waiting for animation...', Math.round((MIN_ANIMATION_DURATION - elapsed) / 1000) + 's remaining')
          }
        } catch (pollError) {
          console.error('Polling error:', pollError)
        }
      }, 1000)

      // Timeout after 60 seconds
      setTimeout(async () => {
        clearInterval(pollInterval)

        // Even if polling fails, try to fetch results with retry logic
        let attempts = 0
        const maxAttempts = 5
        
        while (attempts < maxAttempts) {
          try {
            const resultsResponse = await axios.get(`/api/v1/scan/results/${data.scan_id}`)
            const results = resultsResponse.data
            
            setProgress(100)
            setCurrentStep(6)
            setLoading(false)
            setResult({
              success: true,
              scan_id: results.scan_id,
              security_score: results.security_score || 0,
              severity_counts: results.severity_counts || { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
              findings: results.findings || [],
              total_findings: results.findings_count || 0,
              files_analyzed: results.files_analyzed || results.filesAnalyzed || 0,  // Use backend value
              devops_stack: results.devops_stack,
              detected_technologies: detectedTechnologies.length > 0 ? detectedTechnologies : (results.detected_technologies || []),  // Use real data
              repository_url: repoUrl,
              repository_name: repoUrl.split('/').slice(-2).join('/'),
              branch: selectedBranch,
            })
            break
          } catch (fetchError: any) {
            attempts++
            console.warn(`⚠️ Timeout fetch attempt ${attempts}/${maxAttempts} failed:`, fetchError.response?.data?.detail || fetchError.message)
            
            if (attempts >= maxAttempts) {
              console.error('Fetch error:', fetchError)
              setError('Scan timed out. Please try again.')
              setLoading(false)
            } else {
              const waitTime = Math.pow(2, attempts - 1) * 1000
              await new Promise(resolve => setTimeout(resolve, waitTime))
            }
          }
        }
      }, 60000)

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
                onClick={() => navigate('/')}
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
            backendLogs={scanLogs}  // ✅ Pass real logs from backend
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

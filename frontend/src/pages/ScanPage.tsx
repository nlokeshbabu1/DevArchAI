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

  // Fetch branches when repo URL changes
  const { data: branchesData, isLoading: isLoadingBranches } = useQuery({
    queryKey: ['branches', repoUrl],
    queryFn: async () => {
      if (!repoUrl || !repoUrl.startsWith('https://github.com/')) {
        return { branches: [], default_branch: 'main' }
      }
      const response = await axios.get('/api/v1/github/branches', {
        params: { repo_url: repoUrl }
      })
      return response.data
    },
    enabled: !!repoUrl && repoUrl.startsWith('https://github.com/'),
    staleTime: 5 * 60 * 1000,
  })

  // Update selected branch when branches are loaded
  useEffect(() => {
    if (branchesData?.default_branch) {
      setSelectedBranch(branchesData.default_branch)
    }
  }, [branchesData])

  const branches: GitHubBranch[] = branchesData?.branches || []

  // Simulate progress while API is running
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (loading && progress < 90) {
      interval = setInterval(() => {
        setProgress((prev) => {
          const increment = Math.random() * 5 + 2
          const newProgress = Math.min(prev + increment, 90)
          
          // Update current step based on progress
          const step = Math.floor((newProgress / 100) * 6)
          setCurrentStep(Math.min(step, 5))
          
          return newProgress
        })
      }, 500)
    }
    return () => clearInterval(interval)
  }, [loading, progress])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!repoUrl.trim()) {
      setError('Please enter a repository URL')
      return
    }

    // Reset state
    setLoading(true)
    setProgress(0)
    setCurrentStep(0)
    setResult(null)
    setError(null)

    try {
      console.log('Starting scan for:', repoUrl, 'branch:', selectedBranch)

      // Minimum animation duration: 15 seconds
      const MIN_ANIMATION_DURATION = 15000
      const startTime = Date.now()

      // Clear any previous state
      setProgress(0)
      setCurrentStep(0)

      // Start progress animation - SLOWER (update every 500ms instead of 300ms)
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          // Slower increment: 2-4% per update instead of 6-9%
          const increment = Math.random() * 2 + 2
          const newProgress = Math.min(prev + increment, 90)
          const step = Math.floor((newProgress / 100) * 6)
          setCurrentStep(Math.min(step, 5))
          return newProgress
        })
      }, 500)

      // Use same endpoint for both authenticated and anonymous users
      const response = await axios.post('/api/v1/scan/start', {
        repository_url: repoUrl.trim(),
        branch: selectedBranch || 'main',
      })

      const data = response.data
      console.log('✅ Scan started:', data)

      if (!data.scan_id) {
        throw new Error('No scan_id returned from server')
      }

      // Wait for scan to complete on backend (poll every 1000ms instead of 500ms)
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get(`/api/v1/scan/status/${data.scan_id}`)
          const status = statusResponse.data

          console.log('📊 Scan status:', status.status, 'progress:', status.progress)

          // Only complete if BOTH backend is done AND minimum animation time has passed
          const elapsed = Date.now() - startTime
          const canComplete = status.status === 'completed' || status.progress >= 100
          const minTimePassed = elapsed >= MIN_ANIMATION_DURATION

          if (canComplete && minTimePassed) {
            clearInterval(pollInterval)
            clearInterval(progressInterval)

            // Fetch complete results
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
              files_analyzed: results.findings?.length || 0,
              devops_stack: results.devops_stack,
              detected_technologies: results.detected_technologies,
              repository_url: results.repository_url || repoUrl,
              repository_name: results.repository_name || repoUrl.split('/').slice(-2).join('/'),
              branch: results.branch || selectedBranch,
            }

            setResult(scanResult)
            console.log('✅ Scan complete! Findings:', scanResult.total_findings)
          } else if (canComplete && !minTimePassed) {
            // Backend is done but keep animation running
            console.log('⏳ Backend done, waiting for animation...', Math.round((MIN_ANIMATION_DURATION - elapsed) / 1000) + 's remaining')
          }
        } catch (pollError) {
          console.error('Polling error:', pollError)
        }
      }, 1000)

      // Timeout after 60 seconds
      setTimeout(() => {
        clearInterval(pollInterval)
        clearInterval(progressInterval)

        // Even if polling fails, try to fetch results
        axios.get(`/api/v1/scan/results/${data.scan_id}`)
          .then(resultsResponse => {
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
              files_analyzed: results.findings?.length || 0,
              devops_stack: results.devops_stack,
              detected_technologies: results.detected_technologies,
              repository_url: repoUrl,
              repository_name: repoUrl.split('/').slice(-2).join('/'),
              branch: selectedBranch,
            })
          })
          .catch(fetchError => {
            console.error('Fetch error:', fetchError)
            setError('Scan timed out. Please try again.')
            setLoading(false)
          })
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
      <div className="min-h-screen flex items-center justify-center py-12">
        <div className="max-w-3xl w-full mx-auto px-4 space-y-6">
          <ScanProgress
            progress={progress}
            currentStep={currentStep}
            isComplete={progress >= 100}
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
                  disabled={isLoadingBranches}
                  className="input pl-12 text-base py-3 w-full flex items-center justify-between bg-input hover:bg-input/80 transition-colors"
                >
                  <span className="text-foreground">
                    {isLoadingBranches ? (
                      <Loader2 className="h-4 w-4 animate-spin inline" />
                    ) : branches.length > 0 ? (
                      selectedBranch
                    ) : (
                      'Select branch'
                    )}
                  </span>
                  <ChevronDown className={cn('h-4 w-4 transition-transform', showBranchDropdown && 'rotate-180')} />
                </button>

                {/* Branch Dropdown */}
                {showBranchDropdown && (
                  <div className="absolute z-50 w-full mt-1 max-h-60 overflow-auto rounded-lg border border-white/10 bg-card shadow-lg">
                    {branches.length > 0 ? (
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
                    ) : (
                      <div className="px-4 py-3 text-sm text-muted-foreground">
                        No branches found
                      </div>
                    )}
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Select the branch to analyze
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

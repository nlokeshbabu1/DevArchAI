import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Github, ArrowRight, Loader2, AlertCircle, Check, GitBranch, Shield, Zap, BarChart3, Server, Cloud, FolderOpen, Brain, ChevronDown } from 'lucide-react'
import axios from 'axios'
import { Button, Card } from '../components/ui'
import { cn } from '../lib/utils'
import { ScanProgress } from './ScanProgress'

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

interface AnalysisResult {
  repo: string
  repo_url: string
  repo_owner: string
  repo_name: string
  devops_stack: DevOpsStack
  devops_score: number | null
  files_analyzed: number
  analysis_id: number
  created_at: string
  // New fields from updated API
  findings?: any[]
  security_score?: number
  severity_counts?: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
  }
  total_findings?: number
  repository_url?: string
}

interface GitHubBranch {
  name: string
  protected: boolean
  commit_sha: string
}

interface RepoAnalyzerInputProps {
  onAnalysisComplete?: (result: AnalysisResult) => void
}

const scanSteps = [
  { id: 1, text: 'Cloning GitHub Repository', icon: Github },
  { id: 2, text: 'Detecting DevOps Stack', icon: GitBranch },
  { id: 3, text: 'Parsing Infrastructure Files', icon: FolderOpen },
  { id: 4, text: 'Running Security Rules', icon: Shield },
  { id: 5, text: 'Generating AI Recommendations', icon: Brain },
  { id: 6, text: 'Calculating DevOps Score', icon: BarChart3 },
]

export function RepoAnalyzerInput({ onAnalysisComplete }: RepoAnalyzerInputProps) {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [selectedBranch, setSelectedBranch] = useState<string>('main')
  const [showBranchDropdown, setShowBranchDropdown] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [showProgress, setShowProgress] = useState(false)
  const [currentScanId, setCurrentScanId] = useState<string>('')
  const [currentStep, setCurrentStep] = useState(0)
  const [progressPercent, setProgressPercent] = useState(0)

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
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Update selected branch when branches are loaded
  useEffect(() => {
    if (branchesData?.default_branch) {
      setSelectedBranch(branchesData.default_branch)
    }
  }, [branchesData])

  const branches: GitHubBranch[] = branchesData?.branches || []

  const mutation = useMutation({
    mutationFn: async (url: string) => {
      // Call the unified analysis endpoint and get scan_id
      const response = await axios.post('/api/v1/analyze/repo', {
        repo_url: url,
        branch: selectedBranch || 'main'
      })

      const data = response.data
      const scanId = data.scan_id || `scan-${Date.now()}`
      setCurrentScanId(scanId)
      setShowProgress(true)

      return data
    },
    onSuccess: (data) => {
      setResult(data)
      onAnalysisComplete?.(data)
    },
    onError: () => {
      setShowProgress(false)
      setCurrentStep(0)
      setProgressPercent(0)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (repoUrl.trim()) {
      mutation.mutate(repoUrl.trim())
    }
  }

  const getScoreColor = (score: number | null) => {
    if (!score) return 'text-muted-foreground'
    if (score >= 90) return 'text-green-400'
    if (score >= 80) return 'text-blue-400'
    if (score >= 70) return 'text-yellow-400'
    if (score >= 60) return 'text-orange-400'
    return 'text-red-400'
  }

  const getScoreGrade = (score: number | null) => {
    if (!score) return 'N/A'
    if (score >= 90) return 'A'
    if (score >= 80) return 'B'
    if (score >= 70) return 'C'
    if (score >= 60) return 'D'
    return 'F'
  }

  const StackIndicator = ({ label, detected, icon: Icon }: { label: string; detected: boolean; icon: any }) => (
    <div className={cn(
      'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all',
      detected
        ? 'bg-green-500/10 border-green-500/30 text-green-400'
        : 'bg-white/5 border-white/10 text-muted-foreground'
    )}>
      <Icon className={cn('h-4 w-4', detected && 'text-green-400')} />
      <span className="text-sm font-medium">{label}</span>
      {detected && <Check className="h-3 w-3 ml-auto" />}
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Scan Progress Modal */}
      {showProgress && (
        <Card className="p-8 glow-primary animate-scale-in" hover={false}>
          <div className="space-y-6">
            {/* Header */}
            <div className="text-center space-y-2">
              <div className="inline-flex p-3 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-4">
                <GitBranch className="h-8 w-8 text-white animate-pulse" />
              </div>
              <h3 className="text-2xl font-bold text-foreground">Analyzing Repository</h3>
              <p className="text-muted-foreground">Please wait while we scan your infrastructure</p>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-medium text-primary">{progressPercent.toFixed(0)}%</span>
              </div>
              <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-indigo-500 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            {/* Scan Steps */}
            <div className="space-y-3">
              {scanSteps.map((step, index) => {
                const Icon = step.icon
                const isCompleted = index < currentStep
                const isCurrent = index === currentStep

                return (
                  <div
                    key={step.id}
                    className={cn(
                      'flex items-center gap-3 p-3 rounded-lg transition-all duration-300',
                      isCurrent
                        ? 'bg-primary/15 border border-primary/30'
                        : isCompleted
                        ? 'bg-green-500/10 border border-green-500/30'
                        : 'bg-white/5 border border-white/10'
                    )}
                  >
                    <div className={cn(
                      'p-2 rounded-lg transition-all duration-300',
                      isCurrent
                        ? 'bg-primary/20'
                        : isCompleted
                        ? 'bg-green-500/20'
                        : 'bg-white/10'
                    )}>
                      {isCompleted ? (
                        <Check className="h-4 w-4 text-green-400" />
                      ) : (
                        <Icon className={cn(
                          'h-4 w-4',
                          isCurrent ? 'text-primary animate-pulse' : 'text-muted-foreground'
                        )} />
                      )}
                    </div>
                    <span className={cn(
                      'text-sm font-medium transition-colors duration-300',
                      isCurrent
                        ? 'text-primary'
                        : isCompleted
                        ? 'text-green-400'
                        : 'text-muted-foreground'
                    )}>
                      {step.text}
                    </span>
                    {isCurrent && (
                      <div className="ml-auto">
                        <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </Card>
      )}

      {/* Input Card */}
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
                disabled={mutation.isPending}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Enter a public GitHub repository URL to analyze its DevOps configuration
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
                disabled={mutation.isPending || isLoadingBranches}
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
              Select the branch to analyze. Defaults to the repository's default branch.
            </p>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            disabled={mutation.isPending || !repoUrl.trim()}
            className="w-full py-4 text-lg"
            glow
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Analyzing Repository...
              </>
            ) : (
              <>
                <GitBranch className="h-5 w-5" />
                Analyze Repository
                <ArrowRight className="h-5 w-5" />
              </>
            )}
          </Button>
        </form>

        {mutation.isError && (
          <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3 backdrop-blur-sm">
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-400">
                Failed to analyze repository
              </p>
              <p className="text-sm text-red-400/80 mt-1">
                Please check the repository URL and ensure it's accessible.
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Results */}
      {result && result.findings && (
        <div className="space-y-6 animate-fade-in">
          {/* Score Card */}
          <Card className="p-8 glow-primary" hover={false}>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-foreground">{result.repo_name || result.repo || 'Repository'}</h2>
                <p className="text-muted-foreground mt-1">{result.repository_url || result.repo_url || ''}</p>
                {selectedBranch && (
                  <div className="flex items-center gap-2 mt-2 text-sm">
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Branch:</span>
                    <span className="font-medium text-primary">{selectedBranch}</span>
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className={cn('text-5xl font-bold', getScoreColor(result.security_score || result.devops_score))}>
                  {(result.security_score || result.devops_score || 0).toFixed(1)}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  Grade: <span className={cn('font-bold', getScoreColor(result.security_score || result.devops_score))}>
                    {getScoreGrade(result.security_score || result.devops_score)}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StackIndicator label="Docker" detected={result.devops_stack?.docker || false} icon={Server} />
              <StackIndicator label="Terraform" detected={result.devops_stack?.terraform || false} icon={Cloud} />
              <StackIndicator label="Kubernetes" detected={result.devops_stack?.kubernetes || false} icon={GitBranch} />
              <StackIndicator label="Helm" detected={result.devops_stack?.helm || false} icon={Cloud} />
              <StackIndicator label="CI/CD" detected={!!(result.devops_stack?.cicd) || false} icon={Zap} />
              <StackIndicator label="Monitoring" detected={result.devops_stack?.monitoring || false} icon={BarChart3} />
              <StackIndicator label="Security" detected={result.devops_stack?.security_scanning || false} icon={Shield} />
            </div>

            <div className="mt-6 pt-6 border-t border-white/10">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Files Analyzed</span>
                <span className="font-medium text-foreground">{result.files_analyzed || result.total_findings || 0}</span>
              </div>
            </div>
          </Card>

          {/* DevOps Stack Details */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Detected Tools */}
            <Card className="p-6" hover={false}>
              <h3 className="text-lg font-semibold mb-4 text-foreground">DevOps Stack Detected</h3>
              <div className="space-y-3">
                {result.devops_stack?.docker && (
                  <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Server className="h-4 w-4 text-green-400" />
                      <span className="font-medium text-green-400">Docker</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {result.devops_stack.docker_files?.length || 0} file(s) found
                    </p>
                  </div>
                )}
                {result.devops_stack?.terraform && (
                  <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Cloud className="h-4 w-4 text-purple-400" />
                      <span className="font-medium text-purple-400">Terraform</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {result.devops_stack.terraform_files?.length || 0} file(s) found
                    </p>
                  </div>
                )}
                {result.devops_stack?.kubernetes && (
                  <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <GitBranch className="h-4 w-4 text-blue-400" />
                      <span className="font-medium text-blue-400">Kubernetes</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {result.devops_stack.kubernetes_files?.length || 0} file(s) found
                    </p>
                  </div>
                )}
                {result.devops_stack?.cicd && (
                  <div className="p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-orange-400" />
                      <span className="font-medium text-orange-400">
                        CI/CD: {result.devops_stack.cicd.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {result.devops_stack.cicd_files?.length || 0} workflow file(s) found
                    </p>
                  </div>
                )}
                {result.devops_stack?.monitoring && (
                  <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-cyan-400" />
                      <span className="font-medium text-cyan-400">Monitoring</span>
                    </div>
                    {result.devops_stack?.prometheus && (
                      <span className="text-xs text-cyan-400/80">Prometheus</span>
                    )}
                    {result.devops_stack?.grafana && (
                      <span className="text-xs text-cyan-400/80 ml-2">Grafana</span>
                    )}
                  </div>
                )}
                {!result.devops_stack?.docker &&
                  !result.devops_stack?.terraform &&
                  !result.devops_stack?.kubernetes &&
                  !result.devops_stack?.cicd && (
                  <p className="text-muted-foreground text-sm">
                    No DevOps configuration detected. Consider adding Docker, Terraform, Kubernetes, or CI/CD pipelines.
                  </p>
                )}
              </div>
            </Card>

            {/* Missing Best Practices */}
            <Card className="p-6" hover={false}>
              <h3 className="text-lg font-semibold mb-4 text-foreground">Missing Best Practices</h3>
              <div className="space-y-3">
                {!result.devops_stack?.docker && (
                  <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-400" />
                      <span className="font-medium text-red-400">No Docker Configuration</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Add Dockerfile to containerize your application
                    </p>
                  </div>
                )}
                {!result.devops_stack?.cicd && (
                  <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-400" />
                      <span className="font-medium text-red-400">No CI/CD Pipeline</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Set up GitHub Actions or another CI/CD tool
                    </p>
                  </div>
                )}
                {!result.devops_stack?.monitoring && (
                  <div className="p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-orange-400" />
                      <span className="font-medium text-orange-400">No Monitoring</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Add Prometheus and Grafana for observability
                    </p>
                  </div>
                )}
                {!result.devops_stack?.security_scanning && (
                  <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-yellow-400" />
                      <span className="font-medium text-yellow-400">No Security Scanning</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Add security scanning to your CI/CD pipeline
                    </p>
                  </div>
                )}
                {result.devops_stack?.docker &&
                  result.devops_stack?.cicd &&
                  result.devops_stack?.monitoring &&
                  result.devops_stack?.security_scanning && (
                  <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
                    <Check className="h-6 w-6 text-green-400 mx-auto mb-2" />
                    <p className="font-medium text-green-400">All Best Practices Implemented!</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Your repository follows DevOps best practices
                    </p>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}

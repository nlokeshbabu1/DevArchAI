import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft, RotateCcw, Download, BookOpen, Shield, AlertTriangle,
  AlertCircle, Info, CheckCircle, FileCode, Terminal, ChevronDown,
  ChevronUp, Filter, SortAsc, Home, FolderGit2, Brain, Code, Sparkles,
  FileText,
  FileSpreadsheet
} from 'lucide-react'
import { Button, Card, ScoreCircle } from '../components/ui-animated'
import { Badge } from '../components/ui'
import { TechStackDisplay } from '../components/TechStackDisplay'
import { DiffViewer } from '../components/DiffViewer'
import { CreatePRButton } from '../components/CreatePRButton'
import { reportsApi } from '../api/endpoints/reports'
import { scansApi } from '../api/endpoints/scans'
import { cn } from '../lib/utils'

interface Finding {
  id: string
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path: string
  line_number?: number
  // AI Fix Generator fields
  summary?: string
  risk?: string
  impact?: string
  fix_code?: string
  fix_example?: string
  full_example?: string
  best_practices?: string[]
  confidence?: number
  confidence_score?: number
  documentation_url?: string
  ai_generated?: boolean
  // Code Diff fields
  before_code?: string
  after_code?: string
  unified_diff?: string
  // Legacy fields (fallback)
  ai_explanation?: string
  impact_analysis?: string
  code_fix?: string
}

interface ScanResult {
  id?: string  // Backend returns 'id' not 'scan_id'
  scan_id: string
  scan_status?: string
  ai_status?: 'pending' | 'processing' | 'completed' | 'failed'
  repository_url: string
  repository_name?: string
  security_score: number
  scalability_score?: number
  reliability_score?: number
  cost_score?: number
  observability_score?: number
  overall_score?: number
  severity_counts: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
  }
  findings: Finding[]
  findings_count?: number
  total_findings?: number
  files_analyzed: number
  branch: string
  completed_at: string
  detected_stack?: {
    docker_files?: string[]
    terraform_files?: string[]
    kubernetes_files?: string[]
    github_actions_files?: string[]
    helm_files?: string[]
    jenkins_files?: string[]
    [key: string]: any
  }
  detected_technologies?: string[]
  status?: string
}

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'
type SortOption = 'severity' | 'date'

export function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('severity')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [isRescanning, setIsRescanning] = useState(false)

  // Validate scan ID is a proper UUID (not ":id" literal)
  const isValidScanId = id && id !== ':id' && id.length > 10

  // Show error for invalid scan ID
  if (!isValidScanId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold text-foreground">Invalid Scan ID</h1>
          <p className="text-muted-foreground">The scan ID provided is not valid.</p>
          <Button onClick={() => navigate('/scans')}>View All Scans</Button>
        </div>
      </div>
    )
  }

  // Fetch scan results
  const { data: result, isLoading, error, refetch } = useQuery({
    queryKey: ['scan-result', id],
    queryFn: async () => {
      if (!id) throw new Error('No scan ID provided')
      const response = await scansApi.getScanResults(id)
      return response as ScanResult
    },
    enabled: isValidScanId,
    retry: 2,
    staleTime: 5 * 60 * 1000,  // Consider data fresh for 5 minutes
    refetchInterval: (query) => {
      const data = query.state.data as ScanResult | undefined
      return data?.ai_status === 'pending' || data?.ai_status === 'processing' ? 4000 : false
    },
  })

  // Filter and sort findings
  const filteredFindings = useMemo(() => {
    if (!result?.findings) return []

    let filtered = [...(result as ScanResult).findings]

    // Apply severity filter
    if (severityFilter !== 'all') {
      filtered = filtered.filter(f => f.severity === severityFilter)
    }

    // Apply sorting
    const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    filtered.sort((a, b) => {
      if (sortBy === 'severity') {
        return severityOrder[a.severity] - severityOrder[b.severity]
      }
      return 0 // Date sorting would need timestamp in finding
    })

    return filtered
  }, [result?.findings, severityFilter, sortBy])

  // Calculate severity counts from findings
  const severity_counts = useMemo(() => {
    if (!result?.findings) return { critical: 0, high: 0, medium: 0, low: 0, info: 0 }

    return (result as ScanResult).findings.reduce((acc, finding) => {
      const severity = finding.severity || 'info'
      acc[severity] = (acc[severity] || 0) + 1
      return acc
    }, { critical: 0, high: 0, medium: 0, low: 0, info: 0 } as Record<string, number>)
  }, [(result as ScanResult)?.findings])

  // Get top priority fixes (critical + high, max 3)
  const topPriorityFixes = useMemo(() => {
    if (!result?.findings) return []
    return (result as ScanResult).findings
      .filter(f => f.severity === 'critical' || f.severity === 'high')
      .slice(0, 3)
  }, [result?.findings])

  // Clean file path (remove /tmp/devarchai/... prefix)
  const cleanFilePath = (path: string) => {
    return path.replace(/\/tmp\/devarchai\/[^/]+\//, '')
  }

  // Type-safe result access
  const scanResult = result as ScanResult | undefined
  const isAiPending = scanResult?.ai_status === 'pending' || scanResult?.ai_status === 'processing'

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-500/10 text-red-400 border-red-500/30',
      high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
      medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
      low: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
      info: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
    }
    return colors[severity] || colors.info
  }

  const getSeverityIcon = (severity: string) => {
    const icons: Record<string, any> = {
      critical: AlertCircle,
      high: AlertTriangle,
      medium: Info,
      low: Info,
      info: Info,
    }
    return icons[severity] || Info
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 50) return 'text-orange-400'
    return 'text-red-400'
  }

  const downloadJsonFallback = () => {
    if (!scanResult) return

    const effectiveScanId = scanResult.scan_id || scanResult.id || id
    const reportData = {
      scan_id: effectiveScanId,
      repository_name: scanResult.repository_name || repoName,
      repository_url: scanResult.repository_url,
      branch: scanResult.branch || 'main',
      overall_score: scanResult.overall_score,
      security_score: scanResult.security_score,
      scalability_score: scanResult.scalability_score,
      reliability_score: scanResult.reliability_score,
      cost_score: scanResult.cost_score,
      observability_score: scanResult.observability_score,
      severity_counts,
      findings_count: scanResult.total_findings || scanResult.findings_count || scanResult.findings?.length || 0,
      files_analyzed: scanResult.files_analyzed,
      findings: scanResult.findings || [],
      generated_at: new Date().toISOString(),
    }

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `scan-report-${String(effectiveScanId).slice(0, 8)}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleDownload = async (format: 'pdf' | 'excel' = 'pdf') => {
    if (!scanResult || isDownloading) return

    const effectiveScanId = scanResult.scan_id || scanResult.id || id
    if (!effectiveScanId) {
      alert('Scan ID is missing. Please refresh and try again.')
      return
    }

    setIsDownloading(true)

    try {
      const downloadResponse = await reportsApi.downloadReport(effectiveScanId, format)
      const ext = format === 'pdf' ? 'pdf' : 'xlsx'
      const link = document.createElement('a')
      link.href = downloadResponse.url
      link.download = downloadResponse.filename || `report-${String(effectiveScanId).slice(0, 8)}.${ext}`
      link.rel = 'noopener noreferrer'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (error) {
      console.warn(`${format} download failed, falling back to JSON export:`, error)
      if (format === 'pdf') {
        downloadJsonFallback()
      }
    } finally {
      setIsDownloading(false)
    }
  }

  const handleRescan = async () => {
    if (!scanResult?.repository_url || isRescanning) return
    setIsRescanning(true)
    try {
      const response = await scansApi.startUnifiedScan({
        repository_url: scanResult.repository_url,
        branch: scanResult.branch || 'main',
      })
      if (response.scan_id) {
        navigate(`/scan`, { state: { scanId: response.scan_id } })
      }
    } catch (err: any) {
      console.error('Rescan failed:', err)
      alert(err.response?.data?.detail || 'Failed to start re-scan')
    } finally {
      setIsRescanning(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground">Loading scan results...</p>
        </div>
      </div>
    )
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-8 max-w-md text-center" hover={false}>
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">Error Loading Results</h2>
          <p className="text-muted-foreground mb-4">
            {(error as Error)?.message || 'Failed to load scan results'}
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => refetch()}>
              Retry
            </Button>
            <Button variant="ghost" onClick={() => navigate('/history')}>
              View History
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  const repoName = (result as ScanResult).repository_name || (result as ScanResult).repository_url.split('/').slice(-2).join('/')

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="container mx-auto px-4 max-w-7xl space-y-6">
        {/* Top Navigation */}
        <Card className="p-4" hover={false}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/scans')}
                icon={<ArrowLeft className="h-4 w-4" />}
              >
                Back to Scans
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleRescan}
                disabled={isRescanning || isLoading}
                icon={<RotateCcw className={`h-4 w-4 ${isRescanning ? 'animate-spin' : ''}`} />}
              >
                {isRescanning ? 'Scanning...' : 'Rescan'}
              </Button>
              <div className="relative group">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={isDownloading}
                  icon={<Download className="h-4 w-4" />}
                >
                  {isDownloading ? 'Downloading...' : 'Download'}
                </Button>
                {!isDownloading && (
                  <div className="absolute right-0 mt-1 w-44 py-1 bg-card border border-white/10 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                    <button
                      className="w-full px-4 py-2 text-sm text-left text-foreground hover:bg-white/5 flex items-center gap-2"
                      onClick={() => handleDownload('pdf')}
                    >
                      <FileText className="h-4 w-4" />
                      Download PDF
                    </button>
                    <button
                      className="w-full px-4 py-2 text-sm text-left text-foreground hover:bg-white/5 flex items-center gap-2"
                      onClick={() => handleDownload('excel')}
                    >
                      <FileSpreadsheet className="h-4 w-4" />
                      Download Excel
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center space-y-4"
        >
          <h1 className="text-3xl font-bold text-foreground">{repoName}</h1>
          <p className="text-muted-foreground">
            Branch: {(result as ScanResult).branch || 'main'} • Scanned: {new Date((result as ScanResult).completed_at).toLocaleString()}
          </p>
        </motion.div>

        {isAiPending && (
          <Card className="p-4 border border-primary/30 bg-primary/5" hover={false}>
            <div className="flex items-center gap-3">
              <Brain className="h-5 w-5 text-primary" />
              <div>
                <div className="text-sm font-semibold text-foreground">Static scan is complete</div>
                <div className="text-sm text-muted-foreground">
                  AI suggestions are still generating in the background. This page refreshes automatically.
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Score and Stats */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Security Score */}
          <Card className="p-6" hover={false}>
            <div className="text-center space-y-4">
              <h3 className="text-lg font-semibold text-foreground">Security Score</h3>
              <ScoreCircle score={(result as ScanResult).security_score || 0} size="xl" animated />
              <div className="text-sm text-muted-foreground">
                Grade: <span className={cn('font-bold', getScoreColor((result as ScanResult).security_score || 0))}>
                  {((result as ScanResult).security_score || 0) >= 90 ? 'A' : ((result as ScanResult).security_score || 0) >= 80 ? 'B' : ((result as ScanResult).security_score || 0) >= 70 ? 'C' : ((result as ScanResult).security_score || 0) >= 60 ? 'D' : 'F'}
                </span>
              </div>
            </div>
          </Card>

          {/* Category Scores */}
          <Card className="p-6" hover={false}>
            <h3 className="text-lg font-semibold text-foreground mb-4">Category Scores</h3>
            <div className="flex flex-wrap gap-4 justify-start">
              {/* Scalability */}
              <div className="min-w-[140px] p-6 rounded-xl border-2 border-blue-500/30 bg-blue-500/10 text-center">
                <div className={cn('text-4xl font-bold mb-2', getScoreColor((result as ScanResult).scalability_score || 0))}>
                  {Math.round((result as ScanResult).scalability_score || 0)}%
                </div>
                <div className="text-sm font-semibold text-blue-300">Scalability</div>
              </div>
              
              {/* Reliability */}
              <div className="min-w-[140px] p-6 rounded-xl border-2 border-purple-500/30 bg-purple-500/10 text-center">
                <div className={cn('text-4xl font-bold mb-2', getScoreColor((result as ScanResult).reliability_score || 0))}>
                  {Math.round((result as ScanResult).reliability_score || 0)}%
                </div>
                <div className="text-sm font-semibold text-purple-300">Reliability</div>
              </div>
              
              {/* Cost */}
              <div className="min-w-[140px] p-6 rounded-xl border-2 border-green-500/30 bg-green-500/10 text-center">
                <div className={cn('text-4xl font-bold mb-2', getScoreColor((result as ScanResult).cost_score || 0))}>
                  {Math.round((result as ScanResult).cost_score || 0)}%
                </div>
                <div className="text-sm font-semibold text-green-300">Cost</div>
              </div>
              
              {/* Observability */}
              <div className="min-w-[140px] p-6 rounded-xl border-2 border-cyan-500/30 bg-cyan-500/10 text-center">
                <div className={cn('text-4xl font-bold mb-2', getScoreColor((result as ScanResult).observability_score || 0))}>
                  {Math.round((result as ScanResult).observability_score || 0)}%
                </div>
                <div className="text-sm font-semibold text-cyan-300">Observability</div>
              </div>
            </div>
          </Card>

          {/* Severity Counts */}
          <Card className="p-6" hover={false}>
            <h3 className="text-lg font-semibold text-foreground mb-4">Issues by Severity</h3>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(severity_counts).map(([severity, count]) => {
                const Icon = getSeverityIcon(severity)
                return (
                  <div
                    key={severity}
                    className={cn(
                      'p-4 rounded-xl border text-center capitalize',
                      getSeverityColor(severity)
                    )}
                  >
                    <Icon className="h-6 w-6 mx-auto mb-2" />
                    <div className="text-2xl font-bold mb-1">{count}</div>
                    <div className="text-sm">{severity}</div>
                  </div>
                )
              })}
            </div>
          </Card>

          {/* Scan Info */}
          <Card className="p-6" hover={false}>
            <h3 className="text-lg font-semibold text-foreground mb-4">Scan Information</h3>
            <div className="space-y-4">
              <div>
                <div className="text-sm text-muted-foreground">Repository</div>
                <div className="font-medium text-foreground truncate">{(result as ScanResult).repository_url}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Files Analyzed</div>
                <div className="font-medium text-foreground">{(result as ScanResult).files_analyzed}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total Findings</div>
                <div className="font-medium text-foreground">{(result as ScanResult).findings_count || (result as ScanResult).total_findings || 0}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Scan ID</div>
                <div className="font-mono text-xs text-muted-foreground">{(result as ScanResult).scan_id}</div>
              </div>
            </div>
          </Card>

          {/* Detected Technology Stack */}
          {(result as ScanResult).detected_stack && (
            <Card className="p-6" hover={false}>
              <h3 className="text-lg font-semibold text-foreground mb-4">Detected Technology Stack</h3>
              <div className="flex flex-wrap gap-4 justify-start">
                {/* Docker */}
                {((result as ScanResult).detected_stack as any).docker_files && ((result as ScanResult).detected_stack as any).docker_files.length > 0 && (
                  <div className="min-w-[140px] p-6 rounded-xl border-2 border-blue-500/30 bg-blue-500/10 text-center">
                    <div className="text-4xl font-bold text-blue-400 mb-2">{((result as ScanResult).detected_stack as any).docker_files.length}</div>
                    <div className="text-sm font-semibold text-blue-300">Docker Files</div>
                  </div>
                )}
                
                {/* Terraform */}
                {((result as ScanResult).detected_stack as any).terraform_files && ((result as ScanResult).detected_stack as any).terraform_files.length > 0 && (
                  <div className="min-w-[140px] p-6 rounded-xl border-2 border-purple-500/30 bg-purple-500/10 text-center">
                    <div className="text-4xl font-bold text-purple-400 mb-2">{((result as ScanResult).detected_stack as any).terraform_files.length}</div>
                    <div className="text-sm font-semibold text-purple-300">Terraform Files</div>
                  </div>
                )}
                
                {/* Kubernetes */}
                {((result as ScanResult).detected_stack as any).kubernetes_files && ((result as ScanResult).detected_stack as any).kubernetes_files.length > 0 && (
                  <div className="min-w-[140px] p-6 rounded-xl border-2 border-cyan-500/30 bg-cyan-500/10 text-center">
                    <div className="text-4xl font-bold text-cyan-400 mb-2">{((result as ScanResult).detected_stack as any).kubernetes_files.length}</div>
                    <div className="text-sm font-semibold text-cyan-300">K8s Files</div>
                  </div>
                )}
                
                {/* GitHub Actions */}
                {((result as ScanResult).detected_stack as any).github_actions_files && ((result as ScanResult).detected_stack as any).github_actions_files.length > 0 && (
                  <div className="min-w-[140px] p-6 rounded-xl border-2 border-orange-500/30 bg-orange-500/10 text-center">
                    <div className="text-4xl font-bold text-orange-400 mb-2">{((result as ScanResult).detected_stack as any).github_actions_files.length}</div>
                    <div className="text-sm font-semibold text-orange-300">GitHub Actions</div>
                  </div>
                )}
                
                {/* Helm */}
                {((result as ScanResult).detected_stack as any).helm_files && ((result as ScanResult).detected_stack as any).helm_files.length > 0 && (
                  <div className="min-w-[140px] p-6 rounded-xl border-2 border-green-500/30 bg-green-500/10 text-center">
                    <div className="text-4xl font-bold text-green-400 mb-2">{((result as ScanResult).detected_stack as any).helm_files.length}</div>
                    <div className="text-sm font-semibold text-green-300">Helm Charts</div>
                  </div>
                )}
                
                {/* Jenkins */}
                {((result as ScanResult).detected_stack as any).jenkins_files && ((result as ScanResult).detected_stack as any).jenkins_files.length > 0 && (
                  <div className="min-w-[140px] p-6 rounded-xl border-2 border-red-500/30 bg-red-500/10 text-center">
                    <div className="text-4xl font-bold text-red-400 mb-2">{((result as ScanResult).detected_stack as any).jenkins_files.length}</div>
                    <div className="text-sm font-semibold text-red-300">Jenkins Files</div>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* Top Priority Fixes */}
        {topPriorityFixes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="p-6 glow-primary" hover={false}>
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="h-5 w-5 text-orange-400" />
                <h3 className="text-lg font-semibold text-foreground">Top Priority Fixes</h3>
              </div>
              <div className="space-y-3">
                {topPriorityFixes.map((finding, index) => {
                  const Icon = getSeverityIcon(finding.severity)
                  return (
                    <div
                      key={finding.id}
                      className="p-4 rounded-xl border border-orange-500/30 bg-orange-500/10"
                    >
                      <div className="flex items-start gap-3">
                        <Icon className="h-5 w-5 text-orange-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="secondary" className={getSeverityColor(finding.severity)}>
                              {finding.severity.toUpperCase()}
                            </Badge>
                            <span className="text-xs font-mono text-muted-foreground">
                              {finding.rule_id}
                            </span>
                          </div>
                          <h4 className="font-semibold text-foreground mb-1">
                            {finding.rule_name}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {finding.description}
                          </p>
                          <div className="mt-2 text-sm">
                            <code className="px-2 py-1 bg-black/30 rounded">
                              {cleanFilePath(finding.file_path)}
                              {finding.line_number && `:${finding.line_number}`}
                            </code>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          </motion.div>
        )}

        {/* Automated PR Creation */}
        {result && result.findings.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <CreatePRButton
              scanId={result.id || result.scan_id}
              findingIds={result.findings
                .filter(f => f.severity === 'critical' || f.severity === 'high')
                .map(f => f.id)}
              scoreBefore={result.security_score || 0}
              scoreAfter={Math.min(100, (result.security_score || 0) + 15)}
            />
          </motion.div>
        )}

        {/* Filters and Sorting */}
        <Card className="p-4" hover={false}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Filter:</span>
              <div className="flex gap-2">
                {(['all', 'critical', 'high', 'medium', 'low', 'info'] as const).map((severity) => (
                  <button
                    key={severity}
                    onClick={() => setSeverityFilter(severity)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                      severityFilter === severity
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-white/5 text-muted-foreground hover:bg-white/10'
                    )}
                  >
                    {severity.charAt(0).toUpperCase() + severity.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <SortAsc className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="severity">By Severity</option>
                <option value="date">By Date</option>
              </select>
            </div>
          </div>
        </Card>

        {/* Findings List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-foreground">
              All Findings ({filteredFindings.length})
            </h3>
            <Button
              variant="ghost"
              size="sm"
              icon={<BookOpen className="h-4 w-4" />}
            >
              Fix Guide
            </Button>
          </div>

          {filteredFindings.length === 0 ? (
            <Card className="p-12 text-center" hover={false}>
              <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">
                No findings found
              </h3>
              <p className="text-muted-foreground">
                {severityFilter === 'all'
                  ? 'Great! No issues detected in this scan.'
                  : 'No findings match the selected filter.'}
              </p>
            </Card>
          ) : (
            filteredFindings.map((finding, index) => {
              const Icon = getSeverityIcon(finding.severity)
              const isExpanded = expandedFinding === finding.id

              return (
                <motion.div
                  key={finding.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card className="overflow-hidden" hover={false}>
                    <div
                      className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
                      onClick={() => setExpandedFinding(isExpanded ? null : finding.id)}
                    >
                      <div className="flex items-start gap-4">
                        <div className={cn('p-2 rounded-lg', getSeverityColor(finding.severity))}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="secondary" className={getSeverityColor(finding.severity)}>
                              {finding.severity.toUpperCase()}
                            </Badge>
                            <span className="text-xs font-mono text-muted-foreground">
                              {finding.rule_id}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {finding.category}
                            </span>
                          </div>
                          <h4 className="font-semibold text-foreground mb-1">
                            {finding.rule_name}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {finding.description}
                          </p>
                          <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                            <code className="px-2 py-1 bg-black/30 rounded">
                              {cleanFilePath(finding.file_path)}
                              {finding.line_number && `:${finding.line_number}`}
                            </code>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {isExpanded ? (
                            <ChevronUp className="h-5 w-5 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-5 w-5 text-muted-foreground" />
                          )}
                        </div>
                      </div>
                    </div>

                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        className="px-4 pb-4 border-t border-white/10"
                      >
                        <div className="pt-4 space-y-4">
                          {/* AI Suggestion Header */}
                          {(finding.summary || finding.risk || finding.impact || finding.fix_code || finding.fix_example) && (
                            <div className="space-y-4">
                              <div className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30">
                                  <Brain className="h-5 w-5 text-primary" />
                                </div>
                                <div>
                                  <h5 className="text-sm font-semibold text-foreground">AI Suggestion</h5>
                                  {(finding.confidence || finding.confidence_score) && (
                                    <div className="flex items-center gap-2 mt-1">
                                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/30">
                                        {(finding.confidence || finding.confidence_score || 0) >= 0.8 ? 'High' : (finding.confidence || finding.confidence_score || 0) >= 0.6 ? 'Medium' : 'Low'} Confidence
                                      </span>
                                      <span className="text-xs text-muted-foreground">
                                        ({Math.round(((finding.confidence || finding.confidence_score) || 0.8) * 100)}%)
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Summary */}
                              {finding.summary && (
                                <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
                                  <div className="flex items-center gap-2 mb-2">
                                    <FileText className="h-4 w-4 text-primary" />
                                    <h6 className="text-xs font-semibold text-primary">Summary</h6>
                                  </div>
                                  <p className="text-sm text-muted-foreground">{finding.summary}</p>
                                </div>
                              )}

                              {/* Risk & Impact */}
                              {(finding.risk || finding.impact) && (
                                <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/30">
                                  <div className="flex items-center gap-2 mb-2">
                                    <AlertTriangle className="h-4 w-4 text-orange-400" />
                                    <h6 className="text-xs font-semibold text-orange-400">Risk & Impact</h6>
                                  </div>
                                  {finding.risk && (
                                    <div className="mb-2">
                                      <span className="text-xs font-medium text-orange-300">Risk: </span>
                                      <p className="text-sm text-orange-300 inline">{finding.risk}</p>
                                    </div>
                                  )}
                                  {finding.impact && (
                                    <div>
                                      <span className="text-xs font-medium text-orange-300">Impact: </span>
                                      <p className="text-sm text-orange-300 inline">{finding.impact}</p>
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Code Diff Viewer */}
                              {(finding.before_code && finding.after_code) && (
                                <div className="mt-4">
                                  <DiffViewer
                                    beforeCode={finding.before_code}
                                    afterCode={finding.after_code}
                                    unifiedDiff={finding.unified_diff}
                                    filename={finding.file_path || 'file'}
                                  />
                                </div>
                              )}

                              {/* Fix Code */}
                              {(finding.fix_code || finding.fix_example) && (
                                <div>
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <Code className="h-4 w-4 text-green-400" />
                                      <h6 className="text-xs font-semibold text-foreground">Suggested Fix</h6>
                                    </div>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 text-xs"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        navigator.clipboard.writeText(finding.fix_code || finding.fix_example || '')
                                      }}
                                    >
                                      Copy Fix
                                    </Button>
                                  </div>
                                  <div className="rounded-lg bg-black/50 border border-white/10 overflow-hidden">
                                    <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border-b border-white/10">
                                      <Terminal className="h-4 w-4 text-green-400" />
                                      <span className="text-xs font-medium text-green-400">Production-Ready Fix</span>
                                    </div>
                                    <pre className="p-4 overflow-x-auto max-h-[500px]">
                                      <code className="text-sm text-green-400 font-mono whitespace-pre">
                                        {finding.fix_code || finding.fix_example}
                                      </code>
                                    </pre>
                                  </div>
                                </div>
                              )}

                              {/* Full Example */}
                              {finding.full_example && (
                                <div>
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <FileCode className="h-4 w-4 text-blue-400" />
                                      <h6 className="text-xs font-semibold text-foreground">Full Example</h6>
                                    </div>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 text-xs"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        if (finding.full_example) {
                                          navigator.clipboard.writeText(finding.full_example)
                                        }
                                      }}
                                    >
                                      Copy Full
                                    </Button>
                                  </div>
                                  <pre className="p-4 bg-black/50 border border-white/10 rounded-lg overflow-x-auto max-h-[600px]">
                                    <code className="text-sm text-blue-300 font-mono whitespace-pre">
                                      {finding.full_example}
                                    </code>
                                  </pre>
                                </div>
                              )}

                              {/* Best Practices */}
                              {finding.best_practices && Array.isArray(finding.best_practices) && finding.best_practices.length > 0 && (
                                <div className="p-4 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
                                  <div className="flex items-center gap-2 mb-3">
                                    <Sparkles className="h-4 w-4 text-indigo-400" />
                                    <h6 className="text-xs font-semibold text-indigo-400">Best Practices</h6>
                                  </div>
                                  <ul className="space-y-2">
                                    {finding.best_practices.map((practice, idx) => (
                                      <li key={idx} className="flex items-start gap-2">
                                        <CheckCircle className="h-4 w-4 text-indigo-400 mt-0.5 flex-shrink-0" />
                                        <span className="text-sm text-indigo-300">{practice}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Fallback - Show old fields if no AI data */}
                          {!(finding.summary || finding.risk || finding.impact || finding.fix_code || finding.fix_example) && (
                            <>
                              {/* Recommendation */}
                              <div>
                                <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                                  <Terminal className="h-4 w-4" />
                                  How to Fix
                                </h5>
                                <p className="text-sm text-muted-foreground">
                                  {finding.recommendation}
                                </p>
                              </div>

                              {/* Code Fix Example */}
                              {finding.code_fix && (
                                <div>
                                  <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                                    <FileCode className="h-4 w-4" />
                                    Example Fix
                                  </h5>
                                  <pre className="text-xs bg-black/50 p-4 rounded-lg overflow-x-auto">
                                    <code className="text-green-400">
                                      {finding.code_fix}
                                    </code>
                                  </pre>
                                </div>
                              )}

                              {/* AI Explanation */}
                              {finding.ai_explanation && (
                                <div>
                                  <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                                    <Shield className="h-4 w-4" />
                                    Security Impact
                                  </h5>
                                  <p className="text-sm text-muted-foreground">
                                    {finding.ai_explanation}
                                  </p>
                                </div>
                              )}
                            </>
                          )}

                          {/* Actions */}
                          <div className="flex gap-2 pt-4 border-t border-white/10">
                            <Button 
                              variant="secondary" 
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                const code = finding.fix_code || finding.fix_example || finding.code_fix
                                if (code) navigator.clipboard.writeText(code)
                              }}
                            >
                              Copy Fix
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                const docUrl = finding.documentation_url || 'https://kubernetes.io/docs/'
                                window.open(docUrl, '_blank', 'noopener,noreferrer')
                              }}
                            >
                              <BookOpen className="h-4 w-4 mr-2" />
                              Documentation
                            </Button>
                            <Button variant="ghost" size="sm">
                              Create Issue
                            </Button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </Card>
                </motion.div>
              )
            })
          )}
        </div>

        {/* Bottom CTA */}
        <Card className="p-8 text-center glow-primary" hover={false}>
          <div className="max-w-2xl mx-auto space-y-4">
            <h3 className="text-xl font-bold text-foreground">
              Ready to Improve Your Security Score?
            </h3>
            <p className="text-muted-foreground">
              Fix the issues above and re-scan to verify improvements.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Button
                variant="primary"
                size="lg"
                onClick={handleRescan}
                disabled={isRescanning || isLoading}
                icon={<RotateCcw className={`h-5 w-5 ${isRescanning ? 'animate-spin' : ''}`} />}
                glow
              >
                {isRescanning ? 'Scanning...' : 'Re-scan Repository'}
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => navigate('/history')}
                icon={<FolderGit2 className="h-5 w-5" />}
              >
                View All Scans
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

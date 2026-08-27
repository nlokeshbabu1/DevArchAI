import { useState, useEffect, useRef } from 'react'
import { resolveSecurityScore } from '../lib/security-score'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Download,
  AlertCircle,
  ExternalLink,
  FileText,
  FileSpreadsheet,
  Clock,
  Shield,
  TrendingUp,
  Server,
  DollarSign,
  Activity,
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  Info,
  GitBranch,
  Zap,
  Cloud,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  FileDown,
  History,
  Fingerprint,
  Calendar,
  Target,
  BookOpen,
} from 'lucide-react'
import { Card, ScoreCircle, Button, SeverityBadge } from '../components/ui'
import { api } from '../lib/api'
import { reportsApi } from '../api/endpoints/reports'
import { cn, sanitizePath } from '../lib/utils'

interface Finding {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  risk?: string
  impact?: string
  fix_example?: string
  file_path: string
  line_number?: number
  resource_name?: string
  ai_explanation?: string
  impact_analysis?: string
  suggested_fix?: string
}

interface Scores {
  overall: number
  grade: string
  category_scores: Record<string, number>
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

export function Report() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'findings' | 'recommendations' | 'stack'>('findings')
  const [severityFilter, setSeverityFilter] = useState<string>('all')

  const state = location.state as {
    findings?: Finding[]
    scores?: Scores
    repoUrl?: string
    repoName?: string
    filesAnalyzed?: number
    devopsStack?: DevOpsStack
    branch?: string
  } | null

  // Also check sessionStorage for findings (fallback)
  const sessionFindings = typeof window !== 'undefined' ? JSON.parse(sessionStorage.getItem('latestFindings') || '[]') : []
  const sessionScores = typeof window !== 'undefined' ? JSON.parse(sessionStorage.getItem('latestScores') || '{}') : null

  const [findingsFromState] = useState<Finding[]>(state?.findings || sessionFindings || [])
  const [scoresFromState] = useState<Scores>(state?.scores || sessionScores || { overall: 0, grade: 'N/A', category_scores: {} })
  const [repoInfo] = useState({
    name: state?.repoName || 'Repository',
    url: state?.repoUrl || '',
    filesAnalyzed: state?.filesAnalyzed || 0,
  })
  const scannedBranch = state?.branch || sessionStorage.getItem('scannedBranch') || 'main'
  const [isDownloading, setIsDownloading] = useState(false)
  const [showDownloadMenu, setShowDownloadMenu] = useState(false)
  const [relatedReports, setRelatedReports] = useState<any[]>([])
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowDownloadMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const { data: report, isLoading } = useQuery({
    queryKey: ['report', id],
    queryFn: async () => {
      const reportResponse = await api.get(`/reports/${id}`)
      const reportData = reportResponse.data

      const findingsResponse = await api.get(`/scans/${reportData.scan_id}/findings`)
      const findingsData = findingsResponse.data

      const categoryIcons: Record<string, any> = {
        security: Shield,
        scalability: TrendingUp,
        reliability: Server,
        cost: DollarSign,
        observability: Activity,
      }

      const category_scores = Object.entries(reportData.category_scores || {}).map(([category, score]) => ({
        category,
        score: score as number,
        icon: categoryIcons[category] || Activity,
      }))

      return {
        id: reportData.id,
        scan_id: reportData.scan_id,
        repository_name: reportData.repository_name,
        repository_url: reportData.repository_url,
        overall_score: reportData.overall_score,
        created_at: reportData.created_at,
        analysis_duration_seconds: reportData.analysis_duration_seconds,
        files_analyzed: reportData.files_analyzed,
        category_scores,
        summary: {
          critical: reportData.critical_count || 0,
          high: reportData.high_count || 0,
          medium: reportData.medium_count || 0,
          low: reportData.low_count || 0,
          info: reportData.info_count || 0,
        },
        findings: findingsData.map((f: any) => ({
          rule_id: f.rule_id,
          rule_name: f.rule_name,
          severity: f.severity,
          category: f.category,
          description: f.description,
          recommendation: f.recommendation,
          file_path: f.file_path,
          ai_explanation: f.ai_explanation,
          impact_analysis: f.impact_analysis,
        })),
        organization_id: reportData.organization_id,
        total_findings: reportData.total_findings || 0,
        executive_summary: reportData.executive_summary,
        prioritized_recommendations: reportData.prioritized_recommendations || [],
      }
    },
    enabled: !!id && !state?.findings,
  })

  useEffect(() => {
    if (report?.organization_id && report?.repository_url) {
      reportsApi.listReports(report.organization_id).then((allReports) => {
        const related = allReports
          .filter((r) => r.repository_url === report.repository_url && r.id !== report.id)
          .slice(0, 5)
        setRelatedReports(related)
      }).catch(() => {})
    }
  }, [report?.id])

  const handleDownloadJson = async () => {
    setIsDownloading(true)
    setShowDownloadMenu(false)
    try {
      const reportData = {
        repository: repoInfo.name,
        url: repoInfo.url,
        branch: scannedBranch,
        analyzedAt: new Date().toISOString(),
        scores: finalScores,
        findings: filteredFindings.map((f: Finding) => ({
          ...f,
          file_path: sanitizePath(f.file_path),
        })),
        summary: severitySummary,
      }

      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = url
      a.download = `devarchai-report-${repoInfo.name.replace(/[^a-z0-9]/gi, '-')}-${Date.now()}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download failed:', error)
    } finally {
      setIsDownloading(false)
    }
  }

  const handleDownloadPdf = async () => {
    const scanId = report?.scan_id
    if (!scanId) return
    setIsDownloading(true)
    setShowDownloadMenu(false)
    try {
      const downloadResponse = await reportsApi.downloadReport(scanId, 'pdf')
      const a = document.createElement('a')
      a.href = downloadResponse.url
      a.download = downloadResponse.filename || `report-${scanId}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (error) {
      console.error('PDF download failed:', error)
    } finally {
      setIsDownloading(false)
    }
  }

  const handleDownloadExcel = async () => {
    const scanId = report?.scan_id
    if (!scanId) return
    setIsDownloading(true)
    setShowDownloadMenu(false)
    try {
      const downloadResponse = await reportsApi.downloadReport(scanId, 'excel')
      const a = document.createElement('a')
      a.href = downloadResponse.url
      a.download = downloadResponse.filename || `report-${scanId}.xlsx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (error) {
      console.error('Excel download failed:', error)
    } finally {
      setIsDownloading(false)
    }
  }

  const finalFindings = state?.findings || report?.findings || []
  const reportResolved = resolveSecurityScore({ overall_score: report?.overall_score })
  const finalScores = state?.scores || {
    overall: reportResolved?.value ?? 0,
    grade: reportResolved?.grade ?? 'N/A',
    category_scores: report?.category_scores || {},
  }
  const finalRepoInfo = state?.findings ? {
    name: state.repoName || 'Repository',
    url: state.repoUrl || '',
    filesAnalyzed: state.filesAnalyzed || 0,
  } : {
    name: report?.repository_name || 'Repository',
    url: report?.repository_url || '',
    filesAnalyzed: Array.isArray(report?.files_analyzed) ? report.files_analyzed.length : 0,
  }

  const severitySummary = finalFindings.reduce((acc: Record<string, number>, f: Finding) => {
    acc[f.severity] = (acc[f.severity] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const totalFindings = finalFindings.length

  const filteredFindings = severityFilter === 'all' 
    ? finalFindings 
    : finalFindings.filter((f: Finding) => f.severity === severityFilter)

  const findingsBySeverity = {
    critical: finalFindings.filter((f: Finding) => f.severity === 'critical'),
    high: finalFindings.filter((f: Finding) => f.severity === 'high'),
    medium: finalFindings.filter((f: Finding) => f.severity === 'medium'),
    low: finalFindings.filter((f: Finding) => f.severity === 'low' || f.severity === 'info'),
  }

  const devopsStack = state?.devopsStack || {
    docker: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('docker')),
    docker_files: [],
    terraform: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('.tf')),
    terraform_files: [],
    kubernetes: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('k8s') || f.file_path?.toLowerCase().includes('kubernetes')),
    kubernetes_files: [],
    helm: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('helm')),
    helm_files: [],
    cicd: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('.github') || f.file_path?.toLowerCase().includes('ci')) ? 'github_actions' : null,
    cicd_files: [],
    monitoring: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('prometheus') || f.file_path?.toLowerCase().includes('grafana')),
    monitoring_files: [],
    prometheus: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('prometheus')),
    grafana: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('grafana')),
    ansible: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('ansible')),
    pulumi: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('pulumi')),
    security_scanning: finalFindings.some((f: Finding) => f.file_path?.toLowerCase().includes('security') || f.file_path?.toLowerCase().includes('scan')),
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Shield className="h-6 w-6 text-primary animate-pulse" />
          </div>
        </div>
      </div>
    )
  }

  if (!report && !state?.findings) {
    return (
      <Card className="p-12 text-center" hover={false}>
        <AlertCircle className="h-16 w-16 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2 text-foreground">Report Not Found</h2>
        <p className="text-muted-foreground mb-6">The requested report could not be found.</p>
        <Button onClick={() => navigate('/scan')}>Go Back</Button>
      </Card>
    )
  }

  return (
    <div className="space-y-8">
      {/* Back Button */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/scan')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Analysis
        </Button>
        <button
          onClick={() => navigate('/docs/security-findings')}
          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors ml-auto"
          title="View Security Findings documentation"
        >
          <BookOpen className="h-4 w-4" />
        </button>
      </div>

      {/* Scan Passport */}
      <Card className="overflow-hidden" hover={false}>
        <div className="flex items-center gap-2 px-6 pt-4 pb-2 border-b border-white/5">
          <Fingerprint className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-primary uppercase tracking-wider">Scan Passport</span>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Fingerprint className="h-3 w-3" />
                Scan ID
              </span>
              <span className="block font-mono text-sm text-foreground truncate">
                {report?.scan_id || state?.findings ? (report?.scan_id || 'N/A').substring(0, 12) + '...' : 'N/A'}
              </span>
            </div>
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <GitBranch className="h-3 w-3" />
                Repository
              </span>
              <div className="flex items-center gap-1.5">
                <span className="block text-sm text-foreground truncate font-medium">{finalRepoInfo.name}</span>
                {finalRepoInfo.url && (
                  <a href={finalRepoInfo.url} target="_blank" rel="noopener noreferrer" className="shrink-0 hover:text-primary transition-colors">
                    <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
                  </a>
                )}
              </div>
            </div>
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="h-3 w-3" />
                Generated
              </span>
              <span className="block text-sm text-foreground">
                {report?.created_at
                  ? new Date(report.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                  : state?.findings
                    ? 'Just now'
                    : 'N/A'
                }
              </span>
            </div>
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Target className="h-3 w-3" />
                Score
              </span>
              <span className="block text-sm font-bold text-foreground">
                {finalScores.overall.toFixed(0)}
                <span className="text-muted-foreground font-normal text-xs ml-1">
                  {finalScores.grade}
                </span>
              </span>
            </div>
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="h-3 w-3" />
                Findings
              </span>
              <div className="flex items-center gap-2">
                <span className="block text-sm font-bold text-foreground">{totalFindings}</span>
                <div className="flex gap-1">
                  {severitySummary.critical > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-mono font-bold">
                      {severitySummary.critical}C
                    </span>
                  )}
                  {severitySummary.high > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 font-mono font-bold">
                      {severitySummary.high}H
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{finalRepoInfo.name}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {state?.findings
              ? 'Deep analysis with AI-powered findings'
              : `Analyzed on ${report?.created_at ? new Date(report.created_at).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                }) : 'N/A'}`
            }
          </p>
        </div>
        <div className="relative" ref={menuRef}>
          <Button variant="secondary" onClick={() => setShowDownloadMenu(!showDownloadMenu)} disabled={isDownloading}>
            <FileDown className="h-4 w-4" />
            {isDownloading ? 'Downloading...' : 'Export'}
            <ChevronDown className={cn('h-4 w-4 ml-1 transition-transform', showDownloadMenu && 'rotate-180')} />
          </Button>
          {showDownloadMenu && (
            <div className="absolute right-0 top-full mt-1 min-w-[180px] bg-gray-900 border border-white/10 rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-50">
              <button
                onClick={handleDownloadPdf}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-foreground hover:bg-white/5 transition-colors"
              >
                <FileText className="h-4 w-4 text-primary" />
                <span>PDF Report</span>
              </button>
              <button
                onClick={handleDownloadExcel}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-foreground hover:bg-white/5 transition-colors border-t border-white/5"
              >
                <FileSpreadsheet className="h-4 w-4 text-green-400" />
                <span>Excel Report</span>
              </button>
              <button
                onClick={handleDownloadJson}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-foreground hover:bg-white/5 transition-colors border-t border-white/5"
              >
                <Download className="h-4 w-4 text-yellow-400" />
                <span>JSON Report</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Score Overview */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-8 text-center" hover={false}>
          <h3 className="text-sm font-medium text-muted-foreground mb-6">Overall Score</h3>
          <ScoreCircle score={finalScores.overall} size="xl" animated delay={200} />
        </Card>

        <Card className="p-6" hover={false}>
          <h3 className="text-sm font-medium text-muted-foreground mb-4">Findings Summary</h3>
          <div className="space-y-3">
            {[
              { label: 'Critical', count: severitySummary.critical || 0, color: 'text-red-400', bg: 'bg-red-500/15', border: 'border-red-500/30' },
              { label: 'High', count: severitySummary.high || 0, color: 'text-orange-400', bg: 'bg-orange-500/15', border: 'border-orange-500/30' },
              { label: 'Medium', count: severitySummary.medium || 0, color: 'text-yellow-400', bg: 'bg-yellow-500/15', border: 'border-yellow-500/30' },
              { label: 'Low', count: (severitySummary.low || 0) + (severitySummary.info || 0), color: 'text-green-400', bg: 'bg-green-500/15', border: 'border-green-500/30' },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${item.bg} border ${item.border}`} />
                  <span className="text-sm text-foreground">{item.label}</span>
                </div>
                <span className={`font-bold ${item.color}`}>{item.count}</span>
              </div>
            ))}
          </div>
          <div className="mt-6 pt-4 border-t border-white/10">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total Findings</span>
              <span className="text-lg font-bold text-foreground">{totalFindings}</span>
            </div>
          </div>
        </Card>

        <Card className="p-6" hover={false}>
          <h3 className="text-sm font-medium text-muted-foreground mb-4">Analysis Details</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                <Clock className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Duration</p>
                <p className="font-medium text-foreground">{state?.findings ? 'Real-time' : `${report?.analysis_duration_seconds?.toFixed(1) || 'N/A'}s`}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                <FileText className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Files Analyzed</p>
                <p className="font-medium text-foreground">{finalRepoInfo.filesAnalyzed}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                <Shield className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Rules Checked</p>
                <p className="font-medium text-foreground">35+</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Category Scores */}
      {Object.keys(finalScores.category_scores).length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4 text-foreground">Category Scores</h2>
          <div className="grid gap-4 md:grid-cols-5">
            {Object.entries(finalScores.category_scores).map(([category, score]) => {
              const scoreColor = getCategoryColor(score as number)
              return (
                <Card key={category} className="p-5 text-center" hover>
                  <div className={cn(
                    'inline-flex p-3 rounded-xl mb-3 border border-white/10',
                    scoreColor.bg
                  )}>
                    <Shield className={cn('h-5 w-5', scoreColor.text)} />
                  </div>
                  <div className={cn('text-2xl font-bold', scoreColor.text)}>
                    {(score as number).toFixed(0)}
                  </div>
                  <div className="text-sm text-muted-foreground capitalize mt-1">
                    {category}
                  </div>
                  <div className="w-full h-1.5 bg-white/10 rounded-full mt-3 overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-500',
                        scoreColor.bg.replace('/15', '')
                      )}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* Detected Infrastructure Stack */}
      <div>
        <h2 className="text-lg font-semibold mb-4 text-foreground">Detected Infrastructure Stack</h2>
        <Card className="p-6" hover={false}>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {devopsStack.docker && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/30">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-green-500/20 rounded-lg">
                    <Server className="h-5 w-5 text-green-400" />
                  </div>
                  <span className="font-semibold text-green-400">Docker</span>
                </div>
                <p className="text-xs text-muted-foreground">Container configuration detected</p>
              </div>
            )}
            {devopsStack.terraform && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-indigo-500/10 border border-purple-500/30">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-purple-500/20 rounded-lg">
                    <Cloud className="h-5 w-5 text-purple-400" />
                  </div>
                  <span className="font-semibold text-purple-400">Terraform</span>
                </div>
                <p className="text-xs text-muted-foreground">Infrastructure as Code</p>
              </div>
            )}
            {devopsStack.kubernetes && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/30">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-blue-500/20 rounded-lg">
                    <GitBranch className="h-5 w-5 text-blue-400" />
                  </div>
                  <span className="font-semibold text-blue-400">Kubernetes</span>
                </div>
                <p className="text-xs text-muted-foreground">Container orchestration</p>
              </div>
            )}
            {devopsStack.cicd && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-orange-500/10 to-red-500/10 border border-orange-500/30">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-orange-500/20 rounded-lg">
                    <Zap className="h-5 w-5 text-orange-400" />
                  </div>
                  <span className="font-semibold text-orange-400">CI/CD</span>
                </div>
                <p className="text-xs text-muted-foreground">Automated pipelines</p>
              </div>
            )}
            {devopsStack.monitoring && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-teal-500/10 border border-cyan-500/30">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-cyan-500/20 rounded-lg">
                    <BarChart3 className="h-5 w-5 text-cyan-400" />
                  </div>
                  <span className="font-semibold text-cyan-400">Monitoring</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {devopsStack.prometheus && 'Prometheus'}
                  {devopsStack.prometheus && devopsStack.grafana && ' + '}
                  {devopsStack.grafana && 'Grafana'}
                </p>
              </div>
            )}
            {devopsStack.helm && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-500/10 to-blue-500/10 border border-indigo-500/30">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-indigo-500/20 rounded-lg">
                    <Cloud className="h-5 w-5 text-indigo-400" />
                  </div>
                  <span className="font-semibold text-indigo-400">Helm</span>
                </div>
                <p className="text-xs text-muted-foreground">Kubernetes package manager</p>
              </div>
            )}
            {!devopsStack.docker && !devopsStack.terraform && !devopsStack.kubernetes && !devopsStack.cicd && (
              <p className="text-muted-foreground col-span-full">
                No specific DevOps tools detected. The repository may use alternative infrastructure solutions.
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* Report History */}
      {(relatedReports.length > 0 || report?.id) && (
        <div>
          <h2 className="text-lg font-semibold mb-4 text-foreground flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Report History
          </h2>
          <div className="space-y-2">
            {/* Current report */}
            {report?.id && report?.created_at && (
              <div className="flex items-center justify-between p-4 rounded-xl bg-primary/5 border border-primary/20">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="p-2 rounded-lg bg-primary/10 shrink-0">
                    <FileText className="h-4 w-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">Current Report</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-mono font-bold">LATEST</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Score {reportResolved?.value?.toFixed(0) ?? '—'} · {report.total_findings} findings · {new Date(report.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </p>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground hidden sm:block">{report.id.substring(0, 8)}</span>
              </div>
            )}
            {/* Related reports */}
            {relatedReports.map((related) => (
              <div
                key={related.id}
                className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10 hover:border-primary/30 transition-colors cursor-pointer"
                onClick={() => navigate(`/reports/${related.id}`)}
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="p-2 rounded-lg bg-white/5 shrink-0">
                    <History className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-foreground truncate">{related.repository_name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Score {resolveSecurityScore({ overall_score: related.overall_score })?.value?.toFixed(0) ?? '—'} · {related.total_findings} findings · {related.created_at ? new Date(related.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A'}
                    </p>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground hidden sm:block">{related.id.substring(0, 8)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/10">
        <button
          onClick={() => setActiveTab('findings')}
          className={cn(
            'px-4 py-3 text-sm font-medium border-b-2 transition-all duration-200',
            activeTab === 'findings'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          All Findings ({finalFindings.length})
        </button>
        <button
          onClick={() => setActiveTab('recommendations')}
          className={cn(
            'px-4 py-3 text-sm font-medium border-b-2 transition-all duration-200',
            activeTab === 'recommendations'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          AI Architecture Insights
        </button>
      </div>

      {/* Content based on active tab */}
      {activeTab === 'findings' ? (
        <div className="space-y-6">
          {/* Severity Filter */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant={severityFilter === 'all' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setSeverityFilter('all')}
            >
              All ({totalFindings})
            </Button>
            {(['critical', 'high', 'medium', 'low'] as const).map((severity) => (
              findingsBySeverity[severity].length > 0 && (
                <Button
                  key={severity}
                  variant={severityFilter === severity ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setSeverityFilter(severity)}
                  className={cn(
                    severityFilter === severity && severity === 'critical' && 'bg-red-500 hover:bg-red-600',
                    severityFilter === severity && severity === 'high' && 'bg-orange-500 hover:bg-orange-600',
                    severityFilter === severity && severity === 'medium' && 'bg-yellow-500 hover:bg-yellow-600',
                    severityFilter === severity && severity === 'low' && 'bg-green-500 hover:bg-green-600',
                  )}
                >
                  {severity.charAt(0).toUpperCase() + severity.slice(1)} ({findingsBySeverity[severity].length})
                </Button>
              )
            ))}
          </div>

          {/* Findings grouped by severity */}
          {severityFilter === 'all' ? (
            <div className="space-y-6">
              {findingsBySeverity.critical.length > 0 && (
                <SeverityGroup severity="critical" findings={findingsBySeverity.critical} expandedFinding={expandedFinding} setExpandedFinding={setExpandedFinding} />
              )}
              {findingsBySeverity.high.length > 0 && (
                <SeverityGroup severity="high" findings={findingsBySeverity.high} expandedFinding={expandedFinding} setExpandedFinding={setExpandedFinding} />
              )}
              {findingsBySeverity.medium.length > 0 && (
                <SeverityGroup severity="medium" findings={findingsBySeverity.medium} expandedFinding={expandedFinding} setExpandedFinding={setExpandedFinding} />
              )}
              {findingsBySeverity.low.length > 0 && (
                <SeverityGroup severity="low" findings={findingsBySeverity.low} expandedFinding={expandedFinding} setExpandedFinding={setExpandedFinding} />
              )}
            </div>
          ) : (
            <Card padding="none" hover={false}>
              <div className="divide-y divide-white/10">
                {filteredFindings.map((finding: Finding, index: number) => (
                  <FindingCard
                    key={index}
                    ruleId={finding.rule_id}
                    ruleName={finding.rule_name}
                    severity={finding.severity}
                    category={finding.category}
                    description={finding.description}
                    recommendation={finding.recommendation}
                    filePath={finding.file_path}
                    aiExplanation={finding.ai_explanation}
                    impactAnalysis={finding.impact_analysis}
                    suggestedFix={finding.recommendation}
                    expanded={expandedFinding === index}
                    onToggle={() => setExpandedFinding(expandedFinding === index ? null : index)}
                  />
                ))}
              </div>
            </Card>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {finalFindings.map((rec: Finding, idx: number) => (
            <Card key={idx} className="p-6" hover>
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className={cn(
                      'p-3 rounded-xl border',
                      rec.severity === 'critical' ? 'bg-red-500/15 border-red-500/30' :
                      rec.severity === 'high' ? 'bg-orange-500/15 border-orange-500/30' :
                      rec.severity === 'medium' ? 'bg-yellow-500/15 border-yellow-500/30' :
                      'bg-green-500/15 border-green-500/30'
                    )}>
                      <AlertTriangle className={cn(
                        'h-6 w-6',
                        rec.severity === 'critical' ? 'text-red-400' :
                        rec.severity === 'high' ? 'text-orange-400' :
                        rec.severity === 'medium' ? 'text-yellow-400' :
                        'text-green-400'
                      )} />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-foreground">{rec.rule_name}</h3>
                      <SeverityBadge severity={rec.severity} size="sm" />
                    </div>
                    <p className="text-muted-foreground mb-3">{rec.description}</p>
                    {rec.file_path && (
                      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground font-mono">{sanitizePath(rec.file_path)}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Why this matters */}
                <div className="p-4 rounded-xl bg-orange-500/10 border border-orange-500/30">
                  <div className="flex items-center gap-2 mb-2">
                    <Info className="h-4 w-4 text-orange-400" />
                    <span className="text-sm font-semibold text-orange-400">Why this matters</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {rec.impact_analysis || rec.ai_explanation || 'This issue could impact the security, scalability, or reliability of your infrastructure.'}
                  </p>
                </div>

                {/* Recommended Fix */}
                <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="h-4 w-4 text-green-400" />
                    <span className="text-sm font-semibold text-green-400">Recommended Fix</span>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">{rec.recommendation}</p>
                  {rec.suggested_fix && (
                    <pre className="text-sm text-foreground bg-black/30 p-3 rounded-lg overflow-x-auto border border-white/10">
                      <code>{rec.suggested_fix}</code>
                    </pre>
                  )}
                </div>

                {/* AI Explanation */}
                {rec.ai_explanation && (
                  <div className="p-4 rounded-xl bg-gradient-to-br from-primary/10 to-indigo-600/10 border border-primary/30">
                    <div className="flex items-center gap-2 mb-2">
                      <Lightbulb className="h-4 w-4 text-primary" />
                      <span className="text-sm font-semibold text-primary">AI Insight</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{rec.ai_explanation}</p>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function SeverityGroup({ 
  severity, 
  findings, 
  expandedFinding, 
  setExpandedFinding 
}: { 
  severity: string
  findings: Finding[]
  expandedFinding: number | null
  setExpandedFinding: (index: number | null) => void
}) {
  const [isExpanded, setIsExpanded] = useState(true)
  
  const config = {
    critical: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', icon: AlertTriangle },
    high: { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', icon: AlertTriangle },
    medium: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: AlertCircle },
    low: { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400', icon: CheckCircle },
  }
  
  const { bg, border, text, icon: Icon } = config[severity as keyof typeof config]

  return (
    <div className={cn('rounded-xl border', border)}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full flex items-center justify-between p-4 rounded-t-xl transition-colors',
          bg,
          'hover:brightness-110'
        )}
      >
        <div className="flex items-center gap-3">
          <Icon className={cn('h-5 w-5', text)} />
          <span className={cn('font-semibold capitalize', text)}>
            {severity} ({findings.length})
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className={cn('h-5 w-5', text)} />
        ) : (
          <ChevronDown className={cn('h-5 w-5', text)} />
        )}
      </button>
      
      {isExpanded && (
        <div className="divide-y divide-white/10">
          {findings.map((finding, index) => (
            <FindingCard
              key={index}
              ruleId={finding.rule_id}
              ruleName={finding.rule_name}
              severity={finding.severity}
              category={finding.category}
              description={finding.description}
              recommendation={finding.recommendation}
              filePath={finding.file_path}
              aiExplanation={finding.ai_explanation}
              impactAnalysis={finding.impact_analysis}
              suggestedFix={finding.recommendation}
              expanded={expandedFinding === index}
              onToggle={() => setExpandedFinding(expandedFinding === index ? null : index)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FindingCard({
  ruleId,
  ruleName,
  severity,
  category,
  description,
  recommendation,
  filePath,
  expanded = false,
  onToggle,
  aiExplanation,
  impactAnalysis,
  suggestedFix,
}: FindingCardProps) {
  return (
    <div className={cn(
      'border-b border-white/10 last:border-0',
      'transition-colors duration-150'
    )}>
      <div
        className={cn(
          'p-4 cursor-pointer',
          'hover:bg-white/5',
          'transition-colors duration-150'
        )}
        onClick={onToggle}
      >
        <div className="flex items-start gap-3">
          <SeverityBadge severity={severity} size="sm" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-foreground">{ruleName}</span>
              <span className="text-xs text-muted-foreground font-mono">{ruleId}</span>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">{description}</p>
            {filePath && (
              <p className="text-xs text-muted-foreground mt-2 font-mono">
                📁 {sanitizePath(filePath)}
              </p>
            )}
          </div>
          <svg
            className={cn(
              'h-5 w-5 text-muted-foreground transition-transform duration-200',
              expanded && 'rotate-180'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expandable content */}
      <div className={cn(
        'overflow-hidden transition-all duration-300 ease-in-out',
        expanded ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'
      )}>
        <div className="px-4 pb-4 pt-2 space-y-4">
          {/* Basic Info */}
          <div className="p-4 bg-white/5 rounded-lg border border-white/10">
            <div className="space-y-3">
              <div>
                <span className="text-sm font-medium text-foreground">Category: </span>
                <span className="text-sm text-muted-foreground capitalize">{category}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-foreground">Recommendation: </span>
                <p className="text-sm text-muted-foreground mt-1">{recommendation}</p>
              </div>
            </div>
          </div>

          {/* AI Explanation */}
          {aiExplanation && (
            <div className="p-4 bg-gradient-to-br from-primary/10 to-indigo-600/10 rounded-lg border border-primary/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-primary/20 rounded-lg">
                  <Lightbulb className="h-4 w-4 text-primary" />
                </div>
                <span className="text-sm font-semibold text-primary">AI Explanation</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{aiExplanation}</p>
            </div>
          )}

          {/* Impact Analysis */}
          {impactAnalysis && (
            <div className="p-4 bg-orange-500/10 rounded-lg border border-orange-500/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-orange-500/20 rounded-lg">
                  <AlertTriangle className="h-4 w-4 text-orange-400" />
                </div>
                <span className="text-sm font-semibold text-orange-400">Impact Analysis</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{impactAnalysis}</p>
            </div>
          )}

          {/* Suggested Fix */}
          {suggestedFix && (
            <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-green-500/20 rounded-lg">
                  <CheckCircle className="h-4 w-4 text-green-400" />
                </div>
                <span className="text-sm font-semibold text-green-400">Suggested Fix</span>
              </div>
              <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono bg-black/20 p-3 rounded-lg overflow-x-auto">
                {suggestedFix}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface FindingCardProps {
  ruleId: string
  ruleName: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  filePath?: string
  expanded?: boolean
  onToggle?: () => void
  aiExplanation?: string
  impactAnalysis?: string
  suggestedFix?: string
}

function getCategoryColor(score: number) {
  if (score >= 90) return { bg: 'bg-green-500/15', text: 'text-green-400' }
  if (score >= 80) return { bg: 'bg-blue-500/15', text: 'text-blue-400' }
  if (score >= 70) return { bg: 'bg-yellow-500/15', text: 'text-yellow-400' }
  if (score >= 60) return { bg: 'bg-orange-500/15', text: 'text-orange-400' }
  return { bg: 'bg-red-500/15', text: 'text-red-400' }
}

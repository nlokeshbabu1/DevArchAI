import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import {
  CheckCircle, AlertTriangle, Info, AlertCircle, Shield, Server, Cloud,
  Zap, GitBranch, BarChart3, Brain, Terminal, Lock, ArrowLeft, RotateCcw,
  Download, BookOpen, Code, FileText, ChevronDown, ChevronUp, Filter,
  SortAsc, SortDesc, ExternalLink, Sparkles
} from 'lucide-react'
import { Card, Button } from './ui-animated'
import { cn } from '../lib/utils'
import { TechStackDisplay } from './TechStackDisplay'

interface Finding {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path?: string
  line_number?: number
  // AI Fix Generator fields (production-grade) - MUST match backend
  summary?: string
  risk?: string
  impact?: string
  fix_code?: string
  full_example?: string
  best_practices?: string[]
  confidence?: number  // Backend returns this
  confidence_score?: number  // Also accept this for backwards compatibility
  documentation_url?: string
  // Legacy fields (fallback)
  fix_example?: string
  ai_explanation?: string
  impact_analysis?: string
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
  detected_technologies?: any[]  // Can be string[] or Technology[]
  repository_url?: string
  repository_name?: string
  branch?: string
}

interface ResultComponentProps {
  result: ScanResult
  selectedBranch: string
  onRescan?: () => void
  onDownload?: () => void
  onBack?: () => void
}

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'
type SortOption = 'severity' | 'category' | 'name'

// Full Example Section Component (Expandable)
function FullExampleSection({ fullExample, filePath }: { fullExample: string; filePath?: string }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white/5 hover:bg-white/10 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-400" />
          <span className="text-sm font-semibold text-foreground">Full Fix Example</span>
          {filePath && (
            <span className="text-xs text-muted-foreground">
              ({filePath.split('/').pop()})
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 bg-black/50 border-t border-white/10">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Code className="h-4 w-4 text-blue-400" />
                  <span className="text-xs font-medium text-blue-400">Complete File</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={(e) => {
                    e.stopPropagation()
                    navigator.clipboard.writeText(fullExample)
                  }}
                >
                  Copy Full File
                </Button>
              </div>
              <pre className="p-4 overflow-x-auto max-h-[600px] bg-black/30 rounded-lg">
                <code className="text-sm text-blue-300 font-mono whitespace-pre">
                  {fullExample}
                </code>
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function ResultComponent({ result, selectedBranch, onRescan, onDownload, onBack }: ResultComponentProps) {
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [sortOption, setSortOption] = useState<SortOption>('severity')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 50) return 'text-orange-400'
    return 'text-red-400'
  }

  const getScoreGrade = (score: number) => {
    if (score >= 90) return 'A'
    if (score >= 80) return 'B'
    if (score >= 70) return 'C'
    if (score >= 60) return 'D'
    return 'F'
  }

  const severityIcons: Record<string, any> = {
    critical: AlertCircle,
    high: AlertTriangle,
    medium: Info,
    low: Info,
    info: Info,
  }

  const severityColors: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-400 border-red-500/30',
    high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
    medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    low: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    info: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  }

  const severityPriority = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
    info: 4,
  }

  // Clean file path (remove /tmp/devarchai/...)
  const cleanFilePath = (path: string) => {
    return path.replace(/\/tmp\/devarchai\/[^/]+\//, '')
  }

  // Get documentation URL based on category and file path
  const getDocumentationUrl = (finding: Finding): string => {
    // First check if finding has explicit documentation_url
    if (finding.documentation_url) {
      return finding.documentation_url
    }

    // Dynamic mapping based on category and file path
    const category = finding.category.toLowerCase()
    const filePath = finding.file_path?.toLowerCase() || ''
    const ruleId = finding.rule_id?.toUpperCase() || ''

    // Kubernetes documentation
    if (category.includes('kubernetes') || filePath.includes('k8s') || filePath.includes('kubernetes') || ruleId.startsWith('K8S')) {
      const k8sDocs: Record<string, string> = {
        'security': 'https://kubernetes.io/docs/concepts/security/',
        'reliability': 'https://kubernetes.io/docs/concepts/workloads/pods/disruptions/',
        'scalability': 'https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/',
        'cost': 'https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/',
      }
      return k8sDocs[category] || 'https://kubernetes.io/docs/'
    }

    // Docker documentation
    if (category.includes('docker') || filePath.includes('dockerfile') || ruleId.startsWith('DKR') || ruleId.startsWith('DOCKER')) {
      const dockerDocs: Record<string, string> = {
        'security': 'https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#security',
        'reliability': 'https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#healthcheck',
        'cost': 'https://docs.docker.com/develop/develop-images/multistage-build/',
      }
      return dockerDocs[category] || 'https://docs.docker.com/'
    }

    // Terraform documentation
    if (category.includes('terraform') || filePath.endsWith('.tf') || ruleId.startsWith('TF')) {
      const tfDocs: Record<string, string> = {
        'security': 'https://developer.hashicorp.com/terraform/docs/security',
        'reliability': 'https://developer.hashicorp.com/terraform/language/settings/backends',
        'cost': 'https://developer.hashicorp.com/terraform/cdktf',
      }
      return tfDocs[category] || 'https://developer.hashicorp.com/terraform/docs'
    }

    // CI/CD documentation
    if (category.includes('ci') || category.includes('cd') || category.includes('cicd') || filePath.includes('.github') || filePath.includes('workflow') || ruleId.startsWith('CI')) {
      return 'https://docs.github.com/en/actions'
    }

    // Default fallback - always return a URL
    return 'https://kubernetes.io/docs/'
  }

  // Get confidence badge color
  const getConfidenceBadge = (confidence: number | undefined) => {
    if (!confidence) return { color: 'bg-gray-500/10 text-gray-400', label: 'Unknown' }
    if (confidence >= 0.8) return { color: 'bg-green-500/10 text-green-400', label: 'High' }
    if (confidence >= 0.6) return { color: 'bg-yellow-500/10 text-yellow-400', label: 'Medium' }
    return { color: 'bg-gray-500/10 text-gray-400', label: 'Low' }
  }

  // Get syntax highlighting language from file path
  const getLanguageFromPath = (filePath: string): string => {
    if (!filePath) return 'plaintext'
    if (filePath.endsWith('.tf') || filePath.endsWith('.tfvars')) return 'hcl'
    if (filePath.endsWith('.yaml') || filePath.endsWith('.yml')) {
      if (filePath.includes('k8s') || filePath.includes('kubernetes')) return 'yaml'
      if (filePath.includes('workflow') || filePath.includes('.github')) return 'yaml'
    }
    if (filePath.toLowerCase().includes('dockerfile')) return 'dockerfile'
    if (filePath.endsWith('.sh')) return 'bash'
    if (filePath.endsWith('.json')) return 'json'
    return 'plaintext'
  }

  // Filter and sort findings
  const filteredAndSortedFindings = result.findings
    .filter(finding => {
      if (severityFilter === 'all') return true
      return finding.severity === severityFilter
    })
    .sort((a, b) => {
      let comparison = 0
      
      switch (sortOption) {
        case 'severity':
          comparison = severityPriority[a.severity] - severityPriority[b.severity]
          break
        case 'category':
          comparison = a.category.localeCompare(b.category)
          break
        case 'name':
          comparison = a.rule_name.localeCompare(b.rule_name)
          break
      }
      
      return sortOrder === 'asc' ? comparison : -comparison
    })

  const StackIndicator = ({ label, detected, icon: Icon }: { label: string; detected: boolean; icon: any }) => (
    <div className={cn(
      'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all',
      detected
        ? 'bg-green-500/10 border-green-500/30 text-green-400'
        : 'bg-white/5 border-white/10 text-muted-foreground'
    )}>
      <Icon className={cn('h-4 w-4', detected && 'text-green-400')} />
      <span className="text-sm font-medium">{label}</span>
      {detected && <CheckCircle className="h-3 w-3 ml-auto" />}
    </div>
  )

  const repoName = result.repository_name || result.repository_url?.split('/').slice(-2).join('/') || 'Repository'

  const handleRescan = () => {
    if (onRescan) onRescan()
  }

  const handleDownload = async (format: string = 'json') => {
    if (onDownload) {
      onDownload()
      return
    }

    try {
      const token = localStorage.getItem('access_token')
      
      // For authenticated users with PDF/Excel, try backend endpoint
      if (token && (format === 'pdf' || format === 'xlsx')) {
        try {
          // First get or create report
          const reportResponse = await axios.get(`/api/v1/reports/scan/${result.scan_id}/latest`, {
            headers: { Authorization: `Bearer ${token}` },
          })
          
          const reportId = reportResponse.data.id
          
          // Download in requested format
          const downloadResponse = await axios.get(`/api/v1/reports/${reportId}/download?format=${format}`, {
            headers: { Authorization: `Bearer ${token}` },
            responseType: 'blob',
          })

          const blob = new Blob([downloadResponse.data], {
            type: format === 'pdf' ? 'application/pdf' :
                  format === 'xlsx' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' :
                  'application/json',
          })
          const url = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = `report-${result.scan_id.slice(0, 8)}.${format === 'xlsx' ? 'xlsx' : format === 'pdf' ? 'pdf' : 'json'}`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
          return
        } catch (backendError) {
          console.warn('Backend download failed, falling back to JSON:', backendError)
          // Fall back to JSON download
        }
      }

      // For ALL users (guest and auth), create a JSON download client-side
      const reportData = {
        scan_id: result.scan_id,
        repository_name: repoName,
        repository_url: result.repository_url,
        branch: selectedBranch,
        security_score: result.security_score,
        severity_counts: result.severity_counts,
        findings_count: result.total_findings,
        files_analyzed: result.files_analyzed,
        findings: result.findings.map(f => ({
          rule_id: f.rule_id,
          rule_name: f.rule_name,
          severity: f.severity,
          category: f.category,
          description: f.description,
          recommendation: f.recommendation,
          file_path: f.file_path,
          line_number: f.line_number,
        })),
        generated_at: new Date().toISOString(),
      }
      
      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `scan-report-${result.scan_id.slice(0, 8)}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
    } catch (error) {
      console.error('Download failed:', error)
      alert('Download failed. Please try again.')
    }
  }

  const handleBack = () => {
    if (onBack) onBack()
    else window.history.back()
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Navigation */}
      <Card className="p-4" hover={false}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBack}
              icon={<ArrowLeft className="h-4 w-4" />}
            >
              Back
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleRescan}
              icon={<RotateCcw className="h-4 w-4" />}
            >
              New Scan
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.location.href = '/scans'}
              icon={<FileText className="h-4 w-4" />}
            >
              View History
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative group">
              <Button
                variant="secondary"
                size="sm"
                icon={<Download className="h-4 w-4" />}
              >
                Download Report
              </Button>
              <div className="absolute right-0 mt-2 w-48 bg-card border border-white/10 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                <div className="py-1">
                  <button
                    onClick={() => handleDownload('pdf')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center gap-2"
                  >
                    <FileText className="h-4 w-4" />
                    PDF Report
                  </button>
                  <button
                    onClick={() => handleDownload('xlsx')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center gap-2"
                  >
                    <FileText className="h-4 w-4" />
                    Excel Report
                  </button>
                  <button
                    onClick={() => handleDownload('json')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center gap-2"
                  >
                    <FileText className="h-4 w-4" />
                    JSON Report
                  </button>
                </div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.open('https://docs.devarchai.com', '_blank')}
              icon={<BookOpen className="h-4 w-4" />}
            >
              Fix Guide
              <ExternalLink className="h-3 w-3 ml-1" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Score Card */}
      <Card className="p-8 glow-primary" hover={false}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground">{repoName}</h2>
            <p className="text-muted-foreground mt-1">{result.repository_url || ''}</p>
            {selectedBranch && (
              <div className="flex items-center gap-2 mt-2 text-sm">
                <GitBranch className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Branch:</span>
                <span className="font-medium text-primary">{selectedBranch}</span>
              </div>
            )}
          </div>
          <div className="text-right">
            <div className={cn('text-5xl font-bold', getScoreColor(result.security_score))}>
              {result.security_score.toFixed(1)}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Grade: <span className={cn('font-bold', getScoreColor(result.security_score))}>
                {getScoreGrade(result.security_score)}
              </span>
            </div>
          </div>
        </div>

        {/* Detected Technology Stack */}
        {(result.devops_stack || (result.detected_technologies && result.detected_technologies.length > 0)) && (
          <Card className="p-6" hover={false}>
            <h3 className="text-lg font-semibold mb-4 text-foreground">Detected Technology Stack</h3>
            {result.detected_technologies && result.detected_technologies.length > 0 && (
              <TechStackDisplay technologies={result.detected_technologies as any} />
            )}
          </Card>
        )}

        {/* Summary Stats */}
        <div className={cn(
          "grid gap-4 pt-6 border-t border-white/10",
          result.files_analyzed > 0 ? "grid-cols-2 md:grid-cols-5" : "grid-cols-2 md:grid-cols-4"
        )}>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">{result.severity_counts.critical ?? 0}</div>
            <div className="text-xs text-muted-foreground">Critical</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-400">{result.severity_counts.high ?? 0}</div>
            <div className="text-xs text-muted-foreground">High</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{result.severity_counts.medium ?? 0}</div>
            <div className="text-xs text-muted-foreground">Medium</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{result.severity_counts.low ?? 0}</div>
            <div className="text-xs text-muted-foreground">Low</div>
          </div>
          {result.files_analyzed > 0 && (
            <div className="text-center">
              <div className="text-2xl font-bold text-foreground">{result.files_analyzed}</div>
              <div className="text-xs text-muted-foreground">Files</div>
            </div>
          )}
        </div>
      </Card>

      {/* Filters and Sorting */}
      {result.findings.length > 0 && (
        <Card className="p-4" hover={false}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Filter:</span>
              <div className="flex gap-1">
                {(['all', 'critical', 'high', 'medium', 'low', 'info'] as const).map((severity) => (
                  <button
                    key={severity}
                    onClick={() => setSeverityFilter(severity)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
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
                value={sortOption}
                onChange={(e) => setSortOption(e.target.value as SortOption)}
                className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="severity">Severity</option>
                <option value="category">Category</option>
                <option value="name">Name</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
              >
                {sortOrder === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Findings List */}
      <Card className="p-6" hover={false}>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-foreground">
            Security Findings ({filteredAndSortedFindings.length})
          </h3>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Shield className="h-4 w-4" />
            <span>{severityFilter === 'all' ? 'All severities' : `${severityFilter} only`}</span>
          </div>
        </div>

        <AnimatePresence>
          {filteredAndSortedFindings.length === 0 ? (
            result.findings.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <CheckCircle className="h-16 w-16 text-green-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  No issues found!
                </h3>
                <p className="text-muted-foreground mb-4">
                  Your infrastructure follows best practices. Great job!
                </p>
                <Button
                  variant="primary"
                  onClick={handleRescan}
                  icon={<RotateCcw className="h-4 w-4" />}
                >
                  Scan Another Repository
                </Button>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <Filter className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  No findings match your filters
                </h3>
                <p className="text-muted-foreground">
                  Try adjusting your severity filter
                </p>
              </motion.div>
            )
          ) : (
            <div className="space-y-4">
              {filteredAndSortedFindings.map((finding, index) => {
                const Icon = severityIcons[finding.severity]
                const isExpanded = expandedFinding === `${finding.rule_id}-${index}`

                return (
                  <motion.div
                    key={`${finding.rule_id}-${index}`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="border border-white/10 rounded-xl overflow-hidden"
                  >
                    {/* Debug log - remove in production */}
                    {console.log(`Finding ${index}:`, {
                      rule_id: finding.rule_id,
                      rule_name: finding.rule_name,
                      hasSummary: !!finding.summary,
                      hasRisk: !!finding.risk,
                      hasImpact: !!finding.impact,
                      hasFixCode: !!finding.fix_code,
                      hasFullExample: !!finding.full_example,
                      hasBestPractices: !!finding.best_practices?.length,
                      confidence: finding.confidence ?? finding.confidence_score,
                      full_finding: finding,  // Log entire object for debugging
                    })}
                    <div
                      className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
                      onClick={() => setExpandedFinding(isExpanded ? null : `${finding.rule_id}-${index}`)}
                    >
                      <div className="flex items-start gap-4">
                        <div className={cn('p-2 rounded-lg', severityColors[finding.severity])}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={cn('px-2 py-1 rounded-full text-xs font-medium border', severityColors[finding.severity])}>
                              {finding.severity.toUpperCase()}
                            </span>
                            <span className="text-xs font-mono text-muted-foreground">
                              {finding.rule_id}
                            </span>
                            <span className="text-xs text-muted-foreground capitalize">
                              • {finding.category}
                            </span>
                          </div>
                          <h4 className="font-semibold text-foreground mb-1">
                            {finding.rule_name}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {finding.description}
                          </p>
                        </div>
                        <div className="flex items-center">
                          {isExpanded ? (
                            <ChevronUp className="h-5 w-5 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-5 w-5 text-muted-foreground" />
                          )}
                        </div>
                      </div>
                    </div>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="px-4 pb-4 border-t border-white/10"
                        >
                          <div className="pt-4 space-y-4">
                            {/* Location */}
                            {finding.file_path && (
                              <div>
                                <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                                  <Terminal className="h-4 w-4" />
                                  Location
                                </h5>
                                <code className="text-sm text-muted-foreground bg-white/5 px-3 py-2 rounded-lg block">
                                  {cleanFilePath(finding.file_path)}
                                  {finding.line_number && ` (Line ${finding.line_number})`}
                                </code>
                              </div>
                            )}

                            {/* Risk/Impact */}
                            {(finding.risk || finding.impact) && (
                              <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
                                <h5 className="text-sm font-semibold text-orange-400 mb-2 flex items-center gap-2">
                                  <AlertTriangle className="h-4 w-4" />
                                  Risk & Impact
                                </h5>
                                {finding.risk && (
                                  <p className="text-sm text-orange-300 mb-2">{finding.risk}</p>
                                )}
                                {finding.impact && (
                                  <p className="text-sm text-orange-300">{finding.impact}</p>
                                )}
                              </div>
                            )}

                            {/* AI Suggestion Block - Production Grade */}
                            <div className="space-y-4">
                              {/* Header with Confidence Badge */}
                              <div className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30">
                                  <Brain className="h-5 w-5 text-primary" />
                                </div>
                                <div>
                                  <h5 className="text-sm font-semibold text-foreground">
                                    AI Suggestion
                                  </h5>
                                  {(finding.confidence ?? finding.confidence_score) && (
                                    <div className="flex items-center gap-2 mt-1">
                                      <span className={cn(
                                        'px-2 py-0.5 rounded-full text-xs font-medium',
                                        getConfidenceBadge(finding.confidence ?? finding.confidence_score).color
                                      )}>
                                        {getConfidenceBadge(finding.confidence ?? finding.confidence_score).label} Confidence
                                      </span>
                                      <span className="text-xs text-muted-foreground">
                                        ({((finding.confidence ?? finding.confidence_score) * 100).toFixed(0)}%)
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Summary */}
                              <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
                                <div className="flex items-center gap-2 mb-2">
                                  <FileText className="h-4 w-4 text-primary" />
                                  <h6 className="text-xs font-semibold text-primary">Summary</h6>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {finding.summary || finding.description || 'No summary available'}
                                </p>
                              </div>

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

                              {/* Fix Code Snippet */}
                              {(finding.fix_code || finding.fix_example) && (
                                <div>
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <Code className="h-4 w-4 text-green-400" />
                                      <h6 className="text-xs font-semibold text-foreground">
                                        Suggested Fix
                                      </h6>
                                    </div>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 text-xs"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        const codeToCopy = finding.fix_code || finding.fix_example
                                        if (codeToCopy) {
                                          navigator.clipboard.writeText(codeToCopy)
                                        }
                                      }}
                                    >
                                      Copy Fix
                                    </Button>
                                  </div>
                                  <div className="rounded-lg bg-black/50 border border-white/10 overflow-hidden">
                                    <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border-b border-white/10">
                                      <Terminal className="h-4 w-4 text-green-400" />
                                      <span className="text-xs font-medium text-green-400">
                                        Production-Ready Fix
                                      </span>
                                      {finding.file_path && (
                                        <span className="text-xs text-muted-foreground ml-auto">
                                          {getLanguageFromPath(finding.file_path)}
                                        </span>
                                      )}
                                    </div>
                                    <pre className="p-4 overflow-x-auto max-h-[500px]">
                                      <code className="text-sm text-green-400 font-mono whitespace-pre">
                                        {finding.fix_code || finding.fix_example}
                                      </code>
                                    </pre>
                                  </div>
                                </div>
                              )}

                              {/* Full Example (Expandable) */}
                              {finding.full_example && (
                                <FullExampleSection
                                  fullExample={finding.full_example}
                                  filePath={finding.file_path}
                                />
                              )}

                              {/* Best Practices */}
                              {finding.best_practices && finding.best_practices.length > 0 && (
                                <div className="p-4 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
                                  <div className="flex items-center gap-2 mb-3">
                                    <Sparkles className="h-4 w-4 text-indigo-400" />
                                    <h6 className="text-xs font-semibold text-indigo-400">
                                      Best Practices
                                    </h6>
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

                              {/* Why This Matters (Fallback) */}
                              {finding.recommendation && !(finding.summary || finding.risk || finding.impact) && (
                                <div className="p-4 rounded-lg bg-green-500/5 border border-green-500/20">
                                  <div className="flex items-center gap-2 mb-2">
                                    <CheckCircle className="h-4 w-4 text-green-400" />
                                    <h6 className="text-xs font-semibold text-foreground">
                                      Why This Matters
                                    </h6>
                                  </div>
                                  <p className="text-sm text-muted-foreground">
                                    {finding.recommendation}
                                  </p>
                                </div>
                              )}
                            </div>

                            {/* Action Buttons */}
                            <div className="flex flex-wrap gap-2 pt-4 border-t border-white/10">
                              <Button
                                variant="secondary"
                                size="sm"
                                icon={<Code className="h-4 w-4" />}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  const codeToCopy = finding.fix_code || finding.fix_example
                                  if (codeToCopy) {
                                    navigator.clipboard.writeText(codeToCopy)
                                  }
                                }}
                              >
                                Copy Fix
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                icon={<BookOpen className="h-4 w-4" />}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  const docUrl = getDocumentationUrl(finding)
                                  window.open(docUrl, '_blank', 'noopener,noreferrer')
                                }}
                              >
                                Documentation
                                <ExternalLink className="h-3 w-3 ml-1" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                icon={<ExternalLink className="h-4 w-4" />}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  // Create GitHub issue or Jira ticket (placeholder)
                                  alert('Create Issue feature coming soon. For now, you can copy the finding details and create an issue manually.')
                                }}
                              >
                                Create Issue
                              </Button>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )
              })}
            </div>
          )}
        </AnimatePresence>
      </Card>

      {/* Trust Badges */}
      <div className="flex flex-wrap justify-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Shield className="h-3 w-3" />
          <span>Read-only access</span>
        </div>
        <div className="flex items-center gap-1">
          <CheckCircle className="h-3 w-3" />
          <span>No code stored</span>
        </div>
        <div className="flex items-center gap-1">
          <Lock className="h-3 w-3" />
          <span>Secure scanning</span>
        </div>
      </div>
    </div>
  )
}

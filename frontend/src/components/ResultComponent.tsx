import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckCircle, AlertTriangle, Info, AlertCircle, Shield, Server, Cloud, 
  Zap, GitBranch, BarChart3, Brain, Terminal, Lock, ArrowLeft, RotateCcw,
  Download, BookOpen, Code, FileText, ChevronDown, ChevronUp, Filter,
  SortAsc, SortDesc, ExternalLink
} from 'lucide-react'
import { Card, Button } from './ui-animated'
import { cn } from '../lib/utils'

interface Finding {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path?: string
  line_number?: number
  fix_example?: string
  risk?: string
  impact?: string
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

interface ResultComponentProps {
  result: ScanResult
  selectedBranch: string
  onRescan?: () => void
  onDownload?: () => void
  onBack?: () => void
}

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'
type SortOption = 'severity' | 'category' | 'name'

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

  const handleDownload = () => {
    if (onDownload) onDownload()
    else alert('Download feature coming soon!')
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
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDownload}
              icon={<Download className="h-4 w-4" />}
            >
              Download Report
            </Button>
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

        {/* DevOps Stack */}
        {(result.devops_stack || (result.detected_technologies && result.detected_technologies.length > 0)) && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4 text-foreground">Detected Stack</h3>
            {result.devops_stack ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StackIndicator label="Docker" detected={result.devops_stack.docker} icon={Server} />
                <StackIndicator label="Terraform" detected={result.devops_stack.terraform} icon={Cloud} />
                <StackIndicator label="Kubernetes" detected={result.devops_stack.kubernetes} icon={GitBranch} />
                <StackIndicator label="CI/CD" detected={!!result.devops_stack.cicd} icon={Zap} />
                <StackIndicator label="Helm" detected={result.devops_stack.helm} icon={Cloud} />
                <StackIndicator label="Monitoring" detected={result.devops_stack.monitoring} icon={BarChart3} />
                <StackIndicator label="Prometheus" detected={result.devops_stack.prometheus} icon={BarChart3} />
                <StackIndicator label="Security" detected={result.devops_stack.security_scanning} icon={Shield} />
              </div>
            ) : result.detected_technologies && result.detected_technologies.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {result.detected_technologies.map((tech) => {
                  const iconMap: Record<string, any> = {
                    docker: Server,
                    terraform: Cloud,
                    kubernetes: GitBranch,
                    cicd: Zap,
                    helm: Cloud,
                    monitoring: BarChart3,
                    prometheus: BarChart3,
                    security: Shield,
                  }
                  const Icon = iconMap[tech] || CheckCircle
                  return (
                    <StackIndicator
                      key={tech}
                      label={tech.replace('_', ' ').toUpperCase()}
                      detected={true}
                      icon={Icon}
                    />
                  )
                })}
              </div>
            ) : null}
          </div>
        )}

        {/* Summary Stats */}
        <div className={cn(
          "grid gap-4 pt-6 border-t border-white/10",
          result.files_analyzed > 0 ? "grid-cols-2 md:grid-cols-5" : "grid-cols-2 md:grid-cols-4"
        )}>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">{result.severity_counts.critical}</div>
            <div className="text-xs text-muted-foreground">Critical</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-400">{result.severity_counts.high}</div>
            <div className="text-xs text-muted-foreground">High</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{result.severity_counts.medium}</div>
            <div className="text-xs text-muted-foreground">Medium</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{result.severity_counts.low}</div>
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

                            {/* How to Fix */}
                            <div>
                              <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                                <CheckCircle className="h-4 w-4 text-green-400" />
                                How to Fix
                              </h5>
                              <p className="text-sm text-muted-foreground mb-3">
                                {finding.recommendation}
                              </p>
                              
                              {/* Code Example */}
                              {finding.fix_example && (
                                <div className="rounded-lg bg-black/50 border border-white/10 overflow-hidden">
                                  <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border-b border-white/10">
                                    <Code className="h-4 w-4 text-primary" />
                                    <span className="text-xs font-medium text-primary">Example Fix</span>
                                  </div>
                                  <pre className="p-3 overflow-x-auto">
                                    <code className="text-sm text-green-400 font-mono">
                                      {finding.fix_example}
                                    </code>
                                  </pre>
                                </div>
                              )}
                            </div>

                            {/* Action Buttons */}
                            <div className="flex gap-2 pt-4 border-t border-white/10">
                              <Button
                                variant="secondary"
                                size="sm"
                                icon={<Code className="h-4 w-4" />}
                              >
                                Copy Fix
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                icon={<BookOpen className="h-4 w-4" />}
                              >
                                Documentation
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                icon={<ExternalLink className="h-4 w-4" />}
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

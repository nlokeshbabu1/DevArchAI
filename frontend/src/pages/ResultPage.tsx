import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft, RotateCcw, Download, BookOpen, Shield, AlertTriangle,
  AlertCircle, Info, CheckCircle, FileCode, Terminal, ChevronDown,
  ChevronUp, Filter, SortAsc, Home, FolderGit2
} from 'lucide-react'
import { Button, Card, ScoreCircle } from '../components/ui-animated'
import { Badge } from '../components/ui'
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
  ai_explanation?: string
  code_fix?: string
}

interface ScanResult {
  scan_id: string
  repository_url: string
  repository_name: string
  security_score: number
  severity_counts: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
  }
  findings: Finding[]
  total_findings: number
  files_analyzed: number
  branch: string
  completed_at: string
}

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'
type SortOption = 'severity' | 'date'

export function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('severity')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)

  // Fetch scan results
  const { data: result, isLoading, error, refetch } = useQuery({
    queryKey: ['scan-result', id],
    queryFn: async () => {
      if (!id) throw new Error('No scan ID provided')
      const response = await scansApi.getScanResults(id)
      return response as ScanResult
    },
    enabled: !!id,
    retry: 2,
  })

  // Filter and sort findings
  const filteredFindings = useMemo(() => {
    if (!result?.findings) return []

    let filtered = [...result.findings]

    // Apply severity filter
    if (severityFilter !== 'all') {
      filtered = filtered.filter(f => f.severity === severityFilter)
    }

    // Apply sorting
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    filtered.sort((a, b) => {
      if (sortBy === 'severity') {
        return severityOrder[a.severity] - severityOrder[b.severity]
      }
      return 0 // Date sorting would need timestamp in finding
    })

    return filtered
  }, [result?.findings, severityFilter, sortBy])

  // Get top priority fixes (critical + high, max 3)
  const topPriorityFixes = useMemo(() => {
    if (!result?.findings) return []
    return result.findings
      .filter(f => f.severity === 'critical' || f.severity === 'high')
      .slice(0, 3)
  }, [result?.findings])

  // Clean file path (remove /tmp/devarchai/... prefix)
  const cleanFilePath = (path: string) => {
    return path.replace(/\/tmp\/devarchai\/[^/]+\//, '')
  }

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

  const handleDownload = () => {
    // TODO: Implement report download
    alert('Download feature coming soon!')
  }

  const handleRescan = () => {
    navigate('/scan')
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

  const repoName = result.repository_name || result.repository_url.split('/').slice(-2).join('/')

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="container mx-auto px-4 max-w-7xl space-y-6">
        {/* Top Navigation */}
        <Card className="p-4" hover={false}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/dashboard')}
                icon={<ArrowLeft className="h-4 w-4" />}
              >
                Dashboard
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/history')}
                icon={<FolderGit2 className="h-4 w-4" />}
              >
                History
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleRescan}
                icon={<RotateCcw className="h-4 w-4" />}
              >
                New Scan
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleDownload}
                icon={<Download className="h-4 w-4" />}
              >
                Download
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/scan')}
                icon={<Shield className="h-4 w-4" />}
                glow
              >
                Start New Scan
              </Button>
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
            Branch: {result.branch || 'main'} • Scanned: {new Date(result.completed_at).toLocaleString()}
          </p>
        </motion.div>

        {/* Score and Stats */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Security Score */}
          <Card className="p-6" hover={false}>
            <div className="text-center space-y-4">
              <h3 className="text-lg font-semibold text-foreground">Security Score</h3>
              <ScoreCircle score={result.security_score} size="xl" animated />
              <div className="text-sm text-muted-foreground">
                Grade: <span className={cn('font-bold', getScoreColor(result.security_score))}>
                  {result.security_score >= 90 ? 'A' : result.security_score >= 80 ? 'B' : result.security_score >= 70 ? 'C' : result.security_score >= 60 ? 'D' : 'F'}
                </span>
              </div>
            </div>
          </Card>

          {/* Severity Counts */}
          <Card className="p-6" hover={false}>
            <h3 className="text-lg font-semibold text-foreground mb-4">Issues by Severity</h3>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(result.severity_counts).map(([severity, count]) => {
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
                <div className="font-medium text-foreground truncate">{result.repository_url}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Files Analyzed</div>
                <div className="font-medium text-foreground">{result.files_analyzed}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total Findings</div>
                <div className="font-medium text-foreground">{result.total_findings}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Scan ID</div>
                <div className="font-mono text-xs text-muted-foreground">{result.scan_id}</div>
              </div>
            </div>
          </Card>
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

                          {/* Actions */}
                          <div className="flex gap-2 pt-4 border-t border-white/10">
                            <Button variant="secondary" size="sm">
                              Copy Fix
                            </Button>
                            <Button variant="ghost" size="sm">
                              Create Issue
                            </Button>
                            <Button variant="ghost" size="sm">
                              Ignore
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
                icon={<RotateCcw className="h-5 w-5" />}
                glow
              >
                Re-scan Repository
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

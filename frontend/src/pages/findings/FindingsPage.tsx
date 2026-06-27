import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download, CheckCircle, AlertTriangle, AlertCircle, Info, Sparkles, BookOpen, ExternalLink, Code, Brain, ChevronDown, ChevronUp, FileCode, FolderGit2, Shield, Wrench, FileText } from 'lucide-react'
import { Card, Button, Badge } from '../../components/ui'
import { AISuggestionBlur } from '../../components/billing/AISuggestionBlur'
import { api } from '../../lib/api'
import { useAuthStore } from '../../stores/auth-store'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { cn, sanitizePath } from '../../lib/utils'

interface Finding {
  id: string
  scan_id: string
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path: string
  repository?: string
  repository_name?: string
  repository_url?: string
  line_number?: number
  ai_explanation?: string
  ai_generated?: boolean
  documentation_url?: string
  // AI Fix Generator fields (enrichment)
  summary?: string
  risk?: string
  impact?: string
  fix_code?: string
  full_example?: string
  best_practices?: string[]
  confidence_score?: number
  created_at: string
}

interface FindingExportRow {
  repository: string
  rule_id: string
  rule_name: string
  severity: string
  category: string
  file_path: string
  line_number: string | number
  risk: string
  impact: string
  fix: string
  ai_explanation: string
}

export function Findings() {
  const navigate = useNavigate()
  const { token, isAuthenticated } = useAuthStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string[]>([])
  const [categoryFilter, setCategoryFilter] = useState<string[]>([])
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)

  const severityOrder: Finding['severity'][] = ['critical', 'high', 'medium', 'low', 'info']

  const getRepositoryLabel = (finding: Finding) => {
    if (finding.repository_name) return finding.repository_name
    if (finding.repository) return finding.repository
    if (finding.repository_url) return finding.repository_url.split('/').filter(Boolean).slice(-2).join('/')
    return `Scan ${finding.scan_id?.slice(0, 8) || 'unknown'}`
  }

  const getRiskText = (finding: Finding) => finding.risk || finding.description || 'Risk details are not available for this finding.'

  const getImpactText = (finding: Finding) => finding.impact || finding.summary || 'Review this issue to determine the affected workload, deployment path, and production exposure.'

  const getFixText = (finding: Finding) => finding.recommendation || 'No remediation guidance is available for this finding.'

  const getAiExplanationText = (finding: Finding) => finding.ai_explanation || finding.summary || 'AI explanation is not available for this finding yet.'

  const toggleFilterValue = (values: string[], value: string, setter: (next: string[]) => void) => {
    setter(values.includes(value)
      ? values.filter((item) => item !== value)
      : [...values, value])
  }

  const exportFindings = (format: 'json' | 'csv') => {
    const exportRows: FindingExportRow[] = filteredFindings.map((finding: Finding) => ({
      repository: getRepositoryLabel(finding),
      rule_id: finding.rule_id,
      rule_name: finding.rule_name,
      severity: finding.severity,
      category: finding.category,
      file_path: sanitizePath(finding.file_path),
      line_number: finding.line_number || '',
      risk: getRiskText(finding),
      impact: getImpactText(finding),
      fix: getFixText(finding),
      ai_explanation: getAiExplanationText(finding),
    }))

    const content = format === 'json'
      ? JSON.stringify(exportRows, null, 2)
      : [
          Object.keys(exportRows[0] || {
            repository: '',
            rule_id: '',
            rule_name: '',
            severity: '',
            category: '',
            file_path: '',
            line_number: '',
            risk: '',
            impact: '',
            fix: '',
            ai_explanation: '',
          }).join(','),
          ...exportRows.map((row) => Object.values(row)
            .map((value) => `"${String(value).replace(/"/g, '""')}"`)
            .join(','))
        ].join('\n')

    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `devarchai-findings-${new Date().toISOString().slice(0, 10)}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // Get confidence badge color
  const getConfidenceBadge = (confidence: number | undefined) => {
    if (!confidence) return { color: 'bg-gray-500/10 text-gray-400', label: 'Unknown' }
    if (confidence >= 0.8) return { color: 'bg-green-500/10 text-green-400', label: 'High' }
    if (confidence >= 0.6) return { color: 'bg-yellow-500/10 text-yellow-400', label: 'Medium' }
    return { color: 'bg-gray-500/10 text-gray-400', label: 'Low' }
  }

  // Get documentation URL
  const getDocumentationUrl = (finding: Finding): string => {
    if (finding.documentation_url) return finding.documentation_url

    const category = finding.category.toLowerCase()
    const ruleId = finding.rule_id?.toUpperCase() || ''

    if (category.includes('kubernetes') || ruleId.startsWith('K8S')) {
      return 'https://kubernetes.io/docs/'
    }
    if (category.includes('docker') || ruleId.startsWith('DKR') || ruleId.startsWith('DOCKER')) {
      return 'https://docs.docker.com/develop/'
    }
    if (category.includes('terraform') || ruleId.startsWith('TF')) {
      return 'https://developer.hashicorp.com/terraform/docs'
    }
    if (category.includes('ci') || ruleId.startsWith('CI')) {
      return 'https://docs.github.com/en/actions'
    }

    return 'https://kubernetes.io/docs/'
  }

  // Get user subscription to determine if AI should be blurred
  const [userPlan, setUserPlan] = useState<string>('free')

  useEffect(() => {
    // Fetch user's subscription plan
    const fetchPlan = async () => {
      if (!token) {
        setUserPlan('free')
        return
      }
      try {
        const response = await api.get('/billing/subscription', {
          headers: { Authorization: `Bearer ${token}` }
        })
        setUserPlan(response.data.plan || 'free')
      } catch (error) {
        setUserPlan('free')
      }
    }
    fetchPlan()
  }, [token])

  // Directly fetch findings from the global findings endpoint
  const { data: findingsData, isLoading: findingsLoading, error: findingsError } = useQuery({
    queryKey: ['findings'],
    queryFn: async () => {
      if (!isAuthenticated) return { findings: [], total: 0 }
      const response = await api.get('/findings', {
        params: { page_size: 100 },
      })
      return response.data
    },
    enabled: isAuthenticated,
    refetchInterval: 5000, // Poll every 5 seconds for live updates
  })

  const findings = findingsData?.findings || []
  const isLoading = findingsLoading

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

  const categoryColors: Record<string, string> = {
    security: 'bg-red-500/10 text-red-400',
    reliability: 'bg-blue-500/10 text-blue-400',
    scalability: 'bg-green-500/10 text-green-400',
    cost: 'bg-purple-500/10 text-purple-400',
    observability: 'bg-orange-500/10 text-orange-400',
  }

  const filteredFindings = findings?.filter((finding: Finding) => {
    const normalizedSearch = searchTerm.toLowerCase()
    const matchesSearch =
      finding.rule_name.toLowerCase().includes(normalizedSearch) ||
      finding.description.toLowerCase().includes(normalizedSearch) ||
      finding.rule_id?.toLowerCase().includes(normalizedSearch) ||
      finding.file_path?.toLowerCase().includes(normalizedSearch) ||
      getRepositoryLabel(finding).toLowerCase().includes(normalizedSearch)

    const matchesSeverity = severityFilter.length === 0 || severityFilter.includes(finding.severity)
    const matchesCategory = categoryFilter.length === 0 || categoryFilter.includes(finding.category)

    return matchesSearch && matchesSeverity && matchesCategory
  })

  const severityCounts = findings?.reduce((acc: Record<string, number>, f: Finding) => {
    acc[f.severity] = (acc[f.severity] || 0) + 1
    return acc
  }, {})

  const categories = Array.from(new Set<string>(
    findings
      .map((finding: Finding) => finding.category)
      .filter((category: string | undefined): category is string => Boolean(category))
  ))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Security Findings</h1>
          <p className="text-muted-foreground mt-1">
            View and manage all detected issues across your repositories
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {severityOrder.map((severity) => {
          const count = severityCounts?.[severity] || 0
          const Icon = severityIcons[severity]
          return (
            <Card key={severity} className="p-4" hover={false}>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-2xl font-bold text-foreground">{count}</div>
                  <div className="text-sm text-muted-foreground capitalize">{severity}</div>
                </div>
                <div className={`rounded-xl border p-2 ${severityColors[severity]}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Export Actions */}
      <Card className="p-4" hover={false}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-xl border border-primary/30 bg-primary/10 p-2.5">
              <Download className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold text-foreground">Export Findings</h2>
              <p className="text-sm text-muted-foreground">
                Export the current filtered result set for triage, audit review, or offline analysis.
              </p>
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              variant="secondary"
              onClick={() => exportFindings('csv')}
              disabled={isLoading || filteredFindings.length === 0}
            >
              <FileText className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
            <Button
              variant="secondary"
              onClick={() => exportFindings('json')}
              disabled={isLoading || filteredFindings.length === 0}
            >
              <Download className="h-4 w-4 mr-2" />
              Export JSON
            </Button>
          </div>
        </div>
      </Card>

      {/* Filters */}
      <Card className="p-4" hover={false}>
        <div className="flex flex-col gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by repository, rule, file path, or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-foreground placeholder:text-muted-foreground transition-colors focus:border-primary/50 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>
          <div className="grid gap-4 lg:grid-cols-[auto_1fr] lg:items-start">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Filter className="h-4 w-4" />
              Filters
            </div>
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {severityOrder.map((severity) => (
                  <button
                    key={severity}
                    type="button"
                    onClick={() => toggleFilterValue(severityFilter, severity, setSeverityFilter)}
                    className={cn(
                      'rounded-full border px-3 py-1.5 text-xs font-medium capitalize transition-colors',
                      severityFilter.includes(severity)
                        ? severityColors[severity]
                        : 'border-white/10 bg-white/5 text-muted-foreground hover:bg-white/10 hover:text-foreground'
                    )}
                  >
                    {severity}
                  </button>
                ))}
              </div>
              {categories.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {categories.map((category) => (
                    <button
                      key={category}
                      type="button"
                      onClick={() => toggleFilterValue(categoryFilter, category, setCategoryFilter)}
                      className={cn(
                        'rounded-full border px-3 py-1.5 text-xs font-medium capitalize transition-colors',
                        categoryFilter.includes(category)
                          ? 'border-primary/30 bg-primary/10 text-primary'
                          : 'border-white/10 bg-white/5 text-muted-foreground hover:bg-white/10 hover:text-foreground'
                      )}
                    >
                      {category}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Findings List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
            <p className="text-muted-foreground mt-4">Loading findings...</p>
          </div>
        ) : findingsError || !isAuthenticated ? (
          <Card className="p-12 text-center">
            <AlertCircle className="h-12 w-12 text-orange-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {!isAuthenticated ? 'Authentication Required' : 'Error Loading Findings'}
            </h3>
            <p className="text-muted-foreground mb-4">
              {!isAuthenticated 
                ? 'Please login to view your security findings.'
                : 'Failed to load findings. Please try again.'}
            </p>
            {!isAuthenticated ? (
              <Button onClick={() => navigate('/login')}>
                Login to Continue
              </Button>
            ) : (
              <Button onClick={() => window.location.reload()}>
                Retry
              </Button>
            )}
          </Card>
        ) : filteredFindings?.length === 0 ? (
          <Card className="p-12 text-center">
            <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No findings found</h3>
            <p className="text-muted-foreground">
              {findings?.length === 0
                ? "No findings detected. Run a scan to identify issues."
                : "No findings match your current filters."}
            </p>
          </Card>
        ) : (
          filteredFindings?.map((finding: Finding) => {
            const Icon = severityIcons[finding.severity]
            const isExpanded = expandedFinding === finding.id
            const repositoryLabel = getRepositoryLabel(finding)
            const hasFullExample = Boolean(finding.full_example)
            
            return (
              <Card key={finding.id} className="overflow-hidden border-white/10" hover={false}>
                <div className="border-b border-white/10 bg-white/[0.03] p-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex min-w-0 items-start gap-4">
                      <div className={`rounded-xl border p-2.5 ${severityColors[finding.severity]}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="mb-3 flex flex-wrap items-center gap-2">
                          <Badge variant="secondary" className={severityColors[finding.severity]}>
                            {finding.severity.toUpperCase()}
                          </Badge>
                          <Badge variant="secondary" className="border-white/10 bg-white/5 text-muted-foreground">
                            <Shield className="mr-1 h-3 w-3" />
                            {finding.rule_id}
                          </Badge>
                          <Badge variant="secondary" className="border-primary/20 bg-primary/10 text-primary">
                            {finding.category}
                          </Badge>
                          {finding.confidence_score && (
                            <span className={cn(
                              'rounded-full px-2 py-1 text-xs font-medium',
                              getConfidenceBadge(finding.confidence_score).color
                            )}>
                              {getConfidenceBadge(finding.confidence_score).label} confidence
                            </span>
                          )}
                        </div>
                        <h3 className="text-lg font-semibold leading-7 text-foreground">{finding.rule_name}</h3>
                        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                          <div className="rounded-xl border border-white/10 bg-black/10 p-3">
                            <div className="mb-1 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                              <FolderGit2 className="h-3.5 w-3.5" />
                              Repository
                            </div>
                            <p className="truncate text-sm font-medium text-foreground">{repositoryLabel}</p>
                          </div>
                          <div className="rounded-xl border border-white/10 bg-black/10 p-3 xl:col-span-2">
                            <div className="mb-1 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                              <FileCode className="h-3.5 w-3.5" />
                              File Path
                            </div>
                            <code className="block truncate text-sm text-foreground">
                              {sanitizePath(finding.file_path) || 'Path unavailable'}
                              {finding.line_number ? `:${finding.line_number}` : ''}
                            </code>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const docUrl = getDocumentationUrl(finding)
                          window.open(docUrl, '_blank', 'noopener,noreferrer')
                        }}
                      >
                        <BookOpen className="h-4 w-4 mr-2" />
                        Documentation
                        <ExternalLink className="h-3 w-3 ml-1" />
                      </Button>
                      {hasFullExample && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedFinding(isExpanded ? null : finding.id)}
                        >
                          {isExpanded ? <ChevronUp className="h-4 w-4 mr-2" /> : <ChevronDown className="h-4 w-4 mr-2" />}
                          Full Fix
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 p-5 xl:grid-cols-2">
                  <section className="rounded-xl border border-red-500/20 bg-red-500/[0.06] p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                      <h4 className="text-sm font-semibold text-foreground">Risk</h4>
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">{getRiskText(finding)}</p>
                  </section>

                  <section className="rounded-xl border border-orange-500/20 bg-orange-500/[0.06] p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Info className="h-4 w-4 text-orange-400" />
                      <h4 className="text-sm font-semibold text-foreground">Impact</h4>
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">{getImpactText(finding)}</p>
                  </section>

                  <section className="rounded-xl border border-green-500/20 bg-green-500/[0.06] p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Wrench className="h-4 w-4 text-green-400" />
                        <h4 className="text-sm font-semibold text-foreground">Fix</h4>
                      </div>
                      {finding.fix_code && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => navigator.clipboard.writeText(finding.fix_code || '')}
                        >
                          Copy
                        </Button>
                      )}
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">{getFixText(finding)}</p>
                    {finding.fix_code && (
                      <pre className="mt-3 max-h-48 overflow-x-auto rounded-lg border border-white/10 bg-black/50 p-3">
                        <code className="whitespace-pre font-mono text-sm text-green-300">
                          {finding.fix_code}
                        </code>
                      </pre>
                    )}
                  </section>

                  <section className="rounded-xl border border-primary/20 bg-primary/[0.06] p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Brain className="h-4 w-4 text-primary" />
                      <h4 className="text-sm font-semibold text-foreground">AI Explanation</h4>
                      {finding.confidence_score && (
                        <span className="text-xs text-muted-foreground">
                          {(finding.confidence_score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    {finding.ai_explanation && !(finding.summary || finding.risk || finding.fix_code) ? (
                      <AISuggestionBlur
                        isBlurred={userPlan === 'free'}
                        suggestion={finding.ai_explanation}
                        codeFix={finding.recommendation}
                        onUpgrade={() => navigate('/pricing')}
                        upgradePlan="plus"
                      />
                    ) : (
                      <p className="text-sm leading-6 text-muted-foreground">{getAiExplanationText(finding)}</p>
                    )}
                    {finding.best_practices && Array.isArray(finding.best_practices) && finding.best_practices.length > 0 && (
                      <div className="mt-4 rounded-lg border border-indigo-500/30 bg-indigo-500/10 p-3">
                        <div className="mb-2 flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-indigo-400" />
                          <span className="text-xs font-semibold text-indigo-300">Best Practices</span>
                        </div>
                        <ul className="space-y-1">
                          {finding.best_practices.map((practice, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-indigo-200">
                              <CheckCircle className="mt-0.5 h-3 w-3 flex-shrink-0" />
                              <span>{practice}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </section>
                </div>
                
                {/* Expanded View with Full Example */}
                <AnimatePresence>
                  {isExpanded && finding.full_example && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="mt-4 pt-4 border-t border-white/10"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Code className="h-4 w-4 text-blue-400" />
                          <span className="text-sm font-semibold text-foreground">Full Fix Example</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigator.clipboard.writeText(finding.full_example || '')}
                        >
                          Copy Full File
                        </Button>
                      </div>
                      <pre className="p-4 rounded-lg bg-black/50 border border-white/10 overflow-x-auto max-h-[600px]">
                        <code className="text-sm text-blue-300 font-mono whitespace-pre">
                          {finding.full_example}
                        </code>
                      </pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}

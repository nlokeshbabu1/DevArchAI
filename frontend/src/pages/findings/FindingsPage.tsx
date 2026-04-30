import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download, CheckCircle, AlertTriangle, AlertCircle, Info, Lock, Sparkles, BookOpen, ExternalLink, Code, Brain, ChevronDown, ChevronUp } from 'lucide-react'
import { Card, Button, Badge } from '../../components/ui'
import { AISuggestionBlur } from '../../components/billing/AISuggestionBlur'
import { api } from '../../lib/api'
import { useAuthStore } from '../../stores/auth-store'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils'

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

export function Findings() {
  const navigate = useNavigate()
  const { token, isAuthenticated } = useAuthStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string[]>([])
  const [categoryFilter, setCategoryFilter] = useState<string[]>([])
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)

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
    const matchesSearch =
      finding.rule_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      finding.description.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesSeverity = severityFilter.length === 0 || severityFilter.includes(finding.severity)
    const matchesCategory = categoryFilter.length === 0 || categoryFilter.includes(finding.category)

    return matchesSearch && matchesSeverity && matchesCategory
  })

  const severityCounts = findings?.reduce((acc: Record<string, number>, f: Finding) => {
    acc[f.severity] = (acc[f.severity] || 0) + 1
    return acc
  }, {})

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
        <div className="flex gap-2">
          <Button variant="secondary">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {Object.entries(severityCounts || {}).map(([severity, count]) => {
          const Icon = severityIcons[severity]
          return (
            <Card key={severity} className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${severityColors[severity]}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-foreground">{String(count)}</div>
                  <div className="text-sm text-muted-foreground capitalize">{severity}</div>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search findings..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white border border-white/10 rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2">
            <select
              multiple
              value={severityFilter}
              onChange={(e) => setSeverityFilter(Array.from(e.target.selectedOptions, option => option.value))}
              className="px-4 py-2 bg-white border border-white/10 rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            <select
              multiple
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(Array.from(e.target.selectedOptions, option => option.value))}
              className="px-4 py-2 bg-white border border-white/10 rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="security">Security</option>
              <option value="reliability">Reliability</option>
              <option value="scalability">Scalability</option>
              <option value="cost">Cost</option>
              <option value="observability">Observability</option>
            </select>
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
            
            return (
              <Card key={finding.id} className="p-6 hover:bg-white/5 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`p-2 rounded-lg ${severityColors[finding.severity]}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-foreground">{finding.rule_name}</h3>
                        <Badge variant="secondary" className={categoryColors[finding.category]}>
                          {finding.category}
                        </Badge>
                        <Badge variant="secondary" className={severityColors[finding.severity]}>
                          {finding.severity}
                        </Badge>
                        {finding.confidence_score && (
                          <span className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium',
                            getConfidenceBadge(finding.confidence_score).color
                          )}>
                            {getConfidenceBadge(finding.confidence_score).label}
                          </span>
                        )}
                      </div>
                      <p className="text-muted-foreground mb-3">{finding.description}</p>
                      {finding.file_path && (
                        <div className="text-sm text-muted-foreground mb-3">
                          <code className="px-2 py-1 bg-white/5 rounded">{finding.file_path}</code>
                          {finding.line_number && <span className="ml-2">Line {finding.line_number}</span>}
                        </div>
                      )}
                      
                      {/* AI Suggestion Preview */}
                      {(finding.summary || finding.risk || finding.fix_code) && (
                        <div className="mt-4 p-4 rounded-lg bg-primary/5 border border-primary/20">
                          <div className="flex items-center gap-2 mb-3">
                            <Brain className="h-4 w-4 text-primary" />
                            <span className="text-sm font-semibold text-foreground">AI Suggestion</span>
                            {finding.confidence_score && (
                              <span className="text-xs text-muted-foreground">
                                ({(finding.confidence_score * 100).toFixed(0)}% confidence)
                              </span>
                            )}
                          </div>
                          
                          {finding.summary && (
                            <p className="text-sm text-muted-foreground mb-3">{finding.summary}</p>
                          )}
                          
                          {(finding.risk || finding.impact) && (
                            <div className="mb-3 p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
                              <p className="text-sm text-orange-300">{finding.risk || finding.impact}</p>
                            </div>
                          )}
                          
                          {finding.fix_code && (
                            <div className="mb-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-medium text-green-400">Suggested Fix</span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-xs"
                                  onClick={() => navigator.clipboard.writeText(finding.fix_code || '')}
                                >
                                  Copy
                                </Button>
                              </div>
                              <pre className="p-3 rounded-lg bg-black/50 border border-white/10 overflow-x-auto max-h-48">
                                <code className="text-sm text-green-400 font-mono whitespace-pre">
                                  {finding.fix_code}
                                </code>
                              </pre>
                            </div>
                          )}
                          
                          {finding.best_practices && Array.isArray(finding.best_practices) && finding.best_practices.length > 0 && (
                            <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
                              <div className="flex items-center gap-2 mb-2">
                                <Sparkles className="h-4 w-4 text-indigo-400" />
                                <span className="text-xs font-semibold text-indigo-400">Best Practices</span>
                              </div>
                              <ul className="space-y-1">
                                {finding.best_practices.map((practice, idx) => (
                                  <li key={idx} className="flex items-start gap-2 text-sm text-indigo-300">
                                    <CheckCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                                    <span>{practice}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* Fallback to old AI explanation */}
                      {finding.ai_explanation && !(finding.summary || finding.risk || finding.fix_code) && (
                        <div className="mt-4">
                          <AISuggestionBlur
                            isBlurred={userPlan === 'free'}
                            suggestion={finding.ai_explanation}
                            codeFix={finding.recommendation}
                            onUpgrade={() => navigate('/pricing')}
                            upgradePlan="plus"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedFinding(isExpanded ? null : finding.id)}
                    >
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
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

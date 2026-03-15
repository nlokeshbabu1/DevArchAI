import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Shield, AlertTriangle, AlertCircle, Info, CheckCircle,
  Lock, Github, ArrowRight, Terminal, Cloud, Layers
} from 'lucide-react'
import { Button, Card, ScoreCircle } from '../components/ui-animated'
import { Badge } from '../components/ui'
import { AISuggestionBlur } from '../components/billing/AISuggestionBlur'
import { cn } from '../lib/utils'
import { useAuthStore } from '../stores/auth-store'

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

interface ScanResults {
  session_token: string
  scan_id: string
  status: string
  repository_name: string
  repository_url: string
  security_score?: string
  severity_counts?: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
  }
  findings?: Finding[]
  user_plan?: string  // free, plus, pro, enterprise
  ai_suggestions_blurred?: boolean
  ai_preview_count?: number
  login_required?: boolean
  message?: string
  total_findings?: number
}

export function ScanResultsPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()
  const [results, setResults] = useState<ScanResults | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)

  useEffect(() => {
    fetchResults()
  }, [sessionId])

  // Refetch results when authentication state changes (after login)
  useEffect(() => {
    if (isAuthenticated && results) {
      // User just logged in, refetch to get updated plan-based results
      fetchResults()
    }
  }, [isAuthenticated])

  const fetchResults = async () => {
    try {
      const response = await fetch(`/api/v1/public/scan/${sessionId}`)
      if (!response.ok) throw new Error('Failed to fetch results')
      const data = await response.json()
      setResults(data)
    } catch (error) {
      console.error('Error fetching results:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogin = () => {
    // Store intended destination with plan upgrade context
    sessionStorage.setItem('postLoginRedirect', `/scan/results/${sessionId}`)
    sessionStorage.setItem('upgradeIntent', 'true')
    sessionStorage.setItem('upgradePlan', 'plus')
    navigate('/login')
  }

  const severityIcons = {
    critical: AlertCircle,
    high: AlertTriangle,
    medium: Info,
    low: Info,
    info: Info,
  }

  const severityColors = {
    critical: 'bg-red-500/10 text-red-400 border-red-500/30',
    high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
    medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    low: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    info: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
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

  if (!results) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">Scan Not Found</h2>
          <p className="text-muted-foreground mb-4">
            This scan session has expired or doesn't exist.
          </p>
          <Button onClick={() => navigate('/')}>
            Start New Scan
          </Button>
        </Card>
      </div>
    )
  }

  if (results.status === 'pending') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">Scan in Progress</h2>
          <p className="text-muted-foreground">{results.message}</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background py-12">
      <div className="container mx-auto px-4 max-w-6xl space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <h1 className="text-4xl font-bold text-foreground mb-2">
            Scan Results
          </h1>
          <p className="text-muted-foreground">
            {results.repository_name}
          </p>
        </motion.div>

        {/* Security Score */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="p-8" hover={false}>
            <div className="text-center space-y-6">
              <h2 className="text-2xl font-bold text-foreground">
                Production Readiness Score
              </h2>
              <ScoreCircle
                score={results.security_score ? parseInt(results.security_score) : 0}
                size="xl"
                animated
              />
            </div>
          </Card>
        </motion.div>

        {/* Severity Counts */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="p-6" hover={false}>
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Issues by Severity
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(results.severity_counts || {}).map(([severity, count]) => {
                const Icon = severityIcons[severity as keyof typeof severityIcons]
                return (
                  <div
                    key={severity}
                    className={cn(
                      'p-4 rounded-xl border text-center capitalize',
                      severityColors[severity as keyof typeof severityColors]
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
        </motion.div>

        {/* Issues List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="p-6" hover={false}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">
                Detected Issues
              </h3>
              {(() => {
                const effectivePlan = results.user_plan || user?.plan || 'free'
                const isFreeUser = effectivePlan === 'free'
                const totalFindings = results.findings?.length || 0
                
                // Count unique rules (after deduplication)
                const uniqueRules = new Set(results.findings?.map(f => f.rule_id) || [])
                const uniqueRuleCount = uniqueRules.size
                
                // Free users see only first 10 findings (before deduplication)
                const maxVisible = isFreeUser ? 10 : totalFindings
                const visibleFindings = (results.findings || []).slice(0, maxVisible)
                
                // Deduplicate visible findings
                const deduplicatedVisible = visibleFindings.reduce((acc, finding) => {
                  const existing = acc.find(f => f.rule_id === finding.rule_id)
                  if (!existing) {
                    acc.push(finding)
                  }
                  return acc
                }, [] as typeof visibleFindings)
                
                const displayedCount = deduplicatedVisible.length
                
                if (isFreeUser && uniqueRuleCount > displayedCount) {
                  return (
                    <div className="text-sm text-muted-foreground">
                      Showing {displayedCount} of {uniqueRuleCount} unique issues
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate('/pricing')}
                        className="ml-2 text-primary hover:text-primary"
                      >
                        Upgrade to view all
                      </Button>
                    </div>
                  )
                }
                
                return null
              })()}
            </div>
            
            <div className="space-y-4">
              {(() => {
                const effectivePlan = results.user_plan || user?.plan || 'free'
                const isFreeUser = effectivePlan === 'free'
                const totalFindings = results.findings?.length || 0

                // Free users see only first 10 findings
                const maxVisible = isFreeUser ? 10 : totalFindings
                const visibleFindings = (results.findings || []).slice(0, maxVisible)

                // Deduplicate findings by rule_id and count unique files
                const deduplicatedFindings = visibleFindings.reduce((acc, finding) => {
                  const existing = acc.find(f => f.rule_id === finding.rule_id)
                  if (existing && existing.uniqueFiles) {
                    // Add file to unique files set if not already present
                    if (finding.file_path && !existing.uniqueFiles.has(finding.file_path)) {
                      existing.uniqueFiles.add(finding.file_path)
                      existing.occurrenceCount = existing.uniqueFiles.size
                    }
                  } else if (!existing) {
                    // Add new finding with unique files set
                    const newFinding = { 
                      ...finding, 
                      occurrenceCount: 1,
                      uniqueFiles: new Set(finding.file_path ? [finding.file_path] : [])
                    }
                    acc.push(newFinding)
                  }
                  return acc
                }, [] as (typeof visibleFindings[0] & { occurrenceCount: number; uniqueFiles: Set<string> })[])

                return deduplicatedFindings.map((finding, index) => {
                  const Icon = severityIcons[finding.severity]
                  // Use unique key combining rule_id and index
                  const uniqueKey = `${finding.rule_id}-${index}`
                  const isExpanded = expandedFinding === uniqueKey

                  return (
                    <div
                      key={uniqueKey}
                      className="border border-white/10 rounded-xl overflow-hidden"
                    >
                      <div
                        className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
                        onClick={() => setExpandedFinding(
                          isExpanded ? null : uniqueKey
                        )}
                      >
                        <div className="flex items-start gap-4">
                          <div className={cn(
                            'p-2 rounded-lg',
                            severityColors[finding.severity]
                          )}>
                            <Icon className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant="secondary" className={severityColors[finding.severity]}>
                                {finding.severity.toUpperCase()}
                              </Badge>
                              <span className="text-xs font-mono text-muted-foreground">
                                {finding.rule_id}
                              </span>
                              {finding.occurrenceCount && finding.occurrenceCount > 1 && (
                                <Badge variant="secondary" className="bg-blue-500/10 text-blue-400 border-blue-500/30">
                                  {finding.occurrenceCount} {finding.occurrenceCount === 1 ? 'file' : 'files'}
                                </Badge>
                              )}
                            </div>
                            <h4 className="font-semibold text-foreground mb-1">
                              {finding.rule_name}
                            </h4>
                            <p className="text-sm text-muted-foreground">
                              {finding.description}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Expanded Content */}
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          className="px-4 pb-4 border-t border-white/10"
                        >
                          {/* Issue Details - Always Visible */}
                          <div className="pt-4 space-y-4">
                            <div>
                              <h5 className="text-sm font-semibold text-foreground mb-2">
                                Description
                              </h5>
                              <p className="text-sm text-muted-foreground">
                                {finding.description}
                              </p>
                            </div>

                            {finding.file_path && (
                              <div>
                                <h5 className="text-sm font-semibold text-foreground mb-2">
                                  Location
                                </h5>
                                <code className="text-sm text-muted-foreground bg-white/5 px-2 py-1 rounded">
                                  {finding.file_path}
                                  {finding.line_number && ` (Line ${finding.line_number})`}
                                </code>
                              </div>
                            )}
                          </div>

                          {/* AI Suggestion - GATED based on user plan */}
                          <div className="mt-6">
                            {(() => {
                              // Determine user's effective plan (API response takes precedence)
                              const plan = results.user_plan || user?.plan || 'free'
                              const isLoggedIn = isAuthenticated
                              const isFreeUser = plan === 'free'
                              const isPaidUser = ['plus', 'pro', 'enterprise'].includes(plan)

                              // For free users, show first 2 AI suggestions unblurred
                              const isPreviewFinding = index < (results.ai_preview_count || 2)

                              if (!isLoggedIn) {
                                // NOT LOGGED IN - All AI suggestions blurred with login CTA
                                return (
                                  <AISuggestionBlur
                                    isBlurred={true}
                                    suggestion={finding.recommendation}
                                    onUpgrade={handleLogin}
                                    upgradePlan="free"
                                    showPartialPreview={false}
                                  />
                                )
                              }

                              if (isFreeUser && !isPreviewFinding) {
                                // FREE USER - Show first 2 suggestions, blur the rest
                                return (
                                  <AISuggestionBlur
                                    isBlurred={true}
                                    suggestion={finding.recommendation}
                                    onUpgrade={() => navigate('/pricing')}
                                    upgradePlan="plus"
                                    showPartialPreview={true}
                                  />
                                )
                              }

                              if (isPaidUser || isPreviewFinding) {
                                // PAID USER or Preview finding - Show full AI suggestion
                                return (
                                  <div className="p-4 rounded-xl bg-primary/10 border border-primary/30">
                                    <div className="flex items-center gap-2 mb-2">
                                      <CheckCircle className="h-4 w-4 text-primary" />
                                      <h5 className="font-semibold text-primary">
                                        AI Fix Suggestion
                                        {isFreeUser && isPreviewFinding && (
                                          <span className="ml-2 text-xs text-muted-foreground">
                                            (Preview {index + 1} of 2)
                                          </span>
                                        )}
                                      </h5>
                                    </div>
                                    <p className="text-sm text-muted-foreground mb-3">
                                      {finding.recommendation}
                                    </p>
                                    <div className="flex gap-2">
                                      <Button variant="primary" size="sm">
                                        Copy Fix
                                      </Button>
                                      {isPaidUser && (
                                        <Button variant="secondary" size="sm">
                                          Create PR
                                        </Button>
                                      )}
                                    </div>
                                  </div>
                                )
                              }

                              // Fallback - show blurred
                              return (
                                <AISuggestionBlur
                                  isBlurred={true}
                                  suggestion={finding.recommendation}
                                  onUpgrade={() => navigate('/pricing')}
                                  upgradePlan="plus"
                                  showPartialPreview={false}
                                />
                              )
                            })()}
                          </div>
                        </motion.div>
                      )}
                    </div>
                  )
                })
              })()}
            </div>
          </Card>
        </motion.div>

        {/* Login/Upgrade CTA */}
        {!isAuthenticated && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="p-8 text-center glow-primary" hover={false}>
              <div className="max-w-2xl mx-auto space-y-6">
                <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600">
                  <Lock className="h-8 w-8 text-white" />
                </div>

                <div>
                  <h2 className="text-2xl font-bold text-foreground mb-2">
                    Unlock AI-Powered Remediation
                  </h2>
                  <p className="text-muted-foreground">
                    Login to see detailed fix recommendations and automate security improvements.
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={handleLogin}
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

        {/* Detected Technologies */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card className="p-6" hover={false}>
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Detected Technologies
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[
                { name: 'Docker', icon: Terminal },
                { name: 'Kubernetes', icon: Cloud },
                { name: 'Terraform', icon: Layers },
              ].map((tech) => (
                <div
                  key={tech.name}
                  className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10"
                >
                  <tech.icon className="h-6 w-6 text-primary" />
                  <span className="font-medium text-foreground">{tech.name}</span>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}

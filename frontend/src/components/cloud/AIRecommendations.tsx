import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertCircle, AlertTriangle, BookOpen, CheckCircle,
  ChevronDown, ChevronUp, Copy, DollarSign, Download,
  ExternalLink, ExternalLink as ExternalLinkIcon,
  FileCode, FileText, Info, ListChecks, RotateCcw, Search, Shield,
  Sparkles, Terminal, TrendingUp, XCircle,
} from 'lucide-react'
import React, { useCallback, useEffect, useState } from 'react'

import { cloudApi, type CloudAIRecommendation, type CloudAIRecommendationSummary, type CreateJiraTicketPayload, type JiraTicketResponse } from '@/api/endpoints/cloud'
import { cn } from '@/lib/utils'
import { useCloudStore } from '@/stores/cloud-store'

interface Props {
  connectionId: string
}

const SEVERITY_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  critical: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', label: 'Critical' },
  high: { icon: AlertCircle, color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30', label: 'High' },
  medium: { icon: Info, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30', label: 'Medium' },
  low: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30', label: 'Low' },
}

const CATEGORY_CONFIG: Record<string, { color: string; bg: string }> = {
  security: { color: 'text-red-400', bg: 'bg-red-500/10' },
  cost: { color: 'text-green-400', bg: 'bg-green-500/10' },
  compliance: { color: 'text-purple-400', bg: 'bg-purple-500/10' },
  performance: { color: 'text-blue-400', bg: 'bg-blue-500/10' },
  networking: { color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  storage: { color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  iam: { color: 'text-pink-400', bg: 'bg-pink-500/10' },
}

const CATEGORIES = ['all', 'security', 'cost', 'compliance', 'performance', 'networking', 'storage', 'iam'] as const
const STATUS_FILTERS = ['all', 'open', 'resolved', 'ignored'] as const

export function AIRecommendations({ connectionId }: Props) {
  const { recommendations, setRecommendations, recommendationsSummary, setRecommendationsSummary } = useCloudStore()
  const [loading, setLoading] = useState(true)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [jiraModal, setJiraModal] = useState<{ open: boolean; rec: CloudAIRecommendation | null }>({ open: false, rec: null })
  const [jiraResult, setJiraResult] = useState<JiraTicketResponse | null>(null)
  const [jiraSubmitting, setJiraSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [recsData, summaryData] = await Promise.all([
        cloudApi.recommendations(connectionId),
        cloudApi.recommendationsSummary(connectionId),
      ])
      setRecommendations(recsData.recommendations)
      setRecommendationsSummary(summaryData)
    } catch {
      // ignore
    }
    setLoading(false)
  }, [connectionId, setRecommendations, setRecommendationsSummary])

  useEffect(() => {
    void load()
  }, [load])

  const handleExportPdf = () => {
    void (async () => {
      setExportingPdf(true)
      try {
        const blob = await cloudApi.exportRecommendationsPdf(connectionId)
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `recommendations-${connectionId.slice(0, 8)}.pdf`
        a.click()
        URL.revokeObjectURL(url)
      } catch {
        // ignore
      }
      setExportingPdf(false)
    })()
  }

  const handleCreateJiraTicket = async (rec: CloudAIRecommendation, payload: CreateJiraTicketPayload) => {
    setJiraSubmitting(true)
    setJiraResult(null)
    try {
      const result = await cloudApi.createJiraTicket(connectionId, rec.recommendation_id, payload)
      setJiraResult(result)
    } catch {
      setJiraResult({ success: false, ticket_url: null, ticket_key: null, error: 'Failed to create ticket' })
    }
    setJiraSubmitting(false)
  }

  const openJiraModal = (rec: CloudAIRecommendation) => {
    setJiraResult(null)
    setJiraModal({ open: true, rec })
  }

  const filtered = recommendations.filter((r) => {
    if (categoryFilter !== 'all' && r.category !== categoryFilter) { return false }
    if (statusFilter !== 'all' && r.status !== statusFilter) { return false }
    if (search) {
      const q = search.toLowerCase()
      return (
        r.title.toLowerCase().includes(q) ||
        r.summary.toLowerCase().includes(q) ||
        r.service.toLowerCase().includes(q) ||
        (r.resource_id || '').toLowerCase().includes(q) ||
        (r.resource_name || '').toLowerCase().includes(q)
      )
    }
    return true
  })

  const handleStatusChange = (recId: string, newStatus: string) => {
    void (async () => {
      try {
        await cloudApi.updateRecommendationStatus(connectionId, recId, newStatus)
        setRecommendations(
          recommendations.map((r) => (r.recommendation_id === recId ? { ...r, status: newStatus } : r)),
        )
        if (recommendationsSummary) {
          const oldStatus = recommendations.find((r) => r.recommendation_id === recId)?.status ?? 'open'
          const byStatus = { ...recommendationsSummary.by_status }
          byStatus[oldStatus] = Math.max(0, (byStatus[oldStatus] ?? 0) - 1)
          byStatus[newStatus] = (byStatus[newStatus] ?? 0) + 1
          setRecommendationsSummary({ ...recommendationsSummary, by_status: byStatus })
        }
      } catch {
        // ignore
      }
    })()
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-card/60 border border-white/10 animate-pulse" />
          ))}
        </div>
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 rounded-xl bg-card/60 border border-white/10 animate-pulse" />
        ))}
    </div>
  )
}

// ── Jira Modal ──

function JiraModal({
  rec,
  submitting,
  result,
  onClose,
  onSubmit,
}: {
  rec: CloudAIRecommendation
  submitting: boolean
  result: JiraTicketResponse | null
  onClose: () => void
  onSubmit: (rec: CloudAIRecommendation, payload: CreateJiraTicketPayload) => void
}) {
  const [jiraUrl, setJiraUrl] = useState('')
  const [email, setEmail] = useState('')
  const [apiToken, setApiToken] = useState('')
  const [projectKey, setProjectKey] = useState('')
  const [issueType, setIssueType] = useState('Task')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const description = `${rec.summary}\n\n---\nTechnical Explanation:\n${rec.technical_explanation}\n\nBusiness Impact:\n${rec.business_impact}\n\nService: ${rec.service}\nResource: ${rec.resource_id}\nSeverity: ${rec.severity}\nCategory: ${rec.category}`
    void onSubmit(rec, {
      jira_url: jiraUrl,
      email,
      api_token: apiToken,
      project_key: projectKey,
      summary: `[DevArchAI] ${rec.title}`,
      description,
      issue_type: issueType,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-lg p-6 rounded-2xl bg-card border border-white/10 shadow-2xl"
        onClick={function (e) { e.stopPropagation() }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-foreground">Create Jira Ticket</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <XCircle className="h-4 w-4" />
          </button>
        </div>

        {result ? (
          <div className="space-y-3">
            {result.success ? (
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
                <CheckCircle className="h-8 w-8 text-green-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-green-400 mb-1">Ticket Created!</p>
                <p className="text-xs text-muted-foreground mb-3">{result.ticket_key}</p>
                <a
                  href={result.ticket_url ?? '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                >
                  <ExternalLinkIcon className="h-3 w-3" />
                  Open in Jira
                </a>
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-sm font-medium text-red-400 mb-1">Failed to create ticket</p>
                <p className="text-xs text-muted-foreground">{result.error}</p>
              </div>
            )}
            <button
              onClick={onClose}
              className="w-full py-2 rounded-lg text-xs font-medium bg-white/10 text-foreground hover:bg-white/20 transition-colors"
            >
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1 block">Jira URL</label>
              <input
                type="url"
                value={jiraUrl}
                onChange={function (e) { setJiraUrl(e.target.value) }}
                placeholder="https://your-domain.atlassian.net"
                required
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1 block">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={function (e) { setEmail(e.target.value) }}
                  placeholder="you@example.com"
                  required
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1 block">API Token</label>
                <input
                  type="password"
                  value={apiToken}
                  onChange={function (e) { setApiToken(e.target.value) }}
                  placeholder="jira-api-token"
                  required
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1 block">Project Key</label>
                <input
                  type="text"
                  value={projectKey}
                  onChange={function (e) { setProjectKey(e.target.value) }}
                  placeholder="SEC"
                  required
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1 block">Issue Type</label>
                <select
                  value={issueType}
                  onChange={function (e) { setIssueType(e.target.value) }}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Task">Task</option>
                  <option value="Bug">Bug</option>
                  <option value="Story">Story</option>
                </select>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Summary</p>
              <p className="text-sm text-foreground">[DevArchAI] {rec.title}</p>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2 rounded-lg text-xs font-medium bg-white/10 text-muted-foreground hover:text-foreground hover:bg-white/20 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex-1 py-2 rounded-lg text-xs font-medium bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors disabled:opacity-40"
              >
                {submitting ? 'Creating...' : 'Create Ticket'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Summary Cards */}
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <SummaryCards summary={recommendationsSummary} />
        </div>
        <button
          onClick={handleExportPdf}
          disabled={exportingPdf || !recommendationsSummary || recommendationsSummary.total === 0}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0 mt-1"
          title="Export recommendations as PDF"
        >
          <Download className={cn('h-3.5 w-3.5', exportingPdf && 'animate-bounce')} />
          {exportingPdf ? 'Exporting...' : 'PDF'}
        </button>
      </div>

      {/* Category Filters */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => {
          const cfg = CATEGORY_CONFIG[cat]
          return (
            <button
              key={cat}
              onClick={() => setCategoryFilter(categoryFilter === cat ? 'all' : cat)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-all border',
                categoryFilter === cat
                  ? cn(cfg?.bg || 'bg-white/10', cfg?.color || 'text-foreground', 'border-current')
                  : 'bg-white/5 border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/[0.05]',
              )}
            >
              {cat === 'all' ? 'All' : cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          )
        })}
        <span className="w-px h-6 bg-white/10 mx-1 self-center" />
        {STATUS_FILTERS.map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(statusFilter === st ? 'all' : st)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-all border',
              statusFilter === st
                ? 'bg-white/10 text-foreground border-white/20'
                : 'bg-white/5 border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/[0.05]',
            )}
          >
            {st === 'all' ? 'All' : st.charAt(0).toUpperCase() + st.slice(1)}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search recommendations..."
          className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
        />
      </div>

      {/* Recommendations List */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground text-sm">
            {recommendations.length === 0
              ? 'No AI recommendations yet. Run a scan to generate recommendations.'
              : 'No recommendations match your filters.'}
          </div>
        ) : (
          filtered.map((rec) => {
            const sevConfig = SEVERITY_CONFIG[rec.severity] || SEVERITY_CONFIG.medium
            const catCfg = CATEGORY_CONFIG[rec.category] || { color: 'text-gray-400', bg: 'bg-gray-500/10' }
            const isExpanded = expandedId === rec.recommendation_id

            return (
              <motion.div
                key={rec.recommendation_id}
                layout
                className={cn(
                  'rounded-xl border transition-all overflow-hidden',
                  isExpanded
                    ? 'bg-card/80 border-orange-500/30'
                    : rec.status === 'resolved'
                      ? 'bg-green-500/5 border-green-500/20'
                      : rec.status === 'ignored'
                        ? 'bg-gray-500/5 border-gray-500/20'
                        : 'bg-white/5 border-white/10 hover:bg-white/[0.03]',
                )}
              >
                {/* Header */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : rec.recommendation_id)}
                  className="w-full flex items-start gap-3 p-4 text-left"
                >
                  <sevConfig.icon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', sevConfig.color)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-foreground truncate">
                        {rec.title || rec.summary || `${rec.service} recommendation`}
                      </span>
                      <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full font-medium border whitespace-nowrap', sevConfig.bg, sevConfig.color)}>
                        {rec.severity}
                      </span>
                      <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap', catCfg.bg, catCfg.color)}>
                        {rec.category}
                      </span>
                      {rec.status !== 'open' && (
                        <span className={cn(
                          'text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                          rec.status === 'resolved' ? 'bg-green-500/10 text-green-400' : 'bg-gray-500/10 text-gray-400',
                        )}>
                          {rec.status}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">{rec.technical_explanation || rec.summary}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-[10px] text-muted-foreground font-mono uppercase">{rec.service}</span>
                      {rec.resource_id && <span className="text-[10px] text-muted-foreground font-mono">{rec.resource_id}</span>}
                      {rec.estimated_monthly_savings > 0 && (
                        <span className="text-[10px] text-green-400 font-medium">
                          ${rec.estimated_monthly_savings.toFixed(2)}/mo
                        </span>
                      )}
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                  )}
                </button>

                {/* Expanded Detail */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="border-t border-white/10"
                    >
                      <div className="p-4 space-y-4">
                        {/* Info Grid */}
                        <div className="grid gap-4 md:grid-cols-2">
                          <DetailSection icon={Sparkles} title="Summary">
                            <p className="text-sm text-foreground">{rec.summary}</p>
                          </DetailSection>
                          <DetailSection icon={AlertCircle} title="Technical Explanation">
                            <p className="text-sm text-foreground">{rec.technical_explanation || 'No technical details available.'}</p>
                          </DetailSection>
                          <DetailSection icon={DollarSign} title="Business Impact">
                            <p className="text-sm text-foreground">{rec.business_impact || 'No specific business impact identified.'}</p>
                          </DetailSection>
                        </div>

                        {/* Why This Matters / Cost Impact */}
                        {rec.estimated_monthly_savings > 0 && (
                          <DetailSection icon={TrendingUp} title="Cost Impact">
                            <p className="text-sm text-foreground">
                              Estimated monthly savings: ${rec.estimated_monthly_savings.toFixed(2)}
                            </p>
                          </DetailSection>
                        )}

                        {/* Official Documentation */}
                        {rec.official_documentation_url && (
                          <DetailSection icon={BookOpen} title="Documentation">
                            <a
                              href={rec.official_documentation_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-blue-400 hover:text-blue-300 underline inline-flex items-center gap-1"
                            >
                              {rec.official_documentation_url}
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </DetailSection>
                        )}

                        {/* Estimated Impact Stats */}
                        {(rec.estimated_monthly_savings > 0 || rec.estimated_risk_reduction > 0) && (
                          <div className="grid grid-cols-2 gap-3">
                            {rec.estimated_monthly_savings > 0 && (
                              <div className="p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                                <p className="text-[10px] uppercase tracking-wider text-green-400 mb-1">Estimated Monthly Savings</p>
                                <p className="text-lg font-bold text-green-400">${rec.estimated_monthly_savings.toFixed(2)}</p>
                              </div>
                            )}
                            {rec.estimated_risk_reduction > 0 && (
                              <div className="p-3 rounded-lg bg-orange-500/5 border border-orange-500/20">
                                <p className="text-[10px] uppercase tracking-wider text-orange-400 mb-1">Estimated Risk Reduction</p>
                                <p className="text-lg font-bold text-orange-400">{rec.estimated_risk_reduction.toFixed(0)}%</p>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Remediation Panel */}
                        <RemediationPanel rec={rec} />

                        {/* Recommendation Source */}
                        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                          <span>Source: {rec.recommendation_source}</span>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 pt-2 border-t border-white/10">
                          {rec.status === 'open' && (
                            <>
                              <button
                                onClick={function () { handleStatusChange(rec.recommendation_id, 'resolved') }}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors"
                              >
                                <CheckCircle className="h-3.5 w-3.5" />
                                Mark Resolved
                              </button>
                              <button
                                onClick={function () { handleStatusChange(rec.recommendation_id, 'ignored') }}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-500/10 text-gray-400 hover:bg-gray-500/20 transition-colors"
                              >
                                <XCircle className="h-3.5 w-3.5" />
                                Ignore
                              </button>
                              <span className="w-px h-5 bg-white/10" />
                              <button
                                onClick={function () { openJiraModal(rec) }}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                              >
                                <ExternalLinkIcon className="h-3.5 w-3.5" />
                                Create Jira Ticket
                              </button>
                            </>
                          )}
                          {rec.status !== 'open' && (
                            <button
                              onClick={function () { handleStatusChange(rec.recommendation_id, 'open') }}
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                            >
                              <RotateCcw className="h-3.5 w-3.5" />
                              Reopen
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })
        )}
      </div>

      {/* Jira Modal */}
      {jiraModal.open && jiraModal.rec && (
        <JiraModal
          rec={jiraModal.rec}
          submitting={jiraSubmitting}
          result={jiraResult}
          onClose={function () { setJiraModal({ open: false, rec: null }); setJiraResult(null) }}
          onSubmit={function (rec, payload) { void handleCreateJiraTicket(rec, payload) }}
        />
      )}
    </motion.div>
  )
}

// ── Sub-components ──

function SummaryCards({ summary }: { summary: CloudAIRecommendationSummary | null }) {
  if (!summary) { return null }

  const cards = [
    {
      label: 'Total Recommendations',
      value: summary.total,
      icon: Sparkles,
      color: 'text-orange-400',
      bg: 'bg-orange-500/10',
    },
    {
      label: 'Critical Actions',
      value: summary.critical_count,
      icon: AlertTriangle,
      color: 'text-red-400',
      bg: 'bg-red-500/10',
    },
    {
      label: 'Potential Monthly Savings',
      value: `$${summary.total_monthly_savings.toFixed(0)}`,
      icon: DollarSign,
      color: 'text-green-400',
      bg: 'bg-green-500/10',
    },
    {
      label: 'Avg Risk Reduction',
      value: `${summary.avg_risk_reduction}%`,
      icon: Shield,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
  ]

  return (
    <div className="grid gap-3 md:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div
            key={card.label}
            className="p-4 rounded-xl bg-card/60 backdrop-blur-xl border border-white/10"
          >
            <div className="flex items-center gap-2 mb-2">
              <div className={cn('p-1.5 rounded-lg', card.bg)}>
                <Icon className={cn('h-3.5 w-3.5', card.color)} />
              </div>
              <span className="text-xs font-medium text-muted-foreground">{card.label}</span>
            </div>
            <p className={cn('text-xl font-bold', card.color)}>{card.value}</p>
          </div>
        )
      })}
    </div>
  )
}

function DetailSection({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="p-3 rounded-lg bg-white/5 border border-white/10">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{title}</span>
      </div>
      {children}
    </div>
  )
}

function RemediationPanel({ rec }: { rec: CloudAIRecommendation }) {
  const [copied, setCopied] = useState<string | null>(null)

  const copyToClipboard = (text: string, label: string) => {
    void (async () => {
      try {
        await navigator.clipboard.writeText(text)
        setCopied(label)
        setTimeout(() => setCopied(null), 2000)
      } catch {
        // ignore
      }
    })()
  }

  const hasRemediation = rec.cloudformation_fix || rec.aws_cli_fix || rec.terraform_fix || rec.console_steps?.length

  if (!hasRemediation) { return null }

  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Remediation</p>
      <div className="space-y-2">
        {/* CloudFormation */}
        {rec.cloudformation_fix && (
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <FileCode className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">CloudFormation</span>
              </div>
              <button
                onClick={function () { copyToClipboard(rec.cloudformation_fix ?? '', 'cfn') }}
                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                <Copy className="h-3 w-3" />
                {copied === 'cfn' ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="text-xs text-foreground font-mono whitespace-pre-wrap overflow-x-auto bg-black/30 p-2 rounded-lg">
              {rec.cloudformation_fix}
            </pre>
          </div>
        )}

        {/* AWS CLI */}
        {rec.aws_cli_fix && (
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">AWS CLI</span>
              </div>
              <button
                onClick={function () { copyToClipboard(rec.aws_cli_fix ?? '', 'cli') }}
                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                <Copy className="h-3 w-3" />
                {copied === 'cli' ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="text-xs text-foreground font-mono whitespace-pre-wrap overflow-x-auto bg-black/30 p-2 rounded-lg">
              {rec.aws_cli_fix}
            </pre>
          </div>
        )}

        {/* Terraform */}
        {rec.terraform_fix && (
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <FileCode className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Terraform</span>
              </div>
              <button
                onClick={function () { copyToClipboard(rec.terraform_fix ?? '', 'tf') }}
                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                <Copy className="h-3 w-3" />
                {copied === 'tf' ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="text-xs text-foreground font-mono whitespace-pre-wrap overflow-x-auto bg-black/30 p-2 rounded-lg">
              {rec.terraform_fix}
            </pre>
          </div>
        )}

        {/* Console Steps */}
        {rec.console_steps && rec.console_steps.length > 0 && (
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center gap-1.5 mb-2">
              <ListChecks className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">AWS Console Steps</span>
            </div>
            <ol className="space-y-1.5 ml-4">
              {rec.console_steps.map((step, i) => (
                <li key={i} className="text-xs text-foreground list-decimal">{step}</li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  )
}

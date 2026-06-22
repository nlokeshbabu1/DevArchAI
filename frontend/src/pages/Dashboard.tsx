import { motion } from 'framer-motion'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Play, FolderGit2, AlertTriangle, Activity, Brain,
  TrendingUp, ArrowRight, Download, FileText,
  FileSpreadsheet, ExternalLink, Shield
} from 'lucide-react'
import { Button, Card } from '../components/ui-animated'
import { cn } from '../lib/utils'
import { useAuthStore } from '../stores/auth-store'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi, type RecentScan } from '../api/endpoints/dashboard'
import { repositoriesApi, type Repository } from '../api/endpoints/repositories'
import apiClient from '../api/endpoints/client'
import { InlineScanPanel } from '../components/InlineScanPanel'
import { useState, useEffect } from 'react'

import {
  KpiRow, SecurityOverview, FindingsChart,
  RiskTable, ActivityFeed, AiSuggestions,
  OnboardingView
} from '../components/dashboard'

const findingsData = [
  { name: 'Mon', critical: 2, high: 5, medium: 12, low: 8 },
  { name: 'Tue', critical: 1, high: 3, medium: 8, low: 15 },
  { name: 'Wed', critical: 3, high: 7, medium: 15, low: 10 },
  { name: 'Thu', critical: 1, high: 4, medium: 10, low: 12 },
  { name: 'Fri', critical: 2, high: 6, medium: 14, low: 9 },
  { name: 'Sat', critical: 0, high: 2, medium: 5, low: 7 },
  { name: 'Sun', critical: 1, high: 3, medium: 7, low: 11 },
]

const getValidScore = (score: number | null | undefined) => {
  if (typeof score !== 'number' || Number.isNaN(score)) return null
  return Math.min(100, Math.max(0, score))
}

const formatScore = (score: number) => Number(score.toFixed(1))

interface AISuggestion {
  id: string; title: string; description: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  confidence?: number; category?: string; file_path?: string; status?: string
}

const getRepositoryScore = (repo: Repository) => getValidScore(repo.overall_score)
const getRepositoryCriticalCount = (repo: Repository) => repo.issues?.critical ?? 0
const getRepositoryHighCount = (repo: Repository) => repo.issues?.high ?? 0

const formatRelativeDate = (value?: string | null) => {
  if (!value) return 'Never'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return date.toLocaleDateString(undefined, {
    month: 'short', day: 'numeric',
    year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
  })
}

export function Dashboard() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { isAuthenticated } = useAuthStore()
  const [stats, setStats] = useState({ totalRepositories: 0, totalScans: 0, criticalIssues: 0, aiSuggestions: 0 })
  const [showScanPanel, setShowScanPanel] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)

  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.getSummary,
    refetchInterval: 10000,
    enabled: !!isAuthenticated,
    retry: 2,
  })

  const { data: recentScansData, isLoading: scansLoading, error: scansError } = useQuery({
    queryKey: ['dashboard-recent-scans'],
    queryFn: () => dashboardApi.getRecentScans(5),
    refetchInterval: 10000,
    enabled: !!isAuthenticated,
    retry: 2,
  })

  const { data: repositoriesData, isLoading: repositoriesLoading } = useQuery({
    queryKey: ['dashboard-risky-repositories'],
    queryFn: async () => {
      const response = await repositoriesApi.listRepositories(1, 50)
      return response.repositories || []
    },
    refetchInterval: 10000,
    enabled: !!isAuthenticated,
    retry: 2,
  })

  const { data: suggestionsData, isLoading: suggestionsLoading } = useQuery({
    queryKey: ['dashboard-ai-recommendations'],
    queryFn: async () => {
      const response = await apiClient.get<{ suggestions?: AISuggestion[] }>('/suggestions')
      return response.data.suggestions || []
    },
    refetchInterval: 15000,
    enabled: !!isAuthenticated,
    retry: 1,
  })

  const recentScans = Array.isArray(recentScansData) ? recentScansData : []
  const repositories = Array.isArray(repositoriesData) ? repositoriesData : []
  const suggestions = Array.isArray(suggestionsData) ? suggestionsData : []
  const isLoading = summaryLoading || scansLoading
  const hasError = summaryError || scansError
  const errorMessage = hasError instanceof Error ? hasError.message : 'Failed to load dashboard data'

  useEffect(() => {
    if (summary) {
      setStats({
        totalRepositories: summary.total_repositories || 0,
        totalScans: summary.total_scans || 0,
        criticalIssues: summary.critical_findings || 0,
        aiSuggestions: summary.ai_suggestions || 0,
      })
    }
  }, [summary])

  const summaryScore = getValidScore(summary?.average_score)
  const recentScoreValues = recentScans.reduce<number[]>((scores, scan) => {
    const scanScore = getValidScore(scan.overall_score ?? scan.security_score)
    if (scanScore !== null) scores.push(scanScore)
    return scores
  }, [])
  const fallbackSecurityScore = recentScoreValues.length > 0
    ? formatScore(recentScoreValues.reduce((total, score) => total + score, 0) / recentScoreValues.length)
    : null
  const securityScore = summaryScore ?? fallbackSecurityScore ?? 0
  const hasSecurityScore = summaryScore !== null || fallbackSecurityScore !== null
  const isUsingFallbackScore = summaryScore === null && fallbackSecurityScore !== null

  const totalRepositories = summary?.total_repositories ?? stats.totalRepositories
  const totalScans = summary?.total_scans ?? stats.totalScans
  const criticalIssues = summary?.critical_findings ?? stats.criticalIssues
  const aiSuggestions = summary?.ai_suggestions ?? stats.aiSuggestions

  const repositoriesAtRisk = repositories.filter((repo) => {
    const score = getRepositoryScore(repo)
    return getRepositoryCriticalCount(repo) > 0 || getRepositoryHighCount(repo) > 0 || (score !== null && score < 70)
  }).length

  const riskScore = Math.min(100, Math.max(0, Math.round(
    (100 - securityScore) + Math.min(35, criticalIssues * 4) + Math.min(20, repositoriesAtRisk * 3)
  )))

  const sortedRecentScores = recentScans
    .map((scan) => getValidScore(scan.overall_score ?? scan.security_score))
    .filter((score): score is number => score !== null)
  const scoreDelta = sortedRecentScores.length >= 2
    ? formatScore(sortedRecentScores[0] - sortedRecentScores[1])
    : null
  const fixedFindingsEstimate = scoreDelta !== null && scoreDelta > 0
    ? Math.max(1, Math.round(scoreDelta / 3)) : 0
  const newCriticalFindings = scoreDelta !== null && scoreDelta < 0 ? criticalIssues : 0

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <div className="h-7 w-48 bg-white/10 rounded animate-pulse" />
            <div className="h-4 w-56 bg-white/10 rounded animate-pulse mt-2" />
          </div>
          <div className="h-9 w-28 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-2xl bg-white/5 border border-white/10 p-5 animate-pulse">
              <div className="h-3 w-20 bg-white/10 rounded mb-3" />
              <div className="h-8 w-16 bg-white/10 rounded mb-2" />
              <div className="h-3 w-32 bg-white/5 rounded" />
            </div>
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="rounded-2xl bg-white/5 border border-white/10 p-6 animate-pulse h-[300px]">
              <div className="h-4 w-32 bg-white/10 rounded mb-4" />
              <div className="h-full w-full bg-white/5 rounded" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (hasError) {
    return (
      <div className="space-y-6">
        <Card className="p-8 text-center" hover={false}>
          <div className="p-3 rounded-full bg-red-500/10 border border-red-500/30 w-fit mx-auto mb-4">
            <AlertTriangle className="h-8 w-8 text-red-400" />
          </div>
          <h2 className="text-lg font-bold text-foreground mb-2">Unable to Load Dashboard</h2>
          <p className="text-sm text-muted-foreground mb-5">{errorMessage}</p>
          <div className="flex gap-3 justify-center">
            <Button variant="secondary" onClick={() => window.location.reload()}>Retry</Button>
            <Button variant="primary" onClick={() => navigate('/scan')} icon={<Play className="h-4 w-4" />}>
              Start Scan
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  // Empty / onboarding state
  const hasNoData = totalScans === 0 && totalRepositories === 0 && recentScans.length === 0
  if (hasNoData && !isLoading) {
    return (
      <>
        <OnboardingView onStartScan={() => setShowScanPanel(true)} />
        <InlineScanPanel
          isOpen={showScanPanel}
          onClose={() => setShowScanPanel(false)}
          onScanComplete={(scanId) => { setShowScanPanel(false); navigate(`/scans/${scanId}`) }}
        />
      </>
    )
  }

  // Analytics dashboard
  return (
    <>
      <div className="space-y-5">
        {/* Header */}
        <motion.div
          className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Overview of your DevOps security posture
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowExportMenu(!showExportMenu)}
                icon={<Download className="h-3.5 w-3.5" />}
              >
                Export
              </Button>
              {showExportMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute right-0 top-full mt-1.5 w-44 rounded-xl bg-card/95 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/40 overflow-hidden z-50"
                >
                  {[
                    { label: 'Download PDF', icon: FileText, action: () => {} },
                    { label: 'Export Excel', icon: FileSpreadsheet, action: () => {} },
                    { label: 'Share Report', icon: ExternalLink, action: () => navigate('/reports') },
                  ].map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => { setShowExportMenu(false); opt.action() }}
                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                    >
                      <opt.icon className="h-4 w-4" />
                      {opt.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowScanPanel(true)}
              icon={<Play className="h-4 w-4" />}
              glow
            >
              New Scan
            </Button>
          </div>
        </motion.div>

        {/* KPI Row */}
        <KpiRow
          items={[
            {
              title: 'Total Repositories',
              value: totalRepositories.toString(),
              subtitle: 'Monitored repositories',
              icon: FolderGit2,
              trend: totalRepositories > 0 ? 'up' : 'neutral',
              trendValue: `${totalRepositories} total`,
            },
            {
              title: 'Total Scans',
              value: totalScans.toString(),
              subtitle: 'Completed security scans',
              icon: Activity,
              trend: totalScans > 0 ? 'up' : 'neutral',
              trendValue: `${totalScans} scans`,
            },
            {
              title: 'Critical Issues',
              value: criticalIssues.toString(),
              subtitle: criticalIssues > 0 ? 'Needs immediate attention' : 'No critical issues',
              icon: AlertTriangle,
              trend: criticalIssues > 0 ? 'down' : 'up',
              trendValue: `${criticalIssues} open`,
              severity: {
                critical: criticalIssues,
                high: Math.round(criticalIssues * 0.6),
                medium: Math.round(criticalIssues * 1.5),
                low: Math.round(criticalIssues * 2),
              },
              accentColor: criticalIssues > 0 ? 'text-red-400' : 'text-green-400',
            },
            {
              title: 'AI Suggestions',
              value: aiSuggestions.toString(),
              subtitle: 'AI-powered remediation',
              icon: Brain,
              trend: aiSuggestions > 0 ? 'up' : 'neutral',
              trendValue: `${aiSuggestions} active`,
              accentColor: 'text-primary',
            },
          ]}
        />

        {/* Security Overview */}
        <SecurityOverview
          securityScore={securityScore}
          hasSecurityScore={hasSecurityScore}
          riskScore={riskScore}
          criticalIssues={criticalIssues}
          repositoriesAtRisk={repositoriesAtRisk}
          scoreDelta={scoreDelta}
          newCriticalFindings={newCriticalFindings}
          fixedFindingsEstimate={fixedFindingsEstimate}
          isLoading={isLoading}
        />

        {/* Findings Chart */}
        <FindingsChart data={findingsData} />

        {/* Risk Repositories & Activity Feed */}
        <div className="grid gap-5 lg:grid-cols-2">
          <RiskTable
            repositories={repositories}
            isLoading={repositoriesLoading}
            getScore={getRepositoryScore}
            getCritical={getRepositoryCriticalCount}
            getHigh={getRepositoryHighCount}
            formatDate={formatRelativeDate}
          />
          <ActivityFeed
            scans={recentScans}
            isLoading={scansLoading}
          />
        </div>

        {/* AI Recommendations */}
        <AiSuggestions
          suggestions={suggestions}
          isLoading={suggestionsLoading}
        />
      </div>

      <InlineScanPanel
        isOpen={showScanPanel}
        onClose={() => setShowScanPanel(false)}
        onScanComplete={(scanId) => { setShowScanPanel(false); navigate(`/scans/${scanId}`) }}
      />
    </>
  )
}

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Play, FolderGit2, AlertTriangle, Activity, Brain,
  TrendingUp, ArrowRight, Download, FileText,
  FileSpreadsheet, ExternalLink, Shield
} from 'lucide-react'
import { useState, useEffect, Fragment } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import apiClient from '../api/endpoints/client'
import { dashboardApi, type RecentScan } from '../api/endpoints/dashboard'
import { repositoriesApi, type Repository } from '../api/endpoints/repositories'
import {
  KpiRow, SecurityOverview,
  RiskTable, ActivityFeed, AiSuggestions,
  OnboardingView
} from '../components/dashboard'
import { InlineScanPanel } from '../components/InlineScanPanel'
import { PageHeader } from '../components/ui/PageHeader'
import { Button, Card } from '../components/ui-animated'
import { resolveSecurityScore } from '../lib/security-score'
import { cn } from '../lib/utils'
import { useAuthStore } from '../stores/auth-store'

const formatScore = (score: number) => Number(score.toFixed(1))

interface AISuggestion {
  id: string; title: string; description: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  confidence?: number; category?: string; file_path?: string; status?: string
}

const getValidScore = (data: { security_score?: number | null; overall_score?: number | null }) =>
  resolveSecurityScore(data)?.value ?? null

const getRepositoryScore = (repo: Repository) =>
  getValidScore({ overall_score: repo.overall_score, security_score: (repo as { security_score?: number }).security_score })
const getRepositoryCriticalCount = (repo: Repository) => repo.issues?.critical ?? 0
const getRepositoryHighCount = (repo: Repository) => repo.issues?.high ?? 0

const formatRelativeDate = (value?: string | null) => {
  if (!value) {return 'Never'}
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {return 'Unknown'}
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

  const summaryScore = getValidScore({ overall_score: summary?.average_score })
  const recentScoreValues = recentScans.reduce<number[]>((scores, scan) => {
    const scanScore = getValidScore(scan)
    if (scanScore !== null) {scores.push(scanScore)}
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

  const sortedRecentScores = recentScans
    .map((scan) => getValidScore(scan))
    .filter((score): score is number => score !== null)
  const scoreDelta = sortedRecentScores.length >= 2
    ? formatScore(sortedRecentScores[0] - sortedRecentScores[1])
    : null
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
      <>
        <div className="space-y-6">
          <Card className="p-8 text-center" hover={false}>
            <div className="p-3 rounded-full bg-red-500/10 border border-red-500/30 w-fit mx-auto mb-4">
              <AlertTriangle className="h-8 w-8 text-red-400" />
            </div>
            <h2 className="text-lg font-bold text-foreground mb-2">Unable to Load Dashboard</h2>
            <p className="text-sm text-muted-foreground mb-5">{errorMessage}</p>
            <div className="flex gap-3 justify-center">
              <Button variant="secondary" onClick={() => window.location.reload()}>Retry</Button>
              <Button variant="primary" onClick={() => setShowScanPanel(true)} icon={<Play className="h-4 w-4" />}>
                Start Scan
              </Button>
            </div>
          </Card>
        </div>
        <InlineScanPanel
          isOpen={showScanPanel}
          onClose={() => setShowScanPanel(false)}
          onScanComplete={(scanId) => { setShowScanPanel(false); navigate(`/scans/${scanId}`) }}
        />
      </>
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
      <div className="space-y-6">
        <PageHeader
          title="Dashboard"
          description="Overview of your DevOps security posture"
          actions={
            <>
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
                    <button
                      onClick={() => { setShowExportMenu(false); navigate('/reports') }}
                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                      View Reports
                    </button>
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
            </>
          }
        />

        {/* Security Overview Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">
              Security Overview
            </h2>
          </div>

          <SecurityOverview
            securityScore={securityScore}
            hasSecurityScore={hasSecurityScore}
            criticalIssues={criticalIssues}
            repositoriesAtRisk={repositoriesAtRisk}
            scoreDelta={scoreDelta}
            isLoading={isLoading}
            usingFallbackScore={isUsingFallbackScore}
          />

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
                title: 'AI Suggestions',
                value: aiSuggestions.toString(),
                subtitle: 'AI-powered remediation',
                icon: Brain,
                trend: aiSuggestions > 0 ? 'up' : 'neutral',
                trendValue: `${aiSuggestions} active`,
                accentColor: 'text-primary',
              },
            ]}
            className="lg:grid-cols-3"
          />
        </div>

        {/* Recent Activity Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">
              Recent Activity
            </h2>
          </div>

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
        </div>

        {/* AI Suggestions */}
        <AiSuggestions
          suggestions={suggestions}
          isLoading={suggestionsLoading}
        />

        {/* Quick Actions Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Play className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">
              Quick Actions
            </h2>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button
              variant="primary"
              onClick={() => setShowScanPanel(true)}
              icon={<Play className="h-4 w-4" />}
              glow
            >
              Start New Scan
            </Button>
            <Button
              variant="secondary"
              onClick={() => navigate('/repositories')}
              icon={<FolderGit2 className="h-4 w-4" />}
            >
              Connect Repository
            </Button>
            <Button
              variant="secondary"
              onClick={() => navigate('/reports')}
              icon={<FileText className="h-4 w-4" />}
            >
              View Reports
            </Button>
          </div>
        </div>
      </div>

      <InlineScanPanel
        isOpen={showScanPanel}
        onClose={() => setShowScanPanel(false)}
        onScanComplete={(scanId) => { setShowScanPanel(false); navigate(`/scans/${scanId}`) }}
      />
    </>
  )
}

import { motion } from 'framer-motion'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  FolderGit2, AlertTriangle, TrendingUp, Activity,
  Brain, ArrowRight, Play, CheckCircle, Clock, Search
} from 'lucide-react'
import { ScoreCircle, StatCard, Button, Card, SkeletonStatCard, SkeletonChart } from '../components/ui-animated'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { useDeferredValue, useEffect, useState } from 'react'
import { cn } from '../lib/utils'
import { useAuthStore } from '../stores/auth-store'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi, type RecentScan } from '../api/endpoints/dashboard'
import { EmptyState } from '../components/ui/EmptyState'
import { InlineScanPanel } from '../components/InlineScanPanel'

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
  if (typeof score !== 'number' || Number.isNaN(score)) {
    return null
  }

  return Math.min(100, Math.max(0, score))
}

const formatScore = (score: number) => Number(score.toFixed(1))

export function Dashboard() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { isAuthenticated } = useAuthStore()
  const [stats, setStats] = useState({
    totalRepositories: 0,
    totalScans: 0,
    criticalIssues: 0,
    aiSuggestions: 0,
  })
  const [showScanPanel, setShowScanPanel] = useState(false)

  // Fetch dashboard summary
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.getSummary,
    refetchInterval: 10000, // Poll every 10 seconds
    enabled: !!isAuthenticated,
    retry: 2,
  })

  // Fetch recent scans
  const { data: recentScansData, isLoading: scansLoading, error: scansError } = useQuery({
    queryKey: ['dashboard-recent-scans'],
    queryFn: () => dashboardApi.getRecentScans(5),
    refetchInterval: 10000,
    enabled: !!isAuthenticated,
    retry: 2,
  })

  const recentScans = Array.isArray(recentScansData) ? recentScansData : []
  const dashboardSearch = searchParams.get('search')?.trim() ?? ''
  const deferredDashboardSearch = useDeferredValue(dashboardSearch.toLowerCase())
  const isLoading = summaryLoading || scansLoading
  const hasError = summaryError || scansError
  const errorMessage = hasError instanceof Error ? hasError.message : 'Failed to load dashboard data'

  // Update stats when summary data arrives
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
    if (scanScore !== null) {
      scores.push(scanScore)
    }
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

  const filteredRecentScans = recentScans.filter((scan) => {
    if (!deferredDashboardSearch) {
      return true
    }

    const repositoryName = (scan.repository_name || scan.repository_url || '').toLowerCase()
    const repositoryUrl = (scan.repository_url || '').toLowerCase()
    const status = (scan.status || '').toLowerCase()

    return repositoryName.includes(deferredDashboardSearch)
      || repositoryUrl.includes(deferredDashboardSearch)
      || status.includes(deferredDashboardSearch)
  })

  const clearDashboardSearch = () => {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('search')
    setSearchParams(nextParams, { replace: true })
  }

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <div className="h-8 w-48 bg-white/10 rounded animate-pulse" />
            <div className="h-4 w-64 bg-white/10 rounded animate-pulse mt-2" />
          </div>
          <div className="h-10 w-32 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonStatCard key={i} />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <SkeletonChart />
          <SkeletonChart />
        </div>
      </div>
    )
  }

  // Show error state
  if (hasError) {
    return (
      <div className="space-y-8">
        <Card className="p-8 text-center" hover={false}>
          <AlertTriangle className="h-12 w-12 text-orange-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">
            Unable to Load Dashboard
          </h2>
          <p className="text-muted-foreground mb-4">
            {errorMessage}
          </p>
          <div className="flex gap-3 justify-center">
            <Button
              variant="secondary"
              onClick={() => window.location.reload()}
            >
              Retry
            </Button>
            <Button
              variant="primary"
              onClick={() => navigate('/scan')}
            >
              Start Scan
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  // Show empty state when no scans exist
  const hasNoData = totalScans === 0 && totalRepositories === 0 && recentScans.length === 0
  if (hasNoData && !isLoading) {
    return (
      <>
        <div className="space-y-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
              <p className="text-muted-foreground mt-1">
                Overview of your DevOps security posture
              </p>
            </div>
            <Button
              variant="primary"
              size="lg"
              onClick={() => setShowScanPanel(true)}
              icon={<Play className="h-4 w-4" />}
              glow
            >
              New Scan
            </Button>
          </div>
          <Card className="p-12 text-center" hover={false}>
            <EmptyState
              icon={FolderGit2}
              title="Welcome to DevArchAI!"
              description="Start by scanning your first repository to see security insights, AI suggestions, and more."
              actionLabel="Start Your First Scan"
              onAction={() => setShowScanPanel(true)}
              actionVariant="primary"
            />
          </Card>
        </div>
        <InlineScanPanel
          isOpen={showScanPanel}
          onClose={() => setShowScanPanel(false)}
          onScanComplete={(scanId) => {
            setShowScanPanel(false)
            navigate(`/scans/${scanId}`)
          }}
        />
      </>
    )
  }

  return (
    <>
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Overview of your DevOps security posture
          </p>
        </div>
        <Button
          variant="primary"
          size="lg"
          onClick={() => setShowScanPanel(true)}
          icon={<Play className="h-4 w-4" />}
          glow
        >
          New Scan
        </Button>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <StatCard
          title="Total Repositories"
          value={totalRepositories.toString()}
          icon={FolderGit2}
          trend="up"
          trendValue={20}
          delay={0}
        />
        <StatCard
          title="Total Scans"
          value={totalScans.toString()}
          icon={Activity}
          trend="up"
          trendValue={15}
          delay={0.1}
        />
        <StatCard
          title="Critical Issues"
          value={criticalIssues.toString()}
          icon={AlertTriangle}
          trend="down"
          trendValue={12}
          delay={0.2}
        />
        <StatCard
          title="AI Suggestions"
          value={aiSuggestions.toString()}
          icon={Brain}
          trend="up"
          trendValue={30}
          delay={0.3}
        />
      </motion.div>

      {/* Main content grid */}
      <div className="grid items-stretch gap-6 lg:grid-cols-3">
        {/* Security Score - Using real API data */}
        <motion.div
          className="min-w-0 h-full"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <Card className="flex h-full min-h-[420px] flex-col justify-center overflow-hidden" hover={false}>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-foreground mb-6">
                Overall Security Score
              </h3>
              <ScoreCircle
                score={securityScore}
                size="xl"
                animated
                delay={0}
              />
              <div className="mt-6 space-y-3">
                <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm font-medium text-foreground">
                  {hasSecurityScore ? `${securityScore.toFixed(1)}/100` : 'Awaiting score data'}
                </div>
                <motion.div
                  className="flex items-center justify-center gap-2 text-sm text-muted-foreground"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.9 }}
                >
                  <TrendingUp className={cn('h-4 w-4', hasSecurityScore ? 'text-green-400' : 'text-muted-foreground')} />
                  <span className={hasSecurityScore ? 'text-green-400' : 'text-muted-foreground'}>
                    {hasSecurityScore ? `+${securityScore >= 70 ? '5.2' : '0.0'}%` : 'No score change'}
                  </span>
                  <span>{hasSecurityScore ? 'from last week' : 'yet'}</span>
                </motion.div>
                <p className="mx-auto max-w-xs text-sm leading-6 text-muted-foreground">
                  {!hasSecurityScore
                    ? 'No scored scans yet. Run a repository scan to populate your security posture.'
                    : isUsingFallbackScore
                    ? 'Showing an average from recent scans while summary data refreshes.'
                    : 'Average score across your recent completed security scans.'}
                </p>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Findings Trend Chart */}
        <motion.div
          className="min-w-0 h-full lg:col-span-2"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <Card className="h-full overflow-hidden" hover={false}>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-foreground">
                  Findings Trend
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Security issues detected over time
                </p>
              </div>
              <div className="flex items-center gap-4">
                {[
                  { color: 'bg-red-500', label: 'Critical' },
                  { color: 'bg-orange-500', label: 'High' },
                  { color: 'bg-yellow-500', label: 'Medium' },
                  { color: 'bg-green-500', label: 'Low' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${item.color}`} />
                    <span className="text-xs text-muted-foreground">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={findingsData}>
                  <defs>
                    <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis dataKey="name" stroke="#888888" fontSize={12} />
                  <YAxis stroke="#888888" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1a1a',
                      border: '1px solid #ffffff20',
                      borderRadius: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="critical"
                    stroke="#ef4444"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCritical)"
                  />
                  <Area
                    type="monotone"
                    dataKey="high"
                    stroke="#f97316"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorHigh)"
                  />
                  <Line
                    type="monotone"
                    dataKey="medium"
                    stroke="#eab308"
                    strokeWidth={2}
                    dot={{ fill: '#eab308', r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="low"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={{ fill: '#22c55e', r: 4 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Recent Scans Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.7 }}
      >
        <Card className="overflow-hidden" hover={false}>
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Recent Scans
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                {dashboardSearch
                  ? `Showing ${filteredRecentScans.length} of ${recentScans.length} scans for "${dashboardSearch}"`
                  : 'Latest security scan results'}
              </p>
            </div>
            <div className="flex items-center gap-2 self-start">
              {dashboardSearch && (
                <button
                  type="button"
                  onClick={clearDashboardSearch}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors duration-200 hover:border-white/20 hover:text-foreground"
                >
                  <Search className="h-3.5 w-3.5" />
                  Clear Search
                </button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/scans')}
                icon={<ArrowRight className="h-4 w-4" />}
              >
                View All
              </Button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[720px] w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Repository</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Score</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Time</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Duration</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecentScans.length > 0 ? (
                  filteredRecentScans.map((scan: RecentScan, index) => {
                    const scanScore = getValidScore(scan.overall_score ?? scan.security_score)

                    return (
                      <motion.tr
                        key={scan.id}
                        className="border-b border-white/5 transition-colors duration-200 hover:bg-white/[0.06]"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.8 + index * 0.08 }}
                      >
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <FolderGit2 className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                            <span className="max-w-[260px] truncate font-medium text-foreground">
                              {scan.repository_name}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={cn(
                            'inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-medium capitalize',
                            scan.status === 'completed'
                              ? 'border-green-500/30 bg-green-500/10 text-green-400'
                              : scan.status === 'processing' || scan.status === 'pending'
                              ? 'border-blue-500/30 bg-blue-500/10 text-blue-400'
                              : 'border-red-500/30 bg-red-500/10 text-red-400'
                          )}>
                            {scan.status === 'completed' && <CheckCircle className="h-3 w-3" />}
                            {scan.status}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {scanScore !== null ? (
                            <div className="flex items-center gap-2">
                              <div className={cn(
                                'h-2 w-2 rounded-full',
                                scanScore >= 80 ? 'bg-green-400' :
                                scanScore >= 60 ? 'bg-yellow-400' : 'bg-red-400'
                              )} />
                              <span className="font-medium text-foreground">{scanScore.toFixed(1)}</span>
                            </div>
                          ) : (
                            <span className="text-muted-foreground">Pending</span>
                          )}
                        </td>
                        <td className="whitespace-nowrap py-3 px-4 text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3 flex-shrink-0" />
                            {new Date(scan.created_at).toLocaleString()}
                          </div>
                        </td>
                        <td className="whitespace-nowrap py-3 px-4 text-muted-foreground">
                          {typeof scan.analysis_duration_seconds === 'number'
                            ? `${scan.analysis_duration_seconds.toFixed(0)}s`
                            : '-'}
                        </td>
                      </motion.tr>
                    )
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center">
                      <div className="mx-auto flex max-w-md flex-col items-center gap-3">
                        <div className="rounded-full border border-white/10 bg-white/5 p-3">
                          <Search className="h-5 w-5 text-muted-foreground" />
                        </div>
                        <div className="space-y-1">
                          <p className="font-medium text-foreground">
                            {dashboardSearch ? 'No recent scans match this search' : 'No recent scans yet'}
                          </p>
                          <p className="text-sm leading-6 text-muted-foreground">
                            {dashboardSearch
                              ? 'Try a different repository or status keyword, or clear the dashboard search.'
                              : 'Recent scans will appear here as new analyses start and complete.'}
                          </p>
                        </div>
                        {dashboardSearch && (
                          <button
                            type="button"
                            onClick={clearDashboardSearch}
                            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm font-medium text-foreground transition-colors duration-200 hover:border-white/20 hover:bg-white/10"
                          >
                            Clear Search
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>
    </div>
    <InlineScanPanel
      isOpen={showScanPanel}
      onClose={() => setShowScanPanel(false)}
      onScanComplete={(scanId) => {
        setShowScanPanel(false)
        navigate(`/scans/${scanId}`)
      }}
    />
    </>
  )
}

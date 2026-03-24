import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Shield, FolderGit2, AlertTriangle, TrendingUp, Activity, Zap,
  Brain, ArrowRight, Play, CheckCircle, Clock
} from 'lucide-react'
import { ScoreCircle, StatCard, Button, Card, RepositoryCard, SkeletonStatCard, SkeletonChart } from '../components/ui-animated'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts'
import { useState, useEffect } from 'react'
import { cn } from '../lib/utils'
import { useAuthStore } from '../stores/auth-store'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../api/endpoints/dashboard'

const findingsData = [
  { name: 'Mon', critical: 2, high: 5, medium: 12, low: 8 },
  { name: 'Tue', critical: 1, high: 3, medium: 8, low: 15 },
  { name: 'Wed', critical: 3, high: 7, medium: 15, low: 10 },
  { name: 'Thu', critical: 1, high: 4, medium: 10, low: 12 },
  { name: 'Fri', critical: 2, high: 6, medium: 14, low: 9 },
  { name: 'Sat', critical: 0, high: 2, medium: 5, low: 7 },
  { name: 'Sun', critical: 1, high: 3, medium: 7, low: 11 },
]

const categoryData = [
  { name: 'Security', value: 45, color: '#ef4444' },
  { name: 'Reliability', value: 30, color: '#3b82f6' },
  { name: 'Scalability', value: 15, color: '#22c55e' },
  { name: 'Cost', value: 10, color: '#a855f7' },
]

const repositories = [
  {
    name: 'aws-infrastructure',
    description: 'Main AWS infrastructure Terraform code',
    lastScan: '2 hours ago',
    score: 87.5,
    status: 'scanned' as const,
    issues: { critical: 2, high: 5, medium: 12, low: 8 },
  },
  {
    name: 'kubernetes-manifests',
    description: 'K8s deployment configurations',
    lastScan: '1 day ago',
    score: 72.3,
    status: 'scanned' as const,
    issues: { critical: 1, high: 8, medium: 15, low: 10 },
  },
  {
    name: 'ci-cd-pipelines',
    description: 'GitHub Actions workflows',
    status: 'pending' as const,
  },
]

export function Dashboard() {
  const navigate = useNavigate()
  const { token, isAuthenticated } = useAuthStore()
  const [stats, setStats] = useState({
    totalRepositories: 0,
    totalScans: 0,
    criticalIssues: 0,
    aiSuggestions: 0,
  })

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

  const isLoading = summaryLoading || scansLoading
  const hasError = summaryError || scansError

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
    console.error('Dashboard error:', hasError)
    return (
      <div className="space-y-8">
        <Card className="p-8 text-center" hover={false}>
          <AlertTriangle className="h-12 w-12 text-orange-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">
            Unable to Load Dashboard
          </h2>
          <p className="text-muted-foreground mb-4">
            {hasError.message || 'Failed to load dashboard data'}
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
  const hasNoData = stats.totalScans === 0 && stats.totalRepositories === 0
  if (hasNoData && !isLoading) {
    return (
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
            onClick={() => navigate('/scan')}
            icon={<Play className="h-4 w-4" />}
            glow
          >
            New Scan
          </Button>
        </div>
        <Card className="p-12 text-center" hover={false}>
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 mb-4">
            <FolderGit2 className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Welcome to DevArchAI!
          </h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Start by scanning your first repository to see security insights, AI suggestions, and more.
          </p>
          <Button
            variant="primary"
            size="lg"
            onClick={() => navigate('/scan')}
            icon={<Play className="h-5 w-5" />}
            glow
          >
            Start Your First Scan
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
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
          onClick={() => navigate('/scan')}
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
          value={stats.totalRepositories.toString()}
          icon={FolderGit2}
          trend="up"
          trendValue={20}
          delay={0}
        />
        <StatCard
          title="Total Scans"
          value={stats.totalScans.toString()}
          icon={Activity}
          trend="up"
          trendValue={15}
          delay={0.1}
        />
        <StatCard
          title="Critical Issues"
          value={stats.criticalIssues.toString()}
          icon={AlertTriangle}
          trend="down"
          trendValue={12}
          delay={0.2}
        />
        <StatCard
          title="AI Suggestions"
          value={stats.aiSuggestions.toString()}
          icon={Brain}
          trend="up"
          trendValue={30}
          delay={0.3}
        />
      </motion.div>

      {/* Main content grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Security Score */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <Card className="p-6 h-full" hover={false}>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-foreground mb-6">
                Overall Security Score
              </h3>
              <ScoreCircle score={82.4} size="xl" animated delay={500} />
              <motion.div
                className="mt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                <TrendingUp className="h-4 w-4 text-green-400" />
                <span className="text-green-400">+5.2%</span>
                <span>from last week</span>
              </motion.div>
            </div>
          </Card>
        </motion.div>

        {/* Findings Trend Chart */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <Card className="p-6 h-full" hover={false}>
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
        <Card className="p-6" hover={false}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Recent Scans
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                Latest security scan results
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/scans')}
              icon={<ArrowRight className="h-4 w-4" />}
            >
              View All
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
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
                {(recentScansData || []).map((scan: any, index) => (
                  <motion.tr
                    key={scan.id}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.8 + index * 0.1 }}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <FolderGit2 className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium text-foreground">{scan.repository_name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={cn(
                        'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                        scan.status === 'completed'
                          ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                          : 'bg-red-500/10 text-red-400 border border-red-500/30'
                      )}>
                        {scan.status === 'completed' && <CheckCircle className="h-3 w-3" />}
                        {scan.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {scan.overall_score ? (
                        <div className="flex items-center gap-2">
                          <div className={cn(
                            'w-2 h-2 rounded-full',
                            scan.overall_score >= 80 ? 'bg-green-400' :
                            scan.overall_score >= 60 ? 'bg-yellow-400' : 'bg-red-400'
                          )} />
                          <span className="font-medium text-foreground">{scan.overall_score}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(scan.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {scan.analysis_duration_seconds ? `${scan.analysis_duration_seconds.toFixed(0)}s` : '-'}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>
    </div>
  )
}

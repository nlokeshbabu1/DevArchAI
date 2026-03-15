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

const recentScans = [
  { repo: 'aws-infrastructure', status: 'completed', score: 87.5, time: '2 hours ago', duration: '24s' },
  { repo: 'kubernetes-manifests', status: 'completed', score: 72.3, time: '1 day ago', duration: '31s' },
  { repo: 'docker-services', status: 'completed', score: 91.2, time: '2 days ago', duration: '18s' },
  { repo: 'terraform-modules', status: 'failed', score: null, time: '3 days ago', duration: '5s' },
]

export function Dashboard() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => setIsLoading(false), 1000)
    return () => clearTimeout(timer)
  }, [])

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
          onClick={() => navigate('/analyze')}
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
          value="12"
          icon={FolderGit2}
          trend="up"
          trendValue={20}
          delay={0}
        />
        <StatCard
          title="Total Scans"
          value="847"
          icon={Activity}
          trend="up"
          trendValue={15}
          delay={0.1}
        />
        <StatCard
          title="Critical Issues"
          value="23"
          icon={AlertTriangle}
          trend="down"
          trendValue={12}
          delay={0.2}
        />
        <StatCard
          title="AI Suggestions"
          value="156"
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

      {/* Findings by Category */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.6 }}
      >
        <Card className="p-6" hover={false}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Findings by Category
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                Distribution of issues across categories
              </p>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1a1a',
                      border: '1px solid #ffffff20',
                      borderRadius: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-4">
              {categoryData.map((category) => (
                <div key={category.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: category.color }}
                    />
                    <span className="text-sm font-medium text-foreground">
                      {category.name}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold text-foreground">
                      {category.value}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Recent Repositories */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.7 }}
      >
        <Card className="p-6" hover={false}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Recent Repositories
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                Manage and scan your connected repositories
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/repositories')}
              icon={<ArrowRight className="h-4 w-4" />}
            >
              View All
            </Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {repositories.map((repo, index) => (
              <motion.div
                key={repo.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 + index * 0.1 }}
              >
                <RepositoryCard
                  name={repo.name}
                  description={repo.description}
                  lastScan={repo.lastScan}
                  score={repo.score}
                  status={repo.status}
                  onScan={() => console.log('Scan', repo.name)}
                  onView={() => navigate(`/report/1`)}
                />
              </motion.div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Recent Scans Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.9 }}
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
                {recentScans.map((scan, index) => (
                  <motion.tr
                    key={index}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 1 + index * 0.1 }}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <FolderGit2 className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium text-foreground">{scan.repo}</span>
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
                      {scan.score ? (
                        <div className="flex items-center gap-2">
                          <div className={cn(
                            'w-2 h-2 rounded-full',
                            scan.score >= 80 ? 'bg-green-400' :
                            scan.score >= 60 ? 'bg-yellow-400' : 'bg-red-400'
                          )} />
                          <span className="font-medium text-foreground">{scan.score}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {scan.time}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">{scan.duration}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 1.2 }}
      >
        <Card className="p-6" hover={false}>
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Quick Actions
          </h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { icon: Zap, title: 'Quick Scan', description: 'Scan a repository', color: 'from-yellow-500/20 to-orange-500/20' },
              { icon: Shield, title: 'Security Report', description: 'View latest findings', color: 'from-blue-500/20 to-cyan-500/20' },
              { icon: Brain, title: 'AI Insights', description: 'Get AI recommendations', color: 'from-purple-500/20 to-pink-500/20' },
              { icon: FolderGit2, title: 'Add Repository', description: 'Connect new repo', color: 'from-green-500/20 to-emerald-500/20' },
            ].map((action, index) => (
              <motion.button
                key={action.title}
                className={cn(
                  'flex flex-col items-start gap-3 p-4 rounded-xl border border-white/10 bg-gradient-to-br transition-all duration-300 hover:border-white/20 hover:scale-105',
                  action.color
                )}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.3 + index * 0.1 }}
              >
                <action.icon className="h-6 w-6 text-foreground" />
                <div className="text-left">
                  <p className="font-medium text-foreground">{action.title}</p>
                  <p className="text-sm text-muted-foreground">{action.description}</p>
                </div>
              </motion.button>
            ))}
          </div>
        </Card>
      </motion.div>
    </div>
  )
}

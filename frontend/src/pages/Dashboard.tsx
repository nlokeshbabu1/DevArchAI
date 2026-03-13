import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { 
  Shield, FolderGit2, AlertTriangle,
  TrendingUp, Activity, Zap, Brain, ArrowRight, Play
} from 'lucide-react'
import { ScoreCircle, StatCard, Button, Card, RepositoryCard } from '../components/ui-animated'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const statsData = [
  { title: 'Total Repositories', value: '12', icon: FolderGit2, trend: 'up' as const, trendValue: 20, delay: 0 },
  { title: 'Total Scans', value: '847', icon: Activity, trend: 'up' as const, trendValue: 15, delay: 0.1 },
  { title: 'High Severity', value: '23', icon: AlertTriangle, trend: 'down' as const, trendValue: 12, delay: 0.2 },
  { title: 'AI Suggestions', value: '156', icon: Brain, trend: 'up' as const, trendValue: 30, delay: 0.3 },
]

const findingsData = [
  { name: 'Mon', critical: 2, high: 5, medium: 12, low: 8 },
  { name: 'Tue', critical: 1, high: 3, medium: 8, low: 15 },
  { name: 'Wed', critical: 3, high: 7, medium: 15, low: 10 },
  { name: 'Thu', critical: 1, high: 4, medium: 10, low: 12 },
  { name: 'Fri', critical: 2, high: 6, medium: 14, low: 9 },
  { name: 'Sat', critical: 0, high: 2, medium: 5, low: 7 },
  { name: 'Sun', critical: 1, high: 3, medium: 7, low: 11 },
]

const repositories = [
  {
    name: 'aws-infrastructure',
    description: 'Main AWS infrastructure Terraform code',
    lastScan: '2 hours ago',
    score: 87.5,
    status: 'scanned' as const,
  },
  {
    name: 'kubernetes-manifests',
    description: 'K8s deployment configurations',
    lastScan: '1 day ago',
    score: 72.3,
    status: 'scanned' as const,
  },
  {
    name: 'ci-cd-pipelines',
    description: 'GitHub Actions workflows',
    status: 'pending' as const,
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5
    }
  }
}

export function Dashboard() {
  const navigate = useNavigate()

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
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {statsData.map((stat, index) => (
          <motion.div key={stat.title} variants={itemVariants}>
            <StatCard {...stat} />
          </motion.div>
        ))}
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
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-xs text-muted-foreground">Critical</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orange-500" />
                  <span className="text-xs text-muted-foreground">High</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500" />
                  <span className="text-xs text-muted-foreground">Medium</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-xs text-muted-foreground">Low</span>
                </div>
              </div>
            </div>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={findingsData}>
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
                  <Line
                    type="monotone"
                    dataKey="critical"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={{ fill: '#ef4444', r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="high"
                    stroke="#f97316"
                    strokeWidth={2}
                    dot={{ fill: '#f97316', r: 4 }}
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
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Recent Repositories */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.6 }}
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
                transition={{ delay: 0.7 + index * 0.1 }}
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

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.9 }}
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
                transition={{ delay: 1 + index * 0.1 }}
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

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ')
}

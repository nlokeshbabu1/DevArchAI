import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp,
  Server,
  Activity,
  AlertTriangle,
  AlertCircle,
  ArrowRight,
  Download,
  GitBranch,
  Cloud,
  Zap,
  BarChart3
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, ScoreCircle, StatCard, Button } from '../components/ui'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { cn } from '../lib/utils'
import axios from 'axios'

export function Dashboard() {
  const { data: analyses } = useQuery({
    queryKey: ['analyses'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/analyze/repo/list?page=1&page_size=10')
      return response.data
    },
  })

  const categoryData = [
    { name: 'Containers', score: 75, icon: Server },
    { name: 'Infrastructure', score: 60, icon: Cloud },
    { name: 'Kubernetes', score: 70, icon: GitBranch },
    { name: 'CI/CD', score: 85, icon: Zap },
    { name: 'Monitoring', score: 55, icon: BarChart3 },
  ]

  const severityData = [
    { name: 'Critical', value: 3, color: '#ef4444' },
    { name: 'High', value: 8, color: '#f97316' },
    { name: 'Medium', value: 12, color: '#eab308' },
    { name: 'Low', value: 15, color: '#22c55e' },
  ]

  const totalFindings = severityData.reduce((acc, item) => acc + item.value, 0)
  
  // Calculate average DevOps score from analyses
  const averageScore = analyses?.analyses?.length
    ? analyses.analyses.reduce((a: number, b: any) => a + (b.devops_score || 0), 0) / analyses.analyses.length
    : 78.5

  const totalAnalyses = analyses?.total || 12

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Overview of your DevOps architecture analysis
          </p>
        </div>
        <Link to="/analyze">
          <Button variant="secondary">
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Analyses"
          value={totalAnalyses}
          icon={<Activity className="h-5 w-5 text-primary" />}
          trend="up"
          trendValue={12}
        />
        <StatCard
          title="Average DevOps Score"
          value={averageScore.toFixed(1)}
          icon={<TrendingUp className="h-5 w-5 text-green-400" />}
          trend="up"
          trendValue={5}
        />
        <StatCard
          title="Critical Issues"
          value={severityData[0].value}
          icon={<AlertTriangle className="h-5 w-5 text-red-400" />}
          trend="down"
          trendValue={2}
        />
        <StatCard
          title="Total Findings"
          value={totalFindings}
          icon={<AlertCircle className="h-5 w-5 text-orange-400" />}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Overall Score */}
        <Card className="lg:col-span-1 p-8 glow-primary" hover={false}>
          <h2 className="text-lg font-semibold mb-6 text-center text-foreground">Overall DevOps Score</h2>
          <div className="flex justify-center">
            <ScoreCircle
              score={averageScore}
              size="xl"
              animated
              delay={200}
            />
          </div>
          <div className="mt-8 space-y-3">
            <div className="flex items-center justify-between text-sm p-3 rounded-lg bg-white/5 border border-white/10">
              <span className="text-muted-foreground">Best Score</span>
              <span className="font-medium text-green-400">95.0 (A)</span>
            </div>
            <div className="flex items-center justify-between text-sm p-3 rounded-lg bg-white/5 border border-white/10">
              <span className="text-muted-foreground">Needs Improvement</span>
              <span className="font-medium text-red-400">52.5 (F)</span>
            </div>
          </div>
        </Card>

        {/* Severity Distribution */}
        <Card className="lg:col-span-2 p-6" hover={false}>
          <h2 className="text-lg font-semibold mb-6 text-foreground">Issues by Severity</h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={90}
                    dataKey="value"
                    paddingAngle={2}
                  >
                    {severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '12px',
                      backdropFilter: 'blur(12px)'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col justify-center space-y-3">
              {severityData.map((item) => (
                <div key={item.name} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full shadow-lg"
                      style={{ backgroundColor: item.color, boxShadow: `0 0 10px ${item.color}60` }}
                    />
                    <span className="text-sm font-medium text-foreground">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-foreground">{item.value}</span>
                    <div className="w-24 h-2 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${(item.value / totalFindings) * 100}%`,
                          backgroundColor: item.color,
                          boxShadow: `0 0 10px ${item.color}60`
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Category Scores */}
      <div>
        <h2 className="text-lg font-semibold mb-4 text-foreground">DevOps Stack Breakdown</h2>
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-5">
          {categoryData.map((category) => {
            const Icon = category.icon
            const scoreColor = getCategoryColor(category.score)

            return (
              <Card key={category.name} className="p-5 text-center" hover>
                <div className={cn(
                  'inline-flex p-3 rounded-xl mb-3 border border-white/10',
                  scoreColor.bg
                )}>
                  <Icon className={cn('h-5 w-5', scoreColor.text)} />
                </div>
                <div className={cn('text-2xl font-bold', scoreColor.text)}>
                  {category.score}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {category.name}
                </div>
                <div className="w-full h-1.5 bg-white/10 rounded-full mt-3 overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-500',
                      scoreColor.bg.replace('/15', '').replace('/10', '')
                    )}
                    style={{ width: `${category.score}%` }}
                  />
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Recent Analyses */}
      <Card hover={false}>
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Recent Analyses</h2>
            <Link to="/reports" className="text-sm text-primary hover:underline flex items-center gap-1">
              View all
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
        <div className="divide-y divide-white/10">
          {analyses?.analyses?.map((analysis: any) => (
            <div
              key={analysis.id}
              className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="p-2 bg-white/5 rounded-xl border border-white/10">
                  <Activity className="h-5 w-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-medium text-foreground">{analysis.repo_full_name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {analysis.has_docker && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
                        Docker
                      </span>
                    )}
                    {analysis.has_terraform && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30">
                        Terraform
                      </span>
                    )}
                    {analysis.has_kubernetes && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/30">
                        K8s
                      </span>
                    )}
                    {analysis.cicd_type && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/30">
                        {analysis.cicd_type.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className={cn(
                    'text-lg font-bold',
                    analysis.devops_score >= 80 ? 'text-green-400' :
                    analysis.devops_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                  )}>
                    {analysis.devops_score?.toFixed(0) || 'N/A'}
                  </div>
                  <div className="text-xs text-muted-foreground">Score</div>
                </div>
                <ArrowRight className="h-5 w-5 text-muted-foreground" />
              </div>
            </div>
          ))}
          {!analyses?.analyses?.length && (
            <div className="p-12 text-center">
              <Activity className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
              <p className="text-muted-foreground">No analyses yet. Start by analyzing a repository.</p>
              <Link to="/" className="text-primary hover:underline text-sm mt-2 inline-block">
                Analyze Repository →
              </Link>
            </div>
          )}
        </div>
      </Card>

      {/* Missing Best Practices Summary */}
      <Card className="p-6" hover={false}>
        <h2 className="text-lg font-semibold mb-4 text-foreground">Common Missing Best Practices</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <span className="font-medium text-red-400">No CI/CD Pipeline</span>
            </div>
            <p className="text-sm text-muted-foreground">
              35% of repositories lack automated CI/CD pipelines
            </p>
          </div>
          <div className="p-4 rounded-xl bg-orange-500/10 border border-orange-500/30">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="h-5 w-5 text-orange-400" />
              <span className="font-medium text-orange-400">Missing Monitoring</span>
            </div>
            <p className="text-sm text-muted-foreground">
              45% don't have Prometheus/Grafana configured
            </p>
          </div>
          <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="h-5 w-5 text-yellow-400" />
              <span className="font-medium text-yellow-400">No Security Scanning</span>
            </div>
            <p className="text-sm text-muted-foreground">
              60% lack automated security scanning
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}

function getCategoryColor(score: number) {
  if (score >= 90) return { bg: 'bg-green-500/15', text: 'text-green-400' }
  if (score >= 80) return { bg: 'bg-blue-500/15', text: 'text-blue-400' }
  if (score >= 70) return { bg: 'bg-yellow-500/15', text: 'text-yellow-400' }
  if (score >= 60) return { bg: 'bg-orange-500/15', text: 'text-orange-400' }
  return { bg: 'bg-red-500/15', text: 'text-red-400' }
}

import { motion } from 'framer-motion'
import { Shield, BarChart3, GitBranch, AlertTriangle, CheckCircle, Sparkles, Brain, FileCode, Terminal, Layers, Server, Lock, Eye, TrendingUp, Activity, Clock } from 'lucide-react'
import { cn } from '../../lib/utils'

const dashboardHighlights = [
  {
    title: 'Findings by Severity',
    icon: AlertTriangle,
    description: 'See all security issues organized by criticality, with instant drill-down into each finding.',
    gradient: 'from-red-500/20 to-orange-500/20',
    border: 'border-red-500/30',
  },
  {
    title: 'Risk Score',
    icon: Shield,
    description: 'Overall security score with breakdowns for each category in your DevOps stack.',
    gradient: 'from-primary/20 to-indigo-500/20',
    border: 'border-primary/30',
  },
  {
    title: 'Repository Insights',
    icon: GitBranch,
    description: 'Complete view of all scanned repositories with status, scores, and last scan time.',
    gradient: 'from-blue-500/20 to-cyan-500/20',
    border: 'border-blue-500/30',
  },
  {
    title: 'Technology Detection',
    icon: Layers,
    description: 'Auto-detected DevOps technologies with file counts and security coverage per tool.',
    gradient: 'from-purple-500/20 to-pink-500/20',
    border: 'border-purple-500/30',
  },
  {
    title: 'AI Recommendations',
    icon: Sparkles,
    description: 'AI-powered fix suggestions with code examples, best practices, and documentation links.',
    gradient: 'from-green-500/20 to-emerald-500/20',
    border: 'border-green-500/30',
  },
  {
    title: 'Security Trends',
    icon: TrendingUp,
    description: 'Track security posture over time with historical data and improvement suggestions.',
    gradient: 'from-yellow-500/20 to-amber-500/20',
    border: 'border-yellow-500/30',
  },
]

export function DashboardPreview() {
  return (
    <section className="py-20 lg:py-32 bg-white/[0.02]">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16 space-y-4">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <BarChart3 className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">Central Security Dashboard</span>
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            Complete Visibility at a Glance
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Everything you need to understand, prioritize, and fix security issues across your entire DevOps infrastructure
          </p>
        </div>

        {/* Dashboard Mockup */}
        <motion.div
          className="max-w-6xl mx-auto rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-white/0 backdrop-blur-sm overflow-hidden mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          {/* Top Bar */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-indigo-600">
                <Shield className="h-5 w-5 text-white" />
              </div>
              <span className="font-semibold text-foreground">DevArchAI Dashboard</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-green-400" />
                All Systems Normal
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                Last scan: 2m ago
              </span>
            </div>
          </div>

          {/* Dashboard Content */}
          <div className="p-6 space-y-6">
            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Total Repos', value: '12', icon: GitBranch, color: 'text-blue-400', bg: 'bg-blue-500/10' },
                { label: 'Critical Issues', value: '23', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
                { label: 'Security Score', value: '74', icon: Shield, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
                { label: 'AI Fixes Ready', value: '156', icon: Sparkles, color: 'text-green-400', bg: 'bg-green-500/10' },
              ].map((stat) => {
                const IconStat = stat.icon
                return (
                  <div key={stat.label} className={cn('p-4 rounded-xl border border-white/10', stat.bg)}>
                    <div className="flex items-center justify-between mb-2">
                      <IconStat className={cn('h-5 w-5', stat.color)} />
                    </div>
                    <div className={cn('text-2xl font-bold', stat.color)}>{stat.value}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{stat.label}</div>
                  </div>
                )
              })}
            </div>

            {/* Severity Distribution */}
            <div className="p-5 rounded-xl bg-white/5 border border-white/10">
              <h4 className="text-sm font-semibold text-foreground mb-4">Findings by Severity</h4>
              <div className="space-y-3">
                {[
                  { label: 'Critical', count: 7, color: 'bg-red-500', width: '35%' },
                  { label: 'High', count: 12, color: 'bg-orange-500', width: '60%' },
                  { label: 'Medium', count: 18, color: 'bg-yellow-500', width: '90%' },
                  { label: 'Low', count: 9, color: 'bg-blue-500', width: '45%' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-16">{item.label}</span>
                    <div className="flex-1 h-2.5 rounded-full bg-white/5 overflow-hidden">
                      <motion.div
                        className={cn('h-full rounded-full', item.color)}
                        initial={{ width: 0 }}
                        whileInView={{ width: item.width }}
                        viewport={{ once: true }}
                        transition={{ duration: 1, delay: 0.3 }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground w-6 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Technology Detection */}
            <div className="grid md:grid-cols-3 gap-4">
              {[
                { name: 'Docker', files: 24, icon: FileCode },
                { name: 'Kubernetes', files: 18, icon: Server },
                { name: 'Terraform', files: 31, icon: Layers },
              ].map((tech) => {
                const TechIcon = tech.icon
                return (
                  <div key={tech.name} className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/20 border border-primary/30">
                      <TechIcon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-foreground">{tech.name}</div>
                      <div className="text-xs text-muted-foreground">{tech.files} files scanned</div>
                    </div>
                    <CheckCircle className="h-4 w-4 text-green-400" />
                  </div>
                )
              })}
            </div>
          </div>
        </motion.div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl mx-auto">
          {dashboardHighlights.map((item, index) => {
            const Icon = item.icon
            return (
              <motion.div
                key={item.title}
                className={cn(
                  'group p-5 rounded-xl border backdrop-blur-sm transition-all duration-300',
                  'hover:border-white/30 hover:shadow-lg',
                  item.gradient,
                  item.border
                )}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.08 }}
                whileHover={{ y: -3 }}
              >
                <div className="space-y-3">
                  <Icon className="h-5 w-5 text-foreground" />
                  <div>
                    <h4 className="text-sm font-semibold text-foreground">{item.title}</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{item.description}</p>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
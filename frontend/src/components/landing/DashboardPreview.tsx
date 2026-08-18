import { memo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Shield, BarChart3, GitBranch, AlertTriangle, CheckCircle, Sparkles, Layers, Server, TrendingUp, Activity, Clock } from 'lucide-react'
import { cn } from '../../lib/utils'

const dashboardHighlights = [
  {
    title: 'Findings by Severity',
    icon: AlertTriangle,
    description: 'See all security issues organized by criticality, with instant drill-down into each finding.',
    color: 'text-red-400',
    bg: 'bg-red-500/10 border-red-500/15',
  },
  {
    title: 'Risk Score',
    icon: Shield,
    description: 'Overall security score with breakdowns for each category in your DevOps stack.',
    color: 'text-primary',
    bg: 'bg-primary/10 border-primary/15',
  },
  {
    title: 'Repository Insights',
    icon: GitBranch,
    description: 'Complete view of all scanned repositories with status, scores, and last scan time.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10 border-blue-500/15',
  },
  {
    title: 'Technology Detection',
    icon: Layers,
    description: 'Auto-detected DevOps technologies with file counts and security coverage per tool.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10 border-purple-500/15',
  },
  {
    title: 'AI Recommendations',
    icon: Sparkles,
    description: 'AI-powered fix suggestions with code examples, best practices, and documentation links.',
    color: 'text-green-400',
    bg: 'bg-green-500/10 border-green-500/15',
  },
  {
    title: 'Security Trends',
    icon: TrendingUp,
    description: 'Track security posture over time with historical data and improvement suggestions.',
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/10 border-yellow-500/15',
  },
]

const HighlightCard = memo(function HighlightCard({
  item,
  index,
}: {
  item: typeof dashboardHighlights[0]
  index: number
}) {
  const Icon = item.icon

  return (
    <motion.div
      className={cn(
        'group p-4 rounded-xl border bg-card/30 backdrop-blur-sm',
        'hover:border-white/[0.12] transition-all duration-300',
        item.bg
      )}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: index * 0.06, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="space-y-2.5">
        <Icon className={cn('h-4 w-4', item.color)} />
        <div>
          <h4 className="text-sm font-semibold text-foreground">{item.title}</h4>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{item.description}</p>
        </div>
      </div>
    </motion.div>
  )
})

export function DashboardPreview() {
  return (
    <section className="py-20 lg:py-32 bg-white/[0.02]">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14 space-y-3">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.06] border border-primary/20"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <BarChart3 className="h-4 w-4 text-primary/80" />
            <span className="text-sm font-medium text-primary/90">Central Security Dashboard</span>
          </motion.div>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Complete Visibility at a Glance
          </h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Everything you need to understand, prioritize, and fix security issues across your entire DevOps infrastructure
          </p>
        </div>

        {/* Dashboard Mockup */}
        <motion.div
          className="max-w-5xl mx-auto rounded-2xl border border-white/[0.08] bg-card/40 backdrop-blur-xl overflow-hidden mb-12 shadow-2xl shadow-black/20"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
        >
          {/* Top Bar */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/[0.06] bg-white/[0.02]">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-indigo-600">
                <Shield className="h-4 w-4 text-white" />
              </div>
              <span className="font-semibold text-foreground text-sm">DevArchAI Dashboard</span>
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
          <div className="p-5 space-y-5">
            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Total Repos', value: '12', icon: GitBranch, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/15' },
                { label: 'Critical Issues', value: '23', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/15' },
                { label: 'Security Score', value: '74', icon: Shield, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/15' },
                { label: 'AI Fixes Ready', value: '156', icon: Sparkles, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/15' },
              ].map((stat) => {
                const IconStat = stat.icon
                return (
                  <div key={stat.label} className={cn('p-3.5 rounded-xl border', stat.bg)}>
                    <IconStat className={cn('h-4 w-4 mb-2', stat.color)} />
                    <div className={cn('text-xl font-bold', stat.color)}>{stat.value}</div>
                    <div className="text-[11px] text-muted-foreground mt-0.5">{stat.label}</div>
                  </div>
                )
              })}
            </div>

            {/* Severity Distribution */}
            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-sm font-semibold text-foreground mb-3">Findings by Severity</h4>
              <div className="space-y-2.5">
                {[
                  { label: 'Critical', count: 7, color: 'bg-red-500', width: '35%' },
                  { label: 'High', count: 12, color: 'bg-orange-500', width: '60%' },
                  { label: 'Medium', count: 18, color: 'bg-yellow-500', width: '90%' },
                  { label: 'Low', count: 9, color: 'bg-blue-500', width: '45%' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-2.5">
                    <span className="text-[11px] text-muted-foreground w-14">{item.label}</span>
                    <div className="flex-1 h-2 rounded-full bg-white/[0.04] overflow-hidden">
                      <motion.div
                        className={cn('h-full rounded-full', item.color)}
                        initial={{ width: 0 }}
                        whileInView={{ width: item.width }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, delay: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
                      />
                    </div>
                    <span className="text-[11px] text-muted-foreground w-5 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Technology Detection */}
            <div className="grid md:grid-cols-3 gap-3">
              {[
                { name: 'Docker', files: 24, icon: AlertTriangle },
                { name: 'Kubernetes', files: 18, icon: Server },
                { name: 'Terraform', files: 31, icon: Layers },
              ].map((tech) => {
                const TechIcon = tech.icon
                return (
                  <div key={tech.name} className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 border border-primary/15">
                      <TechIcon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-foreground">{tech.name}</div>
                      <div className="text-[11px] text-muted-foreground">{tech.files} files scanned</div>
                    </div>
                    <CheckCircle className="h-4 w-4 text-green-400/80" />
                  </div>
                )
              })}
            </div>
          </div>
        </motion.div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3 max-w-5xl mx-auto">
          {dashboardHighlights.map((item, index) => (
            <HighlightCard key={item.title} item={item} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}

import { motion } from 'framer-motion'
import { Cloud, DollarSign, Shield, Slack, GitPullRequest, CalendarCheck, TrendingUp, GitBranch, Sparkles, Clock, BarChart3, Users, Puzzle, FileCheck, Eye, Monitor } from 'lucide-react'
import { cn } from '../../lib/utils'

const roadmapItems = [
  {
    title: 'AWS Security Analysis',
    icon: Cloud,
    description: 'Deep security scanning for AWS infrastructure including S3, EC2, Lambda, and IAM configurations.',
    gradient: 'from-orange-500/20 to-amber-500/20',
    border: 'border-orange-500/30',
  },
  {
    title: 'AWS Cost Optimization',
    icon: DollarSign,
    description: 'Identify cost-saving opportunities across your AWS resources with actionable recommendations.',
    gradient: 'from-green-500/20 to-emerald-500/20',
    border: 'border-green-500/30',
  },
  {
    title: 'Compliance Dashboard',
    icon: FileCheck,
    description: 'Centralized compliance tracking for SOC 2, HIPAA, PCI-DSS, and ISO 27001 standards.',
    gradient: 'from-blue-500/20 to-cyan-500/20',
    border: 'border-blue-500/30',
  },
  {
    title: 'Slack Integration',
    icon: Slack,
    description: 'Real-time security alerts and scan results delivered directly to your Slack channels.',
    gradient: 'from-purple-500/20 to-pink-500/20',
    border: 'border-purple-500/30',
  },
  {
    title: 'Jira Integration',
    icon: Puzzle,
    description: 'Automatically create Jira tickets for new findings and track remediation progress.',
    gradient: 'from-blue-500/20 to-indigo-500/20',
    border: 'border-blue-500/30',
  },
  {
    title: 'Scheduled Scans',
    icon: CalendarCheck,
    description: 'Automate recurring security scans on your schedule — daily, weekly, or custom intervals.',
    gradient: 'from-cyan-500/20 to-teal-500/20',
    border: 'border-cyan-500/30',
  },
  {
    title: 'Security Trends',
    icon: TrendingUp,
    description: 'Track security posture over time with historical data and trend analysis across all repos.',
    gradient: 'from-yellow-500/20 to-amber-500/20',
    border: 'border-yellow-500/30',
  },
  {
    title: 'Multi Repository Scanning',
    icon: GitBranch,
    description: 'Scan and manage security across all your repositories from a single dashboard.',
    gradient: 'from-pink-500/20 to-rose-500/20',
    border: 'border-pink-500/30',
  },
]

export function RoadmapSection() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16 space-y-4">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-yellow-500/10 border border-yellow-500/30"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <Sparkles className="h-4 w-4 text-yellow-400" />
            <span className="text-sm font-medium text-yellow-400">Coming Soon</span>
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            What's Next
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            We're building the future of DevOps security. Here's what's on our roadmap.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-6xl mx-auto">
          {roadmapItems.map((item, index) => {
            const Icon = item.icon
            return (
              <motion.div
                key={item.title}
                className={cn(
                  'group relative p-5 rounded-xl border backdrop-blur-sm',
                  'hover:border-white/30 transition-all duration-300',
                  item.gradient,
                  item.border
                )}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.08 }}
                whileHover={{ y: -3 }}
              >
                {/* Coming Soon Badge */}
                <div className="absolute top-3 right-3">
                  <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/30">
                    <Clock className="h-2.5 w-2.5 text-yellow-400" />
                    <span className="text-[10px] font-medium text-yellow-400">Soon</span>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className={cn(
                    'p-2.5 rounded-lg w-fit bg-gradient-to-br border border-white/10',
                    item.gradient
                  )}>
                    <Icon className="h-5 w-5 text-foreground" />
                  </div>
                  <div className="pr-16">
                    <h3 className="text-sm font-semibold text-foreground">{item.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{item.description}</p>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        <motion.div
          className="mt-12 text-center"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <p className="text-sm text-muted-foreground">
            Have a feature request?{' '}
            <a href="#" className="text-primary hover:underline">Let us know</a>
          </p>
        </motion.div>
      </div>
    </section>
  )
}
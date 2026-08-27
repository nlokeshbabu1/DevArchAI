import { memo } from 'react'
import { motion } from 'framer-motion'
import { Cloud, DollarSign, Shield, Slack, CalendarCheck, TrendingUp, GitBranch, Sparkles, Clock, Puzzle, FileCheck } from 'lucide-react'
import { cn } from '../../lib/utils'

const roadmapItems = [
  {
    title: 'AWS Security Analysis',
    icon: Cloud,
    description: 'Deep security scanning for AWS infrastructure including S3, EC2, Lambda, and IAM configurations.',
    color: 'text-orange-400',
    border: 'border-orange-500/15 hover:border-orange-500/30',
    iconBg: 'bg-orange-500/10',
  },
  {
    title: 'AWS Cost Optimization',
    icon: DollarSign,
    description: 'Identify cost-saving opportunities across your AWS resources with actionable recommendations.',
    color: 'text-green-400',
    border: 'border-green-500/15 hover:border-green-500/30',
    iconBg: 'bg-green-500/10',
  },
  {
    title: 'Compliance Dashboard',
    icon: FileCheck,
    description: 'Centralized compliance tracking for SOC 2, HIPAA, PCI-DSS, and ISO 27001 standards.',
    color: 'text-blue-400',
    border: 'border-blue-500/15 hover:border-blue-500/30',
    iconBg: 'bg-blue-500/10',
  },
  {
    title: 'Slack Integration',
    icon: Slack,
    description: 'Real-time security alerts and scan results delivered directly to your Slack channels.',
    color: 'text-purple-400',
    border: 'border-purple-500/15 hover:border-purple-500/30',
    iconBg: 'bg-purple-500/10',
  },
  {
    title: 'Jira Integration',
    icon: Puzzle,
    description: 'Automatically create Jira tickets for new findings and track remediation progress.',
    color: 'text-blue-400',
    border: 'border-blue-500/15 hover:border-blue-500/30',
    iconBg: 'bg-blue-500/10',
  },
  {
    title: 'Scheduled Scans',
    icon: CalendarCheck,
    description: 'Automate recurring security scans on your schedule — daily, weekly, or custom intervals.',
    color: 'text-cyan-400',
    border: 'border-cyan-500/15 hover:border-cyan-500/30',
    iconBg: 'bg-cyan-500/10',
  },
  {
    title: 'Security Trends',
    icon: TrendingUp,
    description: 'Track security posture over time with historical data and trend analysis across all repos.',
    color: 'text-yellow-400',
    border: 'border-yellow-500/15 hover:border-yellow-500/30',
    iconBg: 'bg-yellow-500/10',
  },
  {
    title: 'Multi Repository Scanning',
    icon: GitBranch,
    description: 'Scan and manage security across all your repositories from a single dashboard.',
    color: 'text-pink-400',
    border: 'border-pink-500/15 hover:border-pink-500/30',
    iconBg: 'bg-pink-500/10',
  },
]

const RoadmapCard = memo(function RoadmapCard({
  item,
  index,
}: {
  item: typeof roadmapItems[0]
  index: number
}) {
  const Icon = item.icon

  return (
    <motion.div
      className={cn(
        'group relative p-4 rounded-xl border bg-card/30 backdrop-blur-sm',
        'transition-all duration-300',
        item.border
      )}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: index * 0.06, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="absolute top-3 right-3">
        <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/15">
          <Clock className="h-2.5 w-2.5 text-yellow-400/80" />
          <span className="text-[9px] font-medium text-yellow-400/90">Soon</span>
        </div>
      </div>

      <div className="space-y-2.5">
        <div className={cn('p-2 rounded-lg w-fit border border-white/[0.06]', item.iconBg)}>
          <Icon className={cn('h-4 w-4', item.color)} />
        </div>
        <div className="pr-14">
          <h3 className="text-sm font-semibold text-foreground">{item.title}</h3>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{item.description}</p>
        </div>
      </div>
    </motion.div>
  )
})

export function RoadmapSection() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14 space-y-3">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-yellow-500/[0.08] border border-yellow-500/20"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <Sparkles className="h-4 w-4 text-yellow-400/80" />
            <span className="text-sm font-medium text-yellow-400/90">Coming Soon</span>
          </motion.div>
          <h2 className="display-lg text-foreground">
            What&apos;s Next
          </h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            We&apos;re building the future of DevOps security. Here&apos;s what&apos;s on our roadmap.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 max-w-6xl mx-auto">
          {roadmapItems.map((item, index) => (
            <RoadmapCard key={item.title} item={item} index={index} />
          ))}
        </div>

        <motion.div
          className="mt-10 text-center"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <p className="text-sm text-muted-foreground">
            Have a feature request?{' '}
            <a href="mailto:support@devarchai.com?subject=DevArchAI%20Feature%20Request" className="text-primary hover:underline underline-offset-2">Let us know</a>
          </p>
        </motion.div>
      </div>
    </section>
  )
}

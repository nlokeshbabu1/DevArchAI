import { memo } from 'react'
import { motion } from 'framer-motion'
import {
  GitBranch, Cpu, Server, Shield, Brain, AlertTriangle,
  BarChart3, FileText, LayoutDashboard
} from 'lucide-react'

const steps = [
  { icon: GitBranch, label: 'Repository', description: 'Connect your GitHub, GitLab, or Bitbucket repo' },
  { icon: Cpu, label: 'Detection Engine', description: 'Identify IaC files, Dockerfiles, and manifests' },
  { icon: Server, label: 'Infrastructure Analysis', description: 'Parse and analyze infrastructure configurations' },
  { icon: Shield, label: 'Policy Engine', description: 'Evaluate against 500+ security rules' },
  { icon: Brain, label: 'AI Analysis', description: 'Context-aware findings with fix recommendations' },
  { icon: AlertTriangle, label: 'Risk Prioritization', description: 'Score and rank by severity and impact' },
  { icon: GitBranch, label: 'Pull Request', description: 'Automated PR with inline fix suggestions' },
  { icon: FileText, label: 'PDF Report', description: 'Download comprehensive compliance report' },
  { icon: LayoutDashboard, label: 'Dashboard', description: 'Track posture across all repositories' },
]

const StepItem = memo(function StepItem({
  step,
  index,
  total,
}: {
  step: typeof steps[0]
  index: number
  total: number
}) {
  const Icon = step.icon

  return (
    <motion.div
      className="flex items-start gap-4 relative"
      initial={{ opacity: 0, x: -16 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: index * 0.06, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {/* Connector line */}
      {index < total - 1 && (
        <div className="absolute left-[18px] top-10 w-px h-[calc(100%+8px)] bg-gradient-to-b from-white/10 to-transparent" />
      )}

      {/* Icon */}
      <div className="relative z-10 flex-shrink-0">
        <div className="w-9 h-9 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
          <Icon className="h-4 w-4 text-primary" />
        </div>
      </div>

      {/* Content */}
      <div className="pt-1 pb-6">
        <h4 className="text-sm font-semibold text-foreground mb-0.5">{step.label}</h4>
        <p className="text-sm text-muted-foreground">{step.description}</p>
      </div>
    </motion.div>
  )
})

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 lg:py-32">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-start">
          {/* Left: Header */}
          <div className="lg:sticky lg:top-24">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
            >
              <p className="text-sm font-medium text-primary mb-3">How It Works</p>
              <h2 className="display-lg text-foreground mb-4">
                From repository to production readiness
              </h2>
              <p className="text-base text-muted-foreground max-w-lg leading-relaxed">
                A single scan triggers a comprehensive analysis pipeline. Every step is automated.
                You get actionable results in under 30 seconds.
              </p>
            </motion.div>
          </div>

          {/* Right: Timeline */}
          <div className="relative">
            {steps.map((step, index) => (
              <StepItem key={step.label} step={step} index={index} total={steps.length} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

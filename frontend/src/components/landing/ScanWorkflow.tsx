import { memo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Github, Search, Shield, BarChart3, Sparkles, FileDown, Zap, ArrowRight } from 'lucide-react'
import { cn } from '../../lib/utils'

const steps = [
  {
    icon: Github,
    title: 'Connect Repository',
    description: 'Provide your GitHub, GitLab, or Bitbucket repository URL. No complex setup required.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10 border-blue-500/20',
  },
  {
    icon: Search,
    title: 'Detect Technologies',
    description: 'Our engine automatically identifies Docker, Kubernetes, Terraform, CI/CD, and cloud configs.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10 border-purple-500/20',
  },
  {
    icon: Shield,
    title: 'Run Security Scans',
    description: '500+ security rules scan for vulnerabilities, secrets, misconfigurations, and compliance gaps.',
    color: 'text-orange-400',
    bg: 'bg-orange-500/10 border-orange-500/20',
  },
  {
    icon: BarChart3,
    title: 'Analyze Findings',
    description: 'Prioritized results with severity levels, risk scores, and detailed technical explanations.',
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/10 border-yellow-500/20',
  },
  {
    icon: Sparkles,
    title: 'Generate AI Fixes',
    description: 'AI-powered remediation with production-ready code, best practices, and documentation links.',
    color: 'text-green-400',
    bg: 'bg-green-500/10 border-green-500/20',
  },
  {
    icon: FileDown,
    title: 'Export Reports',
    description: 'Download PDF, Excel, or JSON reports for compliance, audits, and team collaboration.',
    color: 'text-primary',
    bg: 'bg-primary/10 border-primary/20',
  },
]

const StepItem = memo(function StepItem({
  step,
  index,
  isLast,
}: {
  step: typeof steps[0]
  index: number
  isLast: boolean
}) {
  const Icon = step.icon

  return (
    <motion.div
      className="relative flex gap-5 pb-6"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {/* Connector line */}
      {!isLast && (
        <div className="absolute left-7 top-14 bottom-0 w-px bg-gradient-to-b from-white/10 to-transparent" />
      )}

      {/* Step Icon */}
      <div className="relative flex-shrink-0">
        <div className={cn('w-14 h-14 rounded-2xl flex items-center justify-center border', step.bg)}>
          <Icon className={cn('h-6 w-6', step.color)} />
        </div>
        <div className="absolute -top-1.5 -right-1.5 w-6 h-6 rounded-full bg-background border-2 border-primary/40 flex items-center justify-center">
          <span className="text-[9px] font-bold text-primary">{String(index + 1).padStart(2, '0')}</span>
        </div>
      </div>

      {/* Step Content */}
      <div className="flex-1 pt-2">
        <div className="p-4 rounded-xl border border-white/[0.06] bg-card/20 hover:border-white/[0.12] transition-colors duration-200">
          <h3 className="text-base font-semibold text-foreground mb-1">{step.title}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>

          {index === 2 && (
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {['Secret Detection', 'Vulnerabilities', 'Misconfigurations', 'Compliance'].map((tag) => (
                <span key={tag} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-white/[0.04] text-muted-foreground border border-white/[0.06]">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
})

export function ScanWorkflow() {
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
            <Zap className="h-4 w-4 text-primary/80" />
            <span className="text-sm font-medium text-primary/90">From Repo to Report in Minutes</span>
          </motion.div>
          <h2 className="display-lg text-foreground">
            How It Works
          </h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Get comprehensive security analysis in 6 simple steps — no configuration required
          </p>
        </div>

        <div className="max-w-3xl mx-auto">
          {steps.map((step, index) => (
            <StepItem
              key={step.title}
              step={step}
              index={index}
              isLast={index === steps.length - 1}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

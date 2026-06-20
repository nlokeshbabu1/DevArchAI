import { motion } from 'framer-motion'
import { Github, Search, Shield, BarChart3, Sparkles, FileDown, CheckCircle, ArrowRight, GitBranch, Brain, FileText, Zap } from 'lucide-react'
import { cn } from '../../lib/utils'

const steps = [
  {
    icon: Github,
    title: 'Connect Repository',
    description: 'Provide your GitHub, GitLab, or Bitbucket repository URL. No complex setup required.',
    gradient: 'from-blue-500/20 to-cyan-500/20',
    border: 'border-blue-500/30',
    iconColor: 'text-blue-400',
  },
  {
    icon: Search,
    title: 'Detect Technologies',
    description: 'Our engine automatically identifies Docker, Kubernetes, Terraform, CI/CD, and cloud configs.',
    gradient: 'from-purple-500/20 to-pink-500/20',
    border: 'border-purple-500/30',
    iconColor: 'text-purple-400',
  },
  {
    icon: Shield,
    title: 'Run Security Scans',
    description: '500+ security rules scan for vulnerabilities, secrets, misconfigurations, and compliance gaps.',
    gradient: 'from-orange-500/20 to-red-500/20',
    border: 'border-orange-500/30',
    iconColor: 'text-orange-400',
  },
  {
    icon: BarChart3,
    title: 'Analyze Findings',
    description: 'Prioritized results with severity levels, risk scores, and detailed technical explanations.',
    gradient: 'from-yellow-500/20 to-amber-500/20',
    border: 'border-yellow-500/30',
    iconColor: 'text-yellow-400',
  },
  {
    icon: Sparkles,
    title: 'Generate AI Fixes',
    description: 'AI-powered remediation with production-ready code, best practices, and documentation links.',
    gradient: 'from-green-500/20 to-emerald-500/20',
    border: 'border-green-500/30',
    iconColor: 'text-green-400',
  },
  {
    icon: FileDown,
    title: 'Export Reports',
    description: 'Download PDF, Excel, or JSON reports for compliance, audits, and team collaboration.',
    gradient: 'from-primary/20 to-indigo-500/20',
    border: 'border-primary/30',
    iconColor: 'text-primary',
  },
]

export function ScanWorkflow() {
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
            <Zap className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">From Repo to Report in Minutes</span>
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            How It Works
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Get comprehensive security analysis in 6 simple steps — no configuration required
          </p>
        </div>

        <div className="max-w-4xl mx-auto">
          {steps.map((step, index) => {
            const Icon = step.icon
            const isLast = index === steps.length - 1

            return (
              <motion.div
                key={step.title}
                className="relative flex gap-6 pb-8"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.12 }}
              >
                {/* Connector line */}
                {!isLast && (
                  <div className="absolute left-8 top-16 bottom-0 w-0.5 bg-gradient-to-b from-primary/50 to-transparent" />
                )}

                {/* Step Icon */}
                <div className="relative flex-shrink-0">
                  <motion.div
                    className={cn(
                      'w-16 h-16 rounded-2xl bg-gradient-to-br flex items-center justify-center border shadow-lg',
                      step.gradient,
                      step.border
                    )}
                    whileHover={{ scale: 1.05 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 10 }}
                  >
                    <Icon className={cn('h-8 w-8', step.iconColor)} />
                  </motion.div>
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-background border-2 border-primary/50 flex items-center justify-center">
                    <span className="text-[10px] font-bold text-primary">{String(index + 1).padStart(2, '0')}</span>
                  </div>
                </div>

                {/* Step Content */}
                <div className="flex-1 pt-3">
                  <div className={cn(
                    'p-5 rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-transparent backdrop-blur-sm',
                    'hover:border-white/20 transition-all duration-300'
                  )}>
                    <h3 className="text-lg font-semibold text-foreground mb-2">{step.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>

                    {index === 2 && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-red-500/10 text-red-400 border border-red-500/30">Secrets</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-orange-500/10 text-orange-400 border border-orange-500/30">Vulnerabilities</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/30">Misconfigurations</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30">Compliance</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Arrow indicator for non-mobile */}
                {!isLast && (
                  <div className="hidden lg:flex absolute -bottom-2 left-8 items-center gap-2 text-xs text-muted-foreground">
                    <ArrowRight className="h-3 w-3" />
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
import { motion } from 'framer-motion'
import {
  Shield, Zap, GitBranch, Brain, FileText,
  BarChart3
} from 'lucide-react'

const benefits = [
  {
    icon: Zap,
    title: 'Scan in 30 seconds',
    description: 'Full infrastructure analysis completes before your coffee is ready.',
  },
  {
    icon: Brain,
    title: 'AI-powered fixes',
    description: 'Not just alerts. Copy-paste ready code to resolve every finding.',
  },
  {
    icon: Shield,
    title: '500+ security rules',
    description: 'CIS benchmarks, OWASP guidelines, and cloud best practices built in.',
  },
  {
    icon: GitBranch,
    title: 'CI/CD integration',
    description: 'GitHub Actions, GitLab CI, Jenkins — scan on every push automatically.',
  },
  {
    icon: FileText,
    title: 'Compliance reports',
    description: 'SOC 2, HIPAA, PCI-DSS reports generated on demand.',
  },
  {
    icon: BarChart3,
    title: 'Posture tracking',
    description: 'See your security trend over time across all repositories.',
  },
]

export function WhyDevArchAI() {
  return (
    <section className="py-16 lg:py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <p className="text-sm font-medium text-primary mb-3">Why DevArchAI</p>
            <h2 className="display-lg text-white mb-4">
              Built for engineers who ship fast
            </h2>
            <p className="text-base text-slate-400 max-w-2xl mx-auto">
              Security scanning that keeps pace with your deployment velocity.
            </p>
          </motion.div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl mx-auto">
          {benefits.map((benefit, index) => {
            const Icon = benefit.icon
            return (
              <motion.div
                key={benefit.title}
                className="p-5 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.1] transition-all duration-300"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: index * 0.06, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className="p-2 rounded-lg w-fit bg-white/[0.04] border border-white/[0.06] mb-3">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
                <h3 className="text-sm font-semibold text-white mb-1">{benefit.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{benefit.description}</p>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
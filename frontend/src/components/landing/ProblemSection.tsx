import { memo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Key, Hexagon, Layers, GitBranch, AlertTriangle, Container, Cloud, Terminal } from 'lucide-react'
import { cn } from '../../lib/utils'

interface ProblemCard {
  title: string
  icon: React.ElementType
  description: string
  examples: string[]
  severity: 'critical' | 'high' | 'medium'
}

const problems: ProblemCard[] = [
  {
    title: 'Secrets Exposure',
    icon: Key,
    description: 'Hardcoded credentials, API keys, and tokens leaked in code and config files.',
    examples: ['AWS Keys', 'API Keys', 'GitHub Tokens'],
    severity: 'critical',
  },
  {
    title: 'Container Security Risks',
    icon: Container,
    description: 'Docker containers running with excessive privileges and vulnerable base images.',
    examples: ['Root Containers', 'Privileged Mode', 'Weak Images'],
    severity: 'critical',
  },
  {
    title: 'Kubernetes Misconfigurations',
    icon: Hexagon,
    description: 'Pods and deployments missing security contexts, resource limits, and network policies.',
    examples: ['Missing Limits', 'Missing Security Context', 'Missing Network Policies'],
    severity: 'high',
  },
  {
    title: 'Terraform Risks',
    icon: Layers,
    description: 'Infrastructure-as-code with publicly exposed resources and weak access controls.',
    examples: ['Public Resources', 'Missing Encryption', 'Weak IAM'],
    severity: 'high',
  },
  {
    title: 'CI/CD Security Gaps',
    icon: GitBranch,
    description: 'Pipeline workflows with insecure configurations and overly permissive permissions.',
    examples: ['Missing Security Checks', 'Insecure Workflows', 'Dangerous Permissions'],
    severity: 'medium',
  },
  {
    title: 'Cloud Infrastructure Risks',
    icon: Cloud,
    description: 'AWS, Azure, and GCP resources with open security groups and unencrypted data.',
    examples: ['Open Security Groups', 'Unencrypted Storage', 'Overly Permissive Roles'],
    severity: 'high',
  },
]

const severityConfig = {
  critical: {
    badge: 'text-red-400 bg-red-500/10 border-red-500/20',
    icon: 'text-red-400 bg-red-500/10 border-red-500/15',
  },
  high: {
    badge: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
    icon: 'text-orange-400 bg-orange-500/10 border-orange-500/15',
  },
  medium: {
    badge: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
    icon: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/15',
  },
}

const ProblemCardItem = memo(function ProblemCardItem({
  problem,
  index,
}: {
  problem: ProblemCard
  index: number
}) {
  const Icon = problem.icon
  const config = severityConfig[problem.severity]

  return (
    <motion.div
      className="group relative p-5 rounded-2xl border border-white/[0.06] bg-card/30 backdrop-blur-sm hover:border-white/[0.12] transition-all duration-300"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className={cn('p-2.5 rounded-xl border', config.icon)}>
            <Icon className="h-5 w-5" />
          </div>
          <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-medium border', config.badge)}>
            {problem.severity.charAt(0).toUpperCase() + problem.severity.slice(1)}
          </span>
        </div>

        <div>
          <h3 className="text-base font-semibold text-foreground mb-1.5">{problem.title}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{problem.description}</p>
        </div>

        <div className="space-y-2">
          <p className="text-[10px] text-muted-foreground/60 font-medium uppercase tracking-wider">Examples</p>
          <div className="flex flex-wrap gap-1.5">
            {problem.examples.map((example) => (
              <span
                key={example}
                className="px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.06] text-[11px] text-muted-foreground"
              >
                {example}
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-primary/70 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <Terminal className="h-3 w-3" />
          <span>Scan detects this automatically</span>
        </div>
      </div>
    </motion.div>
  )
})

export function ProblemSection() {
  return (
    <section className="py-20 lg:py-32 bg-white/[0.02]">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14 space-y-3">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/[0.08] border border-red-500/20"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <AlertTriangle className="h-4 w-4 text-red-400/80" />
            <span className="text-sm font-medium text-red-400/90">Real Risks Your Team Faces</span>
          </motion.div>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Why DevOps Teams Need DevArchAI
          </h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Every day, production deployments ship with critical security gaps. Here are the most common
            risks caught by our scanning engine before they reach production.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl mx-auto">
          {problems.map((problem, index) => (
            <ProblemCardItem key={problem.title} problem={problem} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}

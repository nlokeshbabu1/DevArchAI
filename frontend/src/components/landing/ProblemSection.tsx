import { motion } from 'framer-motion'
import { Key, Shield, Hexagon, Layers, GitBranch, AlertTriangle, Lock, Globe, Network, FileKey, Container, Code, Users, Server, Cloud, Terminal } from 'lucide-react'
import { cn } from '../../lib/utils'

interface ProblemCard {
  title: string
  icon: React.ElementType
  description: string
  examples: string[]
  gradient: string
  severity: 'critical' | 'high' | 'medium'
}

const problems: ProblemCard[] = [
  {
    title: 'Secrets Exposure',
    icon: Key,
    description: 'Hardcoded credentials, API keys, and tokens leaked in code and config files.',
    examples: ['AWS Keys', 'API Keys', 'GitHub Tokens'],
    gradient: 'from-red-500/10 to-orange-500/5',
    severity: 'critical',
  },
  {
    title: 'Container Security Risks',
    icon: Container,
    description: 'Docker containers running with excessive privileges and vulnerable base images.',
    examples: ['Root Containers', 'Privileged Mode', 'Weak Images'],
    gradient: 'from-orange-500/10 to-yellow-500/5',
    severity: 'critical',
  },
  {
    title: 'Kubernetes Misconfigurations',
    icon: Hexagon,
    description: 'Pods and deployments missing security contexts, resource limits, and network policies.',
    examples: ['Missing Limits', 'Missing Security Context', 'Missing Network Policies'],
    gradient: 'from-yellow-500/10 to-amber-500/5',
    severity: 'high',
  },
  {
    title: 'Terraform Risks',
    icon: Layers,
    description: 'Infrastructure-as-code with publicly exposed resources and weak access controls.',
    examples: ['Public Resources', 'Missing Encryption', 'Weak IAM'],
    gradient: 'from-purple-500/10 to-pink-500/5',
    severity: 'high',
  },
  {
    title: 'CI/CD Security Gaps',
    icon: GitBranch,
    description: 'Pipeline workflows with insecure configurations and overly permissive permissions.',
    examples: ['Missing Security Checks', 'Insecure Workflows', 'Dangerous Permissions'],
    gradient: 'from-blue-500/10 to-cyan-500/5',
    severity: 'medium',
  },
  {
    title: 'Cloud Infrastructure Risks',
    icon: Cloud,
    description: 'AWS, Azure, and GCP resources with open security groups and unencrypted data.',
    examples: ['Open Security Groups', 'Unencrypted Storage', 'Overly Permissive Roles'],
    gradient: 'from-indigo-500/10 to-blue-500/5',
    severity: 'high',
  },
]

export function ProblemSection() {
  return (
    <section className="py-20 lg:py-32 bg-white/[0.02]">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16 space-y-4">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/10 border border-red-500/30"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <span className="text-sm font-medium text-red-400">Real Risks Your Team Faces</span>
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            Why DevOps Teams Need DevArchAI
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Every day, production deployments ship with critical security gaps. Here are the most common
            risks caught by our scanning engine before they reach production.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {problems.map((problem, index) => {
            const Icon = problem.icon
            const severityColors = {
              critical: 'text-red-400 bg-red-500/10 border-red-500/30',
              high: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
              medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
            }

            return (
              <motion.div
                key={problem.title}
                className={cn(
                  'group relative p-6 rounded-2xl border border-white/10 backdrop-blur-sm',
                  'hover:border-white/20 transition-all duration-500',
                  problem.gradient
                )}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -4 }}
              >
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                <div className="relative space-y-4">
                  <div className="flex items-start justify-between">
                    <div className="p-3 rounded-xl bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-white/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <span className={cn(
                      'px-2.5 py-1 rounded-full text-xs font-medium border',
                      severityColors[problem.severity]
                    )}>
                      {problem.severity.charAt(0).toUpperCase() + problem.severity.slice(1)}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-foreground mb-2">{problem.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{problem.description}</p>
                  </div>

                  <div className="space-y-2 pt-2">
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Examples:</p>
                    <div className="flex flex-wrap gap-2">
                      {problem.examples.map((example) => (
                        <span
                          key={example}
                          className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-muted-foreground"
                        >
                          {example}
                        </span>
                      ))}
                    </div>
                  </div>

                  <motion.div
                    className="flex items-center gap-2 text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity"
                    initial={false}
                  >
                    <Terminal className="h-3 w-3" />
                    <span>Scan detects this automatically</span>
                  </motion.div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
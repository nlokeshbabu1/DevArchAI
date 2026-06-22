import { motion } from 'framer-motion'
import { Shield, Search, FileCode, Box, Hexagon, Layers, GitBranch, Brain, FileText, FileDown, FileSpreadsheet, BarChart3, Sparkles, Lock, Eye, Code, CheckCircle, Server, Cloud } from 'lucide-react'
import { cn } from '../../lib/utils'

interface Capability {
  title: string
  icon: React.ElementType
  description: string
  severity: { label: string; count: number; color: string }[]
  gradient: string
  borderColor: string
  iconBg: string
}

const capabilities: Capability[] = [
  {
    title: 'Repository Scanning',
    icon: Search,
    description: 'Deep scan entire git repositories for security issues, secrets, and misconfigurations across all branches.',
    severity: [
      { label: 'Rules', count: 150, color: 'text-blue-400' },
    ],
    gradient: 'from-blue-500/10 to-cyan-500/5',
    borderColor: 'border-blue-500/20',
    iconBg: 'bg-blue-500/20',
  },
  {
    title: 'Secret Detection',
    icon: Lock,
    description: 'Detect hardcoded secrets, API keys, tokens, and credentials before they leak to production.',
    severity: [
      { label: 'Secrets Found', count: 24, color: 'text-red-400' },
    ],
    gradient: 'from-red-500/10 to-orange-500/5',
    borderColor: 'border-red-500/20',
    iconBg: 'bg-red-500/20',
  },
  {
    title: 'Dependency Scanning',
    icon: FileCode,
    description: 'Analyze package dependencies for known vulnerabilities and supply chain risks.',
    severity: [
      { label: 'Vulnerabilities', count: 12, color: 'text-orange-400' },
    ],
    gradient: 'from-orange-500/10 to-yellow-500/5',
    borderColor: 'border-orange-500/20',
    iconBg: 'bg-orange-500/20',
  },
  {
    title: 'Docker Security',
    icon: Box,
    description: 'Scan Dockerfiles and images for root users, privileged mode, and insecure base images.',
    severity: [
      { label: 'Critical', count: 3, color: 'text-red-400' },
      { label: 'High', count: 8, color: 'text-orange-400' },
    ],
    gradient: 'from-cyan-500/10 to-blue-500/5',
    borderColor: 'border-cyan-500/20',
    iconBg: 'bg-cyan-500/20',
  },
  {
    title: 'Kubernetes Security',
    icon: Hexagon,
    description: 'Validate K8s manifests for security contexts, resource limits, network policies, and RBAC.',
    severity: [
      { label: 'Critical', count: 5, color: 'text-red-400' },
      { label: 'High', count: 15, color: 'text-orange-400' },
    ],
    gradient: 'from-purple-500/10 to-pink-500/5',
    borderColor: 'border-purple-500/20',
    iconBg: 'bg-purple-500/20',
  },
  {
    title: 'Terraform Security',
    icon: Layers,
    description: 'Scan IaC for publicly exposed resources, missing encryption, and overly permissive IAM policies.',
    severity: [
      { label: 'Critical', count: 7, color: 'text-red-400' },
      { label: 'High', count: 12, color: 'text-orange-400' },
    ],
    gradient: 'from-indigo-500/10 to-purple-500/5',
    borderColor: 'border-indigo-500/20',
    iconBg: 'bg-indigo-500/20',
  },
  {
    title: 'CI/CD Security',
    icon: GitBranch,
    description: 'Analyze pipeline configurations for insecure workflows, dangerous permissions, and missing checks.',
    severity: [
      { label: 'High', count: 6, color: 'text-orange-400' },
      { label: 'Medium', count: 9, color: 'text-yellow-400' },
    ],
    gradient: 'from-green-500/10 to-emerald-500/5',
    borderColor: 'border-green-500/20',
    iconBg: 'bg-green-500/20',
  },
  {
    title: 'AI Explanations',
    icon: Brain,
    description: 'Every finding includes an AI-generated explanation of the risk, impact, and root cause analysis.',
    severity: [
      { label: 'AI-Powered', count: 100, color: 'text-primary' },
    ],
    gradient: 'from-primary/10 to-indigo-500/5',
    borderColor: 'border-primary/20',
    iconBg: 'bg-primary/20',
  },
  {
    title: 'AI Fix Recommendations',
    icon: Sparkles,
    description: 'Get production-ready code fixes for every security issue, with copy-paste or auto-PR integration.',
    severity: [
      { label: 'Fixes Ready', count: 50, color: 'text-green-400' },
    ],
    gradient: 'from-pink-500/10 to-rose-500/5',
    borderColor: 'border-pink-500/20',
    iconBg: 'bg-pink-500/20',
  },
  {
    title: 'Documentation Generation',
    icon: FileText,
    description: 'Auto-generate comprehensive security documentation with findings, risks, and remediation steps.',
    severity: [
      { label: 'Docs Auto', count: 1, color: 'text-blue-400' },
    ],
    gradient: 'from-yellow-500/10 to-amber-500/5',
    borderColor: 'border-yellow-500/20',
    iconBg: 'bg-yellow-500/20',
  },
  {
    title: 'PDF Reports',
    icon: FileDown,
    description: 'Export professional PDF security reports with executive summaries and technical findings.',
    severity: [
      { label: 'Executive Ready', count: 1, color: 'text-green-400' },
    ],
    gradient: 'from-teal-500/10 to-cyan-500/5',
    borderColor: 'border-teal-500/20',
    iconBg: 'bg-teal-500/20',
  },
  {
    title: 'Excel Reports',
    icon: FileSpreadsheet,
    description: 'Export findings to Excel for custom analysis, filtering, and integration with your workflows.',
    severity: [
      { label: 'Exportable', count: 1, color: 'text-green-400' },
    ],
    gradient: 'from-emerald-500/10 to-green-500/5',
    borderColor: 'border-emerald-500/20',
    iconBg: 'bg-emerald-500/20',
  },
  {
    title: 'Security Dashboard',
    icon: BarChart3,
    description: 'Central dashboard showing security scores, trends, severity distribution, and remediation progress.',
    severity: [
      { label: 'Real-time', count: 1, color: 'text-primary' },
    ],
    gradient: 'from-sky-500/10 to-blue-500/5',
    borderColor: 'border-sky-500/20',
    iconBg: 'bg-sky-500/20',
  },
  {
    title: 'Cloud Security',
    icon: Cloud,
    description: 'Scan AWS, Azure, and GCP configurations for security risks, compliance gaps, and best practices.',
    severity: [
      { label: 'Critical', count: 4, color: 'text-red-400' },
      { label: 'High', count: 11, color: 'text-orange-400' },
    ],
    gradient: 'from-violet-500/10 to-purple-500/5',
    borderColor: 'border-violet-500/20',
    iconBg: 'bg-violet-500/20',
  },
]

export function PlatformCapabilities() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16 space-y-4">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <Shield className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">Complete Security Platform</span>
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            Everything You Need to Secure DevOps
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            From secrets detection to AI-powered fix recommendations, DevArchAI covers your entire security workflow
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 max-w-7xl mx-auto">
          {capabilities.map((cap, index) => {
            const Icon = cap.icon

            return (
              <motion.div
                key={cap.title}
                className={cn(
                  'group relative p-5 rounded-xl border backdrop-blur-sm',
                  'hover:border-white/30 transition-all duration-300',
                  cap.gradient,
                  cap.borderColor
                )}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ y: -3 }}
              >
                <div className="relative space-y-3">
                  <div className="flex items-start justify-between">
                    <div className={cn(
                      'p-2.5 rounded-lg border border-white/10',
                      cap.iconBg
                    )}>
                      <Icon className="h-5 w-5 text-foreground" />
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-1">{cap.title}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{cap.description}</p>
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {cap.severity.map((sev) => (
                      <span
                        key={sev.label}
                        className={cn(
                          'px-2 py-0.5 rounded-md text-[10px] font-medium border',
                          'bg-white/5 border-white/10',
                          sev.color
                        )}
                      >
                        {sev.count > 1 ? `${sev.count} ` : ''}{sev.label}
                      </span>
                    ))}
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
import { memo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Shield, Search, FileCode, Box, Hexagon, Layers, GitBranch, Brain, FileText, FileDown, FileSpreadsheet, BarChart3, Sparkles, Cloud, Lock } from 'lucide-react'
import { cn } from '../../lib/utils'

interface Capability {
  title: string
  icon: React.ElementType
  description: string
  severity: { label: string; count: number; color: string }[]
  accent: string
}

const capabilities: Capability[] = [
  {
    title: 'Repository Scanning',
    icon: Search,
    description: 'Deep scan entire git repositories for security issues, secrets, and misconfigurations across all branches.',
    severity: [{ label: 'Rules', count: 150, color: 'text-blue-400' }],
    accent: 'border-blue-500/15 hover:border-blue-500/30',
  },
  {
    title: 'Secret Detection',
    icon: Lock,
    description: 'Detect hardcoded secrets, API keys, tokens, and credentials before they leak to production.',
    severity: [{ label: 'Secrets Found', count: 24, color: 'text-red-400' }],
    accent: 'border-red-500/15 hover:border-red-500/30',
  },
  {
    title: 'Dependency Scanning',
    icon: FileCode,
    description: 'Analyze package dependencies for known vulnerabilities and supply chain risks.',
    severity: [{ label: 'Vulnerabilities', count: 12, color: 'text-orange-400' }],
    accent: 'border-orange-500/15 hover:border-orange-500/30',
  },
  {
    title: 'Docker Security',
    icon: Box,
    description: 'Scan Dockerfiles and images for root users, privileged mode, and insecure base images.',
    severity: [
      { label: 'Critical', count: 3, color: 'text-red-400' },
      { label: 'High', count: 8, color: 'text-orange-400' },
    ],
    accent: 'border-cyan-500/15 hover:border-cyan-500/30',
  },
  {
    title: 'Kubernetes Security',
    icon: Hexagon,
    description: 'Validate K8s manifests for security contexts, resource limits, network policies, and RBAC.',
    severity: [
      { label: 'Critical', count: 5, color: 'text-red-400' },
      { label: 'High', count: 15, color: 'text-orange-400' },
    ],
    accent: 'border-purple-500/15 hover:border-purple-500/30',
  },
  {
    title: 'Terraform Security',
    icon: Layers,
    description: 'Scan infrastructure as code for publicly exposed resources, missing encryption, and weak IAM policies.',
    severity: [
      { label: 'Critical', count: 7, color: 'text-red-400' },
      { label: 'High', count: 12, color: 'text-orange-400' },
    ],
    accent: 'border-indigo-500/15 hover:border-indigo-500/30',
  },
  {
    title: 'CI/CD Security',
    icon: GitBranch,
    description: 'Analyze pipeline configurations for insecure workflows, dangerous permissions, and missing checks.',
    severity: [
      { label: 'High', count: 6, color: 'text-orange-400' },
      { label: 'Medium', count: 9, color: 'text-yellow-400' },
    ],
    accent: 'border-green-500/15 hover:border-green-500/30',
  },
  {
    title: 'AI Explanations',
    icon: Brain,
    description: 'Every finding includes an AI-generated explanation of the risk, impact, and root cause analysis.',
    severity: [{ label: 'AI-Powered', count: 100, color: 'text-primary' }],
    accent: 'border-primary/15 hover:border-primary/30',
  },
  {
    title: 'AI Fix Recommendations',
    icon: Sparkles,
    description: 'Get production-ready code fixes for every security issue, with copy-paste or auto-PR integration.',
    severity: [{ label: 'Fixes Ready', count: 50, color: 'text-green-400' }],
    accent: 'border-pink-500/15 hover:border-pink-500/30',
  },
  {
    title: 'Documentation Generation',
    icon: FileText,
    description: 'Auto-generate comprehensive security documentation with findings, risks, and remediation steps.',
    severity: [{ label: 'Docs Auto', count: 1, color: 'text-blue-400' }],
    accent: 'border-yellow-500/15 hover:border-yellow-500/30',
  },
  {
    title: 'PDF Reports',
    icon: FileDown,
    description: 'Export professional PDF security reports with executive summaries and technical findings.',
    severity: [{ label: 'Executive Ready', count: 1, color: 'text-green-400' }],
    accent: 'border-teal-500/15 hover:border-teal-500/30',
  },
  {
    title: 'Excel Reports',
    icon: FileSpreadsheet,
    description: 'Export findings to Excel for custom analysis, filtering, and integration with your workflows.',
    severity: [{ label: 'Exportable', count: 1, color: 'text-green-400' }],
    accent: 'border-emerald-500/15 hover:border-emerald-500/30',
  },
  {
    title: 'Security Dashboard',
    icon: BarChart3,
    description: 'Central dashboard showing security scores, trends, severity distribution, and remediation progress.',
    severity: [{ label: 'Real-time', count: 1, color: 'text-primary' }],
    accent: 'border-sky-500/15 hover:border-sky-500/30',
  },
  {
    title: 'Cloud Security',
    icon: Cloud,
    description: 'Scan AWS, Azure, and GCP configurations for security risks, compliance gaps, and best practices.',
    severity: [
      { label: 'Critical', count: 4, color: 'text-red-400' },
      { label: 'High', count: 11, color: 'text-orange-400' },
    ],
    accent: 'border-violet-500/15 hover:border-violet-500/30',
  },
]

const CapabilityCard = memo(function CapabilityCard({
  cap,
  index,
}: {
  cap: Capability
  index: number
}) {
  const Icon = cap.icon

  return (
    <motion.div
      className={cn(
        'group relative p-5 rounded-2xl border bg-card/30 backdrop-blur-sm',
        'transition-all duration-300',
        cap.accent
      )}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: index * 0.04, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="space-y-3">
        <div className="p-2 rounded-lg bg-white/[0.04] border border-white/[0.06] w-fit">
          <Icon className="h-4.5 w-4.5 text-foreground/80" />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-foreground mb-1">{cap.title}</h3>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{cap.description}</p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {cap.severity.map((sev) => (
            <span
              key={sev.label}
              className={cn(
                'px-1.5 py-0.5 rounded text-[10px] font-medium',
                'bg-white/[0.03] border border-white/[0.06]',
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
})

export function PlatformCapabilities() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14 space-y-3">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.06] border border-primary/20"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <Shield className="h-4 w-4 text-primary/80" />
            <span className="text-sm font-medium text-primary/90">Complete Security Platform</span>
          </motion.div>
          <h2 className="display-lg text-foreground">
            Everything You Need to Secure DevOps
          </h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            From secrets detection to AI-powered fix recommendations, DevArchAI covers your entire security workflow
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 max-w-7xl mx-auto">
          {capabilities.map((cap, index) => (
            <CapabilityCard key={cap.title} cap={cap} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}

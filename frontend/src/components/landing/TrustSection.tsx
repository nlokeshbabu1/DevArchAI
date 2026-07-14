import { memo } from 'react'
import { motion } from 'framer-motion'
import { Terminal, Cloud, Server, Shield, Lock, Users } from 'lucide-react'
import { cn } from '../../lib/utils'

interface UserGroup {
  role: string
  icon: React.ElementType
  description: string
  color: string
  tags: string[]
}

const userGroups: UserGroup[] = [
  {
    role: 'DevOps',
    icon: Terminal,
    description: 'Automate security across your entire CI/CD pipeline without slowing down deployments.',
    color: 'border-cyan-500/20',
    tags: ['CI/CD pipeline security', 'Infrastructure as Code', 'Deployment automation'],
  },
  {
    role: 'Platform',
    icon: Cloud,
    description: 'Build and maintain secure internal platforms with guardrails that developers actually follow.',
    color: 'border-indigo-500/20',
    tags: ['Platform engineering', 'Internal developer platforms', 'Security guardrails'],
  },
  {
    role: 'SRE',
    icon: Server,
    description: 'Ensure reliability and security converge with pre-deployment validation and observability.',
    color: 'border-green-500/20',
    tags: ['Reliability engineering', 'Incident prevention', 'Deployment validation'],
  },
  {
    role: 'Security',
    icon: Shield,
    description: 'Shift left with comprehensive scanning that catches vulnerabilities before they reach production.',
    color: 'border-red-500/20',
    tags: ['Vulnerability management', 'Compliance automation', 'Secret detection'],
  },
  {
    role: 'AppSec',
    icon: Lock,
    description: 'Embed application security into DevOps workflows with actionable AI-powered remediation.',
    color: 'border-yellow-500/20',
    tags: ['Application security', 'Developer handoff', 'Fix automation'],
  },
]

const UserGroupCard = memo(function UserGroupCard({
  group, index,
}: {
  group: UserGroup; index: number
}) {
  const Icon = group.icon

  return (
    <motion.div
      className={cn(
        'relative p-5 rounded-2xl border bg-white/[0.02] backdrop-blur-sm',
        'hover:border-white/[0.12] transition-all duration-300',
        group.color
      )}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className={cn('p-2.5 rounded-xl border border-white/[0.06] bg-white/[0.03]', group.color)}>
            <Icon className="h-5 w-5 text-white/80" />
          </div>
          <span className="text-[9px] font-mono text-white/30 px-1.5 py-0.5 rounded border border-white/[0.04]">
            ROLE-{String(index + 1).padStart(2, '0')}
          </span>
        </div>

        <div>
          <h3 className="text-lg font-bold text-white mb-1">{group.role}</h3>
          <p className="text-xs text-slate-400 leading-relaxed">{group.description}</p>
        </div>

        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {group.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.03] text-slate-400/70 border border-white/[0.06]"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  )
})

export function TrustSection() {
  return (
    <section className="py-16 lg:py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12 space-y-3">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.06] border border-primary/20">
            <Users className="h-4 w-4 text-primary/80" />
            <span className="text-sm font-medium text-primary/90">Built for Engineering Teams</span>
          </div>
          <h2 className="display-lg text-white">
            Purpose-Built for Your Role
          </h2>
          <p className="text-base text-slate-400 max-w-2xl mx-auto">
            Security scanning that adapts to how your team works
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 max-w-6xl mx-auto">
          {userGroups.map((group, index) => (
            <UserGroupCard key={group.role} group={group} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}
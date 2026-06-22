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
    color: 'from-cyan-500/20 to-blue-500/20 border-cyan-500/30',
    tags: ['CI/CD pipeline security', 'Infrastructure as Code', 'Deployment automation'],
  },
  {
    role: 'Platform',
    icon: Cloud,
    description: 'Build and maintain secure internal platforms with guardrails that developers actually follow.',
    color: 'from-indigo-500/20 to-purple-500/20 border-indigo-500/30',
    tags: ['Platform engineering', 'Internal developer platforms', 'Security guardrails'],
  },
  {
    role: 'SRE',
    icon: Server,
    description: 'Ensure reliability and security converge with pre-deployment validation and observability.',
    color: 'from-green-500/20 to-emerald-500/20 border-green-500/30',
    tags: ['Reliability engineering', 'Incident prevention', 'Deployment validation'],
  },
  {
    role: 'Security',
    icon: Shield,
    description: 'Shift left with comprehensive scanning that catches vulnerabilities before they reach production.',
    color: 'from-red-500/20 to-orange-500/20 border-red-500/30',
    tags: ['Vulnerability management', 'Compliance automation', 'Secret detection'],
  },
  {
    role: 'AppSec',
    icon: Lock,
    description: 'Embed application security into DevOps workflows with actionable AI-powered remediation.',
    color: 'from-yellow-500/20 to-amber-500/20 border-yellow-500/30',
    tags: ['Application security', 'Developer handoff', 'Fix automation'],
  },
]

export function TrustSection() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30">
            <Users className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">Built for Engineering Teams</span>
          </div>
          <h2 className="text-4xl font-bold gradient-text">
            Purpose-Built for Your Role
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Security scanning that adapts to how your team works
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-6 max-w-6xl mx-auto">
          {userGroups.map((group, index) => {
            const Icon = group.icon

            return (
              <motion.div
                key={group.role}
                className={cn(
                  'relative flex-1 basis-[180px] min-w-[180px] p-5 rounded-2xl bg-gradient-to-br border backdrop-blur-sm overflow-hidden',
                  'hover:shadow-xl transition-all duration-300 group',
                  group.color
                )}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-white/5 to-transparent rounded-bl-full" />

                <div className="space-y-3 relative">
                  <div className="flex items-center justify-between">
                    <div className={cn(
                      'p-2.5 rounded-xl bg-gradient-to-br border border-white/10',
                      group.color
                    )}>
                      <Icon className="h-5 w-5 text-foreground" />
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground/40 px-2 py-0.5 rounded border border-white/5">
                      ROLE-{String(index + 1).padStart(2, '0')}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-lg font-bold text-foreground mb-1.5">{group.role}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">{group.description}</p>
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {group.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-muted-foreground border border-white/10"
                      >
                        {tag}
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

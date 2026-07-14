import { memo } from 'react'
import { motion } from 'framer-motion'
import { Cloud, Layers, Github, Shield, Activity, GitBranch, Box, Package, Code, Lock } from 'lucide-react'
import { cn } from '../../lib/utils'

interface Technology {
  name: string
  icon: React.ElementType
  description: string
  category: string
}

const technologies: Technology[] = [
  { name: 'Terraform', icon: Layers, description: 'Infrastructure security checks', category: 'Infrastructure as Code' },
  { name: 'Pulumi', icon: Code, description: 'Programmatic infrastructure as code', category: 'Infrastructure as Code' },
  { name: 'CloudFormation', icon: Layers, description: 'AWS native infrastructure as code', category: 'Infrastructure as Code' },
  { name: 'AWS', icon: Cloud, description: 'Amazon Web Services', category: 'Cloud Providers' },
  { name: 'Azure', icon: Cloud, description: 'Microsoft Azure', category: 'Cloud Providers' },
  { name: 'GCP', icon: Cloud, description: 'Google Cloud Platform', category: 'Cloud Providers' },
  { name: 'Docker', icon: Box, description: 'Container security', category: 'Containers & Orchestration' },
  { name: 'Kubernetes', icon: Package, description: 'K8s manifest analysis', category: 'Containers & Orchestration' },
  { name: 'Helm', icon: Shield, description: 'Chart validation', category: 'Containers & Orchestration' },
  { name: 'GitHub Actions', icon: Github, description: 'Workflow security', category: 'CI/CD Platforms' },
  { name: 'Jenkins', icon: GitBranch, description: 'Pipeline security', category: 'CI/CD Platforms' },
  { name: 'GitLab CI', icon: GitBranch, description: 'CI/CD validation', category: 'CI/CD Platforms' },
  { name: 'CircleCI', icon: GitBranch, description: 'Pipeline checks', category: 'CI/CD Platforms' },
  { name: 'Trivy', icon: Shield, description: 'Vulnerability scanning', category: 'Security Tools' },
  { name: 'SonarQube', icon: Code, description: 'Code quality', category: 'Security Tools' },
  { name: 'Vault', icon: Lock, description: 'Secrets management', category: 'Security Tools' },
  { name: 'Prometheus', icon: Activity, description: 'Metrics monitoring', category: 'Monitoring' },
  { name: 'Grafana', icon: Activity, description: 'Visualization', category: 'Monitoring' },
  { name: 'ELK Stack', icon: Activity, description: 'Log analytics', category: 'Monitoring' },
]

const categoryColorMap: Record<string, string> = {
  'Infrastructure as Code': 'border-purple-500/15 hover:border-purple-500/30',
  'Cloud Providers': 'border-blue-500/15 hover:border-blue-500/30',
  'Containers & Orchestration': 'border-green-500/15 hover:border-green-500/30',
  'CI/CD Platforms': 'border-orange-500/15 hover:border-orange-500/30',
  'Security Tools': 'border-red-500/15 hover:border-red-500/30',
  'Monitoring': 'border-yellow-500/15 hover:border-yellow-500/30',
}

const categoryBadgeMap: Record<string, string> = {
  'Infrastructure as Code': 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  'Cloud Providers': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  'Containers & Orchestration': 'bg-green-500/10 text-green-400 border-green-500/20',
  'CI/CD Platforms': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  'Security Tools': 'bg-red-500/10 text-red-400 border-red-500/20',
  'Monitoring': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
}

interface DetectedTechStackProps {
  detectedStack?: string[]
}

const TechCard = memo(function TechCard({
  tech,
  index,
  category,
}: {
  tech: Technology
  index: number
  category: string
}) {
  const Icon = tech.icon
  const borderColor = categoryColorMap[category] || categoryColorMap['Monitoring']

  return (
    <motion.div
      className={cn(
        'group relative p-5 rounded-2xl bg-card/30 border backdrop-blur-sm',
        'hover:shadow-lg transition-all duration-300 cursor-default',
        borderColor
      )}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-30px' }}
      transition={{ delay: index * 0.04, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="space-y-3">
        <div className="p-2 rounded-lg w-fit bg-white/[0.04] border border-white/[0.06]">
          <Icon className="h-5 w-5 text-foreground/80" />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-foreground">
            {tech.name}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {tech.description}
          </p>
        </div>
      </div>
    </motion.div>
  )
})

export function DetectedTechStack({ detectedStack }: DetectedTechStackProps) {
  const filteredTech = detectedStack
    ? technologies.filter(t => detectedStack.some(ds => ds.toLowerCase().includes(t.name.toLowerCase())))
    : technologies

  const grouped = filteredTech.reduce((acc, tech) => {
    if (!acc[tech.category]) {
      acc[tech.category] = []
    }
    acc[tech.category].push(tech)
    return acc
  }, {} as Record<string, Technology[]>)

  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-6xl mx-auto">
          <div className="text-center mb-12 space-y-3">
            <h2 className="display-lg text-foreground">
              Supported Technologies
            </h2>
            <p className="text-base text-muted-foreground max-w-2xl mx-auto">
              Comprehensive coverage for your entire DevOps stack
            </p>
          </div>

          <div className="space-y-8">
            {Object.entries(grouped).map(([category, techs]) => {
              const badgeColor = categoryBadgeMap[category] || categoryBadgeMap['Monitoring']

              return (
                <motion.div
                  key={category}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-40px' }}
                  transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
                >
                  <div className="flex items-center gap-2.5 mb-4">
                    <span className={cn('px-3 py-1 rounded-full text-xs font-semibold border', badgeColor)}>
                      {category}
                    </span>
                    <div className="flex-1 h-px bg-white/[0.06]" />
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {techs.map((tech, index) => (
                      <TechCard key={tech.name} tech={tech} index={index} category={category} />
                    ))}
                  </div>
                </motion.div>
              )
            })}
          </div>

          <motion.div
            className="text-center mt-10 p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
              {['500+ Security Rules', 'CIS Benchmarks', 'OWASP Guidelines', 'Cloud Provider Best Practices'].map((item) => (
                <span key={item} className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-green-400/80" />
                  {item}
                </span>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

import { motion } from 'framer-motion'
import { 
  Terminal, Cloud, Layers, Github, Server, Database, Shield, Zap, 
  Code, Lock, Activity, GitBranch, Box, Package, Settings
} from 'lucide-react'
import { cn } from '../../lib/utils'

interface Technology {
  name: string
  icon: React.ElementType
  description: string
  category: string
}

const technologies: Technology[] = [
  // Infrastructure as Code
  {
    name: 'Terraform',
    icon: Layers,
    description: 'IaC security checks',
    category: 'Infrastructure as Code'
  },
  {
    name: 'Pulumi',
    icon: Code,
    description: 'Programmatic IaC',
    category: 'Infrastructure as Code'
  },
  {
    name: 'CloudFormation',
    icon: Layers,
    description: 'AWS native IaC',
    category: 'Infrastructure as Code'
  },
  
  // Cloud Providers
  {
    name: 'AWS',
    icon: Cloud,
    description: 'Amazon Web Services',
    category: 'Cloud Providers'
  },
  {
    name: 'Azure',
    icon: Cloud,
    description: 'Microsoft Azure',
    category: 'Cloud Providers'
  },
  {
    name: 'GCP',
    icon: Cloud,
    description: 'Google Cloud Platform',
    category: 'Cloud Providers'
  },
  
  // Containers & Orchestration
  {
    name: 'Docker',
    icon: Box,
    description: 'Container security',
    category: 'Containers & Orchestration'
  },
  {
    name: 'Kubernetes',
    icon: Package,
    description: 'K8s manifest analysis',
    category: 'Containers & Orchestration'
  },
  {
    name: 'Helm',
    icon: Shield,
    description: 'Chart validation',
    category: 'Containers & Orchestration'
  },
  
  // CI/CD Platforms
  {
    name: 'GitHub Actions',
    icon: Github,
    description: 'Workflow security',
    category: 'CI/CD Platforms'
  },
  {
    name: 'Jenkins',
    icon: GitBranch,
    description: 'Pipeline security',
    category: 'CI/CD Platforms'
  },
  {
    name: 'GitLab CI',
    icon: GitBranch,
    description: 'CI/CD validation',
    category: 'CI/CD Platforms'
  },
  {
    name: 'CircleCI',
    icon: GitBranch,
    description: 'Pipeline checks',
    category: 'CI/CD Platforms'
  },
  
  // Security Tools
  {
    name: 'Trivy',
    icon: Shield,
    description: 'Vulnerability scanning',
    category: 'Security Tools'
  },
  {
    name: 'SonarQube',
    icon: Code,
    description: 'Code quality',
    category: 'Security Tools'
  },
  {
    name: 'Vault',
    icon: Lock,
    description: 'Secrets management',
    category: 'Security Tools'
  },
  
  // Monitoring
  {
    name: 'Prometheus',
    icon: Activity,
    description: 'Metrics monitoring',
    category: 'Monitoring'
  },
  {
    name: 'Grafana',
    icon: Activity,
    description: 'Visualization',
    category: 'Monitoring'
  },
  {
    name: 'ELK Stack',
    icon: Activity,
    description: 'Log analytics',
    category: 'Monitoring'
  },
]

interface DetectedTechStackProps {
  detectedStack?: string[]
}

export function DetectedTechStack({ detectedStack }: DetectedTechStackProps) {
  const categoryColors = {
    'Infrastructure as Code': 'from-purple-500/20 to-indigo-500/20 border-purple-500/30',
    'Cloud Providers': 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
    'Containers & Orchestration': 'from-green-500/20 to-emerald-500/20 border-green-500/30',
    'CI/CD Platforms': 'from-orange-500/20 to-amber-500/20 border-orange-500/30',
    'Security Tools': 'from-red-500/20 to-pink-500/20 border-red-500/30',
    'Monitoring': 'from-yellow-500/20 to-amber-500/20 border-yellow-500/30',
  }

  const filteredTech = detectedStack
    ? technologies.filter(t => detectedStack.some(ds => ds.toLowerCase().includes(t.name.toLowerCase())))
    : technologies

  // Group by category
  const grouped = filteredTech.reduce((acc, tech) => {
    if (!acc[tech.category]) {
      acc[tech.category] = []
    }
    acc[tech.category].push(tech)
    return acc
  }, {} as Record<string, Technology[]>)

  return (
    <div className="w-full max-w-6xl mx-auto">
      <div className="text-center mb-12 space-y-4">
        <h2 className="text-4xl font-bold gradient-text">
          Supported Technologies
        </h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Comprehensive coverage for your entire DevOps stack
        </p>
      </div>

      {/* Categories */}
      <div className="space-y-8">
        {Object.entries(grouped).map(([category, techs]) => {
          const categoryColor = categoryColors[category as keyof typeof categoryColors] || categoryColors['Monitoring']

          return (
            <motion.div
              key={category}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <div className="flex items-center gap-2 mb-4">
                <div className={cn(
                  'px-3 py-1 rounded-full text-xs font-semibold',
                  categoryColor
                )}>
                  {category}
                </div>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {techs.map((tech, index) => {
                  const Icon = tech.icon

                  return (
                    <motion.div
                      key={tech.name}
                      className={cn(
                        'group relative p-6 rounded-2xl bg-gradient-to-br border backdrop-blur-sm',
                        'hover:shadow-xl transition-all duration-300 cursor-default',
                        categoryColor,
                        'hover:border-white/30'
                      )}
                      initial={{ opacity: 0, scale: 0.9 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: index * 0.05 }}
                      whileHover={{ scale: 1.05, y: -5 }}
                    >
                      {/* Glow effect on hover */}
                      <div className={cn(
                        'absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300',
                        'bg-gradient-to-br', categoryColor, 'blur-xl'
                      )} />

                      <div className="relative space-y-4">
                        <div className={cn(
                          'p-3 rounded-xl w-fit bg-gradient-to-br border border-white/10',
                          categoryColor
                        )}>
                          <Icon className="h-8 w-8 text-foreground" />
                        </div>

                        <div>
                          <h3 className="text-lg font-semibold text-foreground mb-1">
                            {tech.name}
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            {tech.description}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Additional info */}
      <motion.div
        className="text-center mt-12 p-6 rounded-2xl bg-white/5 border border-white/10"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-400" />
            500+ Security Rules
          </span>
          <span className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-400" />
            CIS Benchmarks
          </span>
          <span className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-400" />
            OWASP Guidelines
          </span>
          <span className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-400" />
            Cloud Provider Best Practices
          </span>
        </div>
      </motion.div>
    </div>
  )
}

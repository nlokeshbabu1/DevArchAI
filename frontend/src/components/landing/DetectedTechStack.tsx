import { motion } from 'framer-motion'
import { Terminal, Cloud, Layers, Github, Server, Database, Shield, Zap, Code, Lock } from 'lucide-react'
import { cn } from '../../lib/utils'

interface Technology {
  name: string
  icon: React.ElementType
  description: string
  category: 'container' | 'orchestration' | 'iac' | 'cicd' | 'cloud' | 'database'
}

const technologies: Technology[] = [
  { 
    name: 'Docker', 
    icon: Terminal, 
    description: 'Container security scanning',
    category: 'container'
  },
  { 
    name: 'Kubernetes', 
    icon: Cloud, 
    description: 'K8s manifest analysis',
    category: 'orchestration'
  },
  { 
    name: 'Terraform', 
    icon: Layers, 
    description: 'IaC security checks',
    category: 'iac'
  },
  { 
    name: 'GitHub Actions', 
    icon: Github, 
    description: 'CI/CD pipeline security',
    category: 'cicd'
  },
  { 
    name: 'AWS', 
    icon: Server, 
    description: 'Cloud infrastructure',
    category: 'cloud'
  },
  { 
    name: 'Azure', 
    icon: Cloud, 
    description: 'Cloud security',
    category: 'cloud'
  },
  { 
    name: 'PostgreSQL', 
    icon: Database, 
    description: 'Database security',
    category: 'database'
  },
  { 
    name: 'Helm', 
    icon: Shield, 
    description: 'Chart security validation',
    category: 'orchestration'
  },
]

interface DetectedTechStackProps {
  detectedStack?: string[]
}

export function DetectedTechStack({ detectedStack }: DetectedTechStackProps) {
  const categoryColors = {
    container: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
    orchestration: 'from-purple-500/20 to-indigo-500/20 border-purple-500/30',
    iac: 'from-orange-500/20 to-amber-500/20 border-orange-500/30',
    cicd: 'from-green-500/20 to-emerald-500/20 border-green-500/30',
    cloud: 'from-pink-500/20 to-rose-500/20 border-pink-500/30',
    database: 'from-yellow-500/20 to-amber-500/20 border-yellow-500/30',
  }

  const filteredTech = detectedStack 
    ? technologies.filter(t => detectedStack.includes(t.name))
    : technologies

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

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {filteredTech.map((tech, index) => {
          const Icon = tech.icon
          const colorClass = categoryColors[tech.category]
          
          return (
            <motion.div
              key={tech.name}
              className={cn(
                'group relative p-6 rounded-2xl bg-gradient-to-br border backdrop-blur-sm',
                'hover:shadow-xl transition-all duration-300 cursor-default',
                colorClass,
                'hover:border-white/30'
              )}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ scale: 1.05, y: -5 }}
            >
              {/* Glow effect on hover */}
              <div className={cn(
                'absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300',
                'bg-gradient-to-br', colorClass, 'blur-xl'
              )} />
              
              <div className="relative space-y-4">
                <div className={cn(
                  'p-3 rounded-xl w-fit bg-gradient-to-br border border-white/10',
                  colorClass
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

                {/* Category badge */}
                <div className="inline-flex px-2 py-1 rounded-full bg-white/10 text-xs text-muted-foreground capitalize">
                  {tech.category}
                </div>
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
            <CheckCircle className="h-4 w-4 text-green-400" />
            500+ Security Rules
          </span>
          <span className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-400" />
            CIS Benchmarks
          </span>
          <span className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-400" />
            OWASP Guidelines
          </span>
          <span className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-400" />
            Cloud Provider Best Practices
          </span>
        </div>
      </motion.div>
    </div>
  )
}

// Helper component for checkmark
function CheckCircle({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  )
}

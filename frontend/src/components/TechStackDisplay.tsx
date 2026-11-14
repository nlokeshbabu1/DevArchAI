import { motion } from 'framer-motion'
import { 
  Cloud, Server, GitBranch, Zap, Activity, 
  Settings, Database, Shield, CheckCircle,
  Layers, Box, Package
} from 'lucide-react'

import { cn } from '../lib/utils'

interface Technology {
  name: string
  category?: string
  subcategory?: string
  confidence?: number
  files_count?: number
  sample_files?: string[]
  cloud_provider?: string
}

interface TechStackDisplayProps {
  technologies: Technology[] | string[]  // Can be array of strings or Technology objects
}

const categoryIcons: Record<string, any> = {
  cloud: Cloud,
  iac: Layers,
  cicd: GitBranch,
  containers: Box,
  monitoring: Activity,
  config_management: Settings,
  security: Shield,
  database: Database,
}

const categoryColors: Record<string, string> = {
  cloud: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30 text-blue-400',
  iac: 'from-purple-500/20 to-indigo-500/20 border-purple-500/30 text-purple-400',
  cicd: 'from-orange-500/20 to-amber-500/20 border-orange-500/30 text-orange-400',
  containers: 'from-green-500/20 to-emerald-500/20 border-green-500/30 text-green-400',
  monitoring: 'from-red-500/20 to-pink-500/20 border-red-500/30 text-red-400',
  config_management: 'from-yellow-500/20 to-orange-500/20 border-yellow-500/30 text-yellow-400',
  security: 'from-indigo-500/20 to-purple-500/20 border-indigo-500/30 text-indigo-400',
  database: 'from-cyan-500/20 to-blue-500/20 border-cyan-500/30 text-cyan-400',
}

const techIcons: Record<string, any> = {
  aws: Cloud,
  azure: Cloud,
  gcp: Cloud,
  terraform: Layers,
  pulumi: Layers,
  cloudformation: Layers,
  github_actions: GitBranch,
  gitlab_ci: GitBranch,
  jenkins: GitBranch,
  circleci: GitBranch,
  azure_devops: GitBranch,
  docker: Box,
  docker_compose: Box,
  kubernetes: Package,
  helm: Package,
  prometheus: Activity,
  grafana: Activity,
  elk_stack: Activity,
  ansible: Settings,
}

const cloudProviderColors: Record<string, string> = {
  aws: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  azure: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  gcp: 'text-green-400 bg-green-500/10 border-green-500/30',
}

// Map technology names to categories
const techCategoryMap: Record<string, string> = {
  aws: 'cloud',
  azure: 'cloud',
  gcp: 'cloud',
  terraform: 'iac',
  pulumi: 'iac',
  github_actions: 'cicd',
  jenkins: 'cicd',
  gitlab_ci: 'cicd',
  docker: 'containers',
  kubernetes: 'containers',
  helm: 'containers',
  prometheus: 'monitoring',
  grafana: 'monitoring',
  ansible: 'config_management',
}

export function TechStackDisplay({ technologies }: TechStackDisplayProps) {
  if (!technologies || technologies.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Server className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>No technologies detected</p>
      </div>
    )
  }

  // Convert string array to Technology objects if needed
  const techObjects: Technology[] = technologies.map(tech => {
    if (typeof tech === 'string') {
      return {
        name: tech,
        category: techCategoryMap[tech] || 'containers',
        confidence: 0.95,
      }
    }
    return tech
  })

  // Group by category
  const grouped = techObjects.reduce((acc, tech) => {
    if (!tech.category) {return acc}
    if (!acc[tech.category]) {
      acc[tech.category] = []
    }
    acc[tech.category].push(tech)
    return acc
  }, {} as Record<string, Technology[]>)

  const categoryLabels: Record<string, string> = {
    cloud: 'Cloud Providers',
    iac: 'Infrastructure as Code',
    cicd: 'CI/CD',
    containers: 'Containers & Orchestration',
    monitoring: 'Monitoring & Observability',
    config_management: 'Configuration Management',
    security: 'Security',
    database: 'Databases',
  }

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([category, techs]) => {
        const CategoryIcon = categoryIcons[category] || Server
        const categoryColor = categoryColors[category] || categoryColors.containers

        return (
          <motion.div
            key={category}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3"
          >
            <div className="flex items-center gap-2">
              <CategoryIcon className="h-5 w-5 text-muted-foreground" />
              <h3 className="text-sm font-semibold text-foreground">
                {categoryLabels[category] || category}
              </h3>
              <span className="text-xs text-muted-foreground">
                ({techs.length})
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {techs.map((tech, index) => {
                const TechIcon = techIcons[tech.name] || CheckCircle
                const cloudColor = tech.cloud_provider ? cloudProviderColors[tech.cloud_provider] : null

                return (
                  <motion.div
                    key={tech.name}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.05 }}
                    className="group relative"
                  >
                    <div
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-lg border backdrop-blur-sm cursor-pointer transition-all duration-300',
                        'hover:scale-105 hover:shadow-lg',
                        cloudColor || categoryColor
                      )}
                    >
                      <TechIcon className="h-4 w-4" />
                      <span className="text-sm font-medium capitalize">
                        {tech.name.replace('_', ' ')}
                      </span>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

import { Box, ContainerIcon, GitBranch, Github, Layers, Cloud, Server, Shield, Hexagon, Settings } from 'lucide-react'
import { cn } from '../../lib/utils'

interface TechItem {
  name: string
  icon: React.ElementType
  category: string
}

const technologies: TechItem[] = [
  { name: 'Docker', icon: Box, category: 'Containers' },
  { name: 'Docker Compose', icon: Box, category: 'Containers' },
  { name: 'Podman', icon: ContainerIcon, category: 'Containers' },
  { name: 'Kubernetes', icon: Hexagon, category: 'Kubernetes' },
  { name: 'Helm', icon: Shield, category: 'Kubernetes' },
  { name: 'ArgoCD', icon: GitBranch, category: 'Kubernetes' },
  { name: 'OpenShift', icon: Cloud, category: 'Kubernetes' },
  { name: 'EKS', icon: Server, category: 'Kubernetes' },
  { name: 'AKS', icon: Server, category: 'Kubernetes' },
  { name: 'GKE', icon: Server, category: 'Kubernetes' },
  { name: 'GitHub Actions', icon: Github, category: 'CI/CD' },
  { name: 'Jenkins', icon: GitBranch, category: 'CI/CD' },
  { name: 'GitLab CI', icon: GitBranch, category: 'CI/CD' },
  { name: 'Azure DevOps', icon: GitBranch, category: 'CI/CD' },
  { name: 'Terraform', icon: Layers, category: 'Infrastructure' },
  { name: 'CloudFormation', icon: Layers, category: 'Infrastructure' },
  { name: 'Ansible', icon: Settings, category: 'Infrastructure' },
  { name: 'AWS', icon: Cloud, category: 'Cloud' },
]

function TechTile({ tech }: { tech: TechItem }) {
  const Icon = tech.icon
  return (
    <div className="flex items-center gap-3 px-6 py-3 rounded-xl bg-white/5 border border-white/10 hover:border-primary/30 hover:bg-white/10 transition-all duration-300 group">
      <div className="p-2 rounded-lg bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-white/10 group-hover:scale-110 transition-transform">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <span className="text-sm font-medium text-foreground whitespace-nowrap">{tech.name}</span>
    </div>
  )
}

export function TechnologyMarquee() {
  const allTechs = [...technologies, ...technologies, ...technologies]

  return (
    <section className="py-20 lg:py-32 overflow-hidden">
      <div className="container mx-auto px-4 mb-12">
        <div className="text-center space-y-4">
          <h2 className="text-4xl font-bold gradient-text">
            Scan Everything in Your DevOps Stack
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Comprehensive security scanning for containers, orchestrators, CI/CD pipelines, and cloud infrastructure
          </p>
        </div>
      </div>

      <div className="relative">
        <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-background to-transparent z-10 pointer-events-none" />
        <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-background to-transparent z-10 pointer-events-none" />

        <div className="flex gap-4 animate-marquee" style={{ width: 'max-content' }}>
          {allTechs.map((tech, index) => (
            <TechTile key={`${tech.name}-${index}`} tech={tech} />
          ))}
        </div>
      </div>
    </section>
  )
}
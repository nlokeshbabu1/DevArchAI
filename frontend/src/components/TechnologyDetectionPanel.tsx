/**
 * TechnologyDetectionPanel - Shows detected technologies during scan
 */

import { motion } from 'framer-motion'
import { cn } from '../lib/utils'
import { 
  CheckCircle, 
  Loader2, 
  Server, 
  Cloud, 
  Layers, 
  GitBranch,
  Activity,
  Shield
} from 'lucide-react'

interface TechnologyDetectionPanelProps {
  detectedTechnologies?: string[]
  isDetecting?: boolean
}

const techIcons: Record<string, any> = {
  docker: Server,
  kubernetes: Cloud,
  terraform: Layers,
  github_actions: GitBranch,
  cicd: Activity,
  helm: Shield,
  monitoring: Activity,
  prometheus: Activity,
  grafana: Cloud,
  ansible: Layers,
  pulumi: Cloud,
  security_scanning: Shield,
}

const techLabels: Record<string, string> = {
  docker: 'Docker',
  kubernetes: 'Kubernetes',
  terraform: 'Terraform',
  github_actions: 'GitHub Actions',
  cicd: 'CI/CD',
  helm: 'Helm',
  monitoring: 'Monitoring',
  prometheus: 'Prometheus',
  grafana: 'Grafana',
  ansible: 'Ansible',
  pulumi: 'Pulumi',
  security_scanning: 'Security Scanning',
}

export function TechnologyDetectionPanel({ 
  detectedTechnologies,
  isDetecting = false 
}: TechnologyDetectionPanelProps) {
  if (!detectedTechnologies && !isDetecting) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2 mb-4">
        {isDetecting ? (
          <Loader2 className="h-5 w-5 text-primary animate-spin" />
        ) : (
          <CheckCircle className="h-5 w-5 text-green-400" />
        )}
        <h3 className="text-lg font-semibold text-foreground">
          {isDetecting 
            ? 'Detecting Technologies...' 
            : 'Detected Technology Stack'}
        </h3>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {detectedTechnologies?.map((tech, index) => {
          const techKey = tech.toLowerCase().replace(/\s+/g, '_')
          const Icon = techIcons[techKey] || Server
          const label = techLabels[techKey] || tech

          return (
            <motion.div
              key={tech}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              className={cn(
                'flex items-center gap-2 px-4 py-3 rounded-xl border transition-all',
                'bg-green-500/10 border-green-500/30 text-green-400'
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm font-medium">{label}</span>
            </motion.div>
          )
        })}

        {isDetecting && (
          <>
            <motion.div
              initial={{ opacity: 0.5 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2 px-4 py-3 rounded-xl border border-white/10 bg-white/5"
            >
              <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
              <span className="text-sm text-muted-foreground">Scanning...</span>
            </motion.div>
          </>
        )}
      </div>
    </motion.div>
  )
}

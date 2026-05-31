import { motion } from 'framer-motion'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '../../lib/utils'
import { Github, Gitlab, Cloud, Server, Check, Loader2, Link as LinkIcon } from 'lucide-react'
import { Button } from '../../components/ui'
import { AnimatedCard } from '../../components/ui/animated-card'

interface Integration {
  id: string
  name: string
  description: string
  icon: React.ElementType
  status: 'connected' | 'disconnected' | 'connecting'
  features: string[]
}

const integrations: Integration[] = [
  {
    id: 'github',
    name: 'GitHub',
    description: 'Connect your GitHub repositories for automated scanning',
    icon: Github,
    status: 'connected',
    features: ['Auto-scan on push', 'PR comments', 'Status checks'],
  },
  {
    id: 'gitlab',
    name: 'GitLab',
    description: 'Integrate with GitLab CI/CD pipelines',
    icon: Gitlab,
    status: 'disconnected',
    features: ['CI/CD integration', 'MR comments', 'Pipeline status'],
  },
  {
    id: 'aws',
    name: 'AWS',
    description: 'Scan AWS infrastructure and CloudFormation templates',
    icon: Cloud,
    status: 'connected',
    features: ['Resource scanning', 'Compliance checks', 'Cost optimization'],
  },
  {
    id: 'azure',
    name: 'Azure',
    description: 'Connect Azure subscriptions for infrastructure analysis',
    icon: Server,
    status: 'disconnected',
    features: ['Resource scanning', 'Policy compliance', 'Security insights'],
  },
  {
    id: 'bitbucket',
    name: 'Bitbucket',
    description: 'Integrate with Bitbucket repositories',
    icon: LinkIcon,
    status: 'disconnected',
    features: ['PR scanning', 'Commit checks', 'Pipeline integration'],
  },
]

export function IntegrationsPage() {
  const [integrationState, setIntegrationState] = useState<Integration[]>(integrations)
  const navigate = useNavigate()

  const handleConnect = (id: string) => {
    if (id === 'aws') {
      navigate('/aws')
      return
    }
    setIntegrationState(prev =>
      prev.map(integration =>
        integration.id === id
          ? { ...integration, status: 'connecting' as const }
          : integration
      )
    )

    // Simulate connection
    setTimeout(() => {
      setIntegrationState(prev =>
        prev.map(integration =>
          integration.id === id
            ? { ...integration, status: 'connected' as const }
            : integration
        )
      )
    }, 2000)
  }

  const handleDisconnect = (id: string) => {
    setIntegrationState(prev =>
      prev.map(integration =>
        integration.id === id
          ? { ...integration, status: 'disconnected' as const }
          : integration
      )
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-foreground">Integrations</h1>
          <p className="text-muted-foreground mt-1">
            Connect your favorite tools and platforms
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl">
          <Check className="h-5 w-5 text-green-400" />
          <span className="text-sm font-medium text-foreground">
            {integrationState.filter(i => i.status === 'connected').length} connected
          </span>
        </div>
      </motion.div>

      {/* Integrations Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {integrationState.map((integration, index) => {
          const Icon = integration.icon
          return (
            <AnimatedCard key={integration.id} delay={index * 0.1}>
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                      <Icon className="h-6 w-6 text-foreground" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-foreground">{integration.name}</h3>
                      <div className={cn(
                        'flex items-center gap-1.5 text-xs',
                        integration.status === 'connected' && 'text-green-400',
                        integration.status === 'disconnected' && 'text-muted-foreground',
                        integration.status === 'connecting' && 'text-blue-400'
                      )}>
                        {integration.status === 'connected' && <Check className="h-3 w-3" />}
                        {integration.status === 'connecting' && <Loader2 className="h-3 w-3 animate-spin" />}
                        <span className="capitalize">{integration.status}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground">{integration.description}</p>

                <div className="space-y-2">
                  {integration.features.map(feature => (
                    <div key={feature} className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Check className="h-3 w-3 text-green-400" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>

                <div className="pt-4 border-t border-white/10">
                  {integration.status === 'connected' ? (
                    <Button
                      variant="secondary"
                      className="w-full"
                      onClick={() => handleDisconnect(integration.id)}
                    >
                      Disconnect
                    </Button>
                  ) : integration.status === 'connecting' ? (
                    <Button variant="primary" className="w-full" disabled>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Connecting...
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      className="w-full"
                      onClick={() => handleConnect(integration.id)}
                    >
                      Connect
                    </Button>
                  )}
                </div>
              </div>
            </AnimatedCard>
          )
        })}
      </div>

      {/* Coming Soon Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="p-6 bg-card/60 backdrop-blur-xl border border-white/10 rounded-2xl"
      >
        <h3 className="text-lg font-semibold text-foreground mb-2">More integrations coming soon</h3>
        <p className="text-muted-foreground">
          We're working on adding support for more platforms including GCP, Kubernetes, and more.
        </p>
      </motion.div>
    </div>
  )
}

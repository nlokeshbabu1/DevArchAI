import { motion } from 'framer-motion'
import { useState, useEffect, useCallback } from 'react'
import { cn } from '../../lib/utils'
import {
  Github, Gitlab, Cloud, Server, Link as LinkIcon,
  RefreshCw, Shield, Check, ExternalLink, AlertTriangle,
  Plug, Loader2
} from 'lucide-react'
import { Button } from '../../components/ui'
import { AnimatedCard } from '../../components/ui/animated-card'
import { AwsConnectModal } from '../../components/integrations/AwsConnectModal'
import { AzureConnectModal } from '../../components/integrations/AzureConnectModal'
import { integrationsApi, type IntegrationInfo } from '../../api/endpoints/integrations'
import { useAuthStore } from '../../stores/auth-store'

const ICON_MAP: Record<string, React.ElementType> = {
  github: Github,
  gitlab: Gitlab,
  cloud: Cloud,
  server: Server,
  link: LinkIcon,
}

const STATUS_CONFIG = {
  connected: {
    label: 'Connected',
    dotClass: 'bg-green-400 shadow-[0_0_6px_rgba(34,197,94,0.6)]',
    badgeClass: 'bg-green-500/10 text-green-400 border-green-500/30',
    animate: { scale: [1, 1.3, 1], opacity: [1, 0.7, 1] },
  },
  not_connected: {
    label: 'Not Connected',
    dotClass: 'bg-gray-500',
    badgeClass: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
    animate: undefined,
  },
  connecting: {
    label: 'Connecting',
    dotClass: 'bg-blue-400 shadow-[0_0_6px_rgba(59,130,246,0.6)]',
    badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    animate: { scale: [1, 1.3, 1], opacity: [1, 0.7, 1] },
  },
  pending_verification: {
    label: 'Pending Verification',
    dotClass: 'bg-yellow-400 shadow-[0_0_6px_rgba(234,179,8,0.6)]',
    badgeClass: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    animate: { rotate: [0, 360] },
  },
  connection_error: {
    label: 'Connection Error',
    dotClass: 'bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.6)]',
    badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',
    animate: { scale: [1, 1.2, 1], opacity: [1, 0.6, 1] },
  },
}

function StatusDot({ status }: { status: string }) {
  const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG]
  if (!config) return null

  return (
    <motion.span
      className={cn('inline-block h-2 w-2 rounded-full flex-shrink-0', config.dotClass)}
      animate={config.animate ?? undefined}
      transition={config.animate ? { duration: 1.5, repeat: Infinity, ease: 'easeInOut' } : undefined}
    />
  )
}

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG]
  if (!config) return null

  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border', config.badgeClass)}>
      <StatusDot status={status} />
      {config.label}
    </span>
  )
}

function IntegrationCard({
  integration,
  onRefresh,
  onConnect,
  connecting,
}: {
  integration: IntegrationInfo
  onRefresh: () => void
  onConnect: () => void
  connecting: boolean
}) {
  const Icon = ICON_MAP[integration.icon] || LinkIcon
  const isConnected = integration.status === 'connected'
  const isConnecting = integration.status === 'connecting' || connecting
  const isError = integration.status === 'connection_error'
  const isNotConnected = integration.status === 'not_connected'

  return (
    <AnimatedCard>
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-white/5 rounded-xl border border-white/10">
              <Icon className="h-6 w-6 text-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">{integration.label}</h3>
              <StatusBadge status={isConnecting ? 'connecting' : integration.status} />
            </div>
          </div>
        </div>

        <p className="text-sm text-muted-foreground">{integration.description}</p>

        {/* Features */}
        <div className="grid grid-cols-2 gap-1.5">
          {integration.features.map((feature) => (
            <div key={feature} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Check className={cn(
                'h-3 w-3 flex-shrink-0',
                isConnected ? 'text-green-400' : 'text-gray-600'
              )} />
              <span>{feature}</span>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="pt-4 border-t border-white/10">
          {isConnected && (
            <div className="flex gap-2">
              <Button variant="secondary" className="flex-1" disabled>
                Disconnect
              </Button>
              <Button variant="secondary" className="flex-1" onClick={onRefresh}>
                <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                Refresh
              </Button>
            </div>
          )}
          {isError && (
            <div className="space-y-2">
              <Button
                variant="secondary"
                className="w-full text-red-400 border-red-500/30 hover:bg-red-500/10"
                onClick={onRefresh}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry Connection
              </Button>
              <p className="text-[10px] text-center text-red-400/70">
                Unable to verify connection status
              </p>
            </div>
          )}
          {(isNotConnected) && (
            <Button
              variant="primary"
              className="w-full"
              onClick={onConnect}
              disabled={isConnecting}
            >
              {isConnecting ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Connecting...</>
              ) : (
                <><Plug className="h-4 w-4 mr-2" /> Connect {integration.label}</>
              )}
            </Button>
          )}
        </div>
      </div>
    </AnimatedCard>
  )
}

export function IntegrationsPage() {
  const { user } = useAuthStore()
  const [integrations, setIntegrations] = useState<IntegrationInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null)
  const [awsModalOpen, setAwsModalOpen] = useState(false)
  const [azureModalOpen, setAzureModalOpen] = useState(false)

  const authProvider = (user?.provider || 'email') as 'github' | 'gitlab' | 'email'

  const load = useCallback(async () => {
    setLoading(true)
    const result = await integrationsApi.getStatus({ authProvider })
    setIntegrations(result)
    setLoading(false)
  }, [authProvider])

  useEffect(() => {
    load()
  }, [load])

  const handleRefresh = useCallback(() => {
    load()
  }, [load])

  const handleConnect = useCallback((integration: IntegrationInfo) => {
    if (integration.connectType === 'oauth' && integration.connectUrl) {
      setConnectingProvider(integration.provider)
      window.location.href = integration.connectUrl
    } else if (integration.modalType === 'aws') {
      setAwsModalOpen(true)
    } else if (integration.modalType === 'azure') {
      setAzureModalOpen(true)
    }
  }, [])

  const connectedCount = integrations.filter(i => i.status === 'connected').length
  const errorCount = integrations.filter(i => i.status === 'connection_error').length
  const availableCount = integrations.length - connectedCount - errorCount

  return (
    <div className="space-y-6">
      <AwsConnectModal open={awsModalOpen} onClose={() => { setAwsModalOpen(false); handleRefresh() }} />
      <AzureConnectModal open={azureModalOpen} onClose={() => { setAzureModalOpen(false); handleRefresh() }} />

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Integrations</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Connect your tools and infrastructure
          </p>
        </div>

        {!loading && (
          <div className="flex items-center gap-2">
            {errorCount > 0 && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400">
                <AlertTriangle className="h-3 w-3" />
                {errorCount} {errorCount === 1 ? 'error' : 'errors'}
              </span>
            )}
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/30 text-xs text-green-400">
              <Check className="h-3 w-3" />
              {connectedCount} connected
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-muted-foreground">
              {availableCount} available
            </span>
          </div>
        )}
      </motion.div>

      {/* Loading */}
      {loading && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 p-6 animate-pulse space-y-4"
            >
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-xl bg-white/10" />
                <div className="space-y-2">
                  <div className="h-4 w-20 bg-white/10 rounded" />
                  <div className="h-3 w-24 bg-white/5 rounded" />
                </div>
              </div>
              <div className="h-3 w-3/4 bg-white/5 rounded" />
              <div className="grid grid-cols-2 gap-2">
                <div className="h-3 w-full bg-white/5 rounded" />
                <div className="h-3 w-full bg-white/5 rounded" />
              </div>
              <div className="h-9 w-full bg-white/5 rounded-lg" />
            </div>
          ))}
        </div>
      )}

      {/* Integrations Grid */}
      {!loading && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {integrations.map((integration) => (
            <IntegrationCard
              key={integration.provider}
              integration={integration}
              onRefresh={handleRefresh}
              onConnect={() => handleConnect(integration)}
              connecting={connectingProvider === integration.provider}
            />
          ))}
        </div>
      )}

      {/* Coming Soon */}
      {!loading && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.5 }}
          className="p-5 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10"
        >
          <h3 className="text-sm font-semibold text-foreground mb-1">Coming Soon</h3>
          <p className="text-xs text-muted-foreground">
            GCP, Kubernetes, Slack, Jira, and PagerDuty integrations are in development.
          </p>
        </motion.div>
      )}
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Search, Plug, Settings, RefreshCw, Grid3x3 } from 'lucide-react'
import type { ConnectionStatus } from '@/components/integrations/types'

import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth-store'
import { integrationsApi, type IntegrationInfo } from '@/api/endpoints/integrations'
import { cloudApi } from '@/api/endpoints/cloud'
import { kubernetesApi, type KubernetesInfo } from '@/api/endpoints/kubernetes'
import { toast } from '@/hooks/useToast'
import { AwsOnboardingWizard } from '@/components/integrations/AwsOnboardingWizard'
import { KubernetesConnectModal } from '@/components/integrations/KubernetesConnectModal'
import { EksConnectModal } from '@/components/integrations/EksConnectModal'
import { ProviderManageModal } from '@/components/integrations/ProviderManageModal'
import { CloudDashboard } from '@/pages/cloud/CloudDashboard'
import { IntegrationCategory } from '@/components/integrations/IntegrationCategory'
import { buildCategories } from '@/components/integrations/providers'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusBadge } from '@/components/ui/StatusBadge'

type ViewMode = 'grid' | 'cloud-dashboard'

const OAUTH_PROVIDERS = ['github', 'gitlab'] as const
const COMING_SOON_PROVIDERS = ['azure', 'gcp', 'aks', 'gke', 'bitbucket', 'slack', 'teams', 'discord', 'pagerduty']

interface ManageTarget {
  id: string
  name: string
  account?: string
}

export function IntegrationsPage() {
  const { user } = useAuthStore()
  const [view, setView] = useState<ViewMode>('grid')
  const [integrations, setIntegrations] = useState<IntegrationInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [awsModalOpen, setAwsModalOpen] = useState(false)
  const [kubeModalOpen, setKubeModalOpen] = useState(false)
  const [eksModalOpen, setEksModalOpen] = useState(false)
  const [manageTarget, setManageTarget] = useState<ManageTarget | null>(null)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [pending, setPending] = useState<Record<string, ConnectionStatus>>({})
  const [kubeConnections, setKubeConnections] = useState<KubernetesInfo[]>([])
  const [awsConnection, setAwsConnection] = useState<{
    connected: boolean
    accountId?: string
    resourceCount?: number
    securityScore?: number
    lastScan?: string
  }>({ connected: false })
  const [error, setError] = useState<string | null>(null)
  const [autoScanConnectionId, setAutoScanConnectionId] = useState<string | null>(null)

  const authProvider = (user?.provider || 'email') as 'github' | 'gitlab' | 'email'

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await integrationsApi.getStatus({ authProvider })
      setIntegrations(result)
    } catch {
      setError('Failed to load integration status')
    }

    try {
      const connections = await cloudApi.connections()
      const awsConn = connections.find((c) => c.provider === 'aws')
      if (awsConn) {
        setAwsConnection({
          connected: true,
          accountId: awsConn.account_id,
          resourceCount: awsConn.resource_count ?? undefined,
          securityScore: awsConn.security_score ?? undefined,
          lastScan: awsConn.last_scanned_at ? formatTimeAgo(awsConn.last_scanned_at) : undefined,
        })
      } else {
        setAwsConnection({ connected: false })
      }
    } catch {
      setAwsConnection({ connected: false })
    }

    try {
      const kube = await kubernetesApi.list()
      setKubeConnections(kube)
    } catch {
      setKubeConnections([])
    }

    setLoading(false)
  }, [authProvider])

  useEffect(() => {
    load()
  }, [load])

  const getStatus = (provider: string): ConnectionStatus => {
    const integration = integrations.find((i) => i.provider === provider)
    return (integration?.status as ConnectionStatus) || 'not_connected'
  }

  const getCardStatus = (provider: string): ConnectionStatus => {
    if (pending[provider]) return pending[provider]
    return getStatus(provider)
  }

  const kubernetesConnected = getStatus('kubernetes') === 'connected'
  const eksConnected = getStatus('eks') === 'connected'

  const kubernetesAccount = kubernetesConnected
    ? kubeConnections.find((c) => c.kind === 'generic' && c.is_active)?.cluster_name
      || kubeConnections.find((c) => c.kind === 'generic' && c.is_active)?.name
    : undefined
  const eksAccount = eksConnected
    ? kubeConnections.find((c) => c.kind === 'eks' && c.is_active)?.cluster_name
      || kubeConnections.find((c) => c.kind === 'eks' && c.is_active)?.name
    : undefined

  const activeGeneric = kubeConnections.find((c) => c.kind === 'generic' && c.is_active)
  const activeEks = kubeConnections.find((c) => c.kind === 'eks' && c.is_active)

  const toConnMeta = (c: typeof activeGeneric) =>
    c
      ? {
          id: c.id,
          version: c.kubernetes_version,
          healthStatus: c.health_status || c.status,
          lastVerified: c.last_verified_at ? formatTimeAgo(c.last_verified_at) : undefined,
          nodeCount: c.node_count,
          podCount: c.pod_count,
          serviceCount: c.service_count,
          namespaceCount: c.namespace_count,
          deploymentCount: c.deployment_count,
          ingressCount: c.ingress_count,
        }
      : undefined

  const categories = buildCategories({
    githubStatus: getCardStatus('github'),
    gitlabStatus: getCardStatus('gitlab'),
    bitbucketStatus: getCardStatus('bitbucket'),
    awsStatus: awsConnection.connected ? 'connected' : getCardStatus('aws'),
    kubernetesStatus: getCardStatus('kubernetes'),
    eksStatus: getCardStatus('eks'),
    kubernetesAccount,
    eksAccount,
    kubernetesConnection: toConnMeta(activeGeneric),
    eksConnection: toConnMeta(activeEks),
    awsAccountId: awsConnection.accountId,
    awsResourceCount: awsConnection.resourceCount,
    awsSecurityScore: awsConnection.securityScore,
    awsLastScan: awsConnection.lastScan,
    onConnect: handleConnect,
    onManage: handleManage,
    onNotify: handleNotify,
  })

  const filteredCategories = categories.map((cat) => ({
    ...cat,
    providers: cat.providers.filter(
      (p) =>
        !searchQuery ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.description.toLowerCase().includes(searchQuery.toLowerCase()),
    ),
  })).filter((cat) => cat.providers.length > 0)

  const totalConnected = categories.reduce(
    (sum, cat) => sum + cat.providers.filter((p) => p.status === 'connected').length,
    0,
  )
  const totalProviders = categories.reduce((sum, cat) => sum + cat.providers.length, 0)

  async function startOAuth(id: 'github' | 'gitlab') {
    setPending((p) => ({ ...p, [id]: 'connecting' }))
    try {
      const res = await integrationsApi.getOAuthUrl(id)
      if (res.oauth_url) {
        window.location.href = res.oauth_url
      } else {
        setPending((p) => ({ ...p, [id]: 'error' }))
        toast.error(res.error || `Unable to start ${id === 'github' ? 'GitHub' : 'GitLab'} connection`)
        setTimeout(() => setPending((p) => ({ ...p, [id]: 'not_connected' })), 2000)
      }
    } catch (err: any) {
      setPending((p) => ({ ...p, [id]: 'error' }))
      toast.error(err.response?.data?.detail || err.message || `Failed to start ${id} connection`)
      setTimeout(() => setPending((p) => ({ ...p, [id]: 'not_connected' })), 2000)
    }
  }

  function handleConnect(id: string) {
    if ((OAUTH_PROVIDERS as readonly string[]).includes(id)) {
      startOAuth(id as 'github' | 'gitlab')
      return
    }
    if (id === 'aws') {
      setAwsModalOpen(true)
      return
    }
    if (id === 'kubernetes') {
      setKubeModalOpen(true)
      return
    }
    if (id === 'eks') {
      setEksModalOpen(true)
      return
    }
    if ((COMING_SOON_PROVIDERS as readonly string[]).includes(id)) {
      toast.info('This integration is coming soon')
      return
    }
  }

  function handleManage(id: string) {
    if (id === 'aws') {
      setView('cloud-dashboard')
      return
    }
    if (id === 'github' || id === 'gitlab') {
      setManageTarget({ id, name: id === 'github' ? 'GitHub' : 'GitLab' })
      return
    }
    if (id === 'kubernetes') {
      setManageTarget({ id, name: 'Kubernetes', account: kubernetesAccount })
      return
    }
    if (id === 'eks') {
      setManageTarget({ id, name: 'EKS', account: eksAccount })
      return
    }
  }

  function handleNotify(id: string) {
    toast.info('Notification settings coming soon')
  }

  const handleDisconnected = () => {
    setPending({})
    load()
    toast.success('Integration disconnected')
  }

  return (
    <div className="space-y-6">
      <AwsOnboardingWizard
        open={awsModalOpen}
        onClose={() => setAwsModalOpen(false)}
        onComplete={(data) => {
          setAwsModalOpen(false)
          load()
          if (data?.action === 'scan' && data.connectionId) {
            setAutoScanConnectionId(data.connectionId)
            setView('cloud-dashboard')
          } else if (data?.action === 'dashboard') {
            setView('cloud-dashboard')
          }
        }}
      />

      <KubernetesConnectModal
        open={kubeModalOpen}
        onClose={() => setKubeModalOpen(false)}
        onConnected={() => {
          load()
          toast.success('Kubernetes cluster connected')
        }}
      />

      <EksConnectModal
        open={eksModalOpen}
        onClose={() => setEksModalOpen(false)}
        onConnected={() => {
          load()
          toast.success('EKS cluster connected')
        }}
        onNeedAws={() => setAwsModalOpen(true)}
      />

      <ProviderManageModal
        open={!!manageTarget}
        onClose={() => setManageTarget(null)}
        providerId={manageTarget?.id || ''}
        providerName={manageTarget?.name || ''}
        account={manageTarget?.account}
        onDisconnected={handleDisconnected}
      />

      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30"
        >
          <span className="text-sm text-red-200">{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      <PageHeader
        title="Integrations"
        description="Connect source control, CI/CD, and cloud providers for automated security scanning"
        actions={
          <>
            {view === 'cloud-dashboard' && (
              <button
                type="button"
                onClick={() => setView('grid')}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all"
              >
                <Grid3x3 className="h-4 w-4" />
                All Integrations
              </button>
            )}
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all"
            >
              <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
              Refresh
            </button>
          </>
        }
      />

      {/* Stats bar */}
      {view === 'grid' && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex items-center gap-6 px-4 py-3 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10"
        >
          <div className="flex items-center gap-2">
            <Plug className="h-4 w-4 text-emerald-400" />
            <span className="text-xs text-muted-foreground">Connected</span>
            <StatusBadge status="connected" label={`${totalConnected} active`} />
          </div>
          <div className="h-4 w-px bg-white/10" />
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Total</span>
            <span className="text-sm font-semibold text-foreground">{totalProviders}</span>
          </div>
          <div className="flex-1" />
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search integrations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-white/20 transition-all w-56"
            />
          </div>
        </motion.div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-8">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-4">
              <div className="h-8 w-48 rounded-xl bg-card/60 backdrop-blur-xl border border-white/10 animate-pulse" />
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {[...Array(4)].map((_, j) => (
                  <div key={j} className="h-44 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 animate-pulse" />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Cloud Dashboard view */}
      {!loading && view === 'cloud-dashboard' && (
        <CloudDashboard
          isConnected={awsConnection.connected}
          onConnect={() => setAwsModalOpen(true)}
          onRefresh={load}
          autoScanConnectionId={autoScanConnectionId}
          onAutoScanComplete={() => setAutoScanConnectionId(null)}
        />
      )}

      {/* Categories grid view */}
      {!loading && view === 'grid' && (
        <div className="space-y-8">
          {filteredCategories.map((category) => (
            <IntegrationCategory
              key={category.id}
              category={category}
              onConnect={handleConnect}
              onManage={handleManage}
            />
          ))}

          {filteredCategories.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-24 text-center"
            >
              <Search className="h-8 w-8 text-muted-foreground/40 mb-3" />
              <h3 className="text-sm font-medium text-foreground mb-1">No integrations found</h3>
              <p className="text-xs text-muted-foreground">
                Try a different search term
              </p>
            </motion.div>
          )}
        </div>
      )}
    </div>
  )
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

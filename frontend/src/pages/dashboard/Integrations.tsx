import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Search, Plug, Settings, RefreshCw, Grid3x3 } from 'lucide-react'
import type { ConnectionStatus } from '@/components/integrations/types'

import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth-store'
import { integrationsApi, type IntegrationInfo } from '@/api/endpoints/integrations'
import { cloudApi } from '@/api/endpoints/cloud'
import { AwsOnboardingWizard } from '@/components/integrations/AwsOnboardingWizard'
import { CloudDashboard } from '@/pages/cloud/CloudDashboard'
import { IntegrationCategory } from '@/components/integrations/IntegrationCategory'
import { buildCategories } from '@/components/integrations/providers'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusBadge } from '@/components/ui/StatusBadge'

type ViewMode = 'grid' | 'cloud-dashboard'

export function IntegrationsPage() {
  const { user } = useAuthStore()
  const [view, setView] = useState<ViewMode>('grid')
  const [integrations, setIntegrations] = useState<IntegrationInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [awsModalOpen, setAwsModalOpen] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
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

    setLoading(false)
  }, [authProvider])

  useEffect(() => {
    load()
  }, [load])

  const getStatus = (provider: string): ConnectionStatus => {
    const integration = integrations.find((i) => i.provider === provider)
    return (integration?.status as ConnectionStatus) || 'not_connected'
  }

  const categories = buildCategories({
    githubStatus: getStatus('github'),
    gitlabStatus: getStatus('gitlab'),
    bitbucketStatus: getStatus('bitbucket'),
    awsStatus: awsConnection.connected ? 'connected' : getStatus('aws'),
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

  function handleConnect(id: string) {
    if (id === 'aws') setAwsModalOpen(true)
  }

  function handleManage(id: string) {
    if (id === 'aws') setView('cloud-dashboard')
  }

  function handleNotify(id: string) {
    // Future: notification settings
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

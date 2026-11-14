import { motion } from 'framer-motion'
import { Cloud, Plus, RefreshCw, ChevronRight, ShieldCheck, Clock } from 'lucide-react'
import { useState, useCallback, useEffect } from 'react'

import { cloudApi, type CloudConnection } from '@/api/endpoints/cloud'
import { AwsOnboardingWizard } from '@/components/integrations/AwsOnboardingWizard'
import { cn } from '@/lib/utils'
import { CloudDashboard } from '@/pages/cloud/CloudDashboard'

interface CloudAccount {
  provider: 'aws' | 'azure' | 'gcp'
  label: string
  description: string
  comingSoon?: boolean
}

const AVAILABLE_PROVIDERS: CloudAccount[] = [
  { provider: 'aws', label: 'AWS', description: 'Cloud posture, IAM analysis, inventory, compliance and cost optimization.' },
  { provider: 'azure', label: 'Azure', description: 'Resource scanning, policy compliance, Defender for Cloud.' , comingSoon: true },
  { provider: 'gcp', label: 'Google Cloud', description: 'Security Command Center, Cloud Asset Inventory scanning.', comingSoon: true },
]

function maskAccount(id: string): string {
  if (!id) {return '—'}
  if (id.length <= 4) {return `****${id}`}
  return `****${id.slice(-4)}`
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) {return 'just now'}
  if (mins < 60) {return `${mins}m ago`}
  const hours = Math.floor(mins / 60)
  if (hours < 24) {return `${hours}h ago`}
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function healthOf(conn: CloudConnection): { label: string; ok: boolean } {
  if (conn.scan_status === 'failed') {return { label: 'Degraded', ok: false }}
  if (conn.status === 'active') {return { label: 'Healthy', ok: true }}
  return { label: 'Unknown', ok: false }
}

interface CloudAccountsProps {
  provider?: 'aws' | 'azure' | 'gcp'
  title: string
  description: string
}

export function CloudAccounts({ provider = 'aws', title, description }: CloudAccountsProps) {
  const [connections, setConnections] = useState<CloudConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    setRefreshing(true)
    try {
      const conns = await cloudApi.connections()
      const filtered = provider ? conns.filter((c) => c.provider === provider) : conns
      setConnections(filtered)
      setSelectedId((current) => current && filtered.some((c) => c.id === current) ? current : (filtered[0]?.id || null))
      if (!filtered.length) {setSelectedId(null)}
    } catch {
      setError('Unable to load cloud connection status.')
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }, [provider])

  useEffect(() => {
    setLoading(true)
    load()
  }, [load])

  const selected = connections.find((c) => c.id === selectedId) || null

  return (
    <div className="space-y-6">
      <AwsOnboardingWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onComplete={() => {
          setWizardOpen(false)
          load()
        }}
      />

      {/* Stats bar */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-6 px-4 py-3 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Connected</span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {connections.length} active
          </span>
        </div>
        <div className="h-4 w-px bg-white/10" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Provider</span>
          <span className="text-sm font-semibold text-foreground">{title}</span>
        </div>
        <div className="flex-1" />
        <button
          type="button"
          onClick={load}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')} />
          Refresh
        </button>
      </motion.div>

      {/* Error */}
      {error && (
        <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30">
          <span className="text-sm text-red-200">{error}</span>
          <button
            onClick={load}
            className="text-xs font-medium text-red-400 hover:text-red-300 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-6">
          <div className="h-44 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 animate-pulse" />
          <div className="h-96 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 animate-pulse" />
        </div>
      )}

      {!loading && (
        <>
          {/* Account cards */}
          <div>
            <h2 className="text-base font-semibold text-foreground mb-3">Accounts</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {connections.map((conn, index) => {
                const health = healthOf(conn)
                return (
                  <motion.button
                    key={conn.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05, duration: 0.3 }}
                    type="button"
                    onClick={() => setSelectedId(conn.id)}
                    className={cn(
                      'relative text-left rounded-2xl border p-5 transition-all duration-200 group',
                      'bg-card/60 backdrop-blur-xl border-white/10 hover:border-emerald-500/30 hover:shadow-lg hover:shadow-black/20',
                      selected?.id === conn.id && 'ring-2 ring-emerald-500/40 border-emerald-500/30',
                    )}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/20">
                          <Cloud className="h-5 w-5 text-amber-400" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-foreground">{conn.connection_name || 'AWS'}</p>
                          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Connected</p>
                        </div>
                      </div>
                      <span className={cn('inline-flex items-center gap-1 text-[10px] font-medium', health.ok ? 'text-emerald-400' : 'text-red-400')}>
                        <span className={cn('h-1.5 w-1.5 rounded-full', health.ok ? 'bg-emerald-400' : 'bg-red-400')} />
                        {health.label}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Account</span>
                        <span className="font-mono font-medium text-foreground">{maskAccount(conn.account_id)}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Region</span>
                        <span className="font-medium text-foreground">{conn.regions?.[0] || '—'}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Resources</span>
                        <span className="font-medium text-foreground">{conn.resource_count?.toLocaleString() || '—'}</span>
                      </div>
                    </div>

                    <div className="mt-4 flex items-center justify-between">
                      <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {conn.last_scanned_at ? `Last validated ${formatTimeAgo(conn.last_scanned_at)}` : 'Not scanned yet'}
                      </span>
                      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-emerald-400">
                        View Details <ChevronRight className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </motion.button>
                )
              })}

              {/* Connect card */}
              <motion.button
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: connections.length * 0.05, duration: 0.3 }}
                type="button"
                onClick={() => setWizardOpen(true)}
                className="flex flex-col items-center justify-center gap-3 min-h-[220px] rounded-2xl border border-dashed border-white/15 hover:border-white/30 text-muted-foreground hover:text-foreground bg-white/5 hover:bg-white/10 transition-all"
              >
                <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-white/5 border border-white/10">
                  <Plus className="h-5 w-5" />
                </div>
                <span className="text-sm font-medium">Connect {provider === 'aws' ? 'AWS' : 'Account'}</span>
              </motion.button>

              {/* Coming soon providers */}
              {AVAILABLE_PROVIDERS.filter((p) => p.provider !== provider).map((p) => (
                <div
                  key={p.provider}
                  className="flex flex-col justify-center rounded-2xl border border-white/5 bg-white/[0.02] p-5 opacity-60"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Cloud className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-muted-foreground">{p.label}</span>
                  </div>
                  <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-300">
                    Coming Soon
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Detail / empty state */}
          {connections.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-24 text-center"
            >
              <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 mb-4">
                <Cloud className="h-10 w-10 text-amber-400" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-1">No {title} account connected</h3>
              <p className="text-sm text-muted-foreground max-w-sm mb-6">
                {description}
              </p>
              <button
                type="button"
                onClick={() => setWizardOpen(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold transition-all"
              >
                <Plus className="h-4 w-4" />
                Connect {provider === 'aws' ? 'AWS' : 'Account'}
              </button>
            </motion.div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <h2 className="text-base font-semibold text-foreground">Cloud Security</h2>
                <span className="text-xs text-muted-foreground">Posture · IAM · Inventory · Compliance · Cost</span>
              </div>
              <CloudDashboard
                isConnected
                onConnect={() => setWizardOpen(true)}
                onRefresh={load}
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}

import { motion } from 'framer-motion'
import { Container, RefreshCw, Loader2, ArrowRight } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { kubernetesApi, type KubernetesInfo } from '@/api/endpoints/kubernetes'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { cn } from '@/lib/utils'

function formatTimeAgo(dateStr?: string | null): string {
  if (!dateStr) {return 'never'}
  const diff = Date.now() - new Date(dateStr).getTime()
  const secs = Math.floor(diff / 1000)
  if (secs < 60) {return `${secs}s ago`}
  const mins = Math.floor(secs / 60)
  if (mins < 60) {return `${mins}m ago`}
  const hours = Math.floor(mins / 60)
  if (hours < 24) {return `${hours}h ago`}
  return `${Math.floor(hours / 24)}d ago`
}

function healthLabel(status?: string | null): string {
  switch (status) {
    case 'connected': return 'Healthy'
    case 'degraded': return 'Degraded'
    case 'permission_denied': return 'Permission Denied'
    case 'auth_failed': return 'Auth Failed'
    case 'unreachable': return 'Unreachable'
    case 'expired': return 'Expired'
    default: return status || 'Unknown'
  }
}

function providerLabel(conn: KubernetesInfo): string {
  if (conn.kind === 'eks') {return 'AWS EKS'}
  return 'Kubernetes'
}

function ClusterCard({ conn, index }: { conn: KubernetesInfo; index: number }) {
  const health = conn.health_status || conn.status

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-5 hover:border-emerald-500/20 transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-base font-semibold text-foreground">{conn.cluster_name || conn.name}</h3>
          <p className="text-xs text-muted-foreground mt-0.5">{providerLabel(conn)}</p>
        </div>
        <StatusBadge
          status={health === 'connected' ? 'connected' : health === 'degraded' ? 'pending' : 'failed'}
          label={healthLabel(health)}
        />
      </div>

      <div className="text-sm text-muted-foreground mb-3">
        {conn.kubernetes_version || 'Version unknown'}
      </div>

      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="rounded-lg bg-white/5 border border-white/5 px-2 py-1.5 text-center">
          <div className="text-[10px] text-muted-foreground">Nodes</div>
          <div className="text-sm font-semibold">{conn.node_count ?? '—'}</div>
        </div>
        <div className="rounded-lg bg-white/5 border border-white/5 px-2 py-1.5 text-center">
          <div className="text-[10px] text-muted-foreground">Pods</div>
          <div className="text-sm font-semibold">{conn.pod_count ?? '—'}</div>
        </div>
        <div className="rounded-lg bg-white/5 border border-white/5 px-2 py-1.5 text-center">
          <div className="text-[10px] text-muted-foreground">Services</div>
          <div className="text-sm font-semibold">{conn.service_count ?? '—'}</div>
        </div>
      </div>

      <p className="text-[10px] text-muted-foreground mb-4">
        Last verified {formatTimeAgo(conn.last_verified_at)}
      </p>

      <Link
        to={`/kubernetes/${conn.id}`}
        className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition-all"
      >
        Open Cluster
        <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </motion.div>
  )
}

export function KubernetesWorkspacePage() {
  const [connections, setConnections] = useState<KubernetesInfo[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const all = await kubernetesApi.list()
      setConnections(all.filter((c) => c.is_active))
    } catch {
      setConnections([])
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Kubernetes"
        description="Connected clusters — security, health, and AI analysis"
        actions={
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all"
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
            Refresh
          </button>
        }
      />

      {loading && (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && connections.length === 0 && (
        <div className="rounded-2xl border border-white/10 bg-card/60 p-12 text-center">
          <Container className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
          <h3 className="text-sm font-medium text-foreground mb-1">No clusters connected</h3>
          <p className="text-xs text-muted-foreground mb-4">
            Connect a Kubernetes or EKS cluster from the Integrations page.
          </p>
          <Link
            to="/integrations"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
          >
            Go to Integrations
          </Link>
        </div>
      )}

      {!loading && connections.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-foreground mb-3">Connected Clusters</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {connections.map((conn, i) => (
              <ClusterCard key={conn.id} conn={conn} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

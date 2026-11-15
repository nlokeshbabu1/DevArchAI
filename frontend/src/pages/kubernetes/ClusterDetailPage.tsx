import { motion } from 'framer-motion'
import {
  Container, RefreshCw, Loader2, Shield, Brain, Activity,
  ChevronLeft, AlertTriangle, Server, Box,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'


import { kubernetesApi, type ClusterAIJob, type KubernetesInfo } from '@/api/endpoints/kubernetes'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { cn } from '@/lib/utils'

import { AICopilotPanel } from './components/AICopilotPanel'
import { VersionAdvisorPanel } from './components/VersionAdvisorPanel'

type Tab = 'overview' | 'nodes' | 'pods' | 'namespaces' | 'deployments' | 'services' | 'ingress' | 'events' | 'security' | 'health' | 'version' | 'ai'

const RUNNING_AI_STATUSES = new Set(['queued', 'running', 'collecting', 'checking_cache', 'rag_retrieving', 'mcp_retrieving', 'generating'])

function formatTimeAgo(dateStr?: string | null): string {
  if (!dateStr) {return 'never'}
  const diff = Date.now() - new Date(dateStr).getTime()
  const secs = Math.floor(diff / 1000)
  if (secs < 60) {return `${secs}s ago`}
  const mins = Math.floor(secs / 60)
  if (mins < 60) {return `${mins}m ago`}
  return `${Math.floor(mins / 60)}h ago`
}

function StatCard({ title, value, subtitle }: { title: string; value: string | number; subtitle?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-card/60 p-4">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">{title}</div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
    </div>
  )
}

export function ClusterDetailPage() {
  const { connectionId } = useParams<{ connectionId: string }>()
  const [connection, setConnection] = useState<KubernetesInfo | null>(null)
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null)
  const [healthScore, setHealthScore] = useState<Record<string, unknown> | null>(null)
  const [nodes, setNodes] = useState<Record<string, unknown>[]>([])
  const [pods, setPods] = useState<Record<string, unknown>[]>([])
  const [events, setEvents] = useState<Record<string, unknown>[]>([])
  const [securityFindings, setSecurityFindings] = useState<Record<string, unknown>[]>([])
  const [versionAdvisor, setVersionAdvisor] = useState<Record<string, unknown> | null>(null)
  const [aiJob, setAiJob] = useState<ClusterAIJob | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [namespaces, setNamespaces] = useState<Record<string, unknown>[]>([])
  const [deployments, setDeployments] = useState<Record<string, unknown>[]>([])
  const [services, setServices] = useState<Record<string, unknown>[]>([])
  const [ingresses, setIngresses] = useState<Record<string, unknown>[]>([])
  const [aiError, setAiError] = useState<string | null>(null)
  const [selectedPod, setSelectedPod] = useState<Record<string, unknown> | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startAiPolling = useCallback((jobId: string) => {
    if (!connectionId) {return}
    if (pollRef.current) {clearInterval(pollRef.current)}
    pollRef.current = setInterval(async () => {
      try {
        const updated = await kubernetesApi.getAiAnalysis(connectionId, jobId)
        setAiJob(updated)
        if (updated.status === 'completed' || updated.status === 'failed') {
          if (pollRef.current) {clearInterval(pollRef.current)}
          pollRef.current = null
          setActionLoading(null)
        }
      } catch {
        if (pollRef.current) {clearInterval(pollRef.current)}
        pollRef.current = null
        setActionLoading(null)
      }
    }, 3000)
  }, [connectionId])

  const loadOverview = useCallback(async () => {
    if (!connectionId) {return}
    setLoading(true)
    try {
      const data = await kubernetesApi.overview(connectionId)
      setConnection(data.connection)
      setOverview(data.overview)
      setHealthScore(data.health_score as Record<string, unknown> | null)
      setVersionAdvisor(data.version_advisor as Record<string, unknown> | null)
      setSecurityFindings((data.security_findings as Record<string, unknown>[]) || [])
      if (data.ai_job) {
        setAiJob(data.ai_job)
        if (RUNNING_AI_STATUSES.has(data.ai_job.status)) {
          setActionLoading('ai')
          startAiPolling(data.ai_job.id)
          if (data.ai_job.status === 'queued') {
            kubernetesApi.startAiAnalysis(connectionId).catch(() => {})
          }
        }
      }
    } catch {
      setConnection(null)
    }
    setLoading(false)
  }, [connectionId, startAiPolling])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  useEffect(() => {
    if (!connectionId) {return}
    if (activeTab === 'nodes') {
      kubernetesApi.nodes(connectionId).then((d) => setNodes(d.nodes))
    } else if (activeTab === 'pods') {
      kubernetesApi.pods(connectionId).then((d) => setPods(d.pods))
    } else if (activeTab === 'events') {
      kubernetesApi.events(connectionId).then((d) => setEvents(d.events))
    } else if (activeTab === 'security') {
      kubernetesApi.securityScan(connectionId).then((d) => {
        setSecurityFindings((d.findings as Record<string, unknown>[]) || [])
        setHealthScore(d.health_score as Record<string, unknown> | null)
      })
    } else if (activeTab === 'health') {
      kubernetesApi.healthScore(connectionId).then(setHealthScore)
    } else if (activeTab === 'version') {
      kubernetesApi.versionAdvisor(connectionId).then(setVersionAdvisor)
    }
  }, [activeTab, connectionId])

  useEffect(() => {
    return () => {
      if (pollRef.current) {clearInterval(pollRef.current)}
    }
  }, [])

  const handleRefresh = async () => {
    if (!connectionId) {return}
    setActionLoading('refresh')
    try {
      await kubernetesApi.refresh(connectionId)
      await loadOverview()
    } finally {
      setActionLoading(null)
    }
  }

  const handleHealthCheck = async () => {
    if (!connectionId) {return}
    setActionLoading('health')
    try {
      const conn = await kubernetesApi.validate(connectionId)
      setConnection(conn)
    } finally {
      setActionLoading(null)
    }
  }

  const handleSecurityScan = async () => {
    if (!connectionId) {return}
    setActionLoading('security')
    setActiveTab('security')
    try {
      const data = await kubernetesApi.securityScan(connectionId)
      setSecurityFindings((data.findings as Record<string, unknown>[]) || [])
      setHealthScore(data.health_score as Record<string, unknown> | null)
    } finally {
      setActionLoading(null)
    }
  }

  const handleAiAnalysis = async () => {
    if (!connectionId) {return}
    setActionLoading('ai')
    setAiError(null)
    setActiveTab('ai')
    try {
      const job = await kubernetesApi.startAiAnalysis(connectionId)
      setAiJob(job)
      startAiPolling(job.id)
    } catch (err: unknown) {
      setActionLoading(null)
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setAiError(typeof msg === 'string' ? msg : 'Failed to start AI analysis')
    }
  }

  const handlePodClick = async (pod: Record<string, unknown>) => {
    if (!connectionId) {return}
    const ns = String(pod.namespace)
    const name = String(pod.name)
    try {
      const detail = await kubernetesApi.podDetail(connectionId, ns, name)
      setSelectedPod({ ...detail.pod, events: detail.events })
    } catch {
      setSelectedPod(pod)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!connection) {
    return (
      <div className="text-center py-24">
        <p className="text-muted-foreground mb-4">Cluster not found</p>
        <Link to="/kubernetes" className="text-sm text-primary hover:underline">Back to Kubernetes</Link>
      </div>
    )
  }

  const ov = overview as Record<string, Record<string, number>> | null
  const tabs: { key: Tab; label: string; icon: typeof Box }[] = [
    { key: 'overview', label: 'Overview', icon: Box },
    { key: 'nodes', label: 'Nodes', icon: Server },
    { key: 'pods', label: 'Pods', icon: Container },
    { key: 'events', label: 'Events', icon: Activity },
    { key: 'security', label: 'Security', icon: Shield },
    { key: 'version', label: 'Version', icon: AlertTriangle },
    { key: 'ai', label: 'AI Analysis', icon: Brain },
  ]

  return (
    <div className="space-y-6">
      <Link to="/kubernetes" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-3.5 w-3.5" />
        Kubernetes
      </Link>

      <PageHeader
        title={connection.cluster_name || connection.name}
        description={`${connection.kind === 'eks' ? 'AWS EKS' : 'Kubernetes'} · ${connection.kubernetes_version || 'unknown version'}${connection.aws_region ? ` · ${connection.aws_region}` : ''}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={handleRefresh} disabled={!!actionLoading} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium bg-white/5 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50">
              {actionLoading === 'refresh' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Refresh
            </button>
            <button type="button" onClick={handleHealthCheck} disabled={!!actionLoading} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium bg-white/5 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50">
              Health Check
            </button>
            <button type="button" onClick={handleSecurityScan} disabled={!!actionLoading} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium bg-white/5 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50">
              Security Scan
            </button>
            <button type="button" onClick={handleAiAnalysis} disabled={!!actionLoading} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 transition-all disabled:opacity-50">
              {actionLoading === 'ai' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Brain className="h-3.5 w-3.5" />}
              AI Analysis
            </button>
          </div>
        }
      />

      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge
          status={connection.health_status === 'connected' ? 'connected' : 'pending'}
          label={connection.health_status || connection.status}
        />
        <span className="text-xs text-muted-foreground">
          Last verified {formatTimeAgo(connection.last_verified_at)}
        </span>
        {connection.error_message && (
          <span className="text-xs text-amber-400">{connection.error_message}</span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
              activeTab === key
                ? 'bg-white/10 text-foreground border border-white/10'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && ov && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {healthScore && (
            <div className="rounded-xl border border-white/10 bg-card/60 p-4">
              <div className="text-sm font-semibold mb-2">
                Cluster Health: {(healthScore.overall as number) ?? '—'}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                {Object.entries((healthScore.sub_scores as Record<string, number>) || {}).map(([k, v]) => (
                  <div key={k} className="text-center rounded-lg bg-white/5 p-2">
                    <div className="text-[10px] text-muted-foreground capitalize">{k}</div>
                    <div className="text-sm font-semibold">{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Nodes" value={ov.nodes?.total ?? 0} subtitle={`${ov.nodes?.ready ?? 0} Ready · ${ov.nodes?.not_ready ?? 0} NotReady`} />
            <StatCard title="Pods" value={ov.pods?.total ?? 0} subtitle={`${ov.pods?.running ?? 0} Running · ${ov.pods?.failed ?? 0} Failed`} />
            <StatCard title="Deployments" value={ov.deployments?.total ?? 0} subtitle={`${ov.deployments?.healthy ?? 0} Healthy · ${ov.deployments?.degraded ?? 0} Degraded`} />
            <StatCard title="Services" value={ov.services?.total ?? 0} />
            <StatCard title="Ingress" value={ov.ingress?.total ?? 0} />
            <StatCard title="Namespaces" value={ov.namespaces?.total ?? 0} />
            <StatCard title="Warnings" value={ov.warnings?.total ?? 0} />
          </div>
        </motion.div>
      )}

      {activeTab === 'nodes' && (
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-white/5">
              <tr>
                {['Node', 'Status', 'CPU', 'Memory', 'Version', 'Conditions'].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-muted-foreground font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {nodes.map((n) => (
                <tr key={String(n.name)} className="border-t border-white/5 hover:bg-white/5">
                  <td className="px-3 py-2 font-mono">{String(n.name)}</td>
                  <td className="px-3 py-2">{String(n.status)}</td>
                  <td className="px-3 py-2">{String(n.cpu_allocatable || '—')}</td>
                  <td className="px-3 py-2">{String(n.memory_allocatable || '—')}</td>
                  <td className="px-3 py-2">{String(n.version || '—')}</td>
                  <td className="px-3 py-2">
                    {((n.conditions as Record<string, unknown>[]) || [])
                      .filter((c) => c.status === 'True' && c.type !== 'Ready')
                      .map((c) => String(c.type))
                      .join(', ') || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'pods' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-white/10 overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-white/5">
                <tr>
                  {['Namespace', 'Pod', 'Status', 'Node', 'Restarts', 'Age'].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-muted-foreground font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pods.map((p) => (
                  <tr
                    key={`${String(p.namespace)}/${String(p.name)}`}
                    className="border-t border-white/5 hover:bg-white/5 cursor-pointer"
                    onClick={() => handlePodClick(p)}
                  >
                    <td className="px-3 py-2">{String(p.namespace)}</td>
                    <td className="px-3 py-2 font-mono">{String(p.name)}</td>
                    <td className="px-3 py-2">{String(p.status_reason || p.status)}</td>
                    <td className="px-3 py-2">{String(p.node || '—')}</td>
                    <td className="px-3 py-2">{String(p.restart_count ?? 0)}</td>
                    <td className="px-3 py-2">{formatTimeAgo(p.age as string)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selectedPod && (
            <div className="rounded-xl border border-white/10 bg-card/60 p-4">
              <h4 className="text-sm font-semibold mb-2">{String(selectedPod.namespace)}/{String(selectedPod.name)}</h4>
              <pre className="text-xs text-muted-foreground overflow-auto max-h-64">{JSON.stringify(selectedPod, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {activeTab === 'events' && (
        <div className="space-y-2">
          {events.map((e, i) => (
            <div key={i} className={cn('rounded-lg border px-3 py-2 text-xs', e.priority ? 'border-amber-500/20 bg-amber-500/5' : 'border-white/10 bg-white/5')}>
              <div className="flex justify-between gap-2">
                <span className="font-medium">{String(e.reason)}</span>
                <span className="text-muted-foreground">{formatTimeAgo(e.timestamp as string)}</span>
              </div>
              <div className="text-muted-foreground mt-0.5">{String(e.namespace)} · {String(e.resource)}</div>
              <div className="mt-1">{String(e.message)}</div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'security' && (
        <div className="space-y-2">
          {securityFindings.length === 0 && <p className="text-sm text-muted-foreground">No security findings detected.</p>}
          {securityFindings.map((f, i) => (
            <div key={i} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs">
              <div className="flex justify-between">
                <span className="font-medium">{String(f.title)}</span>
                <span className="text-amber-400 uppercase">{String(f.severity)}</span>
              </div>
              <div className="text-muted-foreground mt-0.5">{String(f.namespace)} · {String(f.resource)}</div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'version' && connectionId && (
        <VersionAdvisorPanel
          connectionId={connectionId}
          advisor={versionAdvisor}
          onAdvisorUpdate={setVersionAdvisor}
        />
      )}

      {activeTab === 'ai' && connectionId && (
        <AICopilotPanel connectionId={connectionId} />
      )}
    </div>
  )
}

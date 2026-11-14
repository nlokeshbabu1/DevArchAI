import { motion, AnimatePresence } from 'framer-motion'
import {
  Cloud, RefreshCw, Loader2, Play, Trash2, AlertTriangle,
  Shield, DollarSign, FileCheck, Box, Sparkles, X,
} from 'lucide-react'
import { useState, useEffect, useCallback, useRef } from 'react'

import { cloudApi, type CloudConnection } from '@/api/endpoints/cloud'
import { AIRecommendations } from '@/components/cloud/AIRecommendations'
import { CloudOverview } from '@/components/cloud/CloudOverview'
import { CloudScanProgress } from '@/components/cloud/CloudScanProgress'
import { ComplianceView } from '@/components/cloud/ComplianceView'
import { CostOptimization } from '@/components/cloud/CostOptimization'
import { ResourceInventory } from '@/components/cloud/ResourceInventory'
import { SecurityFindings } from '@/components/cloud/SecurityFindings'
import { Button } from '@/components/ui'
import { useCloudWebSocket } from '@/hooks/useCloudWebSocket'
import { cn } from '@/lib/utils'
import { useCloudStore } from '@/stores/cloud-store'

interface CloudDashboardProps {
  isConnected: boolean
  onConnect: () => void
  onRefresh: () => void
  autoScanConnectionId?: string | null
  onAutoScanComplete?: () => void
}

const TABS = [
  { key: 'overview', label: 'Overview', icon: Box },
  { key: 'resources', label: 'Resources', icon: Cloud },
  { key: 'findings', label: 'Findings', icon: Shield },
  { key: 'recommendations', label: 'AI Recommendations', icon: Sparkles },
  { key: 'cost', label: 'Cost', icon: DollarSign },
  { key: 'compliance', label: 'Compliance', icon: FileCheck },
] as const

type TabKey = (typeof TABS)[number]['key']

export function CloudDashboard({ isConnected, onConnect, onRefresh, autoScanConnectionId, onAutoScanComplete }: CloudDashboardProps) {
  const [connections, setConnections] = useState<CloudConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const autoScanTriggered = useRef(false)
  const scanTriggerRef = useRef(false)

  const {
    scanInProgress, setScanInProgress,
    scanProgress, setScanProgress,
    scanStage, setScanStage,
    overview, setOverview,
    setResources, setFindings, setCosts, setCompliance,
    setRecommendations, setRecommendationsSummary,
    error, setError,
  } = useCloudStore()

  const loadConnections = useCallback(async () => {
    setLoading(true)
    try {
      const conns = await cloudApi.connections()
      setConnections(conns)
      if (conns.length > 0 && !selectedId) {
        setSelectedId(conns[0].id)
      }
    } catch {
      // ignore
    }
    setLoading(false)
  }, [selectedId])

  useEffect(() => {
    loadConnections()
  }, [loadConnections])

  const selectedConnection = connections.find((c) => c.id === selectedId)

  // Auto-trigger scan when autoScanConnectionId is provided (e.g., after "Run First Scan")
  useEffect(() => {
    if (autoScanConnectionId) {
      autoScanTriggered.current = false
    }
  }, [autoScanConnectionId])

  useEffect(() => {
    if (autoScanConnectionId && connections.length > 0 && !autoScanTriggered.current) {
      autoScanTriggered.current = true
      const targetId = autoScanConnectionId
      setSelectedId(targetId)
      handleScanById(targetId)
      onAutoScanComplete?.()
    }
  }, [autoScanConnectionId, connections])

  const loadOverview = useCallback(async () => {
    if (!selectedId) {return}
    try {
      const data = await cloudApi.overview(selectedId)
      setOverview(data)
    } catch {
      // ignore
    }
  }, [selectedId, setOverview])

  const loadTabData = useCallback(async () => {
    if (!selectedId) {return}
    try {
      switch (activeTab) {
        case 'resources': {
          const data = await cloudApi.resources(selectedId)
          setResources(data.resources)
          break
        }
        case 'findings': {
          const data = await cloudApi.findings(selectedId)
          setFindings(data.findings)
          break
        }
        case 'cost': {
          const data = await cloudApi.costs(selectedId)
          setCosts(data.recommendations)
          break
        }
        case 'compliance': {
          const data = await cloudApi.compliance(selectedId)
          setCompliance(data.results)
          break
        }
        case 'recommendations': {
          const [recsData, summaryData] = await Promise.all([
            cloudApi.recommendations(selectedId),
            cloudApi.recommendationsSummary(selectedId),
          ])
          setRecommendations(recsData.recommendations)
          setRecommendationsSummary(summaryData)
          break
        }
      }
    } catch {
      // ignore
    }
  }, [selectedId, activeTab, setResources, setFindings, setCosts, setCompliance, setRecommendations, setRecommendationsSummary])

  useEffect(() => {
    if (selectedId) {
      loadOverview()
      loadTabData()
    }
  }, [selectedId, loadOverview, loadTabData])

  useCloudWebSocket({
    connectionId: selectedId,
    enabled: scanInProgress,
    onComplete: () => {
      setScanInProgress(false)
      loadOverview().then(() => {
        // Check if scan completed with 0 resources after data loads
        const currentOverview = useCloudStore.getState().overview
        if (currentOverview && currentOverview.resource_summary.total === 0) {
          setError('Scan completed but found 0 resources. Check backend logs for scanner errors.')
        }
      })
      loadTabData()
    },
    onFailed: (errorMsg) => {
      setScanInProgress(false)
      setError(errorMsg || 'Scan failed')
    },
  })

  const handleScan = async () => {
    if (!selectedId || scanInProgress) {return}
    await handleScanById(selectedId)
  }

  const handleScanById = async (connectionId: string) => {
    if (scanInProgress) {return}
    setError(null)
    setScanInProgress(true)
    setScanProgress(0)
    setScanStage('Starting scan...')
    try {
      await cloudApi.triggerScan(connectionId)
    } catch {
      setScanInProgress(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await cloudApi.deleteConnection(id)
      if (selectedId === id) {setSelectedId(null)}
      loadConnections()
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-48 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 animate-pulse" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (!isConnected || connections.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center py-24 text-center"
      >
        <div className="p-4 rounded-2xl bg-orange-500/10 border border-orange-500/20 mb-4">
          <Cloud className="h-10 w-10 text-orange-400" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-1">No AWS Connections</h3>
        <p className="text-sm text-muted-foreground max-w-sm mb-6">
          Connect your AWS account using OIDC federation to scan your infrastructure for security, cost, and compliance insights.
        </p>
        <Button variant="primary" onClick={onConnect}>
          <Cloud className="h-4 w-4 mr-2" />
          Connect AWS Account
        </Button>
      </motion.div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Connection Selector + Actions */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-center gap-3">
          <select
            value={selectedId || ''}
            onChange={(e) => setSelectedId(e.target.value)}
            className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
          >
            {connections.map((conn) => (
              <option key={conn.id} value={conn.id}>
                {conn.connection_name} ({conn.account_id})
              </option>
            ))}
          </select>
          {selectedConnection && (
            <StatusPill status={selectedConnection.scan_status} />
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={loadConnections} disabled={scanInProgress}>
            <RefreshCw className="h-4 w-4 mr-1.5" />
            Refresh
          </Button>
          <Button variant="primary" onClick={handleScan} disabled={scanInProgress || !selectedId}>
            {scanInProgress ? (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-1.5" />
            )}
            {scanInProgress ? 'Scanning...' : 'Scan Now'}
          </Button>
          {selectedId && (
            <Button
              variant="secondary"
              className="text-red-400 hover:bg-red-500/10"
              onClick={() => handleDelete(selectedId)}
              disabled={scanInProgress}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Scan Progress */}
      {scanInProgress && (
        <CloudScanProgress stage={scanStage} progress={scanProgress} />
      )}

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <AlertTriangle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-red-400">Scan Error</p>
                <p className="text-sm text-red-300/80 mt-1 break-words">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="p-1 rounded-lg hover:bg-red-500/20 transition-colors flex-shrink-0"
              >
                <X className="h-4 w-4 text-red-400" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl w-fit overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap',
                activeTab === tab.key
                  ? 'bg-white/10 text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'overview' && overview && <CloudOverview data={overview} />}
        {activeTab === 'resources' && selectedId && <ResourceInventory connectionId={selectedId} />}
        {activeTab === 'findings' && selectedId && <SecurityFindings connectionId={selectedId} />}
        {activeTab === 'recommendations' && selectedId && <AIRecommendations connectionId={selectedId} />}
        {activeTab === 'cost' && selectedId && <CostOptimization connectionId={selectedId} />}
        {activeTab === 'compliance' && selectedId && <ComplianceView connectionId={selectedId} />}
      </div>
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const config = {
    idle: { label: 'Idle', dotClass: 'bg-gray-500' },
    scanning: { label: 'Scanning', dotClass: 'bg-blue-400 animate-pulse' },
    completed: { label: 'Completed', dotClass: 'bg-green-400' },
    failed: { label: 'Failed', dotClass: 'bg-red-400' },
  }[status] || { label: status, dotClass: 'bg-gray-500' }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border border-white/10 bg-white/5 text-muted-foreground">
      <span className={cn('inline-block h-2 w-2 rounded-full', config.dotClass)} />
      {config.label}
    </span>
  )
}

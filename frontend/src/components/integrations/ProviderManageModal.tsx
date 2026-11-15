import { motion, AnimatePresence } from 'framer-motion'
import { X, Settings, Loader2, CheckCircle, AlertCircle, RefreshCw, ArrowRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { integrationsApi } from '@/api/endpoints/integrations'
import { kubernetesApi, type KubernetesInfo } from '@/api/endpoints/kubernetes'

interface ProviderManageModalProps {
  open: boolean
  onClose: () => void
  providerId: string
  providerName: string
  account?: string
  onDisconnected: () => void
}

function formatTimeAgo(dateStr?: string | null): string {
  if (!dateStr) {return 'never'}
  const diff = Date.now() - new Date(dateStr).getTime()
  const secs = Math.floor(diff / 1000)
  if (secs < 60) {return `${secs}s ago`}
  const mins = Math.floor(secs / 60)
  if (mins < 60) {return `${mins}m ago`}
  return `${Math.floor(mins / 60)}h ago`
}

export function ProviderManageModal({ open, onClose, providerId, providerName, account, onDisconnected }: ProviderManageModalProps) {
  const [state, setState] = useState<'idle' | 'loading' | 'disconnecting' | 'validating' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [connection, setConnection] = useState<KubernetesInfo | null>(null)

  const isK8s = providerId === 'kubernetes' || providerId === 'eks'

  useEffect(() => {
    if (!open || !isK8s) {return}
    setState('loading')
    kubernetesApi.list()
      .then((connections) => {
        const match = connections
          .filter((c) => c.is_active)
          .find((c) => (providerId === 'eks' ? c.kind === 'eks' : c.kind === 'generic'))
        setConnection(match || null)
        setState('idle')
      })
      .catch(() => setState('idle'))
  }, [open, providerId, isK8s])

  const handleValidate = async () => {
    if (!connection) {return}
    setState('validating')
    try {
      const updated = await kubernetesApi.validate(connection.id)
      setConnection(updated)
      setState('idle')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setErrorMsg(e.response?.data?.detail || e.message || 'Validation failed')
      setState('error')
    }
  }

  const handleDisconnect = async () => {
    setState('disconnecting')
    setErrorMsg('')
    try {
      if (providerId === 'github' || providerId === 'gitlab') {
        await integrationsApi.disconnectOAuth(providerId)
      } else if (isK8s) {
        if (!connection) {throw new Error('No active connection found to disconnect')}
        await kubernetesApi.disconnect(connection.id)
      } else {
        throw new Error('Disconnect not supported for this provider')
      }
      setState('success')
      setTimeout(() => {
        onClose()
        setState('idle')
        onDisconnected()
      }, 1200)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setState('error')
      setErrorMsg(e.response?.data?.detail || e.message || 'Failed to disconnect.')
    }
  }

  const handleClose = () => {
    if (state !== 'disconnecting' && state !== 'validating') {
      onClose()
      setTimeout(() => setState('idle'), 200)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={handleClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-card border border-white/10 rounded-2xl p-6 max-w-md w-full shadow-2xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={`Manage ${providerName}`}
          >
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-white/5 rounded-xl border border-white/10">
                  <Settings className="h-5 w-5 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Manage {providerName}</h3>
                  {(account || connection?.cluster_name) && (
                    <p className="text-xs text-muted-foreground font-mono truncate max-w-[240px]">
                      {connection?.cluster_name || account}
                    </p>
                  )}
                </div>
              </div>
              <button onClick={handleClose} disabled={state === 'disconnecting'} className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50" aria-label="Close">
                <X className="h-5 w-5" />
              </button>
            </div>

            {state === 'success' && (
              <div className="py-6 text-center space-y-3">
                <CheckCircle className="h-12 w-12 text-green-400 mx-auto" />
                <p className="text-lg font-semibold text-foreground">Disconnected</p>
                <p className="text-sm text-muted-foreground">{providerName} has been disconnected.</p>
              </div>
            )}

            {state === 'error' && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-200">{errorMsg}</p>
              </div>
            )}

            {state !== 'success' && isK8s && connection && (
              <div className="space-y-4 mb-4">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-white/5 p-2">
                    <div className="text-muted-foreground">Provider</div>
                    <div className="font-medium">{connection.kind === 'eks' ? 'AWS EKS' : 'Kubernetes'}</div>
                  </div>
                  <div className="rounded-lg bg-white/5 p-2">
                    <div className="text-muted-foreground">Version</div>
                    <div className="font-medium">{connection.kubernetes_version || '—'}</div>
                  </div>
                  <div className="rounded-lg bg-white/5 p-2">
                    <div className="text-muted-foreground">Health</div>
                    <div className="font-medium capitalize">{connection.health_status || connection.status}</div>
                  </div>
                  <div className="rounded-lg bg-white/5 p-2">
                    <div className="text-muted-foreground">Last verified</div>
                    <div className="font-medium">{formatTimeAgo(connection.last_verified_at)}</div>
                  </div>
                </div>

                {connection.error_message && (
                  <p className="text-xs text-amber-400">{connection.error_message}</p>
                )}

                {connection.permissions && connection.permissions.length > 0 && (
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Permissions</div>
                    <div className="flex flex-wrap gap-1">
                      {connection.permissions.map((p) => (
                        <span
                          key={p.resource}
                          className={`px-2 py-0.5 rounded text-[10px] ${p.granted ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}
                        >
                          {p.resource}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleValidate}
                    disabled={state === 'validating' || state === 'disconnecting'}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-white/5 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50"
                  >
                    {state === 'validating' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    Run Health Check
                  </button>
                  <Link
                    to={`/kubernetes/${connection.id}`}
                    onClick={onClose}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 transition-all"
                  >
                    Open Cluster
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            )}

            {state !== 'success' && (
              <div className="space-y-4">
                {!isK8s && (
                  <p className="text-sm text-muted-foreground">
                    Disconnecting {providerName} will stop automated scans and remove the connected account from your workspace.
                  </p>
                )}
                {isK8s && (
                  <p className="text-sm text-muted-foreground">
                    Disconnecting will remove this cluster from your workspace. Credentials are never displayed here.
                  </p>
                )}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={state === 'disconnecting' || state === 'validating'}
                    className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleDisconnect}
                    disabled={state === 'disconnecting' || state === 'validating' || (isK8s && !connection)}
                    className="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-red-500 hover:bg-red-600 text-white transition-all disabled:opacity-50"
                  >
                    {state === 'disconnecting' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {state === 'disconnecting' ? 'Disconnecting...' : 'Disconnect'}
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Settings, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { integrationsApi } from '@/api/endpoints/integrations'
import { kubernetesApi } from '@/api/endpoints/kubernetes'

interface ProviderManageModalProps {
  open: boolean
  onClose: () => void
  providerId: string
  providerName: string
  account?: string
  onDisconnected: () => void
}

export function ProviderManageModal({ open, onClose, providerId, providerName, account, onDisconnected }: ProviderManageModalProps) {
  const [state, setState] = useState<'idle' | 'disconnecting' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const handleDisconnect = async () => {
    setState('disconnecting')
    setErrorMsg('')
    try {
      if (providerId === 'github' || providerId === 'gitlab') {
        await integrationsApi.disconnectOAuth(providerId as 'github' | 'gitlab')
      } else if (providerId === 'kubernetes' || providerId === 'eks') {
        const connections = await kubernetesApi.list()
        const match = connections
          .filter((c) => c.is_active)
          .find((c) => (providerId === 'eks' ? c.kind === 'eks' : c.kind === 'generic'))
        if (!match) {
          throw new Error('No active connection found to disconnect')
        }
        await kubernetesApi.disconnect(match.id)
      } else {
        throw new Error('Disconnect not supported for this provider')
      }
      setState('success')
      setTimeout(() => {
        onClose()
        setState('idle')
        onDisconnected()
      }, 1200)
    } catch (err: any) {
      setState('error')
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to disconnect.')
    }
  }

  const handleClose = () => {
    if (state !== 'disconnecting') {
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
            className="bg-card border border-white/10 rounded-2xl p-6 max-w-sm w-full shadow-2xl"
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
                  {account && (
                    <p className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">{account}</p>
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

            {state !== 'success' && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Disconnecting {providerName} will stop automated scans and remove the {providerId === 'eks' ? 'EKS cluster' : 'connected account'} from your workspace.
                </p>
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={state === 'disconnecting'}
                    className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleDisconnect}
                    disabled={state === 'disconnecting'}
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

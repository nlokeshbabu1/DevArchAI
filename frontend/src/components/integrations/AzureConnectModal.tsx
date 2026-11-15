import { motion, AnimatePresence } from 'framer-motion'
import { X, Server, Loader2, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../ui'

interface AzureConnectModalProps {
  open: boolean
  onClose: () => void
}

export function AzureConnectModal({ open, onClose }: AzureConnectModalProps) {
  const [tenantId, setTenantId] = useState('')
  const [subscriptionId, setSubscriptionId] = useState('')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [showSecret, setShowSecret] = useState(false)
  const [state, setState] = useState<'idle' | 'connecting' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const isValid = tenantId.length > 0 && subscriptionId.length > 0 && clientId.length > 0 && clientSecret.length > 0

  const handleConnect = async () => {
    setState('connecting')
    setErrorMsg('')
    try {
      const response = await fetch('/api/integrations/azure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, subscription_id: subscriptionId, client_id: clientId, client_secret: clientSecret }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to connect Azure')
      }
      setState('success')
      setTimeout(() => { onClose(); setState('idle') }, 1500)
    } catch (err: any) {
      setState('error')
      setErrorMsg(err.message || 'Connection failed. Please verify your credentials.')
    }
  }

  const handleClose = () => {
    if (state !== 'connecting') {
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
            className="bg-card border border-white/10 rounded-2xl p-6 max-w-lg w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Connect Azure"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-500/15 rounded-xl border border-blue-500/30">
                  <Server className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Connect Azure</h3>
                  <p className="text-sm text-muted-foreground">Enter your Azure subscription credentials</p>
                </div>
              </div>
              <button onClick={handleClose} disabled={state === 'connecting'} className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50" aria-label="Close">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Success */}
            {state === 'success' && (
              <div className="py-8 text-center space-y-3">
                <CheckCircle className="h-12 w-12 text-green-400 mx-auto" />
                <p className="text-lg font-semibold text-foreground">Azure Connected</p>
                <p className="text-sm text-muted-foreground">Your Azure subscription has been connected successfully.</p>
              </div>
            )}

            {/* Error */}
            {state === 'error' && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-200">{errorMsg}</p>
              </div>
            )}

            {/* Form */}
            {(state === 'idle' || state === 'connecting' || state === 'error') && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Tenant ID</label>
                  <input
                    type="text"
                    value={tenantId}
                    onChange={(e) => setTenantId(e.target.value)}
                    placeholder="00000000-0000-0000-0000-000000000000"
                    disabled={state === 'connecting'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Subscription ID</label>
                  <input
                    type="text"
                    value={subscriptionId}
                    onChange={(e) => setSubscriptionId(e.target.value)}
                    placeholder="00000000-0000-0000-0000-000000000000"
                    disabled={state === 'connecting'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Client ID</label>
                  <input
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    placeholder="00000000-0000-0000-0000-000000000000"
                    disabled={state === 'connecting'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Client Secret</label>
                  <div className="relative">
                    <input
                      type={showSecret ? 'text' : 'password'}
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      placeholder="Enter your Azure client secret"
                      disabled={state === 'connecting'}
                      className="w-full pr-10 pl-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret(!showSecret)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      aria-label={showSecret ? 'Hide client secret' : 'Show client secret'}
                    >
                      {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* OR Azure Entra ID */}
                <div className="relative py-3">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-white/10" />
                  </div>
                  <div className="relative flex justify-center">
                    <span className="px-3 text-xs text-muted-foreground bg-card">OR</span>
                  </div>
                </div>

                <Button
                  variant="secondary"
                  className="w-full"
                  disabled={state === 'connecting'}
                >
                  Sign in with Azure Entra ID
                </Button>

                <div className="flex gap-3 pt-2">
                  <Button variant="secondary" className="flex-1" onClick={handleClose} disabled={state === 'connecting'}>
                    Cancel
                  </Button>
                  <Button variant="primary" className="flex-1" onClick={handleConnect} disabled={!isValid || state === 'connecting'} loading={state === 'connecting'}>
                    {state === 'connecting' ? 'Connecting...' : 'Connect Azure'}
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

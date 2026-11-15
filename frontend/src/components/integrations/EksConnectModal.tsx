import { motion, AnimatePresence } from 'framer-motion'
import { X, Container, Loader2, CheckCircle, AlertCircle, Cloud as CloudIcon, RefreshCw, ChevronDown } from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'

import { kubernetesApi, type EksCluster } from '@/api/endpoints/kubernetes'

interface EksConnectModalProps {
  open: boolean
  onClose: () => void
  onConnected: () => void
  onNeedAws: () => void
}

const REGIONS = [
  'us-east-1',
  'us-east-2',
  'us-west-1',
  'us-west-2',
  'eu-west-1',
  'eu-west-2',
  'eu-central-1',
  'ap-southeast-1',
  'ap-southeast-2',
  'ap-northeast-1',
  'sa-east-1',
]

export function EksConnectModal({ open, onClose, onConnected, onNeedAws }: EksConnectModalProps) {
  const [region, setRegion] = useState('us-east-1')
  const [clusters, setClusters] = useState<EksCluster[]>([])
  const [selected, setSelected] = useState<string>('')
  const [state, setState] = useState<'idle' | 'checking' | 'loading' | 'connecting' | 'success' | 'error'>('idle')
  const [awsAvailable, setAwsAvailable] = useState(true)
  const [errorMsg, setErrorMsg] = useState('')

  const checkAws = useCallback(async () => {
    if (!open) {return}
    setState('checking')
    setErrorMsg('')
    try {
      const res = await kubernetesApi.eksAwsAvailable()
      if (!res.available) {
        setAwsAvailable(false)
        setState('idle')
        return
      }
      setAwsAvailable(true)
      setState('idle')
    } catch (err: any) {
      setAwsAvailable(true)
      setState('idle')
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to check AWS availability.')
    }
  }, [open])

  useEffect(() => {
    if (open) {
      setClusters([])
      setSelected('')
      setRegion('us-east-1')
      checkAws()
    }
  }, [open, checkAws])

  const loadClusters = async () => {
    setState('loading')
    setErrorMsg('')
    setClusters([])
    setSelected('')
    try {
      const data = await kubernetesApi.listEksClusters(region)
      setClusters(data)
      setState('idle')
    } catch (err: any) {
      setState('error')
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to discover EKS clusters.')
    }
  }

  const handleConnect = async () => {
    if (!selected) {return}
    setState('connecting')
    setErrorMsg('')
    try {
      const cluster = clusters.find((c) => c.name === selected)
      await kubernetesApi.connectEks({ cluster_name: selected, region, name: cluster?.name })
      setState('success')
      setTimeout(() => {
        onClose()
        setState('idle')
        onConnected()
      }, 1200)
    } catch (err: any) {
      setState('error')
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to connect EKS cluster.')
    }
  }

  const handleClose = () => {
    if (state !== 'connecting' && state !== 'loading') {
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
            aria-label="Connect EKS cluster"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-orange-500/15 rounded-xl border border-orange-500/30">
                  <Container className="h-5 w-5 text-orange-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Connect EKS Cluster</h3>
                  <p className="text-sm text-muted-foreground">Discover clusters using your AWS connection</p>
                </div>
              </div>
              <button onClick={handleClose} disabled={state === 'connecting' || state === 'loading'} className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50" aria-label="Close">
                <X className="h-5 w-5" />
              </button>
            </div>

            {state === 'success' && (
              <div className="py-8 text-center space-y-3">
                <CheckCircle className="h-12 w-12 text-green-400 mx-auto" />
                <p className="text-lg font-semibold text-foreground">EKS Cluster Connected</p>
                <p className="text-sm text-muted-foreground">Your cluster has been connected successfully.</p>
              </div>
            )}

            {state === 'error' && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-200">{errorMsg}</p>
              </div>
            )}

            {(state !== 'success') && (
              <div className="space-y-4">
                {!awsAvailable && (
                  <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-amber-200">
                      <p className="font-medium mb-1">AWS connection required</p>
                      <p className="text-xs mb-2">Connect an AWS account first to discover EKS clusters.</p>
                      <button
                        onClick={() => { onClose(); onNeedAws() }}
                        className="text-xs font-semibold text-amber-300 hover:text-amber-200 underline"
                      >
                        Connect AWS
                      </button>
                    </div>
                  </div>
                )}

                {awsAvailable && state !== 'checking' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1.5">Region</label>
                      <div className="relative">
                        <select
                          value={region}
                          onChange={(e) => setRegion(e.target.value)}
                          disabled={state === 'connecting'}
                          className="w-full appearance-none px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all text-sm disabled:opacity-50"
                        >
                          {REGIONS.map((r) => (
                            <option key={r} value={r} className="bg-card">{r}</option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={loadClusters}
                      disabled={state === 'connecting' || state === 'loading'}
                      className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
                    >
                      {state === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                      {state === 'loading' ? 'Discovering...' : 'Discover Clusters'}
                    </button>

                    {clusters.length === 0 && state !== 'loading' && (
                      <p className="text-xs text-muted-foreground">
                        No clusters found in this region yet. Click Discover Clusters to fetch them.
                      </p>
                    )}

                    {clusters.length > 0 && (
                      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                        {clusters.map((c) => (
                          <button
                            key={c.name}
                            type="button"
                            onClick={() => setSelected(c.name)}
                            disabled={state === 'connecting'}
                            className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all text-left ${
                              selected === c.name
                                ? 'border-orange-500/50 bg-orange-500/10'
                                : 'border-white/10 bg-white/5 hover:bg-white/10'
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <CloudIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-foreground truncate">{c.name}</p>
                                <p className="text-xs text-muted-foreground">v{c.version} · {c.status}</p>
                              </div>
                            </div>
                            {selected === c.name && <CheckCircle className="h-4 w-4 text-orange-400 flex-shrink-0" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}

                {state === 'checking' && (
                  <div className="py-6 text-center">
                    <Loader2 className="h-6 w-6 mx-auto animate-spin text-muted-foreground" />
                    <p className="text-xs text-muted-foreground mt-2">Checking AWS connection...</p>
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={state === 'connecting' || state === 'loading'}
                    className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConnect}
                    disabled={!selected || state === 'connecting' || !awsAvailable}
                    className="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-orange-500 hover:bg-orange-600 text-white transition-all disabled:opacity-50"
                  >
                    {state === 'connecting' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Container className="h-4 w-4" />}
                    {state === 'connecting' ? 'Connecting...' : 'Connect'}
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

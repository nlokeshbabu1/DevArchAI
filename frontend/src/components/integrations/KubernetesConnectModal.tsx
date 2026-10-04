import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Container, Loader2, CheckCircle, AlertCircle, FileUp, TestTube2 } from 'lucide-react'
import { kubernetesApi } from '@/api/endpoints/kubernetes'

interface KubernetesConnectModalProps {
  open: boolean
  onClose: () => void
  onConnected: () => void
}

export function KubernetesConnectModal({ open, onClose, onConnected }: KubernetesConnectModalProps) {
  const [name, setName] = useState('')
  const [kubeconfig, setKubeconfig] = useState('')
  const [contextName, setContextName] = useState('')
  const [state, setState] = useState<'idle' | 'testing' | 'connecting' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const isValid = name.trim().length > 0 && kubeconfig.trim().length > 0

  const toBase64 = (text: string) => {
    try {
      return btoa(unescape(encodeURIComponent(text)))
    } catch {
      return btoa(text)
    }
  }

  const handleFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result || '')
      setKubeconfig(text)
      if (!name) setName(file.name.replace(/\.(yaml|yml)$/i, ''))
    }
    reader.readAsText(file)
  }

  const testConnection = async () => {
    if (!kubeconfig) return
    setState('testing')
    setErrorMsg('')
    try {
      await kubernetesApi.test({ name: name || 'k8s', kubeconfig: toBase64(kubeconfig), context_name: contextName || undefined })
      setState('idle')
    } catch (err: any) {
      setState('error')
      setErrorMsg(err.response?.data?.detail || err.message || 'Connection test failed.')
    }
  }

  const connect = async () => {
    setState('connecting')
    setErrorMsg('')
    try {
      await kubernetesApi.connect({ name, kubeconfig: toBase64(kubeconfig), context_name: contextName || undefined })
      setState('success')
      setTimeout(() => {
        onClose()
        setState('idle')
        onConnected()
      }, 1200)
    } catch (err: any) {
      setState('error')
      setErrorMsg(err.response?.data?.detail || err.message || 'Connection failed. Please verify your kubeconfig.')
    }
  }

  const handleClose = () => {
    if (state !== 'connecting' && state !== 'testing') {
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
            aria-label="Connect Kubernetes"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-500/15 rounded-xl border border-indigo-500/30">
                  <Container className="h-5 w-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Connect Kubernetes</h3>
                  <p className="text-sm text-muted-foreground">Upload a kubeconfig to connect your cluster</p>
                </div>
              </div>
              <button onClick={handleClose} disabled={state === 'connecting' || state === 'testing'} className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50" aria-label="Close">
                <X className="h-5 w-5" />
              </button>
            </div>

            {state === 'success' && (
              <div className="py-8 text-center space-y-3">
                <CheckCircle className="h-12 w-12 text-green-400 mx-auto" />
                <p className="text-lg font-semibold text-foreground">Kubernetes Connected</p>
                <p className="text-sm text-muted-foreground">Your cluster has been connected successfully.</p>
              </div>
            )}

            {state === 'error' && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-200">{errorMsg}</p>
              </div>
            )}

            {(state === 'idle' || state === 'testing' || state === 'connecting' || state === 'error') && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Connection name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="production-cluster"
                    disabled={state === 'connecting' || state === 'testing'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Kubeconfig</label>
                  <label className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/5 border border-dashed border-white/20 text-sm text-muted-foreground hover:border-indigo-500/40 hover:text-foreground cursor-pointer transition-all">
                    <FileUp className="h-4 w-4" />
                    Upload kubeconfig file
                    <input
                      type="file"
                      accept=".yaml,.yml,.kubeconfig"
                      className="hidden"
                      disabled={state === 'connecting' || state === 'testing'}
                      onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    />
                  </label>
                  <textarea
                    value={kubeconfig}
                    onChange={(e) => setKubeconfig(e.target.value)}
                    placeholder="Or paste kubeconfig YAML here..."
                    rows={5}
                    disabled={state === 'connecting' || state === 'testing'}
                    className="mt-2 w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all font-mono text-xs disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Context name (optional)</label>
                  <input
                    type="text"
                    value={contextName}
                    onChange={(e) => setContextName(e.target.value)}
                    placeholder="my-context"
                    disabled={state === 'connecting' || state === 'testing'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                  />
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={testConnection}
                    disabled={!kubeconfig || state === 'connecting' || state === 'testing'}
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
                  >
                    {state === 'testing' ? <Loader2 className="h-4 w-4 animate-spin" /> : <TestTube2 className="h-4 w-4" />}
                    {state === 'testing' ? 'Testing...' : 'Test Connection'}
                  </button>
                  <button
                    type="button"
                    onClick={connect}
                    disabled={!isValid || state === 'connecting' || state === 'testing'}
                    className="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-indigo-500 hover:bg-indigo-600 text-white transition-all disabled:opacity-50"
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

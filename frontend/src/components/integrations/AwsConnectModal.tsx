import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Cloud, Loader2, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { Button } from '../ui'

interface AwsConnectModalProps {
  open: boolean
  onClose: () => void
}

const REGIONS = [
  'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
  'eu-west-1', 'eu-west-2', 'eu-central-1', 'eu-north-1',
  'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-south-1',
  'sa-east-1', 'ca-central-1',
]

const REQUIRED_PERMISSIONS = [
  'ReadOnlyAccess',
  'SecurityAudit',
  'CloudFormation Scanner Role',
]

export function AwsConnectModal({ open, onClose }: AwsConnectModalProps) {
  const [accountId, setAccountId] = useState('')
  const [roleArn, setRoleArn] = useState('')
  const [externalId, setExternalId] = useState('')
  const [region, setRegion] = useState('us-east-1')
  const [showExternalId, setShowExternalId] = useState(false)
  const [state, setState] = useState<'idle' | 'connecting' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const isValid = accountId.length >= 12 && roleArn.startsWith('arn:aws:iam::') && externalId.length > 0

  const handleConnect = async () => {
    setState('connecting')
    setErrorMsg('')
    try {
      const response = await fetch('/api/integrations/aws', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: accountId, role_arn: roleArn, external_id: externalId, region }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to connect AWS')
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
            aria-label="Connect AWS"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-orange-500/15 rounded-xl border border-orange-500/30">
                  <Cloud className="h-5 w-5 text-orange-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Connect AWS</h3>
                  <p className="text-sm text-muted-foreground">Enter your AWS account credentials</p>
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
                <p className="text-lg font-semibold text-foreground">AWS Connected</p>
                <p className="text-sm text-muted-foreground">Your AWS account has been connected successfully.</p>
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
                  <label className="block text-sm font-medium text-foreground mb-1.5">AWS Account ID</label>
                  <input
                    type="text"
                    value={accountId}
                    onChange={(e) => setAccountId(e.target.value.replace(/[^0-9]/g, '').slice(0, 12))}
                    placeholder="123456789012"
                    disabled={state === 'connecting'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all font-mono disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">IAM Role ARN</label>
                  <input
                    type="text"
                    value={roleArn}
                    onChange={(e) => setRoleArn(e.target.value)}
                    placeholder="arn:aws:iam::123456789012:role/DevArchAI-Scanner"
                    disabled={state === 'connecting'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">External ID</label>
                  <div className="relative">
                    <input
                      type={showExternalId ? 'text' : 'password'}
                      value={externalId}
                      onChange={(e) => setExternalId(e.target.value)}
                      placeholder="Unique identifier for cross-account access"
                      disabled={state === 'connecting'}
                      className="w-full pr-10 pl-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all font-mono text-sm disabled:opacity-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowExternalId(!showExternalId)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      aria-label={showExternalId ? 'Hide external ID' : 'Show external ID'}
                    >
                      {showExternalId ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Region</label>
                  <select
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    disabled={state === 'connecting'}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all disabled:opacity-50"
                  >
                    {REGIONS.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>

                {/* Required Permissions */}
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <p className="text-xs font-semibold text-foreground mb-2">Required Permissions</p>
                  <div className="space-y-1">
                    {REQUIRED_PERMISSIONS.map((perm) => (
                      <div key={perm} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <CheckCircle className="h-3 w-3 text-orange-400" />
                        <span>{perm}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <Button variant="secondary" className="flex-1" onClick={handleClose} disabled={state === 'connecting'}>
                    Cancel
                  </Button>
                  <Button variant="primary" className="flex-1" onClick={handleConnect} disabled={!isValid || state === 'connecting'} loading={state === 'connecting'}>
                    {state === 'connecting' ? 'Connecting...' : 'Connect AWS'}
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

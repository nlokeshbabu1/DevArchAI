import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Cloud, CheckCircle, AlertCircle, Copy, Check,
  ChevronLeft, Shield, Globe, Key, ArrowRight,
} from 'lucide-react'
import { Button } from '@/components/ui'
import { cloudApi } from '@/api/endpoints/cloud'

interface AwsConnectModalProps {
  open: boolean
  onClose: () => void
}

type Step = 'account' | 'role' | 'regions' | 'review'

const STEPS: Array<{ key: Step; label: string; icon: React.ElementType }> = [
  { key: 'account', label: 'Account', icon: Globe },
  { key: 'role', label: 'IAM Role', icon: Key },
  { key: 'regions', label: 'Regions', icon: Shield },
  { key: 'review', label: 'Review', icon: CheckCircle },
]

const REGIONS = [
  { value: 'us-east-1', label: 'US East (N. Virginia)' },
  { value: 'us-east-2', label: 'US East (Ohio)' },
  { value: 'us-west-1', label: 'US West (N. California)' },
  { value: 'us-west-2', label: 'US West (Oregon)' },
  { value: 'eu-west-1', label: 'Europe (Ireland)' },
  { value: 'eu-west-2', label: 'Europe (London)' },
  { value: 'eu-central-1', label: 'Europe (Frankfurt)' },
  { value: 'eu-north-1', label: 'Europe (Stockholm)' },
  { value: 'ap-southeast-1', label: 'Asia Pacific (Singapore)' },
  { value: 'ap-southeast-2', label: 'Asia Pacific (Sydney)' },
  { value: 'ap-northeast-1', label: 'Asia Pacific (Tokyo)' },
  { value: 'ap-south-1', label: 'Asia Pacific (Mumbai)' },
  { value: 'sa-east-1', label: 'South America (Sao Paulo)' },
  { value: 'ca-central-1', label: 'Canada (Central)' },
]

const TRUST_POLICY_EXAMPLE = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:devarchai/*"
        }
      }
    }
  ]
}`

function generateExternalId(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

export function AwsConnectModal({ open, onClose }: AwsConnectModalProps) {
  const [step, setStep] = useState<Step>('account')
  const [accountId, setAccountId] = useState('')
  const [roleArn, setRoleArn] = useState('')
  const [externalId, setExternalId] = useState('')
  const [selectedRegions, setSelectedRegions] = useState<string[]>(['us-east-1'])
  const [connectionName, setConnectionName] = useState('')
  const [copiedExternalId, setCopiedExternalId] = useState(false)
  const [copiedPolicy, setCopiedPolicy] = useState(false)
  const [state, setState] = useState<'idle' | 'connecting' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  // Generate External ID once when modal opens
  useEffect(() => {
    if (open && !externalId) {
      setExternalId(generateExternalId())
    }
  }, [open, externalId])

  const stepIndex = STEPS.findIndex((s) => s.key === step)
  const isLastStep = step === 'review'

  const canProceed = (() => {
    switch (step) {
      case 'account':
        return accountId.length === 12
      case 'role':
        return roleArn.length > 0
      case 'regions':
        return selectedRegions.length > 0
      case 'review':
        return true
      default:
        return false
    }
  })()

  const handleNext = () => {
    const idx = STEPS.findIndex((s) => s.key === step)
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1].key)
  }

  const handleBack = () => {
    const idx = STEPS.findIndex((s) => s.key === step)
    if (idx > 0) setStep(STEPS[idx - 1].key)
  }

  const handleConnect = async () => {
    setState('connecting')
    setErrorMsg('')
    try {
      await cloudApi.connect({
        provider: 'aws',
        account_id: accountId,
        role_arn: roleArn,
        external_id: externalId,
        regions: selectedRegions,
        connection_name: connectionName || undefined,
      })
      setState('success')
      setTimeout(() => { onClose(); resetForm() }, 1500)
    } catch (err: unknown) {
      setState('error')
      const message = err instanceof Error ? err.message : 'Connection failed. Please verify your credentials.'
      setErrorMsg(message)
    }
  }

  const resetForm = () => {
    setAccountId('')
    setRoleArn('')
    setExternalId('')
    setSelectedRegions(['us-east-1'])
    setConnectionName('')
    setStep('account')
    setState('idle')
    setErrorMsg('')
    setCopiedExternalId(false)
    setCopiedPolicy(false)
  }

  const handleClose = () => {
    if (state !== 'connecting') {
      onClose()
      setTimeout(resetForm, 200)
    }
  }

  const toggleRegion = (region: string) => {
    setSelectedRegions((prev) =>
      prev.includes(region) ? prev.filter((r) => r !== region) : [...prev, region],
    )
  }

  const copyToClipboard = useCallback(async (text: string, onCopied: () => void) => {
    try {
      await navigator.clipboard.writeText(text)
      onCopied()
      setTimeout(() => onCopied(), 2000)
    } catch {
      // fallback
      const el = document.createElement('textarea')
      el.value = text
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      onCopied()
      setTimeout(() => onCopied(), 2000)
    }
  }, [])

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
            className="bg-card border border-white/10 rounded-2xl max-w-xl w-full shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Connect AWS"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-500/15 rounded-xl border border-orange-500/30">
                  <Cloud className="h-5 w-5 text-orange-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Connect AWS</h3>
                  <p className="text-sm text-muted-foreground">OIDC-based secure connection</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                disabled={state === 'connecting'}
                className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Step Indicator */}
            {state !== 'success' && (
              <div className="px-6 py-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  {STEPS.map((s, i) => {
                    const Icon = s.icon
                    const isCurrent = s.key === step
                    const isComplete = i < stepIndex
                    return (
                      <div key={s.key} className="flex items-center gap-2 flex-1">
                        <div
                          className={cn(
                            'flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium transition-all',
                            isComplete
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                              : isCurrent
                                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                                : 'bg-white/5 text-muted-foreground border border-white/10',
                          )}
                        >
                          {isComplete ? <CheckCircle className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                        </div>
                        <span
                          className={cn(
                            'text-xs font-medium hidden sm:block',
                            isCurrent ? 'text-foreground' : 'text-muted-foreground',
                          )}
                        >
                          {s.label}
                        </span>
                        {i < STEPS.length - 1 && (
                          <div className={cn('h-px flex-1', i < stepIndex ? 'bg-green-500/30' : 'bg-white/10')} />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Success */}
            {state === 'success' && (
              <div className="py-12 px-6 text-center space-y-3">
                <CheckCircle className="h-14 w-14 text-green-400 mx-auto" />
                <p className="text-lg font-semibold text-foreground">AWS Connected</p>
                <p className="text-sm text-muted-foreground">Your AWS account has been connected successfully.</p>
              </div>
            )}

            {/* Error */}
            {state === 'error' && (
              <div className="mx-6 mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-200">{errorMsg}</p>
              </div>
            )}

            {/* Step Content */}
            {state !== 'success' && (
              <div className="px-6 py-6 min-h-[360px]">
                <AnimatePresence mode="wait">
                  {step === 'account' && (
                    <motion.div
                      key="account"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-4"
                    >
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-1">AWS Account ID</h4>
                        <p className="text-xs text-muted-foreground mb-4">
                          Enter your 12-digit AWS account ID. Found in AWS Console → My Account.
                        </p>
                        <input
                          type="text"
                          value={accountId}
                          onChange={(e) => setAccountId(e.target.value.replace(/[^0-9]/g, '').slice(0, 12))}
                          placeholder="123456789012"
                          autoFocus
                          className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all font-mono text-lg tracking-wider"
                        />
                      </div>
                      <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                        <p className="text-xs text-muted-foreground">
                          <strong className="text-foreground">Security note:</strong> DevArchAI never stores your AWS credentials. We use OIDC federation with STS AssumeRole for read-only access.
                        </p>
                      </div>
                    </motion.div>
                  )}

                  {step === 'role' && (
                    <motion.div
                      key="role"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-4"
                    >
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-1">IAM Role Setup</h4>
                        <p className="text-xs text-muted-foreground mb-4">
                          Create an IAM Role in your AWS Console and paste the ARN here.
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">IAM Role ARN</label>
                        <input
                          type="text"
                          value={roleArn}
                          onChange={(e) => setRoleArn(e.target.value)}
                          placeholder="arn:aws:iam::123456789012:role/DevArchAI-Scanner"
                          autoFocus
                          className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all font-mono text-sm"
                        />
                      </div>

                      {/* External ID — generated by DevArchAI, read-only */}
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">
                          External ID
                          <span className="text-xs text-orange-400 ml-2 font-normal">Generated by DevArchAI</span>
                        </label>
                        <p className="text-xs text-muted-foreground mb-2">
                          Copy this ID and add it to your IAM Role's Trust Policy condition.
                        </p>
                        <div className="relative">
                          <input
                            type="text"
                            value={externalId}
                            readOnly
                            className="w-full pr-20 pl-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground font-mono text-sm cursor-default select-all"
                          />
                          <button
                            type="button"
                            onClick={() => copyToClipboard(externalId, () => setCopiedExternalId(true))}
                            className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-500/10 border border-orange-500/30 text-orange-400 hover:bg-orange-500/20 transition-all text-xs font-medium"
                          >
                            {copiedExternalId ? (
                              <><Check className="h-3 w-3" /> Copied</>
                            ) : (
                              <><Copy className="h-3 w-3" /> Copy</>
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">Connection Name (optional)</label>
                        <input
                          type="text"
                          value={connectionName}
                          onChange={(e) => setConnectionName(e.target.value)}
                          placeholder="My Production AWS"
                          className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all text-sm"
                        />
                      </div>

                      {/* Trust Policy Helper */}
                      <div className="p-3 rounded-xl bg-orange-500/5 border border-orange-500/20">
                        <div className="flex items-start justify-between mb-2">
                          <p className="text-xs font-semibold text-foreground">Example Trust Policy</p>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(TRUST_POLICY_EXAMPLE, () => setCopiedPolicy(true))}
                            className="text-[10px] text-orange-400 hover:text-orange-300 transition-colors"
                          >
                            {copiedPolicy ? 'Copied!' : 'Copy policy'}
                          </button>
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          In your AWS Console → IAM → Roles → Create Role → Trusted relationships, add a condition with <code className="text-orange-400">StringEquals</code> on the External ID.
                        </p>
                      </div>
                    </motion.div>
                  )}

                  {step === 'regions' && (
                    <motion.div
                      key="regions"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-4"
                    >
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-1">Select Regions</h4>
                        <p className="text-xs text-muted-foreground mb-4">
                          Choose which AWS regions to scan. More regions = more coverage but longer scans.
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-2 max-h-[240px] overflow-y-auto pr-1">
                        {REGIONS.map((region) => (
                          <button
                            key={region.value}
                            onClick={() => toggleRegion(region.value)}
                            className={cn(
                              'flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm text-left transition-all border',
                              selectedRegions.includes(region.value)
                                ? 'bg-orange-500/10 border-orange-500/30 text-orange-400'
                                : 'bg-white/5 border-white/10 text-muted-foreground hover:bg-white/10 hover:text-foreground',
                            )}
                          >
                            <div
                              className={cn(
                                'w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-all',
                                selectedRegions.includes(region.value)
                                  ? 'border-orange-500 bg-orange-500'
                                  : 'border-white/30',
                              )}
                            >
                              {selectedRegions.includes(region.value) && (
                                <CheckCircle className="h-2.5 w-2.5 text-white" />
                              )}
                            </div>
                            <span className="truncate">{region.label}</span>
                          </button>
                        ))}
                      </div>

                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{selectedRegions.length} region{selectedRegions.length !== 1 ? 's' : ''} selected</span>
                        <button
                          onClick={() =>
                            setSelectedRegions(selectedRegions.length === REGIONS.length ? [] : REGIONS.map((r) => r.value))
                          }
                          className="text-orange-400 hover:text-orange-300 transition-colors"
                        >
                          {selectedRegions.length === REGIONS.length ? 'Deselect all' : 'Select all'}
                        </button>
                      </div>
                    </motion.div>
                  )}

                  {step === 'review' && (
                    <motion.div
                      key="review"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-4"
                    >
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-1">Review & Connect</h4>
                        <p className="text-xs text-muted-foreground mb-4">
                          Verify your configuration before connecting.
                        </p>
                      </div>

                      <div className="space-y-3">
                        <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Account ID</p>
                          <p className="text-sm font-mono text-foreground">{accountId}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">IAM Role ARN</p>
                          <p className="text-sm font-mono text-foreground break-all">{roleArn}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">External ID</p>
                          <p className="text-sm font-mono text-foreground">{externalId}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Regions</p>
                          <p className="text-sm text-foreground">{selectedRegions.length} region{selectedRegions.length !== 1 ? 's' : ''}</p>
                        </div>
                        {connectionName && (
                          <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Connection Name</p>
                            <p className="text-sm text-foreground">{connectionName}</p>
                          </div>
                        )}
                      </div>

                      <div className="p-3 rounded-xl bg-orange-500/5 border border-orange-500/20">
                        <p className="text-xs text-muted-foreground">
                          DevArchAI will assume the IAM role using OIDC federation. No permanent credentials are stored. You can disconnect at any time.
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {/* Footer */}
            {state !== 'success' && (
              <div className="flex gap-3 px-6 py-4 border-t border-white/10">
                <Button variant="secondary" className="flex-1" onClick={handleClose} disabled={state === 'connecting'}>
                  Cancel
                </Button>
                {stepIndex > 0 && (
                  <Button variant="secondary" onClick={handleBack} disabled={state === 'connecting'}>
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Back
                  </Button>
                )}
                {isLastStep ? (
                  <Button
                    variant="primary"
                    className="flex-1"
                    onClick={handleConnect}
                    disabled={state === 'connecting'}
                    loading={state === 'connecting'}
                  >
                    {state === 'connecting' ? (
                      'Connecting...'
                    ) : (
                      <>
                        <Key className="h-4 w-4 mr-2" />
                        Connect AWS
                      </>
                    )}
                  </Button>
                ) : (
                  <Button variant="primary" onClick={handleNext} disabled={!canProceed}>
                    Next
                    <ArrowRight className="h-4 w-4 ml-1" />
                  </Button>
                )}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}

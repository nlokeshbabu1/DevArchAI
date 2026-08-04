import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Cloud, CheckCircle, AlertCircle, Copy, Check,
  ChevronRight, Shield, Globe, ArrowRight, ExternalLink,
  Loader2, Database, Lock, Activity, Eye, Clock, Zap, Rocket,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { cloudApi, type WizardInitResponse, type WizardVerifyResponse } from '@/api/endpoints/cloud'

interface AwsOnboardingWizardProps {
  open: boolean
  onClose: () => void
  onComplete: (data?: { connectionId: string; connectionName: string; accountId: string; action: 'scan' | 'dashboard' }) => void
}

type WizardStep = 'account' | 'deploy' | 'verify' | 'complete'

const STEPS: Array<{ key: WizardStep; label: string; number: number }> = [
  { key: 'account', label: 'Account', number: 1 },
  { key: 'deploy', label: 'Deploy Stack', number: 2 },
  { key: 'verify', label: 'Verify', number: 3 },
  { key: 'complete', label: 'Complete', number: 4 },
]

const PERMISSION_CHECKS = [
  { label: 'Checking IAM Role...', icon: Shield, duration: 800 },
  { label: 'Checking Permissions...', icon: Lock, duration: 1200 },
  { label: 'Checking Regions...', icon: Globe, duration: 1000 },
  { label: 'Checking STS...', icon: Activity, duration: 900 },
  { label: 'Checking Cost Explorer...', icon: Database, duration: 1100 },
  { label: 'Checking CloudTrail...', icon: Eye, duration: 1000 },
]

export function AwsOnboardingWizard({ open, onClose, onComplete }: AwsOnboardingWizardProps) {
  const [step, setStep] = useState<WizardStep>('account')
  const [accountId, setAccountId] = useState('')
  const [connectionName, setConnectionName] = useState('')
  const [wizardData, setWizardData] = useState<WizardInitResponse | null>(null)
  const [verifyResult, setVerifyResult] = useState<WizardVerifyResponse | null>(null)
  const [copiedExternalId, setCopiedExternalId] = useState(false)
  const [copiedTemplateUrl, setCopiedTemplateUrl] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [verifyingStep, setVerifyingStep] = useState(0)
  const [isVerifying, setIsVerifying] = useState(false)
  const [completedConnection, setCompletedConnection] = useState<{ connectionId: string; connectionName: string; accountId: string } | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  const stepIndex = STEPS.findIndex((s) => s.key === step)
  const isLastStep = step === 'complete'

  const canProceed = (() => {
    switch (step) {
      case 'account':
        return accountId.length === 12
      case 'deploy':
        return true
      case 'verify':
        return false
      case 'complete':
        return true
      default:
        return false
    }
  })()

  const handleNext = async () => {
    if (step === 'account') {
      // Initialize wizard
      setLoading(true)
      setError('')
      try {
        const result = await cloudApi.initWizard({
          account_id: accountId,
          connection_name: connectionName || undefined,
        })
        setWizardData(result)
        setStep('deploy')
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to initialize wizard'
        setError(message)
      } finally {
        setLoading(false)
      }
    } else if (step === 'deploy') {
      setStep('verify')
      startVerification()
    } else if (step === 'complete') {
      onComplete(completedConnection ? { ...completedConnection, action: 'dashboard' } : undefined)
      resetForm()
    }
  }

  const handleBack = () => {
    const idx = STEPS.findIndex((s) => s.key === step)
    if (idx > 0) setStep(STEPS[idx - 1].key)
  }

  const startVerification = async () => {
    if (!wizardData) return

    setIsVerifying(true)
    setVerifyingStep(0)

    // Animate through permission checks
    for (let i = 0; i < PERMISSION_CHECKS.length; i++) {
      setVerifyingStep(i)
      await new Promise((r) => setTimeout(r, PERMISSION_CHECKS[i].duration))
    }

    // Actually verify
    try {
      const result = await cloudApi.verifyWizard(wizardData.wizard_id)
      setVerifyResult(result)

      if (result.success) {
        // Complete the wizard
        const completeResult = await cloudApi.completeWizard(wizardData.wizard_id, {
          wizard_id: wizardData.wizard_id,
          regions: result.regions,
        })
        setCompletedConnection({
          connectionId: completeResult.connection.id,
          connectionName: completeResult.connection.connection_name,
          accountId: completeResult.connection.account_id,
        })
        setStep('complete')
      } else {
        setError(result.error || 'Verification failed')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Verification failed'
      setError(message)
    } finally {
      setIsVerifying(false)
    }
  }

  const resetForm = () => {
    setAccountId('')
    setConnectionName('')
    setWizardData(null)
    setVerifyResult(null)
    setStep('account')
    setLoading(false)
    setError('')
    setVerifyingStep(0)
    setIsVerifying(false)
    setCopiedExternalId(false)
    setCopiedTemplateUrl(false)
    setCompletedConnection(null)
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const handleClose = () => {
    if (!loading && !isVerifying) {
      onClose()
      setTimeout(resetForm, 200)
    }
  }

  const copyToClipboard = useCallback(async (text: string, onCopied: () => void) => {
    try {
      await navigator.clipboard.writeText(text)
      onCopied()
      setTimeout(() => onCopied(), 2000)
    } catch {
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

  const openCloudFormation = () => {
    if (wizardData?.cloudformation_url) {
      window.open(wizardData.cloudformation_url, '_blank', 'noopener,noreferrer')
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
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="bg-card border border-white/10 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Connect AWS Account"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-xl border border-amber-500/30">
                  <Cloud className="h-5 w-5 text-amber-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Connect AWS Account</h3>
                  <p className="text-xs text-muted-foreground">Secure, read-only access via IAM roles</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                disabled={loading || isVerifying}
                className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Step Indicator */}
            {step !== 'complete' && (
              <div className="px-6 py-4 border-b border-white/5">
                <div className="flex items-center gap-1">
                  {STEPS.map((s, i) => {
                    const isCurrent = s.key === step
                    const isComplete = i < stepIndex
                    return (
                      <div key={s.key} className="flex items-center flex-1">
                        <div className="flex items-center gap-2">
                          <div
                            className={cn(
                              'flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-all',
                              isComplete
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : isCurrent
                                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                  : 'bg-white/5 text-muted-foreground/50 border border-white/10',
                            )}
                          >
                            {isComplete ? (
                              <CheckCircle className="h-3.5 w-3.5" />
                            ) : (
                              s.number
                            )}
                          </div>
                          <span
                            className={cn(
                              'text-xs font-medium hidden sm:block',
                              isCurrent ? 'text-foreground' : 'text-muted-foreground/50',
                            )}
                          >
                            {s.label}
                          </span>
                        </div>
                        {i < STEPS.length - 1 && (
                          <div className={cn(
                            'h-px flex-1 mx-3',
                            i < stepIndex ? 'bg-emerald-500/30' : 'bg-white/10',
                          )} />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Step Content */}
            <div className="px-6 py-6 min-h-[420px]">
              <AnimatePresence mode="wait">
                {/* Step 1: Account */}
                {step === 'account' && (
                  <motion.div
                    key="account"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-6"
                  >
                    {/* Illustration */}
                    <div className="flex justify-center">
                      <div className="relative">
                        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center">
                          <Cloud className="h-10 w-10 text-amber-400" />
                        </div>
                        <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                          <Lock className="h-3 w-3 text-white" />
                        </div>
                      </div>
                    </div>

                    <div className="text-center space-y-2">
                      <h4 className="text-lg font-semibold text-foreground">
                        Enter your AWS Account ID
                      </h4>
                      <p className="text-sm text-muted-foreground max-w-md mx-auto">
                        DevArchAI securely connects to your AWS account using IAM roles.
                        We never store long-lived credentials. Read-only access only.
                      </p>
                    </div>

                    <div className="space-y-4 max-w-sm mx-auto">
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-2">
                          AWS Account ID
                        </label>
                        <input
                          type="text"
                          value={accountId}
                          onChange={(e) => setAccountId(e.target.value.replace(/[^0-9]/g, '').slice(0, 12))}
                          placeholder="123456789012"
                          autoFocus
                          className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 transition-all font-mono text-lg tracking-wider text-center"
                        />
                        <p className="text-[11px] text-muted-foreground/60 mt-2 text-center">
                          Found in AWS Console → My Account → Account ID
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-foreground mb-2">
                          Account Name <span className="text-muted-foreground/50">(optional)</span>
                        </label>
                        <input
                          type="text"
                          value={connectionName}
                          onChange={(e) => setConnectionName(e.target.value)}
                          placeholder="Production, Staging, etc."
                          className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 transition-all text-sm text-center"
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground/60">
                      <Shield className="h-3.5 w-3.5" />
                      <span>You can disconnect at any time</span>
                    </div>
                  </motion.div>
                )}

                {/* Step 2: Deploy Stack */}
                {step === 'deploy' && (
                  <motion.div
                    key="deploy"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-6"
                  >
                    <div className="text-center space-y-2">
                      <h4 className="text-lg font-semibold text-foreground">
                        Deploy CloudFormation Stack
                      </h4>
                      <p className="text-sm text-muted-foreground max-w-md mx-auto">
                        One click creates everything you need. The stack sets up a
                        read-only IAM role that DevArchAI can securely assume.
                      </p>
                    </div>

                    {/* Launch Button */}
                    <div className="flex justify-center">
                      <button
                        onClick={openCloudFormation}
                        className="group flex items-center gap-3 px-6 py-4 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40 transition-all"
                      >
                        <Rocket className="h-5 w-5" />
                        Launch CloudFormation
                        <ExternalLink className="h-4 w-4 opacity-70 group-hover:opacity-100 transition-opacity" />
                      </button>
                    </div>

                    {/* What will be created */}
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <p className="text-xs font-semibold text-foreground mb-3">What will be created:</p>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          'IAM Role',
                          'ReadOnly Policy',
                          'External ID',
                          'Secure Trust Relationship',
                          'Cost Explorer Access',
                          'CloudWatch Access',
                        ].map((item) => (
                          <div key={item} className="flex items-center gap-2 text-xs text-muted-foreground">
                            <CheckCircle className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                            {item}
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3.5 w-3.5" />
                        Estimated time: ~1 minute
                      </div>
                    </div>

                    {/* External ID (for reference) */}
                    {wizardData && (
                      <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-[10px] uppercase tracking-wider text-amber-400 font-medium">
                            External ID (auto-generated)
                          </p>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(wizardData.external_id, () => setCopiedExternalId(true))}
                            className="text-[10px] text-amber-400 hover:text-amber-300 transition-colors"
                          >
                            {copiedExternalId ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                        <p className="text-xs font-mono text-foreground break-all">
                          {wizardData.external_id}
                        </p>
                      </div>
                    )}

                    <p className="text-xs text-muted-foreground/60 text-center">
                      After the stack shows <span className="text-emerald-400 font-medium">CREATE_COMPLETE</span>, click Continue below
                    </p>
                  </motion.div>
                )}

                {/* Step 3: Verify */}
                {step === 'verify' && (
                  <motion.div
                    key="verify"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-6"
                  >
                    <div className="text-center space-y-2">
                      <h4 className="text-lg font-semibold text-foreground">
                        Verifying Connection
                      </h4>
                      <p className="text-sm text-muted-foreground max-w-md mx-auto">
                        We're validating your AWS account and permissions. This usually takes 10-15 seconds.
                      </p>
                    </div>

                    {/* Animated verification steps */}
                    <div className="space-y-3 max-w-sm mx-auto">
                      {PERMISSION_CHECKS.map((check, i) => {
                        const Icon = check.icon
                        const isActive = i === verifyingStep
                        const isComplete = i < verifyingStep
                        const isPending = i > verifyingStep

                        return (
                          <motion.div
                            key={check.label}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className={cn(
                              'flex items-center gap-3 px-4 py-3 rounded-xl border transition-all',
                              isComplete
                                ? 'bg-emerald-500/5 border-emerald-500/20'
                                : isActive
                                  ? 'bg-amber-500/5 border-amber-500/20'
                                  : 'bg-white/5 border-white/10 opacity-50',
                            )}
                          >
                            <div className={cn(
                              'flex items-center justify-center w-8 h-8 rounded-lg',
                              isComplete
                                ? 'bg-emerald-500/20'
                                : isActive
                                  ? 'bg-amber-500/20'
                                  : 'bg-white/5',
                            )}>
                              {isComplete ? (
                                <CheckCircle className="h-4 w-4 text-emerald-400" />
                              ) : isActive ? (
                                <Loader2 className="h-4 w-4 text-amber-400 animate-spin" />
                              ) : (
                                <Icon className="h-4 w-4 text-muted-foreground/50" />
                              )}
                            </div>
                            <span className={cn(
                              'text-sm font-medium',
                              isComplete
                                ? 'text-emerald-400'
                                : isActive
                                  ? 'text-foreground'
                                  : 'text-muted-foreground/50',
                            )}>
                              {check.label}
                            </span>
                          </motion.div>
                        )
                      })}
                    </div>

                    {/* Error display */}
                    {error && (
                      <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2 max-w-sm mx-auto">
                        <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm text-red-200">{error}</p>
                          <button
                            onClick={() => {
                              setError('')
                              startVerification()
                            }}
                            className="text-xs text-red-400 hover:text-red-300 mt-2 underline"
                          >
                            Try again
                          </button>
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Step 4: Complete */}
                {step === 'complete' && (
                  <motion.div
                    key="complete"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="space-y-6"
                  >
                    {/* Success animation */}
                    <div className="flex justify-center">
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', damping: 15, stiffness: 200 }}
                        className="relative"
                      >
                        <div className="w-20 h-20 rounded-full bg-emerald-500/20 border-2 border-emerald-500/30 flex items-center justify-center">
                          <CheckCircle className="h-10 w-10 text-emerald-400" />
                        </div>
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ delay: 0.3, type: 'spring' }}
                          className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center"
                        >
                          <Zap className="h-3 w-3 text-white" />
                        </motion.div>
                      </motion.div>
                    </div>

                    <div className="text-center space-y-2">
                      <h4 className="text-xl font-bold text-foreground">
                        AWS Account Connected
                      </h4>
                      <p className="text-sm text-muted-foreground">
                        Your AWS account is verified and ready to scan.
                      </p>
                    </div>

                    {/* Status checklist */}
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3 max-w-sm mx-auto">
                      {[
                        'AWS Account Connected',
                        'IAM Role Verified',
                        'Ready to Scan',
                      ].map((label) => (
                        <div key={label} className="flex items-center gap-3">
                          <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                            <CheckCircle className="h-3 w-3 text-emerald-400" />
                          </div>
                          <span className="text-sm font-medium text-foreground">{label}</span>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer */}
            {step !== 'complete' && (
              <div className="flex gap-3 px-6 py-4 border-t border-white/10">
                <button
                  onClick={handleClose}
                  disabled={loading || isVerifying}
                  className="px-4 py-2.5 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
                >
                  Cancel
                </button>
                <div className="flex-1" />
                {stepIndex > 0 && step !== 'verify' && (
                  <button
                    onClick={handleBack}
                    disabled={loading || isVerifying}
                    className="px-4 py-2.5 rounded-xl text-sm font-medium bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all disabled:opacity-50"
                  >
                    Back
                  </button>
                )}
                {step === 'verify' ? null : (
                  <button
                    onClick={handleNext}
                    disabled={!canProceed || loading}
                    className={cn(
                      'flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold transition-all',
                      step === 'deploy'
                        ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40'
                        : 'bg-white/10 text-foreground hover:bg-white/15 border border-white/10',
                      loading && 'opacity-50 cursor-not-allowed',
                    )}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Initializing...
                      </>
                    ) : step === 'deploy' ? (
                      <>
                        Continue
                        <ChevronRight className="h-4 w-4" />
                      </>
                    ) : (
                      <>
                        Continue
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                )}
              </div>
            )}

            {/* Complete footer */}
            {step === 'complete' && (
              <div className="flex gap-3 px-6 py-4 border-t border-white/10">
                <button
                  onClick={() => {
                    onComplete(completedConnection ? { ...completedConnection, action: 'scan' } : undefined)
                    resetForm()
                  }}
                  className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold bg-gradient-to-r from-emerald-500 to-green-500 text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 transition-all"
                >
                  <Rocket className="h-4 w-4" />
                  Run First Scan
                </button>
                <button
                  onClick={() => {
                    onComplete(completedConnection ? { ...completedConnection, action: 'dashboard' } : undefined)
                    resetForm()
                  }}
                  className="px-6 py-3 rounded-xl text-sm font-medium bg-white/10 text-foreground hover:bg-white/15 border border-white/10 transition-all"
                >
                  Go To Dashboard
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

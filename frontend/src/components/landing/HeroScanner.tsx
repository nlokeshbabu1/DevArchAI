import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Github, Loader2, Shield, CheckCircle, AlertTriangle, GitBranch, Sparkles, Zap, Cloud, Code, Lock } from 'lucide-react'
import { Button, Card } from '../ui-animated'
import { cn } from '../../lib/utils'
import { useNavigate } from 'react-router-dom'

interface HeroScannerProps {
  onScanComplete?: (sessionId: string) => void
}

const scanSteps = [
  { id: 'clone', label: 'Repository Cloned', icon: Github },
  { id: 'detect', label: 'Stack Detection', icon: Code },
  { id: 'security', label: 'Security Rules Scan', icon: Shield },
  { id: 'ai', label: 'AI Infrastructure Analysis', icon: Zap },
  { id: 'score', label: 'Production Readiness Score', icon: CheckCircle },
]

export function HeroScanner({ onScanComplete }: HeroScannerProps) {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [showBranchInput, setShowBranchInput] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState(0)
  const [scanStatus, setScanStatus] = useState<'idle' | 'scanning' | 'complete' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // Auto-detect branch from URL when user types
  useEffect(() => {
    if (repoUrl) {
      const treeMatch = repoUrl.match(/\/tree\/([^/]+)/)
      if (treeMatch && treeMatch[1]) {
        setBranch(treeMatch[1])
        setShowBranchInput(true)
      } else {
        setBranch('main')
        setShowBranchInput(false)
      }
    }
  }, [repoUrl])

  // Animate scan steps
  useEffect(() => {
    if (isScanning && scanStatus === 'scanning') {
      const stepInterval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= scanSteps.length - 1) return prev
          return prev + 1
        })
      }, 1500)

      return () => clearInterval(stepInterval)
    }
  }, [isScanning, scanStatus])

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!repoUrl.trim()) {
      setErrorMessage('Please enter a GitHub repository URL')
      return
    }

    const githubRegex = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+(\/tree\/[\w-]+)?\/?$/
    if (!githubRegex.test(repoUrl)) {
      setErrorMessage('Please enter a valid GitHub repository URL')
      return
    }

    const cleanUrl = repoUrl.replace(/\/tree\/[\w-]+/, '')

    setIsScanning(true)
    setScanStatus('scanning')
    setScanProgress(0)
    setCurrentStep(0)
    setErrorMessage('')

    try {
      const progressInterval = setInterval(() => {
        setScanProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 5
        })
      }, 200)

      const response = await fetch('/api/v1/public/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository_url: cleanUrl,
          branch: branch,
        }),
      })

      clearInterval(progressInterval)
      setScanProgress(100)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Scan failed')
      }

      const data = await response.json()

      if (data.status === 'failed') {
        throw new Error(data.message || 'Scan processing failed')
      }

      setScanStatus('complete')
      sessionStorage.setItem('anonScanToken', data.session_token)
      sessionStorage.setItem('anonScanRepo', data.repository_name)
      if (data.branch) {
        sessionStorage.setItem('anonScanBranch', data.branch)
      }

      setTimeout(() => {
        navigate(`/scan/results/${data.session_token}`)
        onScanComplete?.(data.session_token)
      }, 2000)

    } catch (error) {
      console.error('Scan error:', error)
      setScanStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Failed to start scan. Please try again.')
      setIsScanning(false)
    }
  }

  const resetScan = () => {
    setRepoUrl('')
    setBranch('main')
    setShowBranchInput(false)
    setIsScanning(false)
    setScanStatus('idle')
    setScanProgress(0)
    setCurrentStep(0)
    setErrorMessage('')
  }

  return (
    <div className="w-full max-w-5xl mx-auto">
      <AnimatePresence mode="wait">
        {scanStatus === 'idle' || scanStatus === 'error' ? (
          <motion.div
            key="scanner-form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-8"
          >
            {/* Header */}
            <div className="text-center space-y-4">
              <motion.div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/15 border border-primary/30 backdrop-blur-sm"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-primary">AI-Powered DevSecOps Platform</span>
              </motion.div>

              <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight">
                <span className="gradient-text">Secure Your DevOps</span>
                <br />
                <span className="text-foreground">Before Production</span>
              </h1>

              <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
                Scan your GitHub repository for Kubernetes risks, Terraform security issues, 
                CI/CD vulnerabilities, and cloud misconfigurations.
              </p>
            </div>

            {/* Scanner Form */}
            <motion.form
              onSubmit={handleScan}
              className="space-y-4 max-w-3xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Github className="h-5 w-5 text-muted-foreground" />
                </div>
                <input
                  type="url"
                  value={repoUrl}
                  onChange={(e) => {
                    setRepoUrl(e.target.value)
                    setErrorMessage('')
                  }}
                  placeholder="github.com/organization/repository"
                  className={cn(
                    'w-full pl-12 pr-4 py-5 rounded-xl bg-white/5 border-2 text-foreground text-lg placeholder:text-muted-foreground focus:outline-none focus:ring-2 transition-all',
                    errorMessage
                      ? 'border-red-500/50 focus:ring-red-500/50'
                      : 'border-white/10 focus:ring-primary/50 focus:border-primary/50'
                  )}
                  disabled={isScanning}
                />
              </div>

              {/* Branch Input - Auto-detected */}
              {showBranchInput && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="flex items-center gap-2 max-w-md mx-auto"
                >
                  <div className="relative flex-1">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <GitBranch className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <input
                      type="text"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      placeholder="Branch name"
                      className="w-full pl-10 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                      disabled={isScanning}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setBranch('main')
                      setShowBranchInput(false)
                    }}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Reset
                  </button>
                </motion.div>
              )}

              {errorMessage && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 text-red-400 text-sm max-w-md mx-auto"
                >
                  <AlertTriangle className="h-4 w-4" />
                  {errorMessage}
                </motion.div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full py-6 text-lg font-semibold"
                disabled={isScanning}
                glow
              >
                {isScanning ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Starting Scan...
                  </>
                ) : (
                  <>
                    <Shield className="h-5 w-5 mr-2" />
                    Start Free Scan
                    <ArrowRight className="h-5 w-5 ml-2" />
                  </>
                )}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                <CheckCircle className="h-4 w-4 inline mr-1 text-green-400" />
                No signup required • Results in 10 seconds
              </p>
            </motion.form>

            {/* Feature Pills */}
            <motion.div
              className="flex flex-wrap justify-center gap-3 pt-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              {[
                { icon: Cloud, label: 'Kubernetes Risks' },
                { icon: Code, label: 'Terraform Security' },
                { icon: Zap, label: 'CI/CD Vulnerabilities' },
                { icon: Lock, label: 'Cloud Misconfigurations' },
              ].map((feature, i) => (
                <div
                  key={feature.label}
                  className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-muted-foreground"
                >
                  <feature.icon className="h-4 w-4 text-primary" />
                  {feature.label}
                </div>
              ))}
            </motion.div>
          </motion.div>
        ) : scanStatus === 'scanning' ? (
          <motion.div
            key="scanning"
            className="space-y-8"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            {/* Scanning Header */}
            <div className="text-center space-y-4">
              <motion.div
                className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600"
                animate={{
                  rotate: [0, 5, -5, 0],
                  scale: [1, 1.05, 1],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  repeatType: 'reverse',
                }}
              >
                <Shield className="h-12 w-12 text-white" />
              </motion.div>

              <div>
                <h3 className="text-2xl font-semibold text-foreground mb-2">
                  Scanning {repoUrl.split('/').slice(-2).join('/').replace('/tree/' + branch, '')}
                </h3>
                <p className="text-muted-foreground">
                  Branch: <span className="text-primary font-mono">{branch}</span>
                </p>
              </div>
            </div>

            {/* Pipeline Animation */}
            <div className="max-w-4xl mx-auto">
              {/* Progress Bar */}
              <div className="space-y-2 mb-8">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="text-foreground font-medium">{scanProgress}%</span>
                </div>
                <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-primary to-indigo-600"
                    initial={{ width: 0 }}
                    animate={{ width: `${scanProgress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>

              {/* Pipeline Steps */}
              <div className="relative">
                {/* Connection Line */}
                <div className="absolute top-8 left-0 right-0 h-0.5 bg-white/10 hidden md:block" />
                
                <div className="grid grid-cols-5 gap-2 md:gap-4">
                  {scanSteps.map((step, index) => {
                    const isCompleted = index < currentStep
                    const isCurrent = index === currentStep
                    const Icon = step.icon

                    return (
                      <motion.div
                        key={step.id}
                        className="flex flex-col items-center gap-3"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                      >
                        <div
                          className={cn(
                            'relative z-10 w-16 h-16 rounded-full flex items-center justify-center border-2 transition-all duration-500',
                            isCompleted
                              ? 'bg-green-500/20 border-green-500/50'
                              : isCurrent
                              ? 'bg-primary/20 border-primary/50 shadow-lg shadow-primary/30'
                              : 'bg-white/5 border-white/10'
                          )}
                        >
                          {isCompleted ? (
                            <CheckCircle className="h-8 w-8 text-green-400" />
                          ) : (
                            <Icon
                              className={cn(
                                'h-8 w-8',
                                isCurrent ? 'text-primary animate-pulse' : 'text-muted-foreground'
                              )}
                            />
                          )}
                        </div>
                        <span
                          className={cn(
                            'text-xs font-medium text-center hidden md:block',
                            isCompleted || isCurrent ? 'text-foreground' : 'text-muted-foreground'
                          )}
                        >
                          {step.label}
                        </span>
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}

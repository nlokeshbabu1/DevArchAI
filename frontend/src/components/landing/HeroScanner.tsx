import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowRight, Github, Loader2, Shield, CheckCircle, AlertTriangle, 
  GitBranch, ChevronDown, Cloud, Code, Zap, Lock, Layers, Server 
} from 'lucide-react'
import { Button, Card } from '../ui-animated'
import { cn } from '../../lib/utils'
import { useNavigate } from 'react-router-dom'

interface HeroScannerProps {
  onScanComplete?: (sessionId: string) => void
}

export function HeroScanner({ onScanComplete }: HeroScannerProps) {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [availableBranches, setAvailableBranches] = useState<string[]>([])
  const [isFetchingBranches, setIsFetchingBranches] = useState(false)
  const [showBranchDropdown, setShowBranchDropdown] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)
  const [scanStatus, setScanStatus] = useState<'idle' | 'scanning' | 'complete' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // Fetch available branches from backend API
  const fetchBranches = async (repoUrl: string) => {
    setIsFetchingBranches(true)
    try {
      const response = await fetch(`/api/v1/github/branches?repo_url=${encodeURIComponent(repoUrl)}`)
      
      if (response.ok) {
        const data = await response.json()
        const branchNames = data.branches.map((b: any) => b.name)
        setAvailableBranches(branchNames)

        // Set default branch - prioritize master if it exists, otherwise main
        let defaultBranch = data.branches.find((b: any) => b.name === 'master')
        if (!defaultBranch) {
          defaultBranch = data.branches.find((b: any) => b.name === 'main')
        }
        if (!defaultBranch) {
          defaultBranch = data.branches.find((b: any) => b.protected)
        }
        if (!defaultBranch && branchNames.length > 0) {
          defaultBranch = data.branches[0]
        }

        if (defaultBranch) {
          setBranch(defaultBranch.name)
        }

        if (branchNames.length > 0) {
          setShowBranchDropdown(true)
        }
      }
    } catch (error) {
      console.error('Failed to fetch branches:', error)
    } finally {
      setIsFetchingBranches(false)
    }
  }

  // Auto-detect branch from URL when user types
  useEffect(() => {
    if (repoUrl) {
      const treeMatch = repoUrl.match(/\/tree\/([^/]+)/)
      if (treeMatch && treeMatch[1]) {
        setBranch(treeMatch[1])
        setShowBranchDropdown(true)
      } else {
        const match = repoUrl.match(/github\.com\/([^/]+)\/([^/]+)/)
        if (match) {
          const timeoutId = setTimeout(() => {
            fetchBranches(repoUrl.replace('.git', ''))
          }, 500)
          return () => clearTimeout(timeoutId)
        } else {
          setBranch('main')
          setShowBranchDropdown(false)
        }
      }
    }
  }, [repoUrl])

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

      setTimeout(() => {
        navigate(`/scan/results/${data.session_token}`)
        onScanComplete?.(data.session_token)
      }, 1000)

    } catch (error) {
      console.error('Scan error:', error)
      setScanStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Failed to start scan. Please try again.')
      setIsScanning(false)
    }
  }

  return (
    <div className="w-full max-w-7xl mx-auto">
      <div className="grid lg:grid-cols-2 gap-12 items-center">
        {/* LEFT SIDE - Hero Content */}
        <motion.div 
          className="space-y-8 text-left"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Headline */}
          <div className="space-y-4">
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-tight">
              <span className="gradient-text">Secure Your DevOps</span>
              <br />
              <span className="text-foreground">Before Production</span>
            </h1>

            {/* Description */}
            <p className="text-xl text-muted-foreground max-w-xl">
              Scan your GitHub repository for Kubernetes risks, Terraform security issues, 
              CI/CD vulnerabilities, and cloud misconfigurations.
            </p>

            {/* Small line */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle className="h-4 w-4 text-green-400" />
              <span>No signup required • Results in 10 seconds</span>
            </div>
          </div>

          {/* Feature Tags */}
          <div className="flex flex-wrap gap-3">
            {[
              { label: 'Kubernetes Risks', icon: Cloud },
              { label: 'Terraform Security', icon: Layers },
              { label: 'CI/CD Vulnerabilities', icon: Zap },
              { label: 'Cloud Misconfigurations', icon: Server },
            ].map((feature) => (
              <div
                key={feature.label}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/5 border border-white/10 text-sm text-muted-foreground hover:border-primary/30 hover:text-primary transition-all cursor-default"
              >
                <feature.icon className="h-4 w-4 text-primary" />
                {feature.label}
              </div>
            ))}
          </div>
        </motion.div>

        {/* RIGHT SIDE - Scanner Form */}
        <motion.div
          className="relative"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {/* DevSecOps Rotating Animation - TOP LEFT */}
          <div className="absolute -top-20 -left-20 hidden lg:block">
            <DevSecOpsAnimation />
          </div>

          {/* Scanner Card */}
          <Card className="p-8 relative z-10" hover={false}>
            {scanStatus === 'idle' || scanStatus === 'error' ? (
              <form onSubmit={handleScan} className="space-y-6">
                {/* Repository URL Input */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    GitHub Repository URL
                  </label>
                  <div className="relative">
                    <Github className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    <input
                      type="url"
                      value={repoUrl}
                      onChange={(e) => {
                        setRepoUrl(e.target.value)
                        setErrorMessage('')
                      }}
                      placeholder="github.com/organization/repository"
                      className={cn(
                        'w-full pl-12 pr-4 py-3.5 rounded-xl bg-white/5 border-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 transition-all',
                        errorMessage
                          ? 'border-red-500/50 focus:ring-red-500/50'
                          : 'border-white/10 focus:ring-primary/50 focus:border-primary/50'
                      )}
                      disabled={isScanning}
                    />
                  </div>
                </div>

                {/* Branch Selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    Branch
                  </label>
                  <div className="relative">
                    <GitBranch className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    {availableBranches.length > 0 ? (
                      <select
                        value={branch}
                        onChange={(e) => setBranch(e.target.value)}
                        className="w-full pl-12 pr-10 py-3.5 rounded-xl bg-white/5 border-2 border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 appearance-none cursor-pointer"
                        disabled={isScanning || isFetchingBranches}
                      >
                        {availableBranches.map((b) => (
                          <option key={b} value={b} className="bg-background">
                            {b}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={branch}
                        onChange={(e) => setBranch(e.target.value)}
                        placeholder="main"
                        className="w-full pl-12 pr-4 py-3.5 rounded-xl bg-white/5 border-2 border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                        disabled={isScanning || isFetchingBranches}
                      />
                    )}
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
                      {isFetchingBranches ? (
                        <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
                      ) : (
                        <ChevronDown className="h-5 w-5 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Error Message */}
                {errorMessage && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 text-red-400 text-sm"
                  >
                    <AlertTriangle className="h-4 w-4" />
                    {errorMessage}
                  </motion.div>
                )}

                {/* Submit Button */}
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  className="w-full py-4 text-lg font-semibold"
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
              </form>
            ) : scanStatus === 'scanning' ? (
              <div className="space-y-6 text-center">
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
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    Scanning Repository
                  </h3>
                  <p className="text-muted-foreground">
                    Branch: <span className="text-primary font-mono">{branch}</span>
                  </p>
                </div>

                {/* Progress Bar */}
                <div className="space-y-2">
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
              </div>
            ) : null}
          </Card>
        </motion.div>
      </div>
    </div>
  )
}

// DevSecOps Rotating Animation Component
function DevSecOpsAnimation() {
  const tools = [
    { Icon: Cloud, label: 'Kubernetes', color: 'text-blue-400' },
    { Icon: Layers, label: 'Terraform', color: 'text-purple-400' },
    { Icon: Zap, label: 'CI/CD', color: 'text-yellow-400' },
    { Icon: Lock, label: 'Security', color: 'text-green-400' },
    { Icon: Code, label: 'DevOps', color: 'text-red-400' },
  ]

  return (
    <div className="relative w-48 h-48">
      {/* Outer rotating ring with tools */}
      <motion.div
        className="absolute inset-0 rounded-full border-2 border-dashed border-primary/30"
        animate={{ rotate: 360 }}
        transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
      />

      {/* Middle rotating ring (opposite direction) */}
      <motion.div
        className="absolute inset-4 rounded-full border-2 border-dashed border-indigo-500/30"
        animate={{ rotate: -360 }}
        transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
      />

      {/* Central shield icon */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center"
        animate={{ scale: [1, 1.1, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30 flex items-center justify-center">
          <Shield className="h-10 w-10 text-primary" />
        </div>
      </motion.div>

      {/* Orbiting tool icons */}
      {tools.map((tool, index) => {
        const angle = (index / tools.length) * 2 * Math.PI
        const radius = 80
        const x = Math.cos(angle) * radius
        const y = Math.sin(angle) * radius

        return (
          <motion.div
            key={tool.label}
            className="absolute"
            style={{
              left: '50%',
              top: '50%',
              x,
              y,
            }}
            animate={{ rotate: 360 }}
            transition={{
              duration: 30,
              repeat: Infinity,
              ease: 'linear',
            }}
          >
            <motion.div
              className="absolute -translate-x-1/2 -translate-y-1/2 p-2.5 rounded-xl bg-gradient-to-br from-white/10 to-white/5 border border-white/20 backdrop-blur-sm"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: index * 0.2,
              }}
              whileHover={{ scale: 1.3 }}
            >
              <tool.Icon className={cn('h-5 w-5', tool.color)} />
            </motion.div>
          </motion.div>
        )
      })}

      {/* Scanning beam effect */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'conic-gradient(from 0deg, transparent, rgba(99, 102, 241, 0.2), transparent)',
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  )
}

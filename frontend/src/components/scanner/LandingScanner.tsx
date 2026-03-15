import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Github, Loader2, Shield, CheckCircle, AlertTriangle, GitBranch, ChevronDown } from 'lucide-react'
import { Button, Card } from '../ui-animated'
import { cn } from '../../lib/utils'
import { useNavigate } from 'react-router-dom'

interface LandingScannerProps {
  onScanComplete?: (sessionId: string) => void
}

export function LandingScanner({ onScanComplete }: LandingScannerProps) {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [showBranchInput, setShowBranchInput] = useState(false)
  const [availableBranches, setAvailableBranches] = useState<string[]>([])
  const [showBranchDropdown, setShowBranchDropdown] = useState(false)
  const [isFetchingBranches, setIsFetchingBranches] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)
  const [scanStatus, setScanStatus] = useState<'idle' | 'scanning' | 'complete' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // Fetch available branches from GitHub API
  const fetchBranches = async (owner: string, repo: string) => {
    setIsFetchingBranches(true)
    try {
      const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/branches`)
      if (response.ok) {
        const data = await response.json()
        const branchNames = data.map((b: any) => b.name)
        setAvailableBranches(branchNames)
        
        // Set default branch - prioritize master if it exists, otherwise main
        let defaultBranch = data.find((b: any) => b.name === 'master')
        if (!defaultBranch) {
          defaultBranch = data.find((b: any) => b.name === 'main')
        }
        if (!defaultBranch) {
          defaultBranch = data.find((b: any) => b.protected)
        }
        if (!defaultBranch && branchNames.length > 0) {
          defaultBranch = data[0]
        }
        
        if (defaultBranch) {
          setBranch(defaultBranch.name)
        }
        
        if (branchNames.length > 0) {
          setShowBranchInput(true)
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
      // Check if URL contains /tree/branch-name pattern
      const treeMatch = repoUrl.match(/\/tree\/([^/]+)/)
      if (treeMatch && treeMatch[1]) {
        setBranch(treeMatch[1])
        setShowBranchInput(true)
      } else {
        // Extract owner and repo from URL
        const match = repoUrl.match(/github\.com\/([^/]+)\/([^/]+)/)
        if (match) {
          const [, owner, repo] = match
          // Fetch branches after a short delay to avoid too many API calls
          const timeoutId = setTimeout(() => {
            fetchBranches(owner, repo.replace('.git', ''))
          }, 500)
          return () => clearTimeout(timeoutId)
        } else {
          setBranch('main')
          setShowBranchInput(false)
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

    // Validate GitHub URL - allow URLs with or without branch
    const githubRegex = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+(\/tree\/[\w-]+)?\/?$/
    if (!githubRegex.test(repoUrl)) {
      setErrorMessage('Please enter a valid GitHub repository URL')
      return
    }

    // Clean URL (remove branch part if present, we send it separately)
    const cleanUrl = repoUrl.replace(/\/tree\/[\w-]+/, '')

    setIsScanning(true)
    setScanStatus('scanning')
    setScanProgress(0)
    setErrorMessage('')

    try {
      // Call anonymous scan API and poll for completion
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

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Scan failed')
      }

      const data = await response.json()
      const sessionToken = data.session_token

      // Check if scan failed immediately
      if (data.status === 'failed') {
        throw new Error(data.message || 'Scan processing failed')
      }

      // Poll for scan completion
      let scanComplete = false
      let pollCount = 0
      const maxPolls = 60 // Max 2 minutes (60 * 2 seconds)

      while (!scanComplete && pollCount < maxPolls) {
        await new Promise(resolve => setTimeout(resolve, 2000)) // Wait 2 seconds
        
        const statusResponse = await fetch(`/api/v1/public/scan/${sessionToken}`)
        if (statusResponse.ok) {
          const statusData = await statusResponse.json()
          
          // Update progress based on status
          if (statusData.status === 'pending' || statusData.status === 'queued') {
            setScanProgress(30)
          } else if (statusData.status === 'processing') {
            setScanProgress(Math.min(90, 30 + (statusData.progress || 50)))
          } else if (statusData.status === 'completed') {
            setScanProgress(100)
            scanComplete = true
            
            // Store session token and navigate to results
            sessionStorage.setItem('anonScanToken', statusData.session_token)
            sessionStorage.setItem('anonScanRepo', statusData.repository_name)
            if (statusData.branch) {
              sessionStorage.setItem('anonScanBranch', statusData.branch)
            }
            
            setTimeout(() => {
              navigate(`/scan/results/${statusData.session_token}`)
              onScanComplete?.(statusData.session_token)
            }, 1000)
            break
          } else if (statusData.status === 'failed') {
            throw new Error(statusData.message || 'Scan failed')
          }
        }
        
        pollCount++
      }

      if (!scanComplete) {
        throw new Error('Scan timed out. Please try again.')
      }

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
    setErrorMessage('')
  }

  return (
    <div className="w-full">
      <AnimatePresence mode="wait">
        {scanStatus === 'idle' || scanStatus === 'error' ? (
          <motion.form
            key="scanner-form"
            onSubmit={handleScan}
            className="space-y-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
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
                  'w-full pl-12 pr-4 py-4 rounded-xl bg-white/5 border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 transition-all',
                  errorMessage
                    ? 'border-red-500/50 focus:ring-red-500/50'
                    : 'border-white/10 focus:ring-primary/50 focus:border-primary/50'
                )}
                disabled={isScanning}
              />
            </div>

            {/* Branch Input - Auto-detected with Dropdown */}
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
                  {showBranchDropdown && availableBranches.length > 0 ? (
                    <select
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      className="w-full pl-10 pr-8 py-2 rounded-lg bg-white/5 border border-white/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 appearance-none cursor-pointer"
                      disabled={isScanning}
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
                      placeholder="Branch name"
                      className="w-full pl-10 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                      disabled={isScanning}
                    />
                  )}
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                    {isFetchingBranches ? (
                      <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setBranch('main')
                    setShowBranchInput(false)
                    setShowBranchDropdown(false)
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
                className="flex items-center gap-2 text-red-400 text-sm"
              >
                <AlertTriangle className="h-4 w-4" />
                {errorMessage}
              </motion.div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full py-6 text-lg"
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
                  Start Free Scan
                  <ArrowRight className="h-5 w-5 ml-2" />
                </>
              )}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              No login required • Free security analysis • Results in seconds
            </p>
          </motion.form>
        ) : scanStatus === 'scanning' ? (
          <motion.div
            key="scanning"
            className="space-y-6"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            <Card className="p-8" hover={false}>
              <div className="text-center space-y-6">
                {/* Animated Shield Icon */}
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
                    Scanning {repoUrl.split('/').slice(-2).join('/').replace('/tree/' + branch, '')}
                  </h3>
                  <p className="text-muted-foreground">
                    Branch: <span className="text-primary font-mono">{branch}</span>
                  </p>
                  <p className="text-muted-foreground mt-1">
                    {scanProgress < 30 && 'Cloning repository...'}
                    {scanProgress >= 30 && scanProgress < 50 && 'Detecting technology stack...'}
                    {scanProgress >= 50 && scanProgress < 80 && 'Running security analysis...'}
                    {scanProgress >= 80 && scanProgress < 100 && 'Generating report...'}
                    {scanProgress === 100 && 'Scan complete!'}
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
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </div>

                {/* Scan Steps */}
                <div className="grid grid-cols-3 gap-4 pt-4">
                  {[
                    { label: 'Fetching Repo', done: scanProgress >= 30 },
                    { label: 'Analyzing Files', done: scanProgress >= 50 },
                    { label: 'Generating Report', done: scanProgress >= 80 },
                  ].map((step) => (
                    <div
                      key={step.label}
                      className={cn(
                        'flex items-center gap-2 justify-center p-3 rounded-lg border transition-all',
                        step.done
                          ? 'bg-green-500/10 border-green-500/30'
                          : 'bg-white/5 border-white/10'
                      )}
                    >
                      {step.done ? (
                        <CheckCircle className="h-5 w-5 text-green-400" />
                      ) : (
                        <Loader2 className="h-5 w-5 text-primary animate-spin" />
                      )}
                      <span className={cn(
                        'text-sm font-medium',
                        step.done ? 'text-green-400' : 'text-muted-foreground'
                      )}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}

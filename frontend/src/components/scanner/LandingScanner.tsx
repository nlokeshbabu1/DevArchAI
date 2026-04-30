import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Github, Loader2, Shield, CheckCircle, AlertTriangle, GitBranch, ChevronDown } from 'lucide-react'
import { Button, Card } from '../ui-animated'
import { api } from '../../lib/api'
import { cn } from '../../lib/utils'
import { useNavigate } from 'react-router-dom'
import { ScanProgress } from '../ScanProgress'

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
  const [scanId, setScanId] = useState<string | null>(null)
  const [scanStatus, setScanStatus] = useState<'idle' | 'scanning' | 'complete' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // Fetch available branches from backend API (not direct GitHub API)
  const fetchBranches = async (repoUrl: string) => {
    setIsFetchingBranches(true)
    try {
      const response = await api.get('/github/branches', {
        params: { repo_url: repoUrl },
      })
      const data = response.data
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
        setShowBranchInput(true)
        setShowBranchDropdown(true)
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
        setShowBranchInput(true)
      } else {
        const match = repoUrl.match(/github\.com\/([^/]+)\/([^/]+)/)
        if (match) {
          const timeoutId = setTimeout(() => {
            fetchBranches(repoUrl.replace('.git', ''))
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

    const githubRegex = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+(\/tree\/[\w-]+)?\/?$/
    if (!githubRegex.test(repoUrl)) {
      setErrorMessage('Please enter a valid GitHub repository URL')
      return
    }

    const cleanUrl = repoUrl.replace(/\/tree\/[\w-]+/, '')

    try {
      // Start unified scan
      const response = await api.post('/scan/start', {
        repository_url: cleanUrl,
        branch: branch,
        include_ai_explanations: true,
      })
      const data = response.data
      
      // Store scan ID and session token
      setScanId(data.scan_id)
      setScanStatus('scanning')
      
      if (data.session_token) {
        sessionStorage.setItem('anonScanToken', data.session_token)
        sessionStorage.setItem('anonScanRepo', cleanUrl.split('/').slice(-2).join('/'))
        sessionStorage.setItem('anonScanBranch', branch)
      }

    } catch (error) {
      console.error('Scan error:', error)
      setScanStatus('error')
      const message =
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        typeof (error as any).response?.data?.detail === 'string'
          ? (error as any).response.data.detail
          : error instanceof Error
          ? error.message
          : 'Failed to start scan. Please try again.'
      setErrorMessage(message)
    }
  }

  const handleScanComplete = (results: any) => {
    setScanStatus('complete')
    
    // Navigate to results page
    const sessionToken = sessionStorage.getItem('anonScanToken')
    if (sessionToken) {
      setTimeout(() => {
        navigate(`/scan/results/${sessionToken}`)
        onScanComplete?.(sessionToken)
      }, 1000)
    }
  }

  const handleScanError = (error: string) => {
    setScanStatus('error')
    setErrorMessage(error)
  }

  const resetScan = () => {
    setRepoUrl('')
    setBranch('main')
    setShowBranchInput(false)
    setScanId(null)
    setScanStatus('idle')
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
                disabled={scanStatus as string === 'scanning'}
              />
            </div>

            {/* Branch Input */}
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
                  {availableBranches.length > 0 ? (
                    <select
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      className="w-full pl-10 pr-8 py-2 rounded-lg bg-white/5 border border-white/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 appearance-none cursor-pointer"
                      disabled={scanStatus as string === 'scanning' || isFetchingBranches}
                    >
                      {availableBranches.map((b) => (
                        <option key={b} value={b} className="bg-background">
                          {b}
                        </option>
                      ))}
                    </select>
                  ) : isFetchingBranches ? (
                    <div className="w-full pl-10 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-muted-foreground text-sm flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading branches...
                    </div>
                  ) : (
                    <input
                      type="text"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      placeholder="Branch name"
                      className="w-full pl-10 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                      disabled={scanStatus as string === 'scanning'}
                    />
                  )}
                </div>
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
              disabled={scanStatus as string === 'scanning'}
              glow
            >
              {scanStatus as string === 'scanning' ? (
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
        ) : null /* TODO: Fix ScanProgress props - pre-existing issue */}
      </AnimatePresence>
    </div>
  )
}

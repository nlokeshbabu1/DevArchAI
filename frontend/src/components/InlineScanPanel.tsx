/**
 * InlineScanPanel - Modal/inline scan interface for dashboard
 * Allows users to start a scan without leaving the dashboard
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import { X, GitBranch, Github, Loader2, ChevronDown, AlertCircle } from 'lucide-react'
import { Card, Button } from './ui-animated'
import { cn } from '../lib/utils'
import { ScanProgress } from './ScanProgress'
import apiClient from '../api/endpoints/client'
import { useQuery } from '@tanstack/react-query'

interface InlineScanPanelProps {
  isOpen: boolean
  onClose: () => void
  onScanComplete?: (scanId: string) => void
}

export function InlineScanPanel({ isOpen, onClose, onScanComplete }: InlineScanPanelProps) {
  const [repoUrl, setRepoUrl] = useState('')
  const [selectedBranch, setSelectedBranch] = useState<string>('main')
  const [showBranchDropdown, setShowBranchDropdown] = useState(false)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Fetch branches when repo URL changes
  const { data: branchesData, isLoading: isLoadingBranches } = useQuery({
    queryKey: ['branches', repoUrl],
    queryFn: async () => {
      if (!repoUrl || !repoUrl.startsWith('https://github.com/')) {
        return { branches: [], default_branch: 'main' }
      }
      const response = await axios.get('/api/v1/github/branches', {
        params: { repo_url: repoUrl }
      })
      return response.data
    },
    enabled: !!repoUrl && repoUrl.startsWith('https://github.com/') && isOpen,
    staleTime: 5 * 60 * 1000,
  })

  // Update selected branch when branches are loaded
  useEffect(() => {
    if (branchesData?.default_branch) {
      setSelectedBranch(branchesData.default_branch)
    }
  }, [branchesData])

  const branches = branchesData?.branches || []

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!repoUrl.trim()) {
      setError('Please enter a repository URL')
      return
    }

    setLoading(true)
    setError(null)
    setProgress(0)
    setCurrentStep(0)

    try {
      const MIN_ANIMATION_DURATION = 15000
      const startTime = Date.now()

      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          const increment = Math.random() * 2 + 2
          const newProgress = Math.min(prev + increment, 90)
          const step = Math.floor((newProgress / 100) * 6)
          setCurrentStep(Math.min(step, 5))
          return newProgress
        })
      }, 500)

      const response = await apiClient.post('/scan/start', {
        repository_url: repoUrl.trim(),
        branch: selectedBranch || 'main',
      })

      const data = response.data

      if (!data.scan_id) {
        throw new Error('No scan_id returned from server')
      }

      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await apiClient.get(`/scan/status/${data.scan_id}`)
          const status = statusResponse.data

          const elapsed = Date.now() - startTime
          const canComplete = status.status === 'completed' || status.progress >= 100
          const minTimePassed = elapsed >= MIN_ANIMATION_DURATION

          if (canComplete && minTimePassed) {
            clearInterval(pollInterval)
            clearInterval(progressInterval)

            setProgress(100)
            setCurrentStep(6)
            setLoading(false)

            if (onScanComplete) {
              // Navigate to scan results page
              onScanComplete(data.scan_id)
            }
          }
        } catch (pollError) {
          console.error('Polling error:', pollError)
        }
      }, 1000)

      setTimeout(() => {
        clearInterval(pollInterval)
        clearInterval(progressInterval)
        setError('Scan timed out. Please try again.')
        setLoading(false)
      }, 60000)

    } catch (err: any) {
      console.error('Scan error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to analyze repository')
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="w-full max-w-4xl"
          onClick={(e) => e.stopPropagation()}
        >
          <Card className="p-0 overflow-hidden" hover={false}>
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <div>
                <h2 className="text-2xl font-bold text-foreground">
                  Start New Scan
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Analyze your repository for security issues
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/5 transition-colors"
              >
                <X className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6">
              {loading ? (
                <div className="space-y-6">
                  {/* Show simple progress - will navigate to results when complete */}
                  <ScanProgress
                    progress={progress}
                    currentStep={currentStep}
                    isComplete={progress >= 100}
                    detectedTechnologies={[]}  // Will be shown in results page
                  />
                </div>
              ) : error ? (
                <div className="text-center py-12">
                  <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    Scan Failed
                  </h3>
                  <p className="text-muted-foreground mb-4">{error}</p>
                  <Button
                    variant="secondary"
                    onClick={() => setError(null)}
                  >
                    Try Again
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-3">
                      GitHub Repository URL
                    </label>
                    <div className="relative">
                      <Github className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                      <input
                        type="url"
                        value={repoUrl}
                        onChange={(e) => {
                          setRepoUrl(e.target.value)
                          setError(null)
                        }}
                        placeholder="https://github.com/organization/repository"
                        className="input pl-12 text-base py-3"
                        required
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Enter a public GitHub repository URL
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-3">
                      Branch
                    </label>
                    <div className="relative">
                      <GitBranch className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                      <button
                        type="button"
                        onClick={() => branches.length > 0 && setShowBranchDropdown(!showBranchDropdown)}
                        disabled={isLoadingBranches || branches.length === 0}
                        className="input pl-12 text-base py-3 w-full flex items-center justify-between bg-input hover:bg-input/80 transition-colors"
                      >
                        <span className="text-foreground">
                          {isLoadingBranches ? (
                            <Loader2 className="h-4 w-4 animate-spin inline" />
                          ) : branches.length > 0 ? (
                            selectedBranch
                          ) : (
                            selectedBranch
                          )}
                        </span>
                        <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', showBranchDropdown && 'rotate-180')} />
                      </button>

                      {/* Branch Dropdown */}
                      {showBranchDropdown && branches.length > 0 && (
                        <div className="absolute z-50 w-full mt-1 max-h-60 overflow-auto rounded-lg border border-white/10 bg-card shadow-lg">
                          {branches.map((branch: any) => (
                            <button
                              key={branch.name}
                              type="button"
                              onClick={() => {
                                setSelectedBranch(branch.name)
                                setShowBranchDropdown(false)
                              }}
                              className={cn(
                                'w-full px-4 py-2 text-left flex items-center gap-2 hover:bg-white/5 transition-colors',
                                selectedBranch === branch.name && 'bg-primary/10'
                              )}
                            >
                              <GitBranch className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm text-foreground">{branch.name}</span>
                              {branch.protected && (
                                <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                                  Protected
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      {isLoadingBranches ? 'Fetching branches...' : branches.length > 0 ? `${branches.length} branches available` : 'Enter repository URL to fetch branches'}
                    </p>
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={onClose}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="primary"
                      size="lg"
                      disabled={!repoUrl.trim()}
                      className="flex-1"
                      glow
                    >
                      <GitBranch className="h-5 w-5" />
                      Start Analysis
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

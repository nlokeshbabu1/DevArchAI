/**
 * InlineScanPanel - Modal/inline scan interface for dashboard
 * Allows users to start a scan without leaving the dashboard
 */

import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { X, GitBranch, Github, Gitlab, Loader2, ChevronDown, AlertCircle } from 'lucide-react'
import { useState, useEffect, useCallback, useMemo } from 'react'

import apiClient from '../api/endpoints/client'
import { scansApi } from '../api/endpoints/scans'
import { useScanWebSocket } from '../hooks/useScanWebSocket'
import { cn } from '../lib/utils'

import { ScanProgressOverlay } from './scans/ScanProgressOverlay'
import { Card, Button } from './ui-animated'

type RepoProvider = 'github' | 'gitlab' | 'unknown'
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
  const [error, setError] = useState<string | null>(null)
  const [currentScanId, setCurrentScanId] = useState<string>('')

  const parsedProvider = useMemo((): RepoProvider => {
    const trimmed = repoUrl.trim().replace(/\/+$/, '')
    if (/github\.com\//i.test(trimmed)) {return 'github'}
    if (/gitlab\.com\//i.test(trimmed)) {return 'gitlab'}
    return 'unknown'
  }, [repoUrl])

  // Fetch branches when repo URL changes
  const { data: branchesData, isLoading: isLoadingBranches } = useQuery({
    queryKey: ['branches', repoUrl],
    queryFn: async () => {
      const trimmed = repoUrl.trim()
      if (!trimmed || parsedProvider === 'unknown') {
        return { branches: [], default_branch: 'main' }
      }
      const endpoint = parsedProvider === 'gitlab' ? '/gitlab/branches' : '/github/branches'
      const response = await apiClient.get(endpoint, {
        params: { repo_url: trimmed }
      })
      return response.data
    },
    enabled: !!repoUrl && parsedProvider !== 'unknown' && isOpen,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  useEffect(() => {
    if (branchesData?.default_branch) {
      setSelectedBranch(branchesData.default_branch)
    }
  }, [branchesData])

  const branches = branchesData?.branches || []

  const handleViewResults = useCallback(() => {
    if (currentScanId) {
      onScanComplete?.(currentScanId)
    }
  }, [currentScanId, onScanComplete])

  const handleCancel = useCallback(() => {
    setLoading(false)
    setError(null)
    onClose()
  }, [onClose])

  const handleRetry = useCallback(() => {
    setError(null)
  }, [])

  const handleScanComplete = useCallback(async (data: Record<string, any>) => {
    // Scan completed - keep overlay open so user can click View Results
  }, [])

  const handleScanFailed = useCallback((data: Record<string, any>) => {
    setError(`Scan failed: ${data.error || 'Unknown error'}`)
    setLoading(false)
  }, [])

  // WebSocket hook for real-time scan progress
  const { scanState } = useScanWebSocket({
    scanId: currentScanId || null,
    enabled: loading && !!currentScanId,
    onComplete: handleScanComplete,
    onFailed: handleScanFailed,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!repoUrl.trim()) {
      setError('Please enter a repository URL')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await scansApi.startUnifiedScan({
        repository_url: repoUrl.trim(),
        branch: selectedBranch || 'main',
      })

      if (!response.scan_id) {
        throw new Error('No scan_id returned from server')
      }

      setCurrentScanId(response.scan_id)
      // WebSocket hook handles real-time updates

    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to analyze repository')
      setLoading(false)
    }
  }

  // During scan, show overlay instead of form modal
  if (loading) {
    const progress = scanState?.progress ?? 0
    const currentStep = scanState?.currentStep ?? undefined
    const isComplete = scanState?.isTerminal && scanState?.status === 'completed'
    const hasFailed = scanState?.isTerminal && scanState?.status === 'failed'

    return (
      <ScanProgressOverlay
        isOpen={true}
        onClose={handleCancel}
        repositoryName={repoUrl.replace(/\/+$/, '').split('/').slice(-2).join('/')}
        branch={selectedBranch}
        progressData={{
          progress,
          currentStep,
          error: hasFailed ? (scanState?.errorMessage || error || undefined) : undefined,
        }}
        isComplete={isComplete ?? false}
        hasFailed={hasFailed ?? false}
        onComplete={handleViewResults}
        onRetry={handleRetry}
      />
    )
  }

  if (error) {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setError(null)}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <Card className="p-8 text-center" hover={false}>
              <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">Scan Failed</h3>
              <p className="text-muted-foreground mb-4">{error}</p>
              <div className="flex gap-3 justify-center">
                <Button variant="secondary" onClick={() => setError(null)}>
                  Try Again
                </Button>
                <Button variant="ghost" onClick={onClose}>
                  Close
                </Button>
              </div>
            </Card>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    )
  }

  if (!isOpen) {return null}

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

            <div className="p-6">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-3">
                    Repository URL
                  </label>
                  <div className="relative">
                    <Github className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    <input
                      type="text"
                      value={repoUrl}
                      onChange={(e) => {
                        setRepoUrl(e.target.value)
                        setError(null)
                      }}
                      placeholder="https://github.com/org/repo or https://gitlab.com/org/repo"
                      autoComplete="off"
                      autoCorrect="off"
                      autoCapitalize="off"
                      spellCheck={false}
                      className="scan-input pl-12 rounded-xl"
                      required
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Enter a public GitHub or GitLab repository URL
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
                      className="scan-input pl-12 w-full flex items-center justify-between hover:bg-white/[0.06] transition-colors"
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
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

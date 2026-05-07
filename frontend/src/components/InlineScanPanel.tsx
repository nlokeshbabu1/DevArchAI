/**
 * InlineScanPanel - Modal/inline scan interface for dashboard
 * Allows users to start a scan without leaving the dashboard
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, GitBranch, Github, Loader2, ChevronDown, AlertCircle } from 'lucide-react'
import { Card, Button } from './ui-animated'
import { cn } from '../lib/utils'
import { ScanProgress } from './ScanProgress'
import apiClient from '../api/endpoints/client'
import { useQuery } from '@tanstack/react-query'

interface FileBeingScanned {
  path: string
  type: 'docker' | 'k8s' | 'terraform' | 'cicd' | 'helm' | 'monitoring'
  status: 'pending' | 'scanning' | 'completed'
}

// Helper function to determine file type from path
function getFileTypeFromPath(path: string): FileBeingScanned['type'] {
  const lowerPath = path.toLowerCase()

  if (lowerPath.includes('dockerfile') || lowerPath.includes('docker')) {
    return 'docker'
  }
  if (lowerPath.includes('k8s') || lowerPath.includes('kubernetes') || lowerPath.includes('deployment') || lowerPath.includes('service')) {
    return 'k8s'
  }
  if (lowerPath.includes('.tf') || lowerPath.includes('terraform')) {
    return 'terraform'
  }
  if (lowerPath.includes('chart') || lowerPath.includes('helm')) {
    return 'helm'
  }
  if (lowerPath.includes('.github') || lowerPath.includes('.gitlab') || lowerPath.includes('jenkins') ||
      lowerPath.includes('ci/') || lowerPath.includes('pipeline') || lowerPath.includes('azure-pipelines')) {
    return 'cicd'
  }
  if (lowerPath.includes('prometheus') || lowerPath.includes('grafana') || lowerPath.includes('monitor')) {
    return 'monitoring'
  }

  return 'cicd' // Default fallback
}

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
  const [detectedTechnologies, setDetectedTechnologies] = useState<string[]>([])
  const [filesList, setFilesList] = useState<string[]>([])

  // Fetch branches when repo URL changes
  const { data: branchesData, isLoading: isLoadingBranches } = useQuery({
    queryKey: ['branches', repoUrl],
    queryFn: async () => {
      if (!repoUrl || !repoUrl.startsWith('https://github.com/')) {
        return { branches: [], default_branch: 'main' }
      }
      const response = await apiClient.get('/github/branches', {
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
    setDetectedTechnologies([])
    setFilesList([])

    try {
      const response = await apiClient.post('/scan/start', {
        repository_url: repoUrl.trim(),
        branch: selectedBranch || 'main',
      })

      const data = response.data

      if (!data.scan_id) {
        throw new Error('No scan_id returned from server')
      }

      // Poll for real progress updates from API only
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await apiClient.get(`/scan/status/${data.scan_id}`)
          const status = statusResponse.data

          // Update progress from API (real data only)
          if (status.progress !== undefined) {
            setProgress(Math.round(status.progress))
          }

          // Update current step from API
          if (status.current_step !== undefined) {
            // Map step name to number for UI
            const stepMap: Record<string, number> = {
              'Connecting to GitHub': 0,
              'Fetching repository': 1,
              'Detecting technologies': 2,
              'Running security rules': 3,
              'Preparing findings': 4,
              'Quality check': 4,
              'Generating AI suggestions': 4,
              'Building reports': 5,
              'Building downloadable reports': 5,
              'Calculating score': 5,
              'Scan completed': 6,
              'Saving results': 6
            }
            const stepNum = stepMap[status.current_step]
            if (stepNum !== undefined) {
              setCurrentStep(stepNum)
            }
          }

          // Update detected technologies from API
          if (status.detected_stack && Array.isArray(status.detected_stack) && status.detected_stack.length > 0) {
            setDetectedTechnologies(status.detected_stack)
          }

          // Update files list from API
          if (status.files_list && Array.isArray(status.files_list) && status.files_list.length > 0) {
            setFilesList(status.files_list)
          }

          // Check if scan FAILED
          if (status.status === 'failed') {
            clearInterval(pollInterval)
            setLoading(false)
            setError(`Scan failed: ${status.error_message || 'Unknown error'}`)
            console.error('❌ Scan failed:', status.error_message)
            return
          }

          // Check if scan is REALLY complete (not just progress=100)
          // Must have: status='completed' AND progress=100 AND have results
          const isReallyComplete = 
            status.status === 'completed' && 
            status.progress >= 100 &&
            (status.files_list?.length > 0 || status.files_scanned > 0)

          if (isReallyComplete) {
            clearInterval(pollInterval)

            setProgress(100)
            setCurrentStep(6)
            setLoading(false)

            if (onScanComplete) {
              // Give user 2 seconds to see the completion state before navigating
              setTimeout(() => onScanComplete(data.scan_id), 2000)
            }
          }
        } catch (pollError) {
          console.error('Polling error:', pollError)
        }
      }, 1000) // Poll every 1 second

      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        setError('Scan timed out. Please try again.')
        setLoading(false)
      }, 300000) // 5 minutes

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
                    detectedTechnologies={detectedTechnologies}
                    detectedFiles={filesList.map(path => ({
                      path,
                      type: getFileTypeFromPath(path),
                      status: 'completed'
                    }))}
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

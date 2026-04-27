import { motion } from 'framer-motion'
import { Plus, Github, Gitlab, Cloud, Server, Loader2, CheckCircle, AlertCircle, Trash2, ExternalLink, Play } from 'lucide-react'
import { Button, Card } from '../../components/ui-animated'
import { Badge } from '../../components/ui'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth-store'
import { useState } from 'react'
import { cn } from '../../lib/utils'
import { repositoriesApi, Repository } from '../../api/endpoints/repositories'
import { AddRepositoryModal } from '../../components/AddRepositoryModal'

interface DisplayRepository extends Repository {
  displayStatus: 'not_scanned' | 'scanning' | 'completed' | 'failed'
  source?: 'github' | 'manual'
}

interface GitHubRepoResponse {
  github_connected: boolean
  github_repositories: DisplayRepository[]
  total?: number
  message?: string
}

export function RepositoriesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { token } = useAuthStore()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showAddModal, setShowAddModal] = useState(false)
  const [scanningRepoIds, setScanningRepoIds] = useState<Set<string>>(new Set())

  // Fetch imported repositories (only repos user has explicitly added/imported)
  const { data: repositoriesResponse, isLoading, refetch } = useQuery({
    queryKey: ['repositories'],
    queryFn: async () => {
      const response = await repositoriesApi.listRepositories(1, 50)
      return response.repositories || []
    },
    refetchInterval: 5000, // Poll every 5 seconds for status updates
  })

  const repositories = repositoriesResponse || []
  const githubConnected = repositories.some((r: any) => r.source === 'github' || r.url?.includes('github.com'))

  // All repos are just the imported/added ones - no automatic GitHub fetch
  const allRepos = repositories.map((r: any) => ({ ...r, source: r.source || (r.url?.includes('github.com') ? 'github' : 'manual') }))

  // Add repository mutation
  const addRepositoryMutation = useMutation({
    mutationFn: async (url: string) => {
      const response = await repositoriesApi.createRepository({ url })
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      setShowAddModal(false)
    },
  })

  // Trigger scan mutation (using scans API like dashboard)
  const triggerScanMutation = useMutation({
    mutationFn: async ({ repoId, repoUrl, branch }: { repoId: string; repoUrl: string; branch?: string }) => {
      const response = await repositoriesApi.triggerScan(repoId, repoUrl, branch || 'main')
      return response
    },
    onMutate: ({ repoId }) => {
      setScanningRepoIds(prev => new Set(prev).add(repoId))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
    onSettled: (_, __, { repoId }) => {
      setScanningRepoIds(prev => {
        const next = new Set(prev)
        next.delete(repoId)
        return next
      })
    },
  })

  // Delete repository mutation
  const deleteRepositoryMutation = useMutation({
    mutationFn: async (repoId: string) => {
      await repositoriesApi.deleteRepository(repoId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
    },
  })

  const handleAddRepository = async (url: string) => {
    await addRepositoryMutation.mutateAsync(url)
  }

  const handleGithubImportSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['repositories'] })
  }

  const handleScan = (repoId: string, repoUrl: string) => {
    triggerScanMutation.mutate({ repoId, repoUrl, branch: 'main' })
  }

  const handleViewResults = (repoId: string) => {
    navigate(`/scans?repo=${repoId}`)
  }

  const handleDelete = async (repoId: string) => {
    if (window.confirm('Are you sure you want to delete this repository? This will not delete existing scan results.')) {
      await deleteRepositoryMutation.mutateAsync(repoId)
    }
  }

  // Transform repositories for display with proper status logic
  const displayRepos: DisplayRepository[] = (allRepos || []).map((repo) => {
    let displayStatus: 'not_scanned' | 'scanning' | 'completed' | 'failed' = 'not_scanned'

    // Determine status from latest scan
    if (repo.scan_status === 'completed' && repo.overall_score !== null && repo.overall_score !== undefined) {
      displayStatus = 'completed'
    } else if (repo.scan_status === 'processing' || scanningRepoIds.has(repo.id)) {
      displayStatus = 'scanning'
    } else if (repo.scan_status === 'failed') {
      displayStatus = 'failed'
    } else if (repo.scan_count && repo.scan_count > 0 && repo.overall_score !== null) {
      // Has scans with results
      displayStatus = 'completed'
    } else if (repo.scan_count && repo.scan_count > 0) {
      // Has scans but no results yet
      displayStatus = 'scanning'
    }
    // else: not_scanned (default)

    return {
      ...repo,
      displayStatus,
    }
  })

  // Filter repositories
  const filteredRepos = displayRepos.filter((repo) => {
    if (statusFilter !== 'all' && repo.displayStatus !== statusFilter) return false
    return true
  })

  // Calculate status counts
  const statusCounts = {
    all: displayRepos.length,
    completed: displayRepos.filter(r => r.displayStatus === 'completed').length,
    scanning: displayRepos.filter(r => r.displayStatus === 'scanning').length,
    not_scanned: displayRepos.filter(r => r.displayStatus === 'not_scanned').length,
    failed: displayRepos.filter(r => r.displayStatus === 'failed').length,
  }

  const isAdding = addRepositoryMutation.isPending
  const isScanning = triggerScanMutation.isPending

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div>
          <h1 className="text-3xl font-bold text-foreground">Repositories</h1>
          <p className="text-muted-foreground mt-1">
            Manage and scan your connected repositories
          </p>
        </div>
        <Button
          variant="primary"
          icon={<Plus className="h-4 w-4" />}
          onClick={() => setShowAddModal(true)}
        >
          Add Repository
        </Button>
      </motion.div>

      {/* Integration Cards */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {[
          { name: 'GitHub', icon: Github, connected: githubConnected },
          { name: 'GitLab', icon: Gitlab, connected: false },
          { name: 'AWS', icon: Cloud, connected: false },
          { name: 'Azure', icon: Server, connected: false },
        ].map((integration) => (
          <Card key={integration.name} className="p-4" hover>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <integration.icon className="h-6 w-6 text-muted-foreground" />
                <span className="font-medium">{integration.name}</span>
              </div>
              <div className={cn(
                'px-2 py-1 rounded-full text-xs font-medium',
                integration.connected
                  ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                  : 'bg-white/5 text-muted-foreground border border-white/10'
              )}>
                {integration.connected ? (
                  <>
                    <CheckCircle className="h-3 w-3 inline mr-1" />
                    Connected
                  </>
                ) : (
                  'Connect'
                )}
              </div>
            </div>
          </Card>
        ))}
      </motion.div>

      {/* Filters */}
      {displayRepos.length > 0 && (
        <Card className="p-4" hover={false}>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-foreground mr-2">Status:</span>
            {(['all', 'completed', 'scanning', 'not_scanned', 'failed'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                  statusFilter === status
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-white/5 text-muted-foreground hover:bg-white/10'
                )}
              >
                {status === 'not_scanned' ? 'Not Scanned' : status.charAt(0).toUpperCase() + status.slice(1)} ({statusCounts[status]})
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Repositories Grid */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {isLoading ? (
          <div className="col-span-full text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
            <p className="text-muted-foreground">Loading repositories...</p>
          </div>
        ) : filteredRepos.length === 0 ? (
          displayRepos.length === 0 ? (
            /* True empty state - no repositories at all */
            <Card className="p-12 text-center col-span-full" hover={false}>
              <Github className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {githubConnected ? 'No repositories found' : 'No repositories yet'}
              </h3>
              <p className="text-muted-foreground mb-6">
                {githubConnected
                  ? 'Your GitHub repositories will appear here. Add one to get started.'
                  : 'Connect GitHub or add a repository manually to start scanning'}
              </p>
              <div className="flex gap-3 justify-center">
                <Button
                  variant="primary"
                  icon={<Plus className="h-4 w-4" />}
                  onClick={() => setShowAddModal(true)}
                >
                  Add Repository
                </Button>
              </div>
            </Card>
          ) : (
            /* Filtered empty state - repositories exist but none match filter */
            <Card className="p-12 text-center col-span-full" hover={false}>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                No repositories match this filter
              </h3>
              <p className="text-muted-foreground mb-4">
                Try selecting a different status filter
              </p>
              <Button
                variant="secondary"
                onClick={() => setStatusFilter('all')}
              >
                Show All
              </Button>
            </Card>
          )
        ) : (
          filteredRepos.map((repo, index) => (
            <motion.div
              key={repo.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + index * 0.1 }}
            >
              <Card className="p-6" hover>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="p-2.5 bg-white/5 rounded-xl border border-white/10">
                      <Github className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold text-foreground truncate">{repo.name}</h3>
                        {repo.source === 'github' && (
                          <Badge variant="secondary" className="text-xs bg-blue-500/10 text-blue-400 border-blue-500/30">
                            <Github className="h-3 w-3 mr-1" />
                            GitHub
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {repo.description || repo.url}
                      </p>
                    </div>
                  </div>
                  <div className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                    repo.displayStatus === 'completed'
                      ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                      : repo.displayStatus === 'scanning'
                      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30 animate-pulse'
                      : repo.displayStatus === 'failed'
                      ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                      : 'bg-gray-500/15 text-gray-400 border border-gray-500/30'
                  )}>
                    {repo.displayStatus === 'scanning' && <Loader2 className="h-3 w-3 animate-spin" />}
                    {repo.displayStatus === 'completed' && <CheckCircle className="h-3 w-3" />}
                    {repo.displayStatus === 'failed' && <AlertCircle className="h-3 w-3" />}
                    <span className="capitalize">{repo.displayStatus === 'not_scanned' ? 'Not Scanned' : repo.displayStatus}</span>
                  </div>
                </div>

                {/* Tech Stack Badges */}
                {repo.tech_stack && repo.tech_stack.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {repo.tech_stack.slice(0, 4).map((tech) => (
                      <Badge key={tech} variant="secondary" className="text-xs">
                        {tech}
                      </Badge>
                    ))}
                    {repo.tech_stack.length > 4 && (
                      <Badge variant="secondary" className="text-xs">
                        +{repo.tech_stack.length - 4}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Issue Counts */}
                {repo.issues && Object.values(repo.issues).some(v => v > 0) && (
                  <div className="flex flex-wrap gap-3 mb-4 text-xs">
                    {repo.issues.critical > 0 && (
                      <span className="text-red-400">Critical: {repo.issues.critical}</span>
                    )}
                    {repo.issues.high > 0 && (
                      <span className="text-orange-400">High: {repo.issues.high}</span>
                    )}
                    {repo.issues.medium > 0 && (
                      <span className="text-yellow-400">Medium: {repo.issues.medium}</span>
                    )}
                    {repo.issues.low > 0 && (
                      <span className="text-blue-400">Low: {repo.issues.low}</span>
                    )}
                  </div>
                )}

                {/* Score and Last Scan */}
                <div className="flex items-center justify-between pt-4 border-t border-white/10 mb-4">
                  <div className="flex items-center gap-2">
                    {repo.overall_score !== undefined && repo.overall_score !== null && (
                      <div className="flex items-center gap-2">
                        <div className={cn(
                          'w-2 h-2 rounded-full',
                          repo.overall_score >= 80 ? 'bg-green-400' :
                          repo.overall_score >= 60 ? 'bg-yellow-400' : 'bg-red-400'
                        )} />
                        <span className="text-sm font-medium">{repo.overall_score.toFixed(1)}</span>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {repo.last_scan_at
                      ? `Last scanned: ${new Date(repo.last_scan_at).toLocaleDateString()} at ${new Date(repo.last_scan_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`
                      : repo.displayStatus === 'scanning'
                      ? 'Scan in progress...'
                      : 'Never scanned'
                    }
                  </div>
                </div>

                {/* Action Buttons - Status-based rendering */}
                <div className="flex gap-2">
                  {/* View Results - only show if completed */}
                  {repo.displayStatus === 'completed' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleViewResults(repo.id)}
                      icon={<ExternalLink className="h-3.5 w-3.5" />}
                    >
                      View Results
                    </Button>
                  )}

                  {/* Scan / Rescan / Retry button */}
                  {repo.displayStatus === 'not_scanned' && (
                    <Button
                      variant="primary"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleScan(repo.id, repo.url)}
                      icon={<Play className="h-3.5 w-3.5" />}
                    >
                      Scan
                    </Button>
                  )}

                  {repo.displayStatus === 'scanning' && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="flex-1"
                      disabled
                      icon={<Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    >
                      Scanning...
                    </Button>
                  )}

                  {repo.displayStatus === 'completed' && (
                    <Button
                      variant="primary"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleScan(repo.id, repo.url)}
                      icon={<Play className="h-3.5 w-3.5" />}
                    >
                      Rescan
                    </Button>
                  )}

                  {repo.displayStatus === 'failed' && (
                    <Button
                      variant="primary"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleScan(repo.id, repo.url)}
                      icon={<Play className="h-3.5 w-3.5" />}
                    >
                      Retry
                    </Button>
                  )}

                  {/* Delete button - disable while scanning */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(repo.id)}
                    disabled={repo.displayStatus === 'scanning'}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </Card>
            </motion.div>
          ))
        )}
      </motion.div>

      {/* Add Repository Modal */}
      <AddRepositoryModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddRepository}
        isLoading={isAdding}
      />
    </div>
  )
}

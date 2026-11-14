import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Plus,
  Github,
  Gitlab,
  GitBranch,
  Cloud,
  Server,
  Loader2,
  CheckCircle,
  AlertCircle,
  Trash2,
  ExternalLink,
  Play,
  Clock,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/ui/empty-state'

import apiClient from '../../api/endpoints/client'
import { repositoriesApi, Repository } from '../../api/endpoints/repositories'
import { scansApi } from '../../api/endpoints/scans'
import { AddRepositoryModal } from '../../components/AddRepositoryModal'
import { RepoSelectionModal } from '../../components/GitHubRepoSelectionModal'
import { ScanProgressOverlay } from '../../components/scans/ScanProgressOverlay'
import { Badge } from '../../components/ui'
import { PageHeader } from '../../components/ui/PageHeader'
import { SecurityScore } from '../../components/ui/SecurityScore'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Button, Card } from '../../components/ui-animated'
import { useScanWebSocket } from '../../hooks/useScanWebSocket'
import { normalizeLifecycleStage } from '../../lib/scanLifecycle'
import { cn } from '../../lib/utils'
import { useAuthStore } from '../../stores/auth-store'
import type { StageMetadata } from '../../types'


type DisplayStatus = 'not_scanned' | 'scanning' | 'completed' | 'failed'

interface DisplayRepository extends Repository {
  displayStatus: DisplayStatus
  source?: 'github' | 'gitlab' | 'manual'
}

interface TriggerScanVariables {
  repoId: string
  repoName: string
  repoUrl: string
  branch: string
}

interface ActiveRepositoryScan {
  scanId: string
  repoId: string
  repoName: string
  repoUrl: string
  branch: string
}

interface UnifiedScanStep {
  name: string
  status: string
}

interface UnifiedScanStatus {
  scan_id: string
  status: string
  progress: number
  current_step: string
  steps?: UnifiedScanStep[]
  detected_stack?: string[]
  logs?: string[]
  files_list?: string[]
  error_message?: string | null
}

interface ImportableRepoItem {
  id: number
  full_name: string
  html_url: string
  description: string | null
  private: boolean
  default_branch: string
  language: string | null
  stargazers_count: number
  forks_count: number
  updated_at: string
}
function getStatusLabel(status: DisplayStatus | 'all') {
  if (status === 'all') {
    return 'All'
  }

  if (status === 'not_scanned') {
    return 'Not Scanned'
  }

  return status.charAt(0).toUpperCase() + status.slice(1)
}

function getRepositoryActivityLabel(repo: DisplayRepository) {
  if (repo.last_scan_at) {
    const lastScan = new Date(repo.last_scan_at)
    return `${lastScan.toLocaleDateString()} • ${lastScan.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }

  if (repo.displayStatus === 'scanning') {
    return 'Scan in progress'
  }

  return 'Never scanned'
}

function isRunningStatus(status?: string | null) {
  return status === 'processing' || status === 'pending' || status === 'queued' || status === 'running'
}

function parseRepositoryId(id: string) {
  const parts = id.split('_')
  const parsedId = Number(parts[parts.length - 1])
  return Number.isFinite(parsedId) ? parsedId : null
}

export function RepositoriesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [scanningRepoIds, setScanningRepoIds] = useState<Set<string>>(new Set())
  const [scanStartPendingIds, setScanStartPendingIds] = useState<Set<string>>(new Set())
  const [activeScan, setActiveScan] = useState<ActiveRepositoryScan | null>(null)
  const [activeScanError, setActiveScanError] = useState<string | null>(null)

  const { data: stagesData } = useQuery({
    queryKey: ['scan-stages'],
    queryFn: () => scansApi.getStages(),
    staleTime: Infinity,
  })
  const stages: StageMetadata[] = stagesData || []

  const {
    scanState: wsScanState,
    completedStages,
    stageMessages,
    failedStage,
  } = useScanWebSocket({
    scanId: activeScan?.scanId ?? null,
    enabled: !!activeScan?.scanId,
    onComplete: () => {
      if (!activeScan) {return}
      setScanningRepoIds((prev) => {
        const next = new Set(prev)
        next.delete(activeScan.repoId)
        return next
      })
      void queryClient.invalidateQueries({ queryKey: ['repositories'] })
      void queryClient.invalidateQueries({ queryKey: ['scans'] })
      window.setTimeout(() => {
        const repoId = activeScan.repoId
        setActiveScan(null)
        setActiveScanError(null)
        navigate(`/scans/${activeScan.scanId}`, { replace: true })
      }, 1200)
    },
    onFailed: (data) => {
      setActiveScanError(data?.error_message || data?.error || 'Scan failed')
      if (activeScan) {
        setScanningRepoIds((prev) => {
          const next = new Set(prev)
          next.delete(activeScan.repoId)
          return next
        })
      }
      void queryClient.invalidateQueries({ queryKey: ['repositories'] })
      void queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })

  const { data: repositoriesResponse, isLoading } = useQuery({
    queryKey: ['repositories'],
    queryFn: async () => {
      const response = await repositoriesApi.listRepositories(1, 50)
      return response.repositories || []
    },
    refetchInterval: 5000,
  })

  const repositories = repositoriesResponse || []
  const allRepos: DisplayRepository[] = repositories.map((repo) => ({
    ...repo,
    displayStatus: 'not_scanned',
    source: repo.url?.includes('github.com') ? 'github' : repo.url?.includes('gitlab.com') ? 'gitlab' : 'manual',
  }))

  const activeProvider: 'github' | 'gitlab' = 
    user?.provider === 'gitlab' ? 'gitlab' 
    : user?.provider === 'github' ? 'github'
    : user?.has_gitlab && !user?.has_github ? 'gitlab' 
    : 'github'

  const {
    data: githubRepositoriesResponse,
    isLoading: isGitHubRepositoriesLoading,
    error: githubRepositoriesError,
  } = useQuery({
    queryKey: ['github-repositories'],
    queryFn: () => repositoriesApi.listGitHubRepositories(),
    enabled: showImportModal && activeProvider === 'github',
    staleTime: 60_000,
    retry: false,
  })

  const {
    data: gitlabProjectsResponse,
    isLoading: isGitLabProjectsLoading,
    error: gitlabProjectsError,
  } = useQuery({
    queryKey: ['gitlab-projects'],
    queryFn: () => repositoriesApi.listGitLabProjects(),
    enabled: showImportModal && activeProvider === 'gitlab',
    staleTime: 60_000,
    retry: false,
  })

  const githubConnected =
    activeProvider === 'github'
      ? (githubRepositoriesResponse?.github_connected ??
        repositories.some((repo) => repo.url?.includes('github.com')))
      : false
  const gitlabConnected = user?.has_gitlab ?? false
  const importedRepositoryUrls = new Set(repositories.map((repo) => repo.url))

  const isImportLoading = activeProvider === 'github' ? isGitHubRepositoriesLoading : isGitLabProjectsLoading
  const importError = activeProvider === 'github' ? githubRepositoriesError : gitlabProjectsError

  console.debug('[Import] Provider detection:', {
    activeProvider,
    userProvider: user?.provider,
    hasGithub: user?.has_github,
    hasGitlab: user?.has_gitlab,
  })
  console.debug('[Import] GitLab projects response:', {
    exists: !!gitlabProjectsResponse,
    count: gitlabProjectsResponse?.gitlab_projects?.length,
    connected: gitlabProjectsResponse?.gitlab_connected,
    message: gitlabProjectsResponse?.message,
  })

  const rawItems = activeProvider === 'github'
    ? (githubRepositoriesResponse?.github_repositories || [])
    : (gitlabProjectsResponse?.gitlab_projects || [])

  const importableItems = rawItems.reduce<ImportableRepoItem[]>((list, item: any) => {
    const parsedId = parseRepositoryId(item.id)
    if (parsedId === null) {
      console.debug('[Import] Skipped item - parseRepositoryId returned null:', item.id, item.name)
      return list
    }
    if (importedRepositoryUrls.has(item.url)) {
      console.debug('[Import] Skipped item - already imported:', item.name, item.url)
      return list
    }
    list.push({
      id: parsedId,
      full_name: item.name,
      html_url: item.url,
      description: item.description || null,
      private: item.is_private,
      default_branch: item.default_branch || 'main',
      language: item.language || null,
      stargazers_count: item.stargazers_count || 0,
      forks_count: item.forks_count || 0,
      updated_at: item.updated_at,
    })
    return list
  }, [])

  const importStatusMessage = importError
    ? activeProvider === 'github'
      ? 'Failed to load GitHub repositories. Please try again.'
      : 'Failed to load GitLab projects. Please try again.'
    : activeProvider === 'github' && !githubConnected
    ? (githubRepositoriesResponse?.message || 'Connect GitHub with OAuth to import repositories.')
    : activeProvider === 'gitlab' && !gitlabConnected
    ? (gitlabProjectsResponse?.message || 'Connect GitLab with OAuth to import projects.')
    : rawItems.length > 0 && importableItems.length === 0
    ? activeProvider === 'github'
      ? 'All available GitHub repositories are already imported.'
      : 'All available GitLab projects are already imported.'
    : activeProvider === 'github'
    ? githubRepositoriesResponse?.message
    : gitlabProjectsResponse?.message

  const addRepositoryMutation = useMutation({
    mutationFn: async (url: string) => repositoriesApi.createRepository({ url }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      setShowAddModal(false)
    },
  })

  const importRepositoriesMutation = useMutation({
    mutationFn: async (repoIds: number[]) => {
      if (activeProvider === 'github') {
        return repositoriesApi.importGitHubRepositories(repoIds)
      }
      return repositoriesApi.importGitLabProjects(repoIds)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['repositories'] }),
        queryClient.invalidateQueries({ queryKey: [activeProvider === 'github' ? 'github-repositories' : 'gitlab-projects'] }),
      ])
    },
  })

  const triggerScanMutation = useMutation({
    mutationFn: async ({ repoId, repoUrl, branch }: TriggerScanVariables) => (
      scansApi.startUnifiedScan({
        repository_id: repoId,
        repository_url: repoUrl,
        branch: branch || 'main',
      })
    ),
    onMutate: ({ repoId }) => {
      setActiveScanError(null)
      setScanStartPendingIds((prev) => new Set(prev).add(repoId))
    },
    onSuccess: (response, variables) => {
      setScanningRepoIds((prev) => new Set(prev).add(variables.repoId))
      setActiveScan({
        scanId: response.scan_id,
        repoId: variables.repoId,
        repoName: variables.repoName,
        repoUrl: variables.repoUrl,
        branch: response.branch || variables.branch,
      })
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
    onError: (error: any) => {
      window.alert(error.response?.data?.detail || 'Failed to start scan')
    },
    onSettled: (_, __, variables) => {
      setScanStartPendingIds((prev) => {
        const next = new Set(prev)
        next.delete(variables.repoId)
        return next
      })
    },
  })

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

  const handleImportRepositories = async (repoIds: number[]) => {
    await importRepositoriesMutation.mutateAsync(repoIds)
  }

  const handleScan = (repo: DisplayRepository) => {
    const isAlreadyBusy =
      scanStartPendingIds.has(repo.id) ||
      scanningRepoIds.has(repo.id) ||
      activeScan?.repoId === repo.id ||
      repo.displayStatus === 'scanning'

    if (isAlreadyBusy) {
      return
    }

    triggerScanMutation.mutate({
      repoId: repo.id,
      repoName: repo.name,
      repoUrl: repo.url,
      branch: repo.default_branch || 'main',
    })
  }

  const handleViewResults = async (repoId: string) => {
    try {
      const response = await apiClient.get(`/repositories/${repoId}/results`)
      const id = response.data?.scan?.id as string | undefined
      if (id) {
        navigate(`/scans/${id}`)
        return
      }
    } catch {
      // fall through to repository results page
    }
    navigate(`/repositories/${repoId}/results`)
  }

  const handleDelete = async (repoId: string) => {
    if (window.confirm('Are you sure you want to delete this repository? This will not delete existing scan results.')) {
      await deleteRepositoryMutation.mutateAsync(repoId)
    }
  }

  const closeProgressModal = () => {
    const terminal = wsScanState?.isTerminal || ['completed', 'failed', 'cancelled'].includes(wsScanState?.status || '')
    if (activeScan && !terminal) {
      return
    }

    if (activeScan) {
      setScanningRepoIds((prev) => {
        const next = new Set(prev)
        next.delete(activeScan.repoId)
        return next
      })
    }

    setActiveScan(null)
    setActiveScanError(null)
  }

  const handleCancelActiveScan = async () => {
    if (!activeScan?.scanId) {return}
    try {
      await scansApi.cancelScan(activeScan.scanId)
    } catch {
      // cancellation will surface via WebSocket
    }
  }

  const displayRepos: DisplayRepository[] = allRepos.map((repo) => {
    let displayStatus: DisplayStatus = 'not_scanned'

    if (repo.scan_status === 'completed' && repo.overall_score !== null && repo.overall_score !== undefined) {
      displayStatus = 'completed'
    } else if (isRunningStatus(repo.scan_status) || scanningRepoIds.has(repo.id)) {
      displayStatus = 'scanning'
    } else if (repo.scan_status === 'failed') {
      displayStatus = 'failed'
    } else if (repo.scan_count && repo.scan_count > 0 && repo.overall_score !== null && repo.overall_score !== undefined) {
      displayStatus = 'completed'
    } else if (repo.scan_count && repo.scan_count > 0) {
      displayStatus = 'scanning'
    }

    return {
      ...repo,
      displayStatus,
    }
  })

  const filteredRepos = displayRepos.filter((repo) => {
    if (statusFilter !== 'all' && repo.displayStatus !== statusFilter) {
      return false
    }

    return true
  })

  const statusCounts = {
    all: displayRepos.length,
    completed: displayRepos.filter((repo) => repo.displayStatus === 'completed').length,
    scanning: displayRepos.filter((repo) => repo.displayStatus === 'scanning').length,
    not_scanned: displayRepos.filter((repo) => repo.displayStatus === 'not_scanned').length,
    failed: displayRepos.filter((repo) => repo.displayStatus === 'failed').length,
  }

  const isAdding = addRepositoryMutation.isPending

  return (
    <>
      <div className="space-y-8">
        <PageHeader
          title="Repositories"
          description="Manage and scan your connected repositories"
          actions={
            <>
              {user?.provider !== 'password' && (
                <Button
                  variant="secondary"
                  icon={activeProvider === 'github' ? <Github className="h-4 w-4" /> : <Gitlab className="h-4 w-4" />}
                  onClick={() => setShowImportModal(true)}
                >
                  Import {activeProvider === 'gitlab' ? 'Projects' : 'Repository'}
                </Button>
              )}
              <Button
                variant="primary"
                icon={<Plus className="h-4 w-4" />}
                onClick={() => setShowAddModal(true)}
              >
                Add Repository
              </Button>
            </>
          }
        />

        <motion.div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          {[
            { name: 'GitHub', icon: Github, status: githubConnected ? 'connected' as const : 'not_connected' as const },
            { name: 'GitLab', icon: Gitlab, status: gitlabConnected ? 'connected' as const : 'not_connected' as const },
            { name: 'AWS', icon: Cloud, status: 'not_connected' as const },
            { name: 'Azure', icon: Server, status: 'coming_soon' as const },
          ].map((integration) => (
            <Card key={integration.name} className="p-4" hover>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <integration.icon className="h-6 w-6 text-muted-foreground" />
                  <span className="font-medium">{integration.name}</span>
                </div>
                <StatusBadge status={integration.status} dot />
              </div>
            </Card>
          ))}
        </motion.div>

        {displayRepos.length > 0 && (
          <Card className="p-4" hover={false}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="mr-2 text-sm font-medium text-foreground">Status:</span>
              {(['all', 'completed', 'scanning', 'not_scanned', 'failed'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={cn(
                    'rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                    statusFilter === status
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-white/5 text-muted-foreground hover:bg-white/10',
                  )}
                >
                  {getStatusLabel(status)} ({statusCounts[status]})
                </button>
              ))}
            </div>
          </Card>
        )}

        <motion.div
          className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          {isLoading ? (
            <div className="col-span-full py-12 text-center">
              <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Loading repositories...</p>
            </div>
          ) : filteredRepos.length === 0 ? (
              displayRepos.length === 0 ? (
              <EmptyState
                className="col-span-full"
                icon={
                  user?.provider === 'password'
                    ? <GitBranch className="h-12 w-12 text-muted-foreground" />
                    : activeProvider === 'github'
                    ? <Github className="h-12 w-12 text-muted-foreground" />
                    : <Gitlab className="h-12 w-12 text-muted-foreground" />
                }
                title="No repositories connected"
                description="Import your first repository to begin continuous security analysis."
                action={
                  <div className="flex flex-col justify-center gap-3 sm:flex-row">
                    {user?.provider !== 'password' && (
                      <Button
                        variant="secondary"
                        icon={activeProvider === 'github' ? <Github className="h-4 w-4" /> : <Gitlab className="h-4 w-4" />}
                        onClick={() => setShowImportModal(true)}
                      >
                        Import {activeProvider === 'gitlab' ? 'Projects' : 'Repository'}
                      </Button>
                    )}
                    <Button
                      variant="primary"
                      icon={<Plus className="h-4 w-4" />}
                      onClick={() => setShowAddModal(true)}
                    >
                      Add Repository
                    </Button>
                  </div>
                }
              />
            ) : (
              <EmptyState
                className="col-span-full"
                icon={<GitBranch className="h-12 w-12 text-muted-foreground" />}
                title="No repositories match this filter"
                description="Try selecting a different status filter."
                action={
                  <Button
                    variant="secondary"
                    onClick={() => setStatusFilter('all')}
                  >
                    Show All
                  </Button>
                }
              />
            )
          ) : (
            filteredRepos.map((repo, index) => {
              const isStartPending = scanStartPendingIds.has(repo.id)
              const isRepoScanning = repo.displayStatus === 'scanning' || scanningRepoIds.has(repo.id) || activeScan?.repoId === repo.id
              const hasScore = repo.overall_score !== undefined && repo.overall_score !== null
              const scanButtonLabel = repo.displayStatus === 'completed'
                ? 'Rescan'
                : repo.displayStatus === 'failed'
                ? 'Retry Scan'
                : 'Scan'

              return (
                <motion.div
                  key={repo.id}
                  className="h-full"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + index * 0.08 }}
                >
                  <Card className="flex h-full flex-col overflow-hidden" hover>
                    <div className="flex flex-1 flex-col gap-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 flex-1 items-start gap-3">
                          <div className="rounded-xl border border-white/10 bg-white/5 p-2.5">
                            {repo.source === 'gitlab'
                              ? <Gitlab className="h-5 w-5 text-muted-foreground" />
                              : <Github className="h-5 w-5 text-muted-foreground" />
                            }
                          </div>
                          <div className="min-w-0 flex-1 space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="truncate text-lg font-semibold text-foreground">
                                {repo.name}
                              </h3>
                              {repo.source === 'github' && (
                                <Badge variant="secondary" className="border-blue-500/30 bg-blue-500/10 text-xs text-blue-400">
                                  <Github className="mr-1 h-3 w-3" />
                                  GitHub
                                </Badge>
                              )}
                              {repo.source === 'gitlab' && (
                                <Badge variant="secondary" className="border-orange-500/30 bg-orange-500/10 text-xs text-orange-400">
                                  <Gitlab className="mr-1 h-3 w-3" />
                                  GitLab
                                </Badge>
                              )}
                            </div>
                            <p className="line-clamp-2 text-sm leading-6 text-muted-foreground">
                              {repo.description || repo.url}
                            </p>
                          </div>
                        </div>
                        <div
                          className={cn(
                            'inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium',
                            repo.displayStatus === 'completed'
                              ? 'border-green-500/30 bg-green-500/15 text-green-400'
                              : repo.displayStatus === 'scanning'
                              ? 'border-blue-500/30 bg-blue-500/15 text-blue-400'
                              : repo.displayStatus === 'failed'
                              ? 'border-red-500/30 bg-red-500/15 text-red-400'
                              : 'border-gray-500/30 bg-gray-500/15 text-gray-400',
                          )}
                        >
                          {repo.displayStatus === 'scanning' && <Loader2 className="h-3 w-3 animate-spin" />}
                          {repo.displayStatus === 'completed' && <CheckCircle className="h-3 w-3" />}
                          {repo.displayStatus === 'failed' && <AlertCircle className="h-3 w-3" />}
                          <span>{getStatusLabel(repo.displayStatus)}</span>
                        </div>
                      </div>

                      {repo.tech_stack && repo.tech_stack.length > 0 && (
                        <div className="flex flex-wrap gap-2">
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

                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                            Security Score
                          </div>
                          {hasScore ? (
                            <div className="mt-3">
                              <SecurityScore
                                data={{ overall_score: repo.overall_score }}
                                size="sm"
                                showLabel={false}
                                animated={false}
                              />
                            </div>
                          ) : (
                            <p className="mt-3 text-sm text-muted-foreground">
                              {repo.displayStatus === 'scanning' ? 'Refreshing after scan...' : 'No score available yet'}
                            </p>
                          )}
                        </div>

                        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                            Latest Activity
                          </div>
                          <div className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
                            <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
                            <span className="leading-6">{getRepositoryActivityLabel(repo)}</span>
                          </div>
                        </div>
                      </div>

                      {repo.issues && Object.values(repo.issues).some((value) => value > 0) && (
                        <div className="flex flex-wrap gap-2">
                          {repo.issues.critical > 0 && (
                            <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400">
                              Critical {repo.issues.critical}
                            </span>
                          )}
                          {repo.issues.high > 0 && (
                            <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-2.5 py-1 text-xs font-medium text-orange-400">
                              High {repo.issues.high}
                            </span>
                          )}
                          {repo.issues.medium > 0 && (
                            <span className="rounded-full border border-yellow-500/30 bg-yellow-500/10 px-2.5 py-1 text-xs font-medium text-yellow-400">
                              Medium {repo.issues.medium}
                            </span>
                          )}
                          {repo.issues.low > 0 && (
                            <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-400">
                              Low {repo.issues.low}
                            </span>
                          )}
                        </div>
                      )}

                      <div className="mt-auto border-t border-white/10 pt-5">
                        <div className="flex flex-col gap-2 sm:flex-row">
                          {repo.displayStatus === 'completed' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="sm:flex-1"
                              onClick={() => handleViewResults(repo.id)}
                              icon={<ExternalLink className="h-3.5 w-3.5" />}
                            >
                              View Results
                            </Button>
                          )}

                          {isRepoScanning ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              className="sm:flex-1"
                              disabled
                              icon={<Loader2 className="h-3.5 w-3.5 animate-spin" />}
                            >
                              {isStartPending ? 'Starting Scan...' : 'Scanning...'}
                            </Button>
                          ) : (
                            <Button
                              variant="primary"
                              size="sm"
                              className="sm:flex-1"
                              onClick={() => handleScan(repo)}
                              disabled={isStartPending}
                              icon={isStartPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                            >
                              {isStartPending ? 'Starting Scan...' : scanButtonLabel}
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="sm"
                            className="sm:w-11"
                            onClick={() => handleDelete(repo.id)}
                            disabled={isRepoScanning || isStartPending}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )
            })
          )}
        </motion.div>

        <AddRepositoryModal
          isOpen={showAddModal}
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddRepository}
          isLoading={isAdding}
        />

        <RepoSelectionModal
          isOpen={showImportModal}
          onClose={() => setShowImportModal(false)}
          onImport={handleImportRepositories}
          repos={importableItems}
          isLoading={isImportLoading}
          provider={activeProvider}
          connected={activeProvider === 'github' ? githubConnected : gitlabConnected}
          statusMessage={importStatusMessage}
          hasError={Boolean(importError)}
        />
      </div>

      <ScanProgressOverlay
        slideIn
        isOpen={!!activeScan}
        onClose={closeProgressModal}
        onCancel={() => { void handleCancelActiveScan() }}
        repositoryName={activeScan?.repoName || ''}
        branch={activeScan?.branch || ''}
        stages={stages}
        currentStage={normalizeLifecycleStage(wsScanState?.currentStage ?? null)}
        completedStages={completedStages}
        failedStage={failedStage}
        stageMessages={stageMessages}
        technologies={wsScanState?.technologies}
        startedAt={wsScanState?.startedAt}
        progressData={{
          progress: wsScanState?.progress ?? undefined,
          currentStep: wsScanState?.currentStep || wsScanState?.currentOperation,
          findingsCount: wsScanState
            ? Object.values(wsScanState.severityCounts).reduce((a, b) => a + b, 0)
            : undefined,
          error: activeScanError ?? wsScanState?.errorMessage ?? undefined,
        }}
        showProgressPercent={typeof wsScanState?.progress === 'number'}
        isComplete={wsScanState?.isTerminal === true && wsScanState.status === 'completed'}
        hasFailed={
          !!activeScanError ||
          (wsScanState?.isTerminal === true && (wsScanState.status === 'failed' || wsScanState.status === 'cancelled'))
        }
        onComplete={() => {
          if (activeScan) {
            setActiveScan(null)
            setActiveScanError(null)
            navigate(`/scans/${activeScan.scanId}`, { replace: true })
          }
        }}
        onRetry={closeProgressModal}
      />
    </>
  )
}

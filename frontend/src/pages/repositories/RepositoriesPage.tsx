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
import { integrationsApi } from '../../api/endpoints/integrations'
import { repositoriesApi, Repository } from '../../api/endpoints/repositories'
import { scansApi } from '../../api/endpoints/scans'
import { AddRepositoryModal } from '../../components/AddRepositoryModal'
import { RepoSelectionModal } from '../../components/GitHubRepoSelectionModal'
import { RepositoryListCard } from '../../components/repositories/RepositoryListCard'
import { ScanProgressOverlay } from '../../components/scans/ScanProgressOverlay'
import { Badge } from '../../components/ui'
import { PageHeader } from '../../components/ui/PageHeader'
import { SecurityScore } from '../../components/ui/SecurityScore'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Button, Card } from '../../components/ui-animated'
import { useScanWebSocket } from '../../hooks/useScanWebSocket'
import {
  countRepositoriesByStatus,
  inferRepositoryProvider,
  REPOSITORY_STATUS_FILTERS,
  repositoryStatusLabel,
  resolveRepositoryDisplayStatus,
  type RepositoryDisplayStatus,
} from '../../lib/repository-display'
import { normalizeLifecycleStage } from '../../lib/scanLifecycle'
import { cn } from '../../lib/utils'
import { useAuthStore } from '../../stores/auth-store'
import type { StageMetadata } from '../../types'


interface DisplayRepository extends Repository {
  displayStatus: RepositoryDisplayStatus
  source?: ReturnType<typeof inferRepositoryProvider>
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

  const { data: integrationStatus } = useQuery({
    queryKey: ['integrations-status'],
    queryFn: () => integrationsApi.getIntegrationStatus(),
    staleTime: 60_000,
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
    source: inferRepositoryProvider(repo.url),
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

  const githubOAuthConnected = integrationStatus?.github_oauth ?? false
  const githubAppInstalled = integrationStatus?.github_app_installed ?? false
  const githubOAuthForImport =
    activeProvider === 'github' ? (githubRepositoriesResponse?.github_connected ?? githubOAuthConnected) : false
  const gitlabOAuthConnected = integrationStatus?.gitlab_oauth ?? integrationStatus?.gitlab ?? (user?.has_gitlab ?? false)
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
    : activeProvider === 'github' && !githubOAuthForImport
    ? (githubRepositoriesResponse?.message || 'Connect GitHub with OAuth to import repositories.')
    : activeProvider === 'gitlab' && !gitlabOAuthConnected
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

  const displayRepos: DisplayRepository[] = allRepos.map((repo) => ({
    ...repo,
    displayStatus: resolveRepositoryDisplayStatus(repo, {
      locallyScanning: scanningRepoIds.has(repo.id) || activeScan?.repoId === repo.id,
    }),
  }))

  const filteredRepos = displayRepos.filter((repo) => {
    if (statusFilter !== 'all' && repo.displayStatus !== statusFilter) {
      return false
    }

    return true
  })

  const statusCounts = countRepositoriesByStatus(displayRepos)

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
            {
              name: 'GitHub',
              icon: Github,
              status: githubOAuthConnected
                ? ('connected' as const)
                : githubAppInstalled
                ? ('pending' as const)
                : ('not_connected' as const),
              label: githubOAuthConnected
                ? 'OAuth linked'
                : githubAppInstalled
                ? 'App installed'
                : undefined,
            },
            {
              name: 'GitLab',
              icon: Gitlab,
              status: gitlabOAuthConnected ? ('connected' as const) : ('not_connected' as const),
              label: gitlabOAuthConnected ? 'OAuth linked' : undefined,
            },
            { name: 'AWS', icon: Cloud, status: 'not_connected' as const },
            { name: 'Azure', icon: Server, status: 'coming_soon' as const },
          ].map((integration) => (
            <Card key={integration.name} className="p-4" hover>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <integration.icon className="h-6 w-6 text-muted-foreground" />
                  <span className="font-medium">{integration.name}</span>
                </div>
                <StatusBadge status={integration.status} label={integration.label} dot />
              </div>
            </Card>
          ))}
        </motion.div>

        {displayRepos.length > 0 && (
          <Card className="p-4" hover={false}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="mr-2 text-sm font-medium text-foreground">Status:</span>
              {REPOSITORY_STATUS_FILTERS.map((status) => (
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
                  {repositoryStatusLabel(status)} ({statusCounts[status]})
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
            filteredRepos.map((repo, index) => (
              <RepositoryListCard
                key={repo.id}
                repo={repo}
                index={index}
                isStartPending={scanStartPendingIds.has(repo.id)}
                isLocallyScanning={scanningRepoIds.has(repo.id) || activeScan?.repoId === repo.id}
                onScan={() => handleScan(repo)}
                onViewResults={() => { void handleViewResults(repo.id) }}
                onDelete={() => { void handleDelete(repo.id) }}
              />
            ))
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
          connected={activeProvider === 'github' ? githubOAuthForImport : gitlabOAuthConnected}
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

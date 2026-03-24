import { motion } from 'framer-motion'
import { Plus, Github, Gitlab, Cloud, Server, Loader2, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'
import { Button, Card, RepositoryCard } from '../../components/ui-animated'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '../../stores/auth-store'
import { useState } from 'react'
import { Badge } from '../../components/ui'
import { cn } from '../../lib/utils'

interface Repository {
  id: string
  name: string
  url: string
  description?: string
  default_branch: string
  is_private: boolean
  created_at: string
  updated_at: string
  last_scan_at?: string
  scan_status?: 'pending' | 'processing' | 'completed' | 'failed'
  overall_score?: number
  tech_stack?: string[]
  issues?: {
    critical: number
    high: number
    medium: number
    low: number
  }
}

const api = axios.create({
  baseURL: '/api/v1',
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function RepositoriesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { token } = useAuthStore()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [techFilter, setTechFilter] = useState<string[]>([])

  // Fetch repositories
  const { data: repositoriesResponse, isLoading, refetch } = useQuery({
    queryKey: ['repositories'],
    queryFn: async () => {
      const response = await api.get('/repositories')
      // API returns { repositories: [], total: 0, page: 1, page_size: 20 }
      return response.data.repositories || []
    },
    refetchInterval: 10000, // Poll every 10 seconds
  })

  const repositories = repositoriesResponse || []

  // Trigger scan mutation
  const triggerScanMutation = useMutation({
    mutationFn: async (repoUrl: string) => {
      const response = await api.post('/scans/analyze', {
        repository_url: repoUrl,
        branch: 'main',
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })

  const handleRescan = (repoUrl: string) => {
    triggerScanMutation.mutate(repoUrl)
  }

  const handleView = (repoId: string) => {
    navigate(`/scans?repo=${repoId}`)
  }

  // Transform repositories for display
  const displayRepos = (repositories || []).map((repo: Repository) => {
    const techStack = repo.tech_stack || []
    const issues = repo.issues || { critical: 0, high: 0, medium: 0, low: 0 }
    
    let status: 'scanned' | 'scanning' | 'pending' | 'error' = 'pending'
    if (repo.scan_status === 'completed') status = 'scanned'
    else if (repo.scan_status === 'processing') status = 'scanning'
    else if (repo.scan_status === 'failed') status = 'error'

    return {
      name: repo.name,
      description: repo.description || repo.url,
      lastScan: repo.last_scan_at ? new Date(repo.last_scan_at).toLocaleString() : undefined,
      score: repo.overall_score,
      status,
      techStack,
      issues,
      url: repo.url,
      id: repo.id,
    }
  })

  const filteredRepos = displayRepos.filter((repo: any) => {
    if (statusFilter !== 'all' && repo.status !== statusFilter) return false
    if (techFilter.length > 0 && !repo.techStack?.some((tech: string) => techFilter.includes(tech))) return false
    return true
  })

  const statusCounts = {
    all: displayRepos.length,
    scanned: displayRepos.filter((r: any) => r.status === 'scanned').length,
    scanning: displayRepos.filter((r: any) => r.status === 'scanning').length,
    pending: displayRepos.filter((r: any) => r.status === 'pending').length,
    error: displayRepos.filter((r: any) => r.status === 'error').length,
  }

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
          onClick={() => navigate('/scan')}
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
          { name: 'GitHub', icon: Github, connected: true },
          { name: 'GitLab', icon: Gitlab, connected: false },
          { name: 'AWS', icon: Cloud, connected: true },
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
      <Card className="p-4" hover={false}>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">Status:</span>
            {(['all', 'scanned', 'scanning', 'pending', 'error'] as const).map((status) => (
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
                {status.charAt(0).toUpperCase() + status.slice(1)} ({statusCounts[status]})
              </button>
            ))}
          </div>
        </div>
      </Card>

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
          <Card className="p-12 text-center col-span-full">
            <Cloud className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No repositories found</h3>
            <p className="text-muted-foreground mb-4">
              Start by adding a repository to scan
            </p>
            <Button onClick={() => navigate('/scan')}>
              Add Repository
            </Button>
          </Card>
        ) : (
          filteredRepos.map((repo: any, index: number) => (
            <motion.div
              key={repo.id || repo.name}
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
                      <h3 className="text-lg font-semibold text-foreground truncate">{repo.name}</h3>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{repo.description}</p>
                    </div>
                  </div>
                  <div className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                    repo.status === 'scanned'
                      ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                      : repo.status === 'scanning'
                      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30 animate-pulse'
                      : repo.status === 'error'
                      ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                      : 'bg-gray-500/15 text-gray-400 border border-gray-500/30'
                  )}>
                    {repo.status === 'scanning' && <Loader2 className="h-3 w-3 animate-spin" />}
                    {repo.status === 'scanned' && <CheckCircle className="h-3 w-3" />}
                    {repo.status === 'error' && <AlertCircle className="h-3 w-3" />}
                    <span className="capitalize">{repo.status}</span>
                  </div>
                </div>

                {/* Tech Stack Badges */}
                {repo.techStack && repo.techStack.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {repo.techStack.slice(0, 4).map((tech: string) => (
                      <Badge key={tech} variant="secondary" className="text-xs">
                        {tech}
                      </Badge>
                    ))}
                    {repo.techStack.length > 4 && (
                      <Badge variant="secondary" className="text-xs">
                        +{repo.techStack.length - 4}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Issue Counts */}
                {repo.issues && (
                  <div className="flex gap-3 mb-4 text-xs">
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
                    {Object.values(repo.issues).every(v => v === 0) && (
                      <span className="text-green-400">No issues found</span>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between pt-4 border-t border-white/10">
                  <div className="flex items-center gap-2">
                    {repo.score !== undefined && (
                      <div className="flex items-center gap-2">
                        <div className={cn(
                          'w-2 h-2 rounded-full',
                          repo.score >= 80 ? 'bg-green-400' :
                          repo.score >= 60 ? 'bg-yellow-400' : 'bg-red-400'
                        )} />
                        <span className="text-sm font-medium">{repo.score.toFixed(1)}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {repo.lastScan || 'Never scanned'}
                    </span>
                  </div>
                </div>

                <div className="flex gap-2 mt-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleView(repo.id)}
                  >
                    View
                  </Button>
                  <Button
                    variant={repo.status === 'scanning' ? 'secondary' : 'primary'}
                    size="sm"
                    className="flex-1"
                    onClick={() => handleRescan(repo.url)}
                    disabled={repo.status === 'scanning' || triggerScanMutation.isPending}
                    icon={repo.status === 'scanning' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : undefined}
                  >
                    {repo.status === 'scanning' ? 'Scanning...' : 'Rescan'}
                  </Button>
                </div>
              </Card>
            </motion.div>
          ))
        )}
      </motion.div>
    </div>
  )
}

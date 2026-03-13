import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Clock, CheckCircle, XCircle, AlertCircle, Loader2, Trash2, Eye } from 'lucide-react'
import { Card, Button, Badge, Progress } from '../../components/ui'
import axios from 'axios'
import { Link } from 'react-router-dom'

interface Scan {
  id: string
  repository_url: string
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
  progress: number
  overall_score?: number
  security_score?: number
  reliability_score?: number
  created_at: string
  completed_at?: string
  analysis_duration_seconds?: number
  error_message?: string
}

export function ScansPage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data: scans, isLoading, refetch } = useQuery({
    queryKey: ['scans'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/scans')
      return response.data
    },
    refetchInterval: 5000, // Poll every 5 seconds for live updates
  })

  const triggerScanMutation = useMutation({
    mutationFn: async (repoUrl: string) => {
      const response = await axios.post('/api/v1/scans/analyze', {
        repository_url: repoUrl,
        branch: 'main',
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })

  const cancelScanMutation = useMutation({
    mutationFn: async (scanId: string) => {
      await axios.post(`/api/v1/scans/${scanId}/cancel`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })

  const deleteScanMutation = useMutation({
    mutationFn: async (scanId: string) => {
      await axios.delete(`/api/v1/scans/${scanId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })

  const statusIcons = {
    pending: Clock,
    queued: Clock,
    processing: Loader2,
    completed: CheckCircle,
    failed: XCircle,
    cancelled: AlertCircle,
  }

  const statusColors = {
    pending: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
    queued: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    processing: 'bg-blue-500/10 text-blue-400 border-blue-500/30 animate-pulse',
    completed: 'bg-green-500/10 text-green-400 border-green-500/30',
    failed: 'bg-red-500/10 text-red-400 border-red-500/30',
    cancelled: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 50) return 'text-orange-400'
    return 'text-red-400'
  }

  const filteredScans = scans?.filter((scan: Scan) => {
    if (statusFilter === 'all') return true
    return scan.status === statusFilter
  })

  const handleQuickScan = () => {
    const repoUrl = prompt('Enter GitHub repository URL:')
    if (repoUrl) {
      triggerScanMutation.mutate(repoUrl)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Scan History</h1>
          <p className="text-muted-foreground mt-1">
            View and manage all repository scans
          </p>
        </div>
        <Button onClick={handleQuickScan} disabled={triggerScanMutation.isPending}>
          <Play className="h-4 w-4 mr-2" />
          {triggerScanMutation.isPending ? 'Starting...' : 'New Scan'}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {scans?.filter((s: Scan) => s.status === 'completed').length || 0}
          </div>
          <div className="text-sm text-muted-foreground">Completed</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {scans?.filter((s: Scan) => s.status === 'processing' || s.status === 'queued').length || 0}
          </div>
          <div className="text-sm text-muted-foreground">In Progress</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {scans?.filter((s: Scan) => s.status === 'failed').length || 0}
          </div>
          <div className="text-sm text-muted-foreground">Failed</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {scans?.length || 0}
          </div>
          <div className="text-sm text-muted-foreground">Total</div>
        </Card>
      </div>

      {/* Filter */}
      <Card className="p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Filter:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none"
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </Card>

      {/* Scans List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
            <p className="text-muted-foreground">Loading scans...</p>
          </div>
        ) : filteredScans?.length === 0 ? (
          <Card className="p-12 text-center">
            <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No scans found</h3>
            <p className="text-muted-foreground mb-4">
              Start by scanning a repository to see results here
            </p>
            <Button onClick={handleQuickScan}>
              <Play className="h-4 w-4 mr-2" />
              Start First Scan
            </Button>
          </Card>
        ) : (
          filteredScans?.map((scan: Scan) => {
            const Icon = statusIcons[scan.status]
            const isRunning = scan.status === 'processing' || scan.status === 'queued' || scan.status === 'pending'

            return (
              <Card key={scan.id} className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`p-2 rounded-lg ${statusColors[scan.status]}`}>
                      <Icon className={`h-5 w-5 ${isRunning ? 'animate-spin' : ''}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-foreground">
                          {scan.repository_url.split('/').slice(-2).join('/')}
                        </h3>
                        <Badge variant="outline" className={statusColors[scan.status]}>
                          {scan.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground mb-3">
                        {new Date(scan.created_at).toLocaleString()}
                      </div>

                      {isRunning ? (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Progress</span>
                            <span className="text-foreground">{scan.progress}%</span>
                          </div>
                          <Progress value={scan.progress} className="h-2" />
                        </div>
                      ) : (
                        <div className="flex items-center gap-6">
                          {scan.overall_score !== undefined && (
                            <div>
                              <div className="text-sm text-muted-foreground">Score</div>
                              <div className={`text-xl font-bold ${getScoreColor(scan.overall_score)}`}>
                                {scan.overall_score.toFixed(1)}
                              </div>
                            </div>
                          )}
                          {scan.analysis_duration_seconds && (
                            <div>
                              <div className="text-sm text-muted-foreground">Duration</div>
                              <div className="text-foreground">
                                {scan.analysis_duration_seconds.toFixed(0)}s
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {scan.error_message && (
                        <div className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                          <p className="text-sm text-red-400">{scan.error_message}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    {scan.status === 'completed' && (
                      <Link to={`/report/${scan.id}`}>
                        <Button variant="outline" size="sm">
                          <Eye className="h-4 w-4 mr-2" />
                          View Report
                        </Button>
                      </Link>
                    )}
                    {isRunning && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => cancelScanMutation.mutate(scan.id)}
                      >
                        Cancel
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteScanMutation.mutate(scan.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}

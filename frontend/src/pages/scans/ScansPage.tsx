import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Clock, CheckCircle, XCircle, AlertCircle, Loader2, Trash2, Eye, Download, FileJson, FileSpreadsheet, FileText, Scan } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/ui/empty-state'

import { scansApi } from '../../api/endpoints/scans'
import { Card, Button, Badge, Progress } from '../../components/ui'
import { NativeSelect, nativeSelectOptionProps } from '../../components/ui/native-select'
import { SecurityScore } from '../../components/ui/SecurityScore'
import { toast } from '../../hooks/useToast'
import { api } from '../../lib/api'
import { resolveSecurityScore } from '../../lib/security-score'
import { useAuthStore } from '../../stores/auth-store'


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
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [scanPendingDelete, setScanPendingDelete] = useState<Scan | null>(null)
  const { token } = useAuthStore()

  const { data: scans, isLoading, refetch } = useQuery({
    queryKey: ['scans'],
    queryFn: async () => {
      const response = await api.get('/scans')
      return response.data
    },
    refetchInterval: 5000, // Poll every 5 seconds for live updates
  })

  const triggerScanMutation = useMutation({
    mutationFn: async (repoUrl: string) => {
      const response = await scansApi.startUnifiedScan({
        repository_url: repoUrl,
        branch: 'main',
      })
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      navigate('/scans')
    },
  })

  const cancelScanMutation = useMutation({
    mutationFn: async (scanId: string) => {
      await api.post(`/scans/${scanId}/cancel`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })

  const deleteScanMutation = useMutation({
    mutationFn: async (scanId: string) => scansApi.deleteScan(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-recent-scans'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-risky-repositories'] })
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      setScanPendingDelete(null)
      toast.success('Scan deleted')
    },
    onError: (error: unknown) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Failed to delete scan')
    },
  })

  const handleExport = async (scanId: string, format: 'json' | 'xlsx' | 'pdf') => {
    try {
      const normalizedFormat = format === 'xlsx' ? 'excel' : format
      const response = await api.get(`/reports/${scanId}/download?format=${normalizedFormat}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      const link = document.createElement('a')
      link.href = response.data.url
      link.download = `report_${scanId}.${format === 'xlsx' ? 'xlsx' : format === 'pdf' ? 'pdf' : 'json'}`
      link.rel = 'noopener noreferrer'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Failed to export report. Please try again.')
    }
  }

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

  const filteredScans = (scans || []).filter((scan: Scan) => {
    if (statusFilter === 'all') {return true}
    return scan.status === statusFilter
  })

  const stats = {
    completed: (scans || []).filter((s: Scan) => s.status === 'completed').length,
    inProgress: (scans || []).filter((s: Scan) => s.status === 'processing' || s.status === 'queued' || s.status === 'pending').length,
    failed: (scans || []).filter((s: Scan) => s.status === 'failed').length,
    total: (scans || []).length,
  }

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
      <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {stats.completed}
          </div>
          <div className="text-sm text-muted-foreground">Completed</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {stats.inProgress}
          </div>
          <div className="text-sm text-muted-foreground">In Progress</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {stats.failed}
          </div>
          <div className="text-sm text-muted-foreground">Failed</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">
            {stats.total}
          </div>
          <div className="text-sm text-muted-foreground">Total</div>
        </Card>
      </div>

      {/* Filter */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-foreground font-medium">Filter:</span>
          <NativeSelect
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter scans by status"
          >
            <option value="all" {...nativeSelectOptionProps()}>All</option>
            <option value="pending" {...nativeSelectOptionProps()}>Pending</option>
            <option value="queued" {...nativeSelectOptionProps()}>Queued</option>
            <option value="processing" {...nativeSelectOptionProps()}>Processing</option>
            <option value="completed" {...nativeSelectOptionProps()}>Completed</option>
            <option value="failed" {...nativeSelectOptionProps()}>Failed</option>
            <option value="cancelled" {...nativeSelectOptionProps()}>Cancelled</option>
          </NativeSelect>
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
          <EmptyState
            icon={<Scan className="h-12 w-12 text-muted-foreground" />}
            title="No scans yet"
            description="Run a repository scan to generate security findings."
            action={
              <Button onClick={handleQuickScan}>
                <Play className="h-4 w-4 mr-2" />
                Start First Scan
              </Button>
            }
          />
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
                          {resolveSecurityScore(scan) && (
                            <SecurityScore data={scan} size="xs" showGrade animated={false} />
                          )}
                          {scan.analysis_duration_seconds !== null && scan.analysis_duration_seconds !== undefined && (
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
                      <>
                        <Button
                          variant="primary"
                          size="sm"
                          className="w-full"
                          onClick={() => navigate(`/scans/${scan.id}`)}
                        >
                          <Eye className="h-4 w-4 mr-2" />
                          View Report
                        </Button>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleExport(scan.id, 'pdf')}
                            title="Export PDF"
                          >
                            <FileText className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleExport(scan.id, 'xlsx')}
                            title="Export Excel"
                          >
                            <FileSpreadsheet className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleExport(scan.id, 'json')}
                            title="Export JSON"
                          >
                            <FileJson className="h-4 w-4" />
                          </Button>
                        </div>
                      </>
                    )}
                    {isRunning && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => cancelScanMutation.mutate(scan.id)}
                      >
                        Cancel
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Delete scan for ${scan.repository_url}`}
                      disabled={deleteScanMutation.isPending}
                      onClick={() => setScanPendingDelete(scan)}
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

      {scanPendingDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <Card className="w-full max-w-md p-6" hover={false}>
            <h2 className="text-lg font-semibold text-foreground">Delete scan?</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              This permanently removes the scan for{' '}
              <span className="font-medium text-foreground break-all">{scanPendingDelete.repository_url}</span>
              . Findings and reports for this scan will be deleted.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <Button
                variant="secondary"
                disabled={deleteScanMutation.isPending}
                onClick={() => setScanPendingDelete(null)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                loading={deleteScanMutation.isPending}
                disabled={deleteScanMutation.isPending}
                onClick={() => deleteScanMutation.mutate(scanPendingDelete.id)}
              >
                Delete scan
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

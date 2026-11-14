import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { 
  FolderGit2, Clock, CheckCircle, XCircle, AlertCircle, Loader2, 
  Search, Filter, ArrowRight, BarChart3, Shield, Zap
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { scansApi } from '../api/endpoints/scans'
import { Badge } from '../components/ui'
import { NativeSelect, nativeSelectOptionProps } from '../components/ui/native-select'
import { SecurityScore } from '../components/ui/SecurityScore'
import { Card, Button } from '../components/ui-animated'
import { resolveSecurityScore } from '../lib/security-score'
import { cn } from '../lib/utils'

interface Scan {
  id: string
  repository_url: string
  status: string  // Changed to string to match API response
  progress: number
  overall_score?: number
  security_score?: number
  created_at?: string  // Made optional to match API
  completed_at?: string
  analysis_duration_seconds?: number
  error_message?: string
}

type StatusFilter = 'all' | 'completed' | 'failed' | 'processing'

export function ScanHistoryPage() {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sortBy, setSortBy] = useState<'date' | 'score'>('date')

  // Fetch all scans (including anonymous for demo purposes)
  const { data: scans, isLoading, error, refetch } = useQuery({
    queryKey: ['scans-history'],
    queryFn: async () => {
      try {
        const response = await scansApi.listScans(undefined, 1, 100)
        const sortedScans = (response || []).sort((a, b) => {
          const dateA = a.created_at ? new Date(a.created_at).getTime() : 0
          const dateB = b.created_at ? new Date(b.created_at).getTime() : 0
          return dateB - dateA
        })
        return sortedScans
      } catch (err) {
        console.error('❌ Failed to fetch scan history:', err)
        return []
      }
    },
    // PHASE 3D: Auto-refresh every 30 seconds (production-ready)
    refetchInterval: 30000,
    // PHASE 3D: Refetch on window focus for latest data
    refetchOnWindowFocus: true,
    retry: 3,
  })

  // Filter and sort scans
  const filteredScans = (scans || [])
    .filter((scan: Scan) => {
      const matchesSearch = scan.repository_url.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesStatus = statusFilter === 'all' || scan.status === statusFilter
      return matchesSearch && matchesStatus
    })
    .sort((a: Scan, b: Scan) => {
      if (sortBy === 'date') {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0
        return dateB - dateA
      }
      return (resolveSecurityScore(b)?.value ?? 0) - (resolveSecurityScore(a)?.value ?? 0)
    })

  // Calculate stats
  const stats = {
    total: scans?.length || 0,
    completed: scans?.filter((s: Scan) => s.status === 'completed').length || 0,
    failed: scans?.filter((s: Scan) => s.status === 'failed').length || 0,
    inProgress: scans?.filter((s: Scan) => ['processing', 'queued', 'pending'].includes(s.status)).length || 0,
  }

  const statusIcons: Record<string, any> = {
    completed: CheckCircle,
    failed: XCircle,
    processing: Loader2,
    queued: Clock,
    pending: Clock,
    cancelled: AlertCircle,
  }

  const statusColors: Record<string, string> = {
    completed: 'bg-green-500/10 text-green-400 border-green-500/30',
    failed: 'bg-red-500/10 text-red-400 border-red-500/30',
    processing: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    queued: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    pending: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
    cancelled: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  }

  const handleScanClick = (scanId: string) => {
    navigate(`/scans/${scanId}`)
  }

  const handleNewScan = () => {
    navigate('/scan')
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div className="h-8 w-48 bg-white/10 rounded animate-pulse" />
          <div className="h-10 w-32 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="grid gap-4 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="p-12 text-center" hover={false}>
        <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-foreground mb-2">Failed to Load Scans</h3>
        <p className="text-muted-foreground mb-4">{(error).message}</p>
        <Button variant="secondary" onClick={() => refetch()}>Retry</Button>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Scan History</h1>
          <p className="text-muted-foreground mt-1">
            View and manage all your repository scans
          </p>
        </div>
        <Button
          variant="primary"
          size="lg"
          onClick={handleNewScan}
          icon={<Zap className="h-4 w-4" />}
          glow
        >
          New Scan
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card className="p-4" hover={false}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <FolderGit2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">{stats.total}</div>
              <div className="text-sm text-muted-foreground">Total Scans</div>
            </div>
          </div>
        </Card>
        <Card className="p-4" hover={false}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/10">
              <CheckCircle className="h-5 w-5 text-green-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">{stats.completed}</div>
              <div className="text-sm text-muted-foreground">Completed</div>
            </div>
          </div>
        </Card>
        <Card className="p-4" hover={false}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <Loader2 className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">{stats.inProgress}</div>
              <div className="text-sm text-muted-foreground">In Progress</div>
            </div>
          </div>
        </Card>
        <Card className="p-4" hover={false}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10">
              <XCircle className="h-5 w-5 text-red-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">{stats.failed}</div>
              <div className="text-sm text-muted-foreground">Failed</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4" hover={false}>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <NativeSelect
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              aria-label="Filter by status"
            >
              <option value="all" {...nativeSelectOptionProps()}>All Status</option>
              <option value="completed" {...nativeSelectOptionProps()}>Completed</option>
              <option value="processing" {...nativeSelectOptionProps()}>In Progress</option>
              <option value="failed" {...nativeSelectOptionProps()}>Failed</option>
            </NativeSelect>
            <NativeSelect
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'date' | 'score')}
              aria-label="Sort scans"
            >
              <option value="date" {...nativeSelectOptionProps()}>Sort by Date</option>
              <option value="score" {...nativeSelectOptionProps()}>Sort by Score</option>
            </NativeSelect>
          </div>
        </div>
      </Card>

      {/* Scans List */}
      <div className="space-y-4">
        {filteredScans.length === 0 ? (
          <Card className="p-12 text-center" hover={false}>
            <div className="inline-flex p-4 rounded-2xl bg-white/5 mb-4">
              <FolderGit2 className="h-12 w-12 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {scans?.length === 0 ? 'No scans yet' : 'No scans found'}
            </h3>
            <p className="text-muted-foreground mb-4">
              {scans?.length === 0
                ? 'Start by scanning your first repository'
                : 'Try adjusting your search or filters'}
            </p>
            {scans?.length === 0 && (
              <Button
                variant="primary"
                onClick={handleNewScan}
                icon={<Zap className="h-4 w-4" />}
              >
                Start First Scan
              </Button>
            )}
          </Card>
        ) : (
          filteredScans.map((scan: Scan) => {
            const Icon = statusIcons[scan.status]
            const isRunning = ['processing', 'queued', 'pending'].includes(scan.status)
            const repoName = scan.repository_url.split('/').slice(-2).join('/')

            return (
              <motion.div
                key={scan.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.01 }}
                onClick={() => handleScanClick(scan.id)}
                className="cursor-pointer"
              >
                <Card
                  className="p-4 transition-all hover:border-primary/30"
                  hover={false}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className={cn(
                        'p-2 rounded-lg',
                        statusColors[scan.status]
                      )}>
                        <Icon className={cn(
                          'h-5 w-5',
                          isRunning && 'animate-spin'
                        )} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-foreground truncate">
                            {repoName}
                          </h3>
                          <Badge
                            variant="secondary"
                            className={cn(
                              'text-xs',
                              statusColors[scan.status]
                            )}
                          >
                            {scan.status}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {scan.created_at && new Date(scan.created_at).toLocaleDateString()}
                          </span>
                          {scan.analysis_duration_seconds && (
                            <span>{scan.analysis_duration_seconds.toFixed(0)}s</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      {resolveSecurityScore(scan) && (
                        <SecurityScore data={scan} size="sm" showGrade animated={false} />
                      )}
                      <ArrowRight className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </div>

                  {isRunning && (
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Progress</span>
                        <span className="text-foreground">{scan.progress}%</span>
                      </div>
                      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-primary to-indigo-500 rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${scan.progress}%` }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                    </div>
                  )}

                  {scan.error_message && (
                    <div className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <p className="text-sm text-red-400">{scan.error_message}</p>
                    </div>
                  )}
                </Card>
              </motion.div>
            )
          })
        )}
      </div>
    </div>
  )
}

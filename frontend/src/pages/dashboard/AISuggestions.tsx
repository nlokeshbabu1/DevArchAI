import { motion } from 'framer-motion'
import { 
  Brain, 
  Lightbulb, 
  Code, 
  CheckCircle, 
  ArrowRight, 
  Search, 
  Filter,
  Copy,
  Play,
  GitPullRequest,
  Eye,
  X,
  AlertCircle,
  RefreshCw,
  Lock,
  Sparkles
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { CodeBlock } from '../../components/ui/code-block'
import { SeverityBadge } from '../../components/ui/severity-badge'
import { Button } from '../../components/ui'
import { AnimatedCard } from '../../components/ui/animated-card'
import { useAuthStore } from '../../stores/auth-store'
import { apiClient } from '../../api/client'

// Simple toast implementation (replace with react-hot-toast if available)
const toast = {
  success: (msg: string) => console.log('✓', msg),
  error: (msg: string) => console.error('✗', msg),
}

interface AISuggestion {
  id: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  confidence: number
  category: string
  fix_type: string
  file_path: string
  line_number: number | null
  fix_code: string | null
  auto_fix_available: boolean
  status: 'open' | 'in_progress' | 'fixed' | 'ignored'
  created_at: string
  updated_at: string
  pr_url?: string | null
  pr_number?: number | null
}

interface StatusBadgeProps {
  status: string
}

function StatusBadge({ status }: StatusBadgeProps) {
  const statusConfig: Record<string, { color: string; icon: any; label: string }> = {
    open: { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: AlertCircle, label: 'Open' },
    in_progress: { color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', icon: RefreshCw, label: 'In Progress' },
    fixed: { color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle, label: 'Fixed' },
    ignored: { color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: X, label: 'Ignored' },
  }

  const config = statusConfig[status] || statusConfig.open
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${config.color}`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  )
}

interface AISuggestionModalProps {
  suggestion: AISuggestion
  onClose: () => void
  onStatusChange: (id: string, newStatus: string) => void
  userPlan: string
}

function AISuggestionModal({ suggestion, onClose, onStatusChange, userPlan }: AISuggestionModalProps) {
  const [copied, setCopied] = useState(false)
  const [applying, setApplying] = useState(false)
  const [creatingPR, setCreatingPR] = useState(false)
  const [ignoring, setIgnoring] = useState(false)
  const [markingFixed, setMarkingFixed] = useState(false)
  const [rescanning, setRescanning] = useState(false)

  const canCopyFix = ['plus', 'pro', 'enterprise'].includes(userPlan)
  const canApplyFix = ['pro', 'enterprise'].includes(userPlan)
  const canCreatePR = ['pro', 'enterprise'].includes(userPlan)
  const canRescan = ['pro', 'enterprise'].includes(userPlan)

  const handleCopyFix = async () => {
    if (!canCopyFix || !suggestion.fix_code) return
    
    try {
      await navigator.clipboard.writeText(suggestion.fix_code)
      setCopied(true)
      toast.success('Fix code copied to clipboard!')
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      toast.error('Failed to copy fix code')
    }
  }

  const handleApplyFix = async () => {
    if (!canApplyFix) return
    
    setApplying(true)
    try {
      const response = await apiClient.post(`/api/v1/suggestions/${suggestion.id}/apply`, {
        dry_run: false,
      })
      
      if (response.data.success) {
        toast.success('Fix applied successfully!')
        onStatusChange(suggestion.id, 'in_progress')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to apply fix')
    } finally {
      setApplying(false)
    }
  }

  const handleCreatePR = async () => {
    if (!canCreatePR) return
    
    setCreatingPR(true)
    try {
      const response = await apiClient.post(`/api/v1/suggestions/${suggestion.id}/create-pr`, {
        branch_name: undefined,
        pr_title: suggestion.title,
        pr_description: `Automated fix for ${suggestion.title}`,
      })
      
      if (response.data.success) {
        toast.success('PR created successfully!')
        window.open(response.data.pr_url, '_blank')
        onStatusChange(suggestion.id, 'in_progress')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create PR')
    } finally {
      setCreatingPR(false)
    }
  }

  const handleIgnore = async () => {
    setIgnoring(true)
    try {
      await apiClient.post(`/api/v1/suggestions/${suggestion.id}/ignore`)
      toast.success('Suggestion ignored')
      onStatusChange(suggestion.id, 'ignored')
      onClose()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to ignore suggestion')
    } finally {
      setIgnoring(false)
    }
  }

  const handleMarkFixed = async () => {
    setMarkingFixed(true)
    try {
      await apiClient.post(`/api/v1/suggestions/${suggestion.id}/mark-fixed`)
      toast.success('Suggestion marked as fixed')
      onStatusChange(suggestion.id, 'fixed')
      onClose()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to mark as fixed')
    } finally {
      setMarkingFixed(false)
    }
  }

  const handleRescan = async () => {
    if (!canRescan) return
    
    setRescanning(true)
    try {
      const response = await apiClient.post(`/api/v1/suggestions/${suggestion.id}/rescan`)
      if (response.data.success) {
        toast.success('Re-scan initiated! Check back in a few minutes.')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to initiate re-scan')
    } finally {
      setRescanning(false)
    }
  }

  const isBlurred = !canCopyFix && !suggestion.fix_code

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="bg-card/80 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/50 rounded-2xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1">
              <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
                <Lightbulb className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-foreground">{suggestion.title}</h2>
                <p className="text-sm text-muted-foreground mt-1 font-mono">{suggestion.file_path}</p>
                {suggestion.line_number && (
                  <p className="text-xs text-muted-foreground mt-0.5">Line {suggestion.line_number}</p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-3">
            <SeverityBadge severity={suggestion.severity} />
            <StatusBadge status={suggestion.status} />
            <span className="text-sm text-muted-foreground capitalize">{suggestion.category}</span>
            <span className="text-sm text-muted-foreground">{(suggestion.confidence * 100).toFixed(0)}% confidence</span>
            <span className="text-sm text-muted-foreground capitalize">{suggestion.fix_type}</span>
          </div>

          {/* Description */}
          <div className="p-4 bg-card/50 border border-white/10 rounded-xl">
            <h3 className="text-sm font-semibold text-foreground mb-2">Description</h3>
            <p className="text-sm text-muted-foreground">{suggestion.description}</p>
          </div>

          {/* Fix Code */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Code className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Suggested Fix</span>
              </div>
              {canCopyFix && suggestion.fix_code && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyFix}
                  disabled={copied}
                >
                  {copied ? (
                    <>
                      <CheckCircle className="h-3.5 w-3.5 mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 mr-1" />
                      Copy
                    </>
                  )}
                </Button>
              )}
            </div>
            
            <div className="relative">
              {suggestion.fix_code ? (
                <>
                  <CodeBlock
                    code={suggestion.fix_code}
                    language={
                      suggestion.fix_type === 'terraform' ? 'hcl' :
                      suggestion.fix_type === 'dockerfile' ? 'dockerfile' :
                      suggestion.fix_type === 'kubernetes' ? 'yaml' :
                      suggestion.fix_type === 'ci_cd' ? 'yaml' : 'plaintext'
                    }
                    title="Fix"
                    showLineNumbers
                  />
                  {!canCopyFix && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center rounded-xl">
                      <div className="text-center p-6">
                        <Lock className="h-12 w-12 text-primary mx-auto mb-3" />
                        <p className="text-sm font-medium text-foreground mb-1">
                          Fix Code Locked
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Upgrade to Plus or higher to view and copy fixes
                        </p>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="p-8 bg-card/50 border border-white/10 rounded-xl text-center">
                  <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No fix code available</p>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2 pt-4 border-t border-white/10">
            {canApplyFix && suggestion.fix_code && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleApplyFix}
                disabled={applying || suggestion.status === 'fixed'}
              >
                {applying ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Applying...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Apply Fix
                  </>
                )}
              </Button>
            )}
            
            {canCreatePR && suggestion.fix_code && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleCreatePR}
                disabled={creatingPR || suggestion.status === 'fixed'}
              >
                {creatingPR ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <GitPullRequest className="h-4 w-4 mr-2" />
                    Create PR
                  </>
                )}
              </Button>
            )}
            
            {canRescan && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleRescan}
                disabled={rescanning}
              >
                {rescanning ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Re-Scan
                  </>
                )}
              </Button>
            )}
            
            <Button
              variant="secondary"
              size="sm"
              onClick={handleMarkFixed}
              disabled={markingFixed || suggestion.status === 'fixed'}
            >
              {markingFixed ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Marking...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark Fixed
                </>
              )}
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleIgnore}
              disabled={ignoring || suggestion.status === 'ignored'}
            >
              {ignoring ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Ignoring...
                </>
              ) : (
                <>
                  <X className="h-4 w-4 mr-2" />
                  Ignore
                </>
              )}
            </Button>
          </div>

          {/* Plan gating notice */}
          {!canApplyFix && (
            <div className="p-4 bg-gradient-to-r from-primary/10 to-indigo-600/10 border border-primary/30 rounded-xl">
              <div className="flex items-start gap-3">
                <Sparkles className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground mb-2">
                    Unlock full AI remediation capabilities
                  </p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    <li className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-primary" />
                      Apply fixes automatically with Pro plan
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-primary" />
                      Create GitHub pull requests automatically
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-primary" />
                      Trigger re-scans to verify fixes
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

export function AISuggestionsPage() {
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSuggestion, setSelectedSuggestion] = useState<AISuggestion | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [scanId, setScanId] = useState<string | null>(null)
  const { user, isAuthenticated } = useAuthStore()

  const userPlan = user?.plan || 'free'

  // For now, show empty state - AI suggestions endpoint needs scan_id
  // In production, this would fetch from URL params or context
  useEffect(() => {
    // Don't auto-fetch - wait for user to select a scan
    setLoading(false)
  }, [])

  const fetchSuggestions = async (id: string) => {
    setLoading(true)
    try {
      const response = await apiClient.get(`/api/v1/suggestions/${id}`)
      setSuggestions(response.data.suggestions || [])
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
      // Use mock data for demonstration
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = (id: string, newStatus: string) => {
    setSuggestions(prev =>
      prev.map(s => s.id === id ? { ...s, status: newStatus as any } : s)
    )
  }

  const filteredSuggestions = suggestions.filter(suggestion => {
    const matchesSearch = suggestion.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      suggestion.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      suggestion.file_path.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = categoryFilter === 'all' || suggestion.category.toLowerCase() === categoryFilter.toLowerCase()
    const matchesStatus = statusFilter === 'all' || suggestion.status === statusFilter
    return matchesSearch && matchesCategory && matchesStatus
  })

  const categories = ['all', ...Array.from(new Set(suggestions.map(s => s.category)))]
  const statuses = ['all', 'open', 'in_progress', 'fixed', 'ignored']

  const stats = {
    total: suggestions.length,
    open: suggestions.filter(s => s.status === 'open').length,
    inProgress: suggestions.filter(s => s.status === 'in_progress').length,
    fixed: suggestions.filter(s => s.status === 'fixed').length,
    ignored: suggestions.filter(s => s.status === 'ignored').length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-foreground">AI Suggestions</h1>
          <p className="text-muted-foreground mt-1">
            AI-powered recommendations with actionable fixes
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl">
            <Brain className="h-5 w-5 text-primary" />
            <span className="text-sm font-medium text-foreground">{stats.total} suggestions</span>
          </div>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-5 gap-4"
      >
        <AnimatedCard className="p-4">
          <div className="text-2xl font-bold text-foreground">{stats.total}</div>
          <div className="text-sm text-muted-foreground">Total</div>
        </AnimatedCard>
        <AnimatedCard className="p-4">
          <div className="text-2xl font-bold text-blue-400">{stats.open}</div>
          <div className="text-sm text-muted-foreground">Open</div>
        </AnimatedCard>
        <AnimatedCard className="p-4">
          <div className="text-2xl font-bold text-yellow-400">{stats.inProgress}</div>
          <div className="text-sm text-muted-foreground">In Progress</div>
        </AnimatedCard>
        <AnimatedCard className="p-4">
          <div className="text-2xl font-bold text-green-400">{stats.fixed}</div>
          <div className="text-sm text-muted-foreground">Fixed</div>
        </AnimatedCard>
        <AnimatedCard className="p-4">
          <div className="text-2xl font-bold text-gray-400">{stats.ignored}</div>
          <div className="text-sm text-muted-foreground">Ignored</div>
        </AnimatedCard>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="flex flex-col sm:flex-row gap-4"
      >
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search suggestions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl text-foreground focus:outline-none"
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat === 'all' ? 'All Categories' : cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl text-foreground focus:outline-none"
          >
            {statuses.map(status => (
              <option key={status} value={status}>
                {status === 'all' ? 'All Statuses' : status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>
        </div>
      </motion.div>

      {/* Suggestions Grid */}
      {loading ? (
        <div className="text-center py-12">
          <RefreshCw className="h-8 w-8 text-primary mx-auto mb-4 animate-spin" />
          <p className="text-muted-foreground">Loading suggestions...</p>
        </div>
      ) : filteredSuggestions.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-12"
        >
          <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">No suggestions found</h3>
          <p className="text-muted-foreground">Try adjusting your search or filters.</p>
        </motion.div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {filteredSuggestions.map((suggestion, index) => (
            <AnimatedCard
              key={suggestion.id}
              delay={index * 0.05}
              onClick={() => setSelectedSuggestion(suggestion)}
              className="cursor-pointer"
            >
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
                      <Lightbulb className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-foreground truncate">{suggestion.title}</h3>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{suggestion.description}</p>
                      <p className="text-xs text-muted-foreground mt-1 font-mono truncate">{suggestion.file_path}</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={suggestion.severity} size="sm" />
                    <StatusBadge status={suggestion.status} />
                  </div>
                  <Button variant="ghost" size="sm">
                    View Details
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            </AnimatedCard>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedSuggestion && (
        <AISuggestionModal
          suggestion={selectedSuggestion}
          onClose={() => setSelectedSuggestion(null)}
          onStatusChange={handleStatusChange}
          userPlan={userPlan}
        />
      )}
    </div>
  )
}

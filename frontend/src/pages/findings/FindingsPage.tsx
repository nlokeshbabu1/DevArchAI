import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download, CheckCircle, AlertTriangle, AlertCircle, Info, Lock, Sparkles } from 'lucide-react'
import { Card, Button, Badge } from '../../components/ui'
import { AISuggestionBlur } from '../../components/billing/AISuggestionBlur'
import axios from 'axios'
import { useAuthStore } from '../../stores/auth-store'
import { useNavigate } from 'react-router-dom'

interface Finding {
  id: string
  scan_id: string
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path: string
  line_number?: number
  ai_explanation?: string
  created_at: string
}

// Configure axios with auth token
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

export function Findings() {
  const navigate = useNavigate()
  const { token } = useAuthStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string[]>([])
  const [categoryFilter, setCategoryFilter] = useState<string[]>([])
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  
  // Get user subscription to determine if AI should be blurred
  const [userPlan, setUserPlan] = useState<string>('free')
  
  useEffect(() => {
    // Fetch user's subscription plan
    const fetchPlan = async () => {
      if (!token) {
        setUserPlan('free')
        return
      }
      try {
        const response = await axios.get('/api/v1/billing/subscription', {
          headers: { Authorization: `Bearer ${token}` }
        })
        setUserPlan(response.data.plan || 'free')
      } catch (error) {
        setUserPlan('free')
      }
    }
    fetchPlan()
  }, [token])

  // Fetch all scans first, then get findings for each scan
  const { data: scans, isLoading: scansLoading } = useQuery({
    queryKey: ['scans'],
    queryFn: async () => {
      const response = await api.get('/scans?page_size=100')
      return response.data
    },
    refetchInterval: 5000, // Poll every 5 seconds
  })

  // Fetch findings for all scans
  const { data: allFindings = [], isLoading: findingsLoading } = useQuery({
    queryKey: ['all-findings', scans],
    queryFn: async () => {
      if (!scans || scans.length === 0) return []

      // Fetch findings for each scan
      const findingsPromises = scans.map((scan: any) =>
        api.get(`/scans/${scan.id}/findings`)
      )

      const results = await Promise.all(findingsPromises)
      return results.flatMap(r => r.data || [])
    },
    enabled: !!scans && scans.length > 0,
    refetchInterval: 5000, // Poll every 5 seconds for live updates
  })

  const findings = allFindings
  const isLoading = scansLoading || findingsLoading

  const severityIcons: Record<string, any> = {
    critical: AlertCircle,
    high: AlertTriangle,
    medium: Info,
    low: Info,
    info: Info,
  }

  const severityColors: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-400 border-red-500/30',
    high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
    medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    low: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    info: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  }

  const categoryColors: Record<string, string> = {
    security: 'bg-red-500/10 text-red-400',
    reliability: 'bg-blue-500/10 text-blue-400',
    scalability: 'bg-green-500/10 text-green-400',
    cost: 'bg-purple-500/10 text-purple-400',
    observability: 'bg-orange-500/10 text-orange-400',
  }

  const filteredFindings = findings?.filter((finding: Finding) => {
    const matchesSearch =
      finding.rule_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      finding.description.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesSeverity = severityFilter.length === 0 || severityFilter.includes(finding.severity)
    const matchesCategory = categoryFilter.length === 0 || categoryFilter.includes(finding.category)

    return matchesSearch && matchesSeverity && matchesCategory
  })

  const severityCounts = findings?.reduce((acc: Record<string, number>, f: Finding) => {
    acc[f.severity] = (acc[f.severity] || 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Security Findings</h1>
          <p className="text-muted-foreground mt-1">
            View and manage all detected issues across your repositories
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {Object.entries(severityCounts || {}).map(([severity, count]) => {
          const Icon = severityIcons[severity]
          return (
            <Card key={severity} className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${severityColors[severity]}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-foreground">{String(count)}</div>
                  <div className="text-sm text-muted-foreground capitalize">{severity}</div>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search findings..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white border border-white/10 rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2">
            <select
              multiple
              value={severityFilter}
              onChange={(e) => setSeverityFilter(Array.from(e.target.selectedOptions, option => option.value))}
              className="px-4 py-2 bg-white border border-white/10 rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            <select
              multiple
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(Array.from(e.target.selectedOptions, option => option.value))}
              className="px-4 py-2 bg-white border border-white/10 rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="security">Security</option>
              <option value="reliability">Reliability</option>
              <option value="scalability">Scalability</option>
              <option value="cost">Cost</option>
              <option value="observability">Observability</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Findings List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
            <p className="text-muted-foreground mt-4">Loading findings...</p>
          </div>
        ) : filteredFindings?.length === 0 ? (
          <Card className="p-12 text-center">
            <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No findings found</h3>
            <p className="text-muted-foreground">
              {findings?.length === 0
                ? "No findings detected. Run a scan to identify issues."
                : "No findings match your current filters."}
            </p>
          </Card>
        ) : (
          filteredFindings?.map((finding: Finding) => {
            const Icon = severityIcons[finding.severity]
            return (
              <Card key={finding.id} className="p-6 hover:bg-white/5 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`p-2 rounded-lg ${severityColors[finding.severity]}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-foreground">{finding.rule_name}</h3>
                        <Badge variant="secondary" className={categoryColors[finding.category]}>
                          {finding.category}
                        </Badge>
                        <Badge variant="secondary" className={severityColors[finding.severity]}>
                          {finding.severity}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground mb-3">{finding.description}</p>
                      {finding.file_path && (
                        <div className="text-sm text-muted-foreground mb-3">
                          <code className="px-2 py-1 bg-white/5 rounded">{finding.file_path}</code>
                          {finding.line_number && <span className="ml-2">Line {finding.line_number}</span>}
                        </div>
                      )}
                      {finding.ai_explanation && (
                        <div className="mt-4">
                          <AISuggestionBlur
                            isBlurred={userPlan === 'free'}
                            suggestion={finding.ai_explanation}
                            codeFix={finding.recommendation}
                            onUpgrade={() => navigate('/pricing')}
                            upgradePlan="plus"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Button variant="secondary" size="sm">
                      View Details
                    </Button>
                    <Button variant="ghost" size="sm">
                      <CheckCircle className="h-4 w-4" />
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

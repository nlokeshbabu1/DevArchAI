import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import {
  Brain, Lightbulb, Code, CheckCircle, Search, Filter,
  Copy, GitPullRequest, Eye, X, AlertCircle, RefreshCw,
  Shield, Zap, BarChart3, DollarSign, BookOpen,
  FileCode, Info,
  Layers, ChevronLeft, Star, Gauge, FolderGit2, Files, Wrench, GitBranch, ArrowUp, ArrowDown, ExternalLink
} from 'lucide-react'
import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { Button } from '../../components/ui'
import { CodeBlock } from '../../components/ui/code-block'
import { ErrorState } from '../../components/ui/error-state'
import { PageHeader } from '../../components/ui/PageHeader'
import { SeverityBadge } from '../../components/ui/severity-badge'
import { StatusBadge, type ProductStatus } from '../../components/ui/StatusBadge'
import { Skeleton, SkeletonCard } from '../../components/ui-animated'
import { toast } from '../../hooks/useToast'
import { cn, copyToClipboard } from '../../lib/utils'
import { useAuthStore } from '../../stores/auth-store'

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
  scan_id?: string
  finding_id?: string
}

type SectionType = 'fix-first' | 'recommended' | 'optimization'

const SECTION_CONFIG: Record<SectionType, { label: string; icon: any; description: string; colors: string }> = {
  'fix-first': {
    label: 'Fix First',
    icon: Shield,
    description: 'Critical and high-severity issues that impact security and stability',
    colors: 'from-red-500/10 to-orange-500/5 border-red-500/15',
  },
  'recommended': {
    label: 'Recommended',
    icon: Star,
    description: 'Medium-severity improvements for reliability and best practices',
    colors: 'from-amber-500/10 to-yellow-500/5 border-amber-500/15',
  },
  'optimization': {
    label: 'Optimization',
    icon: Gauge,
    description: 'Low-priority enhancements for performance and cost efficiency',
    colors: 'from-cyan-500/10 to-blue-500/5 border-cyan-500/15',
  },
}

const CATEGORY_CONFIG: Record<string, { label: string; icon: any; color: string }> = {
  security: { label: 'Security', icon: Shield, color: 'text-red-400 bg-red-500/10 border-red-500/20' },
  reliability: { label: 'Reliability', icon: BarChart3, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  performance: { label: 'Performance', icon: Zap, color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' },
  cost: { label: 'Cost', icon: DollarSign, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  'best-practices': { label: 'Best Practices', icon: BookOpen, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' },
}

function suggestionStatusBadge(status: AISuggestion['status']): ProductStatus {
  switch (status) {
    case 'in_progress': return 'processing'
    case 'fixed': return 'completed'
    case 'ignored': return 'not_connected'
    default: return 'pending'
  }
}

function getCategoryColor(category: string): string {
  const c = category.toLowerCase().replace(/\s+/g, '-')
  return CATEGORY_CONFIG[c]?.color || 'text-gray-400 bg-gray-500/10 border-gray-500/20'
}

function getCategoryIcon(category: string) {
  const c = category.toLowerCase().replace(/\s+/g, '-')
  return CATEGORY_CONFIG[c]?.icon || Lightbulb
}

function getCategoryLabel(category: string): string {
  const c = category.toLowerCase().replace(/\s+/g, '-')
  return CATEGORY_CONFIG[c]?.label || category.charAt(0).toUpperCase() + category.slice(1)
}

function getSeveritySection(severity: string): SectionType {
  if (severity === 'critical' || severity === 'high') {return 'fix-first'}
  if (severity === 'medium') {return 'recommended'}
  return 'optimization'
}

function sanitizePath(filePath: string): string {
  const cleaned = filePath
    .replace(/^\/tmp\/[^/]+\//, '')
    .replace(/^\/home\/[^/]+\//, '')
    .replace(/^\/app\/[^/]*\//, '')
    .replace(/^\/var\/[^/]+\//, '')
  const hashPrefix = cleaned.replace(/^([0-9a-f]{8,})_/, '')
  const parts = hashPrefix.split('/')
  if (parts.length > 3) {
    return parts.slice(-3).join('/')
  }
  return hashPrefix
}

function extractRepo(filePath: string): string {
  const cleaned = filePath
    .replace(/^\/tmp\/[^/]+\//, '')
    .replace(/^\/home\/[^/]+\//, '')
    .replace(/^\/app\/[^/]*\//, '')
  const parts = cleaned.split('/')
  if (parts.length >= 2) {
    let first = parts[0]
    // Strip scan hash prefix (e.g. "3a586b3c_gen-ai" -> "gen-ai")
    const hashMatch = first.match(/^([0-9a-f]{8,})_(.+)$/)
    if (hashMatch) {first = hashMatch[2]}
    return first
  }
  return parts[0] || 'unknown'
}

interface GroupedSuggestion {
  key: string
  repository: string
  category: string
  suggestions: AISuggestion[]
  section: SectionType
  count: number
  avgConfidence: number
  uniqueFiles: string[]
  topSuggestion: AISuggestion
}

function groupSuggestions(suggestions: AISuggestion[]): GroupedSuggestion[] {
  const sectionOrder: SectionType[] = ['fix-first', 'recommended', 'optimization']
  const groups: GroupedSuggestion[] = []

  for (const section of sectionOrder) {
    const sectionSugs = suggestions.filter(
      s => getSeveritySection(s.severity) === section && s.status === 'open'
    )
    const byRepoAndCat = new Map<string, AISuggestion[]>()
    for (const s of sectionSugs) {
      const repo = extractRepo(s.file_path)
      const cat = s.category.toLowerCase()
      const key = `${repo}::${cat}`
      const existing = byRepoAndCat.get(key) || []
      existing.push(s)
      byRepoAndCat.set(key, existing)
    }

    for (const [key, catSugs] of byRepoAndCat) {
      const [repo, category] = key.split('::')
      const allFiles = [...new Set(catSugs.map(s => sanitizePath(s.file_path)))]
      groups.push({
        key: `${section}-${key}`,
        repository: repo,
        category,
        suggestions: catSugs,
        section,
        count: catSugs.length,
        avgConfidence: catSugs.length > 0
          ? Math.round(catSugs.reduce((sum, s) => sum + s.confidence, 0) / catSugs.length * 100) / 100
          : 0,
        uniqueFiles: allFiles,
        topSuggestion: catSugs.sort((a, b) => {
          const sevOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
          return (sevOrder[a.severity] ?? 5) - (sevOrder[b.severity] ?? 5)
        })[0],
      })
    }
  }

  return groups
}

// ─── Category Badge ─────────────────────────────────────────
function CategoryBadge({ category, size = 'sm' }: { category: string; size?: 'sm' | 'md' }) {
  const catKey = category.toLowerCase().replace(/\s+/g, '-')
  const config = CATEGORY_CONFIG[catKey]
  const Icon = config?.icon || Lightbulb
  const label = config?.label || category
  const color = config?.color || 'text-gray-400 bg-gray-500/10 border-gray-500/20'

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 font-medium border rounded-full',
      size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs',
      color
    )}>
      <Icon className={size === 'sm' ? 'h-2.5 w-2.5' : 'h-3 w-3'} />
      {label}
    </span>
  )
}

// ─── Side Panel ─────────────────────────────────────────────
interface SidePanelProps {
  suggestion: AISuggestion
  onClose: () => void
  onStatusChange: (id: string, status: string) => void
  userPlan: string
}

function AIDetailSidePanel({ suggestion, onClose, onStatusChange, userPlan }: SidePanelProps) {
  const shouldReduceMotion = useReducedMotion()
  const panelRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)
  const [creatingPR, setCreatingPR] = useState(false)
  const [showPRPreview, setShowPRPreview] = useState(false)

  const canCopyFix = ['plus', 'pro', 'enterprise'].includes(userPlan)
  const canCreatePR = ['pro', 'enterprise'].includes(userPlan)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showPRPreview) {setShowPRPreview(false)}
        else {onClose()}
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose, showPRPreview])

  const handleCopyFix = async () => {
    if (!canCopyFix || !suggestion.fix_code) {return}
    try {
      await copyToClipboard(suggestion.fix_code)
      setCopied(true)
      toast.success('Fix code copied!')
      setTimeout(() => setCopied(false), 2000)
    } catch { toast.error('Failed to copy') }
  }

  const handleCreatePR = () => {
    if (!canCreatePR) {return}
    setShowPRPreview(true)
  }

  const handleConfirmPR = async () => {
    if (!canCreatePR) {return}
    setCreatingPR(true)
    try {
      const response = await apiClient.post(`/suggestions/${suggestion.id}/create-pr`, {
        pr_title: suggestion.title,
        pr_description: `Automated fix for ${suggestion.title}`,
      })
      if (response.data.success) {
        toast.success('PR created!')
        window.open(response.data.pr_url, '_blank')
        onStatusChange(suggestion.id, 'in_progress')
        setShowPRPreview(false)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create PR')
    } finally { setCreatingPR(false) }
  }

  const handleIgnore = async () => {
    try {
      await apiClient.post(`/suggestions/${suggestion.id}/ignore`)
      toast.success('Suggestion ignored')
      onStatusChange(suggestion.id, 'ignored')
      onClose()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to ignore')
    }
  }

  const prPreviewData = useMemo(() => ({
    repository: extractRepo(suggestion.file_path),
    file: sanitizePath(suggestion.file_path),
    lineCount: suggestion.fix_code ? suggestion.fix_code.split('\n').length : 0,
    riskReduction: suggestion.severity === 'critical' ? 'High' : suggestion.severity === 'high' ? 'Medium' : 'Low',
  }), [suggestion.file_path, suggestion.fix_code, suggestion.severity])

  const CatIcon = getCategoryIcon(suggestion.category)
  const repoName = extractRepo(suggestion.file_path)

  return (
    <motion.div
      initial={shouldReduceMotion ? {} : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={shouldReduceMotion ? {} : { opacity: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.2 }}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        ref={panelRef}
        initial={shouldReduceMotion ? { x: 0 } : { x: '100%' }}
        animate={{ x: 0 }}
        exit={shouldReduceMotion ? { x: 0 } : { x: '100%' }}
        transition={{ duration: shouldReduceMotion ? 0 : 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-[#0a0a10]/95 backdrop-blur-2xl border-l border-white/[0.06] shadow-2xl shadow-black/50 overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[#0a0a10]/90 backdrop-blur-xl border-b border-white/[0.06] px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <button onClick={onClose} className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/80 transition-colors">
              <ChevronLeft className="h-3 w-3" />
              Back to suggestions
            </button>
            <div className="flex items-center gap-2">
              <SeverityBadge severity={suggestion.severity} size="sm" />
              <CategoryBadge category={suggestion.category} size="sm" />
            </div>
          </div>
          <h2 className="text-lg font-semibold text-white/90 leading-snug">{suggestion.title}</h2>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <StatusBadge status={suggestionStatusBadge(suggestion.status)} />
            {suggestion.scan_id && (
              <button
                type="button"
                onClick={() => window.open(`/scans/${suggestion.scan_id}`, '_self')}
                className="flex items-center gap-1.5 text-xs text-indigo-300/80 hover:text-indigo-200 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                View scan
              </button>
            )}
            {suggestion.finding_id && (
              <span className="text-xs font-mono text-white/30">Finding {suggestion.finding_id.slice(0, 8)}</span>
            )}
            <div className="flex items-center gap-1.5 text-xs text-white/40">
              <FolderGit2 className="h-3 w-3" />
              <span>{repoName}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-white/40">
              <FileCode className="h-3 w-3" />
              <span className="font-mono">{sanitizePath(suggestion.file_path)}</span>
              {suggestion.line_number && <span className="text-white/30">:L{suggestion.line_number}</span>}
            </div>
          </div>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* Issue Summary */}
          <div>
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Info className="h-3 w-3" />
              Issue Summary
            </h3>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <p className="text-sm text-white/70 leading-relaxed">{suggestion.description || suggestion.title}</p>
            </div>
          </div>

          {/* Why This Matters */}
          {suggestion.description && suggestion.description !== suggestion.title && (
            <div>
              <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <AlertCircle className="h-3 w-3" />
                Why This Matters
              </h3>
              <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
                <p className="text-sm text-amber-200/70 leading-relaxed">{suggestion.description}</p>
              </div>
            </div>
          )}

          {/* Security Impact */}
          <div>
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Shield className="h-3 w-3" />
              Security Impact
            </h3>
            <div className="p-3 rounded-xl bg-orange-500/5 border border-orange-500/15">
              <p className="text-sm text-orange-200/60 leading-relaxed">
                {suggestion.severity === 'critical' || suggestion.severity === 'high'
                  ? `This ${suggestion.severity}-severity issue poses a significant risk to your infrastructure security posture.`
                  : 'This issue has a moderate security impact on your infrastructure.'}
              </p>
            </div>
          </div>

          {/* Affected Repository + File */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-1.5">Repository</h4>
              <div className="flex items-center gap-1.5 text-sm text-white/70">
                <FolderGit2 className="h-3.5 w-3.5 text-white/40" />
                <span className="truncate">{repoName}</span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-1.5">Affected File</h4>
              <div className="flex items-center gap-1.5 text-sm text-white/70">
                <FileCode className="h-3.5 w-3.5 text-white/40" />
                <span className="font-mono text-xs truncate">{sanitizePath(suggestion.file_path)}</span>
                {suggestion.line_number && <span className="text-white/30 text-xs">:L{suggestion.line_number}</span>}
              </div>
            </div>
          </div>

          {/* Confidence + Metadata chips */}
          <div className="flex flex-wrap items-center gap-2">
            {suggestion.confidence != null && (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                <Brain className="h-3 w-3 text-indigo-400" />
                <span className="text-xs font-mono text-indigo-300/80">{(suggestion.confidence * 100).toFixed(0)}% confidence</span>
              </div>
            )}
            {suggestion.scan_id && (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                <Layers className="h-3 w-3 text-white/40" />
                <span className="text-xs font-mono text-white/40">Scan: {suggestion.scan_id.slice(0, 8)}</span>
              </div>
            )}
            {suggestion.finding_id && (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                <Layers className="h-3 w-3 text-white/40" />
                <span className="text-xs font-mono text-white/40">ID: {suggestion.finding_id.slice(0, 8)}</span>
              </div>
            )}
          </div>

          {/* Current Code (not available from backend) */}
          <div>
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Code className="h-3 w-3" />
              Current Code
            </h3>
            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-center">
              <Code className="h-5 w-5 text-white/20 mx-auto mb-2" />
              <p className="text-xs text-white/40">Source code not available for this finding type</p>
            </div>
          </div>

          {/* Suggested Code */}
          <div>
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Wrench className="h-3 w-3" />
              Suggested Code
            </h3>
            {suggestion.fix_code ? (
              <div className="relative">
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
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-center">
                <Code className="h-5 w-5 text-white/20 mx-auto mb-2" />
                <p className="text-xs text-white/40">No suggested code available for this recommendation</p>
              </div>
            )}
          </div>

          {/* Best Practice */}
          <div>
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Shield className="h-3 w-3" />
              Best Practice
            </h3>
            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-center">
              <Shield className="h-5 w-5 text-white/20 mx-auto mb-2" />
              <p className="text-xs text-white/40">Best practice details not available for this finding</p>
            </div>
          </div>

          {/* Reference Links */}
          <div>
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <BookOpen className="h-3 w-3" />
              Reference Links
            </h3>
            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              {suggestion.finding_id ? (
                <div className="flex items-center gap-2 text-sm text-white/50">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                  <span className="font-mono text-xs">Finding ID: {suggestion.finding_id}</span>
                </div>
              ) : (
                <p className="text-xs text-white/40">No reference links available</p>
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="sticky bottom-0 bg-[#0a0a10]/90 backdrop-blur-xl border-t border-white/[0.06] px-6 py-4">
          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" glow onClick={() => toast.success('AI Explanation')}>
              <Brain className="h-3.5 w-3.5 mr-1.5" />
              Explain
            </Button>
            {suggestion.fix_code && (
              <>
                <Button variant="secondary" size="sm" onClick={handleCopyFix} disabled={copied}>
                  {copied ? <CheckCircle className="h-3.5 w-3.5 mr-1.5" /> : <Copy className="h-3.5 w-3.5 mr-1.5" />}
                  {copied ? 'Copied' : 'Copy Fix'}
                </Button>
                <Button variant="secondary" size="sm" onClick={handleCreatePR} disabled={creatingPR || !canCreatePR}>
                  <GitPullRequest className="h-3.5 w-3.5 mr-1.5" />
                  {creatingPR ? 'Creating...' : 'Create PR'}
                </Button>
              </>
            )}
            <div className="flex-1" />
            <Button variant="ghost" size="sm" onClick={handleIgnore}>
              <X className="h-3.5 w-3.5 mr-1.5" />
              Ignore
            </Button>
          </div>
        </div>

        {/* PR Preview Modal */}
        {showPRPreview && (
          <div className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setShowPRPreview(false)}>
            <div className="bg-[#0a0a10] border border-white/[0.08] rounded-2xl max-w-lg w-full shadow-2xl shadow-black/50" onClick={(e) => e.stopPropagation()}>
              <div className="p-5 border-b border-white/[0.06]">
                <h3 className="text-base font-semibold text-white/90">PR Preview</h3>
                <p className="text-xs text-white/40 mt-1">Review the changes before creating the pull request</p>
              </div>
              <div className="p-5 space-y-3">
                <div className="flex items-center gap-3 text-sm">
                  <GitBranch className="h-4 w-4 text-white/40 shrink-0" />
                  <span className="text-white/50">Repository</span>
                  <span className="ml-auto text-white/80 font-medium">{prPreviewData.repository}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <FileCode className="h-4 w-4 text-white/40 shrink-0" />
                  <span className="text-white/50">Affected File</span>
                  <span className="ml-auto text-white/80 font-mono text-xs">{prPreviewData.file}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <ArrowUp className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span className="text-white/50">Lines Changed</span>
                  <span className="ml-auto text-white/80 font-mono">{prPreviewData.lineCount} added</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <Shield className="h-4 w-4 text-amber-400 shrink-0" />
                  <span className="text-white/50">Risk Reduction</span>
                  <span className="ml-auto text-white/80">{prPreviewData.riskReduction}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <AlertCircle className="h-4 w-4 text-white/40 shrink-0" />
                  <span className="text-white/50">Findings Fixed</span>
                  <span className="ml-auto text-white/80 font-mono">1</span>
                </div>
              </div>
              <div className="p-5 border-t border-white/[0.06] flex items-center gap-2 justify-end">
                <Button variant="ghost" size="sm" onClick={() => setShowPRPreview(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" glow onClick={handleConfirmPR} disabled={creatingPR}>
                  <GitPullRequest className="h-3.5 w-3.5 mr-1.5" />
                  {creatingPR ? 'Creating...' : 'Create Pull Request'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

// ─── Recommendation Card ────────────────────────────────────
function RecommendationCard({
  group,
  index,
  onSelect,
}: {
  group: GroupedSuggestion
  index: number
  onSelect: (s: AISuggestion) => void
}) {
  const shouldReduceMotion = useReducedMotion()
  const Icon = CATEGORY_CONFIG[group.category.toLowerCase().replace(/\s+/g, '-')]?.icon || Lightbulb
  const fixAvailable = group.suggestions.some(s => s.fix_code)
  const hasMultipleFiles = group.uniqueFiles.length > 1
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelect(group.topSuggestion)
    }
  }, [onSelect, group.topSuggestion])

  return (
    <motion.div
      initial={shouldReduceMotion ? {} : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.35, delay: shouldReduceMotion ? 0 : index * 0.06, ease: [0.16, 1, 0.3, 1] }}
      className="group relative rounded-xl border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.04] transition-all duration-300 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a10]"
      onClick={() => onSelect(group.topSuggestion)}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`View recommendation: ${group.topSuggestion.title}`}
    >
      {/* Corner tick — signature move */}
      <div className="absolute top-0 right-0 w-8 h-8 overflow-hidden opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-opacity duration-300 pointer-events-none" aria-hidden="true">
        <div className="absolute top-0 right-0 w-12 h-12 bg-gradient-to-bl from-indigo-500/20 to-transparent transform rotate-45 translate-x-6 -translate-y-6" />
      </div>

      <div className="p-4 sm:p-5 space-y-3">
        {/* Row 1: Repository + Severity */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <FolderGit2 className="h-3.5 w-3.5 text-white/30 shrink-0" />
            <span className="text-xs font-medium text-white/70 truncate">{group.repository}</span>
          </div>
          <SeverityBadge severity={group.topSuggestion.severity} size="sm" />
        </div>

        {/* Row 2: Issue Title */}
        <h3 className="text-sm font-semibold text-white/90 leading-snug line-clamp-2">
          {group.topSuggestion.title}
        </h3>

        {/* Row 3: Affected File + Fix Available + Confidence */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
            <FileCode className="h-3 w-3 text-white/30" />
            <span className="text-[10px] font-mono text-white/50">
              {hasMultipleFiles ? `${group.uniqueFiles.length} files` : sanitizePath(group.topSuggestion.file_path)}
            </span>
          </div>
          {fixAvailable && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <Wrench className="h-2.5 w-2.5 text-emerald-400" />
              <span className="text-[10px] font-medium text-emerald-300/80">Fix available</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
            <Files className="h-3 w-3 text-white/30" />
            <span className="text-[10px] font-mono text-white/50">
              {group.count} {group.count === 1 ? 'finding' : 'findings'}
            </span>
          </div>
        </div>

        {/* Row 4: Actions */}
        <div className="flex items-center gap-1.5 flex-wrap pt-1">
          <button
            onClick={(e) => { e.stopPropagation(); onSelect(group.topSuggestion) }}
            className="px-3 py-1.5 rounded-lg text-[11px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors"
          >
            <Brain className="h-3 w-3 mr-1 inline-block" />
            Explain
          </button>
          {group.topSuggestion.fix_code && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); onSelect(group.topSuggestion) }}
                className="px-3 py-1.5 rounded-lg text-[11px] font-medium bg-white/[0.04] text-white/60 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
              >
                <Eye className="h-3 w-3 mr-1 inline-block" />
                Preview Fix
              </button>
              <button
                onClick={async (e) => {
                  e.stopPropagation()
                  try {
                    const r = await apiClient.post(`/suggestions/${group.topSuggestion.id}/create-pr`, {
                      pr_title: group.topSuggestion.title,
                      pr_description: `Automated fix for ${group.topSuggestion.title}`,
                    })
                    if (r.data.success) {
                      toast.success('PR created!')
                      window.open(r.data.pr_url, '_blank')
                    }
                  } catch { toast.error('Failed to create PR') }
                }}
                className="px-3 py-1.5 rounded-lg text-[11px] font-medium bg-white/[0.04] text-white/60 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
              >
                <GitPullRequest className="h-3 w-3 mr-1 inline-block" />
                Create PR
              </button>
            </>
          )}
          <button
            onClick={async (e) => {
              e.stopPropagation()
              try {
                await apiClient.post(`/suggestions/${group.topSuggestion.id}/ignore`)
                toast.success('Ignored')
              } catch { toast.error('Failed to ignore') }
            }}
            className="px-3 py-1.5 rounded-lg text-[11px] font-medium bg-white/[0.04] text-white/40 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
          >
            <X className="h-3 w-3 mr-1 inline-block" />
            Ignore
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// ─── Section Block ──────────────────────────────────────────
function SectionBlock({
  section,
  groups,
  onSelect,
}: {
  section: SectionType
  groups: GroupedSuggestion[]
  onSelect: (s: AISuggestion) => void
}) {
  const config = SECTION_CONFIG[section]
  const SectionIcon = config.icon

  if (groups.length === 0) {return null}

  return (
    <div className="space-y-4">
      <div className={cn('p-4 rounded-xl border bg-gradient-to-r', config.colors)}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-white/[0.06]">
            <SectionIcon className="h-5 w-5 text-white/70" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white/90">{config.label}</h2>
            <p className="text-xs text-white/40 mt-0.5">{config.description}</p>
          </div>
          <div className="ml-auto">
            <span className="text-xs font-mono text-white/30 bg-white/[0.04] px-2 py-1 rounded-lg">
              {groups.reduce((sum, g) => sum + g.count, 0)} {groups.reduce((sum, g) => sum + g.count, 0) === 1 ? 'finding' : 'findings'}
            </span>
          </div>
        </div>
      </div>
      <div className="grid gap-4">
        {groups.map((group, i) => (
          <RecommendationCard key={group.key} group={group} index={i} onSelect={onSelect} />
        ))}
      </div>
    </div>
  )
}

// ─── Main Page ──────────────────────────────────────────────
export function AISuggestionsPage() {
  const navigate = useNavigate()
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSuggestion, setSelectedSuggestion] = useState<AISuggestion | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const { user, isAuthenticated } = useAuthStore()
  const userPlan = user?.plan || 'free'
  const shouldReduceMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (isAuthenticated) {fetchAllSuggestions()}
  }, [isAuthenticated])

  const fetchAllSuggestions = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/suggestions')
      setSuggestions(response.data.suggestions || [])
    } catch (err: any) {
      console.error('Failed to fetch suggestions:', err)
      setError(err?.response?.data?.detail || err?.message || 'Failed to load recommendations. Please try again.')
      setSuggestions([])
    } finally { setLoading(false) }
  }

  const handleStatusChange = (id: string, newStatus: string) => {
    setSuggestions(prev => prev.map(s => s.id === id ? { ...s, status: newStatus as any } : s))
  }

  const openSuggestions = useMemo(() =>
    suggestions.filter(s => s.status === 'open'),
    [suggestions]
  )

  const filteredByCategory = useMemo(() => {
    if (categoryFilter === 'all') {return openSuggestions}
    return openSuggestions.filter(s => s.category.toLowerCase() === categoryFilter.toLowerCase())
  }, [openSuggestions, categoryFilter])

  const searchFiltered = useMemo(() => {
    if (!searchTerm.trim()) {return filteredByCategory}
    const term = searchTerm.toLowerCase()
    return filteredByCategory.filter(s =>
      s.title.toLowerCase().includes(term) ||
      s.description.toLowerCase().includes(term) ||
      s.file_path.toLowerCase().includes(term) ||
      s.category.toLowerCase().includes(term)
    )
  }, [filteredByCategory, searchTerm])

  const grouped = useMemo(() => groupSuggestions(searchFiltered), [searchFiltered])

  const groupsBySection = useMemo(() => {
    const map: Record<SectionType, GroupedSuggestion[]> = {
      'fix-first': [],
      'recommended': [],
      'optimization': [],
    }
    for (const g of grouped) {
      map[g.section].push(g)
    }
    return map
  }, [grouped])

  const categories = useMemo(() =>
    ['all', ...Array.from(new Set(suggestions.map(s => s.category.toLowerCase())))],
    [suggestions]
  )

  const totalOpen = openSuggestions.length
  const fixAvailableCount = useMemo(() =>
    openSuggestions.filter(s => s.fix_code).length,
    [openSuggestions]
  )

  const severityCounts = useMemo(() => ({
    critical: suggestions.filter(s => s.status === 'open' && s.severity === 'critical').length,
    high: suggestions.filter(s => s.status === 'open' && s.severity === 'high').length,
    medium: suggestions.filter(s => s.status === 'open' && s.severity === 'medium').length,
    low: suggestions.filter(s => s.status === 'open' && s.severity === 'low').length,
  }), [suggestions])

  return (
    <div className="min-h-screen bg-[#0a0a10]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <PageHeader
          title="AI Recommendations"
          description={
            totalOpen > 0
              ? `${totalOpen} open recommendation${totalOpen !== 1 ? 's' : ''} across ${grouped.length} ${grouped.length === 1 ? 'group' : 'groups'}`
              : 'Actionable fixes from your security scans'
          }
          actions={
            <>
              <button
                onClick={() => navigate('/docs/ai-recommendations')}
                className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                title="View AI Recommendations documentation"
                type="button"
              >
                <BookOpen className="h-4 w-4" />
              </button>
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                <Brain className="h-4 w-4 text-indigo-400" />
                <span className="text-sm font-medium text-white/70">{totalOpen} open</span>
              </div>
              <button
                onClick={fetchAllSuggestions}
                className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] transition-colors"
                disabled={loading}
                type="button"
                aria-label="Refresh recommendations"
              >
                <RefreshCw className={cn('h-4 w-4 text-white/40', loading && 'animate-spin')} />
              </button>
            </>
          }
        />

          {/* Stats Banner — counts from backend data only; no synthetic metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="text-xs text-white/40 mb-1">Total (all statuses)</div>
              <div className="text-lg font-bold font-mono text-white/80">
                {loading ? (
                  <span className="text-white/30">...</span>
                ) : (
                  suggestions.length
                )}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="text-xs text-white/40 mb-1">Open</div>
              <div className="text-lg font-bold font-mono text-blue-400">
                {loading ? <span className="text-white/30">...</span> : totalOpen}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="text-xs text-white/40 mb-1">Fix Available</div>
              <div className="text-lg font-bold font-mono text-emerald-400">
                {loading ? <span className="text-white/30">...</span> : fixAvailableCount}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="text-xs text-white/40 mb-1">Open by Severity</div>
              <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                {loading ? (
                  <span className="text-xs text-white/30">...</span>
                ) : (
                  <>
                    {['critical', 'high', 'medium', 'low'].map(sev => {
                      const count = severityCounts[sev as keyof typeof severityCounts]
                      if (count === 0) {return null}
                      const colors: Record<string, string> = {
                        critical: 'text-red-400 bg-red-500/10 border-red-500/20',
                        high: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
                        medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
                        low: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
                      }
                      return (
                        <span key={sev} className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${colors[sev]}`}>
                          {count} {sev}
                        </span>
                      )
                    })}
                    {severityCounts.critical === 0 && severityCounts.high === 0 && severityCounts.medium === 0 && severityCounts.low === 0 && (
                      <span className="text-xs text-white/30">None</span>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

        {/* === Search + Filters === */}
        <motion.div
          initial={shouldReduceMotion ? {} : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: shouldReduceMotion ? 0 : 0.1, duration: shouldReduceMotion ? 0 : 0.3 }}
          className="flex flex-col sm:flex-row gap-3"
        >
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
            <input
              type="text"
              placeholder="Search recommendations by title, description, file, or category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-sm text-white/80 placeholder:text-white/25 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/40 transition-all"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-white/30" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-sm text-white/70 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 appearance-none cursor-pointer"
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>
                  {cat === 'all' ? 'All Categories' : getCategoryLabel(cat)}
                </option>
              ))}
            </select>
          </div>
        </motion.div>

        {/* === Content === */}
        {error ? (
          <ErrorState
            title="Failed to load recommendations"
            message={`${error}. You can retry to fetch the latest AI suggestions.`}
            onRetry={fetchAllSuggestions}
          />
        ) : loading ? (
          <div className="space-y-6" aria-label="Loading recommendations">
            {([1, 2, 3]).map((i) => (
              <div key={i} className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-3.5 w-24 rounded" />
                    <Skeleton className="h-3.5 w-16 rounded" />
                  </div>
                  <Skeleton className="h-5 w-14 rounded-full" />
                </div>
                <Skeleton className="h-4 w-3/4 rounded" />
                <div className="flex items-center gap-2">
                  <Skeleton className="h-6 w-32 rounded-lg" />
                  <Skeleton className="h-6 w-20 rounded-lg" />
                </div>
                <div className="flex items-center gap-1.5 pt-1">
                  <Skeleton className="h-7 w-20 rounded-lg" />
                  <Skeleton className="h-7 w-20 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        ) : searchFiltered.length === 0 ? (
          <motion.div initial={shouldReduceMotion ? {} : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: shouldReduceMotion ? 0 : 0.3 }} className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
              <Brain className="h-8 w-8 text-white/20" />
            </div>
            <h3 className="text-base font-semibold text-white/60 mb-1">No recommendations found</h3>
            <p className="text-sm text-white/30">
              {searchTerm || categoryFilter !== 'all'
                ? 'Try adjusting your search or filters.'
                : 'No open recommendations at this time.'}
            </p>
          </motion.div>
        ) : (
          <motion.div
            initial={shouldReduceMotion ? {} : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: shouldReduceMotion ? 0 : 0.15, duration: shouldReduceMotion ? 0 : 0.35 }}
            className="space-y-10"
          >
            {(Object.entries(SECTION_CONFIG) as [SectionType, typeof SECTION_CONFIG['fix-first']][]).map(([sectionKey]) => (
              <SectionBlock
                key={sectionKey}
                section={sectionKey}
                groups={groupsBySection[sectionKey]}
                onSelect={(s) => setSelectedSuggestion(s)}
              />
            ))}
          </motion.div>
        )}

        {/* === Side Panel === */}
        <AnimatePresence>
          {selectedSuggestion && (
            <AIDetailSidePanel
              suggestion={selectedSuggestion}
              onClose={() => setSelectedSuggestion(null)}
              onStatusChange={handleStatusChange}
              userPlan={userPlan}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

import { useState, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Search, Filter, ArrowUpDown, ChevronDown, ChevronRight,
  FileCode, Sparkles, ExternalLink, ArrowLeft, ArrowRight,
  ScanSearch, Hash, GitMerge, BadgeCheck,
} from "lucide-react"
import { Finding } from "../../types"
import { cn, getSeverityColor, sanitizePath, getFileName, parseScannerSources } from "../../lib/utils"
import { Badge } from "../ui"
import { DiffViewer } from "../DiffViewer"
import { Button } from "../ui-animated"

interface FindingsExplorerProps {
  findings: Finding[]
  severityFilter: string
  sortBy: string
  searchQuery: string
  expandedFinding: string | null
  onSeverityFilterChange: (filter: string) => void
  onSortByChange: (sort: string) => void
  onSearchQueryChange: (query: string) => void
  onExpandedFindingChange: (id: string | null) => void
  onFindingClick?: (id: string) => void
  rawFindingsCount?: number
}

const SOURCE_COLORS: Record<string, string> = {
  DevArchAI: "bg-indigo-500/15 text-indigo-300 border-indigo-500/20",
  Checkov: "bg-cyan-500/15 text-cyan-300 border-cyan-500/20",
  Tfsec: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
  tfsec: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
  Trivy: "bg-rose-500/15 text-rose-300 border-rose-500/20",
  Gitleaks: "bg-amber-500/15 text-amber-300 border-amber-500/20",
  Hadolint: "bg-blue-500/15 text-blue-300 border-blue-500/20",
  "npm audit": "bg-purple-500/15 text-purple-300 border-purple-500/20",
  npm_audit: "bg-purple-500/15 text-purple-300 border-purple-500/20",
  "pip audit": "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/20",
  pip_audit: "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/20",
  govulncheck: "bg-orange-500/15 text-orange-300 border-orange-500/20",
  "Dependency Check": "bg-yellow-500/15 text-yellow-300 border-yellow-500/20",
  dependency_check: "bg-yellow-500/15 text-yellow-300 border-yellow-500/20",
  "Kube Score": "bg-sky-500/15 text-sky-300 border-sky-500/20",
  kube_score: "bg-sky-500/15 text-sky-300 border-sky-500/20",
}

function getSourceColor(source: string): string {
  return SOURCE_COLORS[source] ?? "bg-white/10 text-white/50 border-white/10"
}

const columns = [
  { key: "severity", label: "Severity", width: "w-[80px]" },
  { key: "rule_id", label: "Rule ID", width: "w-[120px]" },
  { key: "scanner", label: "Source", width: "w-[110px]" },
  { key: "category", label: "Category", width: "w-[90px]" },
  { key: "issue", label: "Issue", width: "flex-1 min-w-[160px]" },
  { key: "file", label: "File", width: "w-[130px]" },
  { key: "confidence", label: "Conf.", width: "w-[60px]" },
  { key: "actions", label: "", width: "w-[60px]" },
]

export function FindingsExplorer({
  findings, severityFilter, sortBy, searchQuery,
  expandedFinding, onSeverityFilterChange, onSortByChange,
  onSearchQueryChange, onExpandedFindingChange, onFindingClick,
  rawFindingsCount,
}: FindingsExplorerProps) {
  const [page, setPage] = useState(1)
  const perPage = 15

  const filtered = useMemo(() => {
    let result = [...findings]

    if (severityFilter !== "all") {
      result = result.filter(f => f.severity === severityFilter)
    }

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(f =>
        (f.summary?.toLowerCase().includes(q)) ||
        (f.message?.toLowerCase().includes(q)) ||
        (f.rule_id?.toLowerCase().includes(q)) ||
        (f.rule_name?.toLowerCase().includes(q)) ||
        (f.file_path?.toLowerCase().includes(q)) ||
        (f.category?.toLowerCase().includes(q)) ||
        (f.scanner_name?.toLowerCase().includes(q))
      )
    }

    switch (sortBy) {
      case "severity":
        const order = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
        result.sort((a, b) => (order[a.severity as keyof typeof order] ?? 5) - (order[b.severity as keyof typeof order] ?? 5))
        break
      case "file":
        result.sort((a, b) => (a.file_path || "").localeCompare(b.file_path || ""))
        break
      case "category":
        result.sort((a, b) => (a.category || "").localeCompare(b.category || ""))
        break
      default:
        break
    }

    return result
  }, [findings, severityFilter, sortBy, searchQuery])

  const totalPages = Math.ceil(filtered.length / perPage)
  const paged = filtered.slice((page - 1) * perPage, page * perPage)
  const severityOptions = ["all", "critical", "high", "medium", "low", "info"]
  const sortOptions = [
    { value: "severity", label: "Severity" },
    { value: "file", label: "File" },
    { value: "category", label: "Category" },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl overflow-hidden"
    >
      {/* Header with search & filters */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
            Findings Explorer
            <span className="ml-2 text-xs text-white/30 font-normal normal-case">
              ({filtered.length} of {findings.length})
            </span>
          </h3>
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
            <input
              type="text"
              placeholder="Search findings..."
              value={searchQuery}
              onChange={e => { onSearchQueryChange(e.target.value); setPage(1) }}
              className="w-full h-9 pl-9 pr-3 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 placeholder-white/20 outline-none focus:border-indigo-500/40 focus:bg-white/[0.04] transition-colors"
            />
          </div>
          <div className="flex gap-2">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20 pointer-events-none" />
              <select
                value={severityFilter}
                onChange={e => { onSeverityFilterChange(e.target.value); setPage(1) }}
                className="h-9 pl-9 pr-8 rounded-lg bg-white/5 border border-white/10 text-sm text-white/60 outline-none appearance-none cursor-pointer focus:border-indigo-500/40 transition-colors"
              >
                {severityOptions.map(s => (
                  <option key={s} value={s} className="bg-slate-900">
                    {s === "all" ? "All Severities" : s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-white/20 pointer-events-none" />
            </div>
            <div className="relative">
              <ArrowUpDown className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20 pointer-events-none" />
              <select
                value={sortBy}
                onChange={e => onSortByChange(e.target.value)}
                className="h-9 pl-9 pr-8 rounded-lg bg-white/5 border border-white/10 text-sm text-white/60 outline-none appearance-none cursor-pointer focus:border-indigo-500/40 transition-colors"
              >
                {sortOptions.map(s => (
                  <option key={s.value} value={s.value} className="bg-slate-900">{s.label}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-white/20 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Raw vs Normalized bar */}
        {rawFindingsCount != null && rawFindingsCount !== findings.length && (
          <div className="mt-3 flex items-center gap-2 text-[10px] text-white/30 bg-white/[0.02] rounded-lg px-3 py-2 border border-white/5">
            <GitMerge className="w-3 h-3 text-indigo-400/60" />
            <span>
              <span className="text-white/50 font-medium">{rawFindingsCount}</span> scanner findings deduplicated to{" "}
              <span className="text-white/50 font-medium">{findings.length}</span> unique findings
            </span>
            <span className="text-white/10">·</span>
            <span className="text-indigo-400/60">
              {rawFindingsCount - findings.length} duplicates merged
            </span>
          </div>
        )}
      </div>

      {/* Enterprise table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              {columns.map(col => (
                <th key={col.key} className={cn("px-3 py-3 text-left text-[10px] font-semibold text-white/30 uppercase tracking-wider", col.width)}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            <AnimatePresence mode="popLayout">
              {paged.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-12 text-center text-white/30">
                    <Search className="w-6 h-6 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No findings match your filters</p>
                  </td>
                </tr>
              ) : (
                paged.map((finding, i) => {
                  const findingId = finding.id ?? finding.rule_id
                  const severityColor = getSeverityColor(finding.severity)
                  const isExpanded = expandedFinding === findingId
                  const confidence = finding.confidence ?? finding.confidence_score
                  const sources = parseScannerSources(finding.scanner_name)
                  const hasAutoFix = !!finding.fix_code
                  const hasMergedSources = sources.length > 1
                  return (
                    <motion.tr
                      key={findingId}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ delay: i * 0.015 }}
                      className={cn(
                        "transition-colors",
                        isExpanded ? "bg-indigo-500/5" : "hover:bg-white/[0.02]"
                      )}
                    >
                      <td className="px-3 py-3">
                        <span className={cn(
                          "px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider inline-block",
                          severityColor.bg, severityColor.text
                        )}>
                          {finding.severity}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <span className="text-xs text-white/40 font-mono">{finding.rule_id}</span>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-1">
                          {sources.map((source, si) => (
                            <span
                              key={si}
                              className={cn(
                                "inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium border",
                                getSourceColor(source),
                                si > 0 && "relative"
                              )}
                            >
                              {si === 0 && <ScanSearch className="w-2.5 h-2.5 shrink-0" />}
                              {source}
                            </span>
                          ))}
                          {hasMergedSources && (
                            <span
                              className="inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[8px] font-medium bg-indigo-500/10 text-indigo-400/70 border border-indigo-500/10 cursor-help"
                              title={`Detected by ${sources.join(", ")}`}
                            >
                              <GitMerge className="w-2 h-2" />
                              merged
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-3 text-xs text-white/50 capitalize">{finding.category || "—"}</td>
                      <td className="px-3 py-3">
                        <button
                          onClick={() => onFindingClick?.(findingId)}
                          className="text-sm text-white/80 hover:text-white transition-colors text-left line-clamp-1"
                        >
                          {finding.summary || finding.message || finding.rule_name || finding.rule_id}
                        </button>
                      </td>
                      <td className="px-3 py-3 text-xs text-white/40 font-mono truncate max-w-[130px]" title={sanitizePath(finding.file_path) || ''}>
                        {getFileName(finding.file_path)}
                      </td>
                      <td className="px-3 py-3">
                        {confidence != null ? (
                          <span className={cn(
                            "text-[10px] font-medium px-1 py-0.5 rounded",
                            confidence >= 0.8 ? "bg-emerald-500/10 text-emerald-400" :
                            confidence >= 0.5 ? "bg-yellow-500/10 text-yellow-400" :
                            "bg-gray-500/10 text-gray-400"
                          )}>
                            {(confidence * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-[10px] text-white/20">—</span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-1">
                          {hasAutoFix && (
                            <span title="Auto-fix available" className="inline-flex items-center justify-center w-5 h-5 rounded bg-emerald-500/10">
                              <Sparkles className="w-3 h-3 text-emerald-400" />
                            </span>
                          )}
                          <button
                            onClick={() => onExpandedFindingChange(isExpanded ? null : findingId)}
                            className="text-white/20 hover:text-white/40 transition-colors"
                          >
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  )
                })
              )}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      {/* Expanded finding detail */}
      <AnimatePresence>
        {expandedFinding && (() => {
          const finding = findings.find(f => (f.id ?? f.rule_id) === expandedFinding)
          if (!finding) return null
          return (
            <motion.div
              key={expandedFinding}
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-t border-white/5"
            >
              <div className="p-4 space-y-3 bg-white/[0.01]">
                {finding.description && (
                  <p className="text-xs text-white/50 leading-relaxed">{finding.description}</p>
                )}
                {(finding.before_code || finding.after_code || finding.unified_diff) && (
                  <DiffViewer
                    beforeCode={finding.before_code}
                    afterCode={finding.after_code}
                    unifiedDiff={finding.unified_diff}
                    filename={sanitizePath(finding.file_path) || "file"}
                  />
                )}
                <div className="flex items-center gap-2">
                  {finding.fix_code && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigator.clipboard.writeText(finding.fix_code || "")}
                    >
                      Copy Fix
                    </Button>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })()}
      </AnimatePresence>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-white/5">
          <span className="text-xs text-white/30">
            Page {page} of {totalPages} ({filtered.length} total)
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="w-7 h-7 rounded flex items-center justify-center text-xs text-white/30 hover:text-white/60 hover:bg-white/5 disabled:opacity-20 disabled:cursor-not-allowed"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 3, totalPages - 6))
              const p = start + i
              if (p > totalPages) return null
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={cn(
                    "w-7 h-7 rounded text-xs transition-colors",
                    page === p
                      ? "bg-indigo-500/20 text-indigo-300"
                      : "text-white/30 hover:text-white/60 hover:bg-white/5"
                  )}
                >
                  {p}
                </button>
              )
            })}
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="w-7 h-7 rounded flex items-center justify-center text-xs text-white/30 hover:text-white/60 hover:bg-white/5 disabled:opacity-20 disabled:cursor-not-allowed"
            >
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </motion.div>
  )
}

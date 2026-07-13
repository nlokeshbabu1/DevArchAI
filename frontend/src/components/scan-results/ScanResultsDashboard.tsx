import { useState, useMemo } from "react"
import { SecurityHero } from "./SecurityHero"
import { ExecutiveSummary } from "./ExecutiveSummary"
import { FixTheseFirst } from "./PriorityRisks"
import { FindingsExplorer } from "./FindingsExplorer"
import { DetectionCoverage } from "./DetectionCoverage"
import { ScannerExecutionTable } from "./ScannerExecutionTable"
import { ScanCoverageSummary } from "./ScanCoverageSummary"
import { EmptyState } from "./EmptyState"
import { FindingDetailsDrawer } from "./FindingDetailsDrawer"
import { Diagnostics } from "./Diagnostics"
import { motion } from "framer-motion"
import { X } from "lucide-react"
import { cn, getFileName } from "../../lib/utils"

interface ScanResultData {
  ai_status?: "pending" | "processing" | "completed" | "failed"
  status?: string
  scan_id?: string
  overall_score?: number
  security_score?: number
  files_analyzed?: number
  directories_scanned?: number
  lines_analyzed?: number
  repository_size?: string
  branch?: string
  repository_url?: string
  repository_name?: string
  completed_at?: string
  analysis_duration_seconds?: number
  detected_technologies?: string[]
  findings?: any[]
  severity_counts?: Record<string, number>
  category_scores?: { category: string; score: number; findings_count?: number; files_scanned?: number }[]
  commit_hash?: string
  scanner_executions?: any[]
  ai_suggestions_count?: number
  findings_count?: number
}

interface ScanResultsDashboardProps {
  result: ScanResultData
  repoName: string
  findings: any[]
  severityCounts: Record<string, number>
  priorityFixes: any[]
  isAiReady: boolean
  isAiPending: boolean
  aiSummary: string | null
  severityFilter: string
  sortBy: string
  expandedFinding: string | null
  searchQuery: string
  onSeverityFilterChange: (filter: string) => void
  onSortByChange: (sort: string) => void
  onExpandedFindingChange: (id: string | null) => void
  onSearchQueryChange: (query: string) => void
  onRescan: () => void
  onDownload: (format: "pdf" | "excel" | "json" | "sarif") => void
  onShare: () => void
  onFindFix: (findingId: string) => void
  onGenerateFix: (findingId: string) => void
  onCreatePR: (findingId: string) => void
  onBatchCreatePR?: (findingIds: string[]) => void
  hideHeaderActions?: boolean
}

export function ScanResultsDashboard({
  result, repoName, findings, severityCounts, priorityFixes,
  isAiReady, isAiPending, aiSummary,
  severityFilter, sortBy, expandedFinding, searchQuery,
  onSeverityFilterChange, onSortByChange, onExpandedFindingChange,
  onSearchQueryChange, onRescan, onDownload, onShare, onFindFix,
  onGenerateFix, onCreatePR, onBatchCreatePR, hideHeaderActions = false,
}: ScanResultsDashboardProps) {
  const [drawerFindingId, setDrawerFindingId] = useState<string | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const isEmpty = findings.length === 0
  const score = result.overall_score ?? 0

  const rawFindingsCount = useMemo(() => {
    if (!result.scanner_executions) return undefined
    return result.scanner_executions.reduce((sum: number, e: any) => sum + (e.findings_count || 0), 0)
  }, [result.scanner_executions])

  const scannersCount = result.scanner_executions?.length

  const filesScanned = useMemo(() => {
    const backend = result.files_analyzed
    const uniqueFiles = new Set(findings.map(f => f.file_path).filter(Boolean))
    const derived = uniqueFiles.size
    if ((backend === 0 || backend == null) && derived > 0) return derived
    return Math.max(backend ?? 0, derived)
  }, [result.files_analyzed, findings])

  const affectedFiles = useMemo(() => {
    return new Set(findings.map(f => f.file_path).filter(Boolean)).size
  }, [findings])

  const rulesExecuted = useMemo(() => {
    return new Set(findings.map(f => f.rule_id).filter(Boolean)).size
  }, [findings])

  const directoriesScanned = useMemo(() => {
    if (result.directories_scanned != null) return result.directories_scanned
    const dirs = new Set(findings.map(f => {
      const p = f.file_path
      if (!p) return null
      const parts = p.split("/")
      if (parts.length > 1) return parts.slice(0, -1).join("/")
      return "/"
    }).filter(Boolean))
    return dirs.size > 0 ? dirs.size : undefined
  }, [result.directories_scanned, findings])

  const technologiesCount = result.detected_technologies?.length ?? 0

  const coverageScores = result.category_scores?.reduce((acc, cat) => {
    acc[cat.category] = cat.score
    return acc
  }, {} as Record<string, number>) ?? {}

  const filteredByCategory = useMemo(() => {
    if (!categoryFilter) return findings
    const catKey = categoryFilter.toLowerCase()
    return findings.filter((f: any) => {
      const fc = (f.category ?? "").toLowerCase()
      const fp = (f.file_path ?? "").toLowerCase()
      if (catKey === "secrets") return fc.includes("secret") || fc.includes("credential") || fc.includes("key") || fc.includes("token")
      if (catKey === "sca") return fc.includes("dependency") || fc.includes("sca") || fc.includes("package") || fc.includes("npm") || fc.includes("pip")
      if (catKey === "container") return fc.includes("container") || fc.includes("docker") || fp.includes("dockerfile")
      if (catKey === "iac") return fc.includes("iac") || fc.includes("terraform") || fc.includes("tf") || fp.endsWith(".tf")
      if (catKey === "sast") return fc.includes("sast") || fc.includes("code analysis") || fc.includes("static")
      if (catKey === "cicd") return fc.includes("ci") || fc.includes("cd") || fc.includes("cicd") || fp.includes(".github") || fp.includes("workflow")
      if (catKey === "misconfig") return fc.includes("misconfig") || fc.includes("misconfiguration") || fc.includes("hardening")
      if (catKey === "license") return fc.includes("license") || fc.includes("licensing") || fc.includes("compliance")
      return true
    })
  }, [findings, categoryFilter])

  const drawerFinding = drawerFindingId
    ? findings.find(f => (f.id ?? f.rule_id) === drawerFindingId)
    : null

  const handleOpenDrawer = (id: string) => setDrawerFindingId(id)
  const handleCloseDrawer = () => setDrawerFindingId(null)

  const handleCopyFix = (code: string) => navigator.clipboard.writeText(code)

  const handleDownloadPatch = (finding: any) => {
    if (!finding.fix_code) return
    const blob = new Blob([finding.fix_code], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `fix-${finding.rule_id}-${getFileName(finding.file_path) || "patch"}.patch`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleCreatePR = (finding: any) => onCreatePR(finding.id ?? finding.rule_id)
  const handleCategoryClick = (cat: string) => setCategoryFilter(cat || null)

  return (
    <div className="min-h-screen bg-[#0a0a10]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 lg:py-6 space-y-4">

        {/* ===== SECTION 1: Repository Summary ===== */}
        <SecurityHero
          overallScore={score}
          repoName={repoName}
          branch={result.branch}
          completedAt={result.completed_at}
          techStack={result.detected_technologies}
          filesAnalyzed={filesScanned}
          totalFindings={findings.length}
          analysisDuration={result.analysis_duration_seconds}
          affectedFiles={affectedFiles}
        />

        {/* Empty State */}
        {isEmpty ? (
          <EmptyState
            score={score}
            repoName={repoName}
            filesAnalyzed={filesScanned}
            coveragePercent={coverageScores.sast ?? 100}
            rulesExecuted={rulesExecuted}
            onRescan={onRescan}
          />
        ) : (
          <>
            {/* Scan Coverage Metrics */}
            <ScanCoverageSummary
              filesScanned={filesScanned}
              directoriesScanned={directoriesScanned}
              rulesExecuted={rulesExecuted}
              technologiesCount={technologiesCount}
              scanDuration={result.analysis_duration_seconds}
              linesAnalyzed={result.lines_analyzed}
              repoSize={result.repository_size}
            />

            {/* ===== SECTION 2: Technology Coverage ===== */}
            <DetectionCoverage
              scannerExecutions={result.scanner_executions}
              findings={findings}
            />

            {/* ===== SECTION 3: Security Findings (PRIMARY) ===== */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-1 h-5 rounded-full bg-indigo-500" />
                <h2 className="text-base font-bold text-white/80">Security Findings</h2>
                <span className="text-xs text-white/30">{findings.length} issue{findings.length !== 1 ? "s" : ""}</span>
              </div>

              {/* AI Recommendations + Priority Risks */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2">
                  <ExecutiveSummary
                    severityCounts={severityCounts}
                    categoryScores={result.category_scores ?? []}
                    onCategoryClick={handleCategoryClick}
                    activeCategory={categoryFilter}
                    findings={findings}
                    detectedTechnologies={result.detected_technologies}
                  />
                </div>
                <div className="lg:col-span-1">
                  <FixTheseFirst
                    findings={priorityFixes}
                    currentScore={score}
                    onSelect={handleOpenDrawer}
                    selectedId={drawerFindingId}
                  />
                </div>
              </div>

              {/* Findings Table */}
              <FindingsExplorer
                findings={filteredByCategory}
                severityFilter={severityFilter}
                sortBy={sortBy}
                searchQuery={searchQuery}
                expandedFinding={expandedFinding}
                onSeverityFilterChange={onSeverityFilterChange}
                onSortByChange={onSortByChange}
                onSearchQueryChange={onSearchQueryChange}
                onExpandedFindingChange={onExpandedFindingChange}
                onFindingClick={handleOpenDrawer}
                rawFindingsCount={rawFindingsCount}
              />
            </div>

            {/* Category filter indicator */}
            {categoryFilter && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2"
              >
                <span className="text-xs text-white/40">Filtered by category:</span>
                <button
                  onClick={() => setCategoryFilter(null)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[11px] text-indigo-300 hover:bg-indigo-500/20 transition-colors"
                >
                  {categoryFilter}
                  <X className="w-3 h-3" />
                </button>
                <span className="text-xs text-white/20">{filteredByCategory.length} findings</span>
              </motion.div>
            )}

            {/* ===== SECTION 5: Scanner Health ===== */}
            {result.scanner_executions && result.scanner_executions.length > 0 && (
              <ScannerExecutionTable executions={result.scanner_executions} />
            )}

            {/* ===== SECTION 6: Diagnostics ===== */}
            <Diagnostics
              repoName={repoName}
              filesCount={filesScanned}
              directoriesCount={directoriesScanned}
              findingsCount={findings.length}
              rulesCount={rulesExecuted}
              technologiesCount={technologiesCount}
              scanDuration={result.analysis_duration_seconds}
              completedAt={result.completed_at}
              branch={result.branch}
              commitHash={result.commit_hash}
              rawFindingsCount={rawFindingsCount}
              aiSuggestionsCount={result.ai_suggestions_count}
              scannersCount={scannersCount}
              currentStep={8}
              totalScanners={result.scanner_executions?.length ?? 0}
              completedScanners={result.scanner_executions?.filter((e: any) =>
                ["COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS"].includes(e.status)
              ).length ?? 0}
              aiStatus={result.ai_status ?? (isAiReady ? "completed" : isAiPending ? "processing" : "pending")}
              scanStatus={result.status ?? "completed"}
            />
          </>
        )}
      </div>

      {/* Finding Details Drawer */}
      <FindingDetailsDrawer
        finding={drawerFinding}
        isOpen={!!drawerFinding}
        onClose={handleCloseDrawer}
        currentScore={score}
        onCopyFix={handleCopyFix}
        onDownloadPatch={handleDownloadPatch}
        onCreatePR={handleCreatePR}
      />
    </div>
  )
}

import { useState } from "react"
import { SecurityHero } from "./SecurityHero"
import { ExecutiveSummary } from "./ExecutiveSummary"
import { FixTheseFirst } from "./PriorityRisks"
import { FindingsExplorer } from "./FindingsExplorer"
import { SecurityCoverage } from "./SecurityCoverage"
import { SecurityTrends } from "./SecurityTrends"
import { FixRoadmap } from "./FixRoadmap"
import { ReportCenter } from "./ReportCenter"
import { EmptyState } from "./EmptyState"
import { FindingDetailsDrawer } from "./FindingDetailsDrawer"
import { motion } from "framer-motion"
import { RefreshCw, Share2, Download } from "lucide-react"
import { Button } from "../ui-animated"

interface ScanResultData {
  overall_score?: number
  security_score?: number
  files_analyzed?: number
  branch?: string
  repository_url?: string
  repository_name?: string
  completed_at?: string
  analysis_duration_seconds?: number
  detected_technologies?: string[]
  findings?: any[]
  severity_counts?: Record<string, number>
  category_scores?: { category: string; score: number; findings_count?: number }[]
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
  hideHeaderActions?: boolean
}

export function ScanResultsDashboard({
  result, repoName, findings, severityCounts, priorityFixes,
  isAiReady, isAiPending, aiSummary,
  severityFilter, sortBy, expandedFinding, searchQuery,
  onSeverityFilterChange, onSortByChange, onExpandedFindingChange,
  onSearchQueryChange, onRescan, onDownload, onShare, onFindFix,
  onGenerateFix, onCreatePR, hideHeaderActions = false,
}: ScanResultsDashboardProps) {
  const [drawerFindingId, setDrawerFindingId] = useState<string | null>(null)
  const isEmpty = findings.length === 0
  const score = result.overall_score ?? 0

  const coverageScores = result.category_scores?.reduce((acc, cat) => {
    acc[cat.category] = cat.score
    return acc
  }, {} as Record<string, number>) ?? {}

  const drawerFinding = drawerFindingId
    ? findings.find(f => (f.id ?? f.rule_id) === drawerFindingId)
    : null

  const handleOpenDrawer = (id: string) => {
    setDrawerFindingId(id)
  }

  const handleCloseDrawer = () => {
    setDrawerFindingId(null)
  }

  const handleCopyFix = (code: string) => {
    navigator.clipboard.writeText(code)
  }

  const handleDownloadPatch = (finding: any) => {
    if (!finding.fix_code) return
    const blob = new Blob([finding.fix_code], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `fix-${finding.rule_id}-${finding.file_path?.split("/").pop() || "patch"}.patch`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleCreatePR = (finding: any) => {
    onCreatePR(finding.id ?? finding.rule_id)
  }

  return (
    <div className="min-h-screen bg-[#0a0a10]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
        {/* Header Actions */}
        {!hideHeaderActions && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between"
          >
            <div>
              <h1 className="text-lg font-semibold text-white/80">Scan Results</h1>
              <p className="text-xs text-white/30 mt-0.5">Detailed security analysis for {repoName}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onRescan}>
                <RefreshCw className="w-4 h-4 mr-1.5" />
                Rescan
              </Button>
              <Button variant="ghost" size="sm" onClick={onShare as any}>
                <Share2 className="w-4 h-4 mr-1.5" />
                Share
              </Button>
              <Button variant="ghost" size="sm" onClick={() => onDownload("pdf")}>
                <Download className="w-4 h-4 mr-1.5" />
                Export
              </Button>
            </div>
          </motion.div>
        )}

        {/* Section 1: Security Hero */}
        <SecurityHero
          overallScore={score}
          repoName={repoName}
          branch={result.branch}
          techStack={result.detected_technologies}
          filesAnalyzed={result.files_analyzed ?? 0}
          totalFindings={result.findings?.length ?? 0}
          completedAt={result.completed_at}
          analysisDuration={result.analysis_duration_seconds}
        />

        {/* Empty State */}
        {isEmpty ? (
          <EmptyState
            score={score}
            repoName={repoName}
            filesAnalyzed={result.files_analyzed ?? 0}
            coveragePercent={coverageScores.sast ?? 100}
            rulesExecuted={0}
            onRescan={onRescan}
          />
        ) : (
          <>
            {/* Section 2 & 3: Executive Summary + Priority Risks */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ExecutiveSummary
                  severityCounts={severityCounts}
                  categoryScores={result.category_scores ?? []}
                  findings={findings}
                />
              </div>
              <div className="lg:col-span-1">
                <FixTheseFirst
                  findings={priorityFixes}
                  currentScore={score}
                  onSelect={handleOpenDrawer}
                  onGenerateFix={onGenerateFix}
                  onCreatePR={handleCreatePR}
                  selectedId={drawerFindingId}
                />
              </div>
            </div>

            {/* Section 4: Fix Roadmap + Security Trends (side by side) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <FixRoadmap
                  currentScore={score}
                />
              </div>
              <div className="lg:col-span-1">
                <SecurityTrends
                  currentScore={score}
                  criticalTrend={{ previous: severityCounts.critical || 0, current: severityCounts.critical || 0 }}
                  highTrend={{ previous: severityCounts.high || 0, current: severityCounts.high || 0 }}
                  mediumTrend={{ previous: severityCounts.medium || 0, current: severityCounts.medium || 0 }}
                />
              </div>
            </div>

            {/* Section 5: Findings Explorer */}
            <FindingsExplorer
              findings={findings}
              severityFilter={severityFilter}
              sortBy={sortBy}
              searchQuery={searchQuery}
              expandedFinding={expandedFinding}
              onSeverityFilterChange={onSeverityFilterChange}
              onSortByChange={onSortByChange}
              onSearchQueryChange={onSearchQueryChange}
              onExpandedFindingChange={onExpandedFindingChange}
              onFindingClick={handleOpenDrawer}
            />

            {/* Section 6: Security Coverage */}
            <SecurityCoverage scores={coverageScores} />
          </>
        )}

        {/* Report Center */}
        <ReportCenter onDownload={onDownload} onShare={onShare} />

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center pb-8"
        >
          <p className="text-xs text-white/10">
            DevArchAI Security Scan · {new Date().toISOString().split("T")[0]}
          </p>
        </motion.div>
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

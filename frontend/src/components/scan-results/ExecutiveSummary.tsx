import { motion } from "framer-motion"
import {
  AlertTriangle, Bug, AlertCircle, Info,
  Shield, ShieldCheck, ShieldAlert, ShieldX,
  Code2, Database, GanttChartSquare,
  Globe, Key, Files, List, Box, Braces,
  Server, Container, ArrowRight, CircleDot
} from "lucide-react"
import { useMemo, memo } from "react"

import { cn, classifyFindingScanner } from "../../lib/utils"

interface ExecutiveSummaryProps {
  severityCounts: Record<string, number>
  categoryScores?: { category: string; score: number; findings_count?: number; files_scanned?: number }[]
  onCategoryClick?: (category: string) => void
  activeCategory?: string | null
  findings?: any[]
  detectedTechnologies?: string[]
}

const severityConfig: Record<string, { icon: typeof AlertTriangle; color: string; bg: string; border: string; label: string }> = {
  critical: { icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", label: "Critical" },
  high: { icon: Bug, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", label: "High" },
  medium: { icon: AlertCircle, color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20", label: "Medium" },
  low: { icon: Info, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", label: "Low" },
  info: { icon: Info, color: "text-gray-400", bg: "bg-gray-500/10", border: "border-gray-500/20", label: "Info" },
}

const categoryConfig = [
  { key: "secrets", label: "Secret Detection", icon: Key, color: "text-pink-400", bg: "bg-pink-500/10", border: "border-pink-500/20" },
  { key: "container", label: "Container", icon: Container, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
  { key: "iac", label: "Infrastructure", icon: GanttChartSquare, color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20" },
  { key: "cicd", label: "CI/CD", icon: Globe, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20" },
  { key: "kubernetes", label: "Kubernetes", icon: Server, color: "text-cyan-400", bg: "bg-cyan-500/10", border: "border-cyan-500/20" },
  { key: "sast", label: "Code Security", icon: Code2, color: "text-indigo-400", bg: "bg-indigo-500/10", border: "border-indigo-500/20" },
  { key: "sca", label: "Dependency Security", icon: Database, color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20" },
  { key: "license", label: "License Compliance", icon: Braces, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
]

function matchSecurityCategory(finding: any, catKey: string): boolean {
  return classifyFindingScanner(finding) === catKey
}

export const ExecutiveSummary = memo(function ExecutiveSummary({
  severityCounts = {}, categoryScores = [],
  onCategoryClick, activeCategory, findings = [],
  detectedTechnologies = []
}: ExecutiveSummaryProps) {
  const hasData = Object.keys(severityCounts).length > 0 || findings.length > 0

  const categoryStats = useMemo(() => {
    const counts: Record<string, number> = {}
    const files: Record<string, Set<string>> = {}
    for (const cat of categoryConfig) {
      counts[cat.key] = 0
      files[cat.key] = new Set()
    }
    for (const f of findings) {
      for (const cat of categoryConfig) {
        if (matchSecurityCategory(f, cat.key)) {
          counts[cat.key] = (counts[cat.key] || 0) + 1
          if (f.file_path) {files[cat.key].add(f.file_path)}
        }
      }
    }
    const fileCounts: Record<string, number> = {}
    for (const [k, v] of Object.entries(files)) {
      fileCounts[k] = v.size
    }
    return { counts, fileCounts }
  }, [findings])

  const totalFindings = findings.length
  const totalFiles = useMemo(() => {
    const unique = new Set<string>()
    for (const f of findings) {
      if (f.file_path) {unique.add(f.file_path)}
    }
    return unique.size
  }, [findings])

  const techs = detectedTechnologies.length > 0 ? detectedTechnologies : []

  const criticalCount = severityCounts.critical || 0
  const highCount = severityCounts.high || 0
  const mediumCount = severityCounts.medium || 0
  const lowCount = severityCounts.low || 0

  const overallGrade = criticalCount > 0 ? "F" : highCount > 0 ? "D" : mediumCount > 2 ? "C" : mediumCount > 0 ? "B" : "A"
  const gradeColor = overallGrade === "A" ? "text-emerald-400" : overallGrade === "B" ? "text-green-400" : overallGrade === "C" ? "text-yellow-400" : overallGrade === "D" ? "text-orange-400" : "text-red-400"
  const gradeBg = overallGrade === "A" ? "bg-emerald-500/10 border-emerald-500/20" : overallGrade === "B" ? "bg-green-500/10 border-green-500/20" : overallGrade === "C" ? "bg-yellow-500/10 border-yellow-500/20" : overallGrade === "D" ? "bg-orange-500/10 border-orange-500/20" : "bg-red-500/10 border-red-500/20"
  const GradeIcon = overallGrade === "A" ? ShieldCheck : overallGrade === "B" ? Shield : overallGrade === "C" ? ShieldAlert : ShieldX
  const gradeLabel = overallGrade === "A" ? "Excellent" : overallGrade === "B" ? "Good" : overallGrade === "C" ? "Fair" : overallGrade === "D" ? "Poor" : "Critical"

  const affectedCategories = useMemo(() => {
    return categoryConfig
      .map((cat) => ({ ...cat, count: categoryStats.counts[cat.key] || 0 }))
      .filter((cat) => cat.count > 0)
      .sort((a, b) => b.count - a.count)
  }, [categoryStats])

  const actions = useMemo(() => {
    const items: { label: string; severity: "critical" | "high" | "medium" | "low" }[] = []
    if (criticalCount > 0) {items.push({ label: `Address ${criticalCount} critical ${criticalCount === 1 ? "finding" : "findings"} immediately`, severity: "critical" })}
    if (highCount > 0) {items.push({ label: `Review ${highCount} high-severity ${highCount === 1 ? "issue" : "issues"}`, severity: "high" })}
    for (const cat of affectedCategories.slice(0, 3)) {
      items.push({ label: `Audit ${cat.label} (${cat.count} ${cat.count === 1 ? "finding" : "findings"})`, severity: cat.count > 5 ? "high" : "medium" })
    }
    if (items.length === 0 && lowCount > 0) {items.push({ label: `Address ${lowCount} low-priority ${lowCount === 1 ? "item" : "items"}`, severity: "low" })}
    return items
  }, [criticalCount, highCount, lowCount, affectedCategories])

  const actionSeverityColors: Record<string, string> = {
    critical: "text-red-400 bg-red-500/10",
    high: "text-orange-400 bg-orange-500/10",
    medium: "text-yellow-400 bg-yellow-500/10",
    low: "text-blue-400 bg-blue-500/10",
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 h-full flex flex-col"
    >
      <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">
        Executive Summary
      </h3>

      {!hasData ? (
        <div className="flex items-center justify-center h-24 text-white/30 text-sm">
          <Shield className="w-5 h-5 mr-2" />
          No issues found
        </div>
      ) : (
        <div className="flex-1 space-y-5">
          {/* Overall Posture */}
          <div className={cn("rounded-xl border p-4", gradeBg)}>
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-14 h-14 rounded-xl bg-white/5 border border-white/10">
                <span className={cn("text-2xl font-bold", gradeColor)}>{overallGrade}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <GradeIcon className={cn("w-4 h-4", gradeColor)} />
                  <span className={cn("text-sm font-semibold", gradeColor)}>{gradeLabel}</span>
                </div>
                <p className="text-[11px] text-white/40">
                  {totalFindings} {totalFindings === 1 ? "finding" : "findings"} across {totalFiles} {totalFiles === 1 ? "file" : "files"}
                </p>
              </div>
            </div>
            {/* Severity bar */}
            {totalFindings > 0 && (
              <div className="mt-3 space-y-1.5">
                <div className="flex h-1.5 gap-0.5 rounded-full overflow-hidden bg-white/5">
                  {Object.entries(severityConfig).map(([key, config]) => {
                    const count = severityCounts[key] || 0
                    if (count === 0) {return null}
                    const pct = (count / totalFindings) * 100
                    return (
                      <div
                        key={key}
                        className={cn("h-full rounded-full transition-all duration-700", config.bg.replace("/10", "/40"))}
                        style={{ width: `${pct}%` }}
                      />
                    )
                  })}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-white/40">
                  {criticalCount > 0 && <span className="text-red-400">{criticalCount} critical</span>}
                  {highCount > 0 && <span className="text-orange-400">{highCount} high</span>}
                  {mediumCount > 0 && <span className="text-yellow-400">{mediumCount} medium</span>}
                  {lowCount > 0 && <span className="text-blue-400">{lowCount} low</span>}
                </div>
              </div>
            )}
          </div>

          {/* Critical Risks */}
          {(criticalCount > 0 || highCount > 0) && (
            <div>
              <h4 className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-2.5">
                Critical Risks
              </h4>
              <div className="space-y-1.5">
                {criticalCount > 0 && (
                  <motion.div
                    whileHover={{ scale: 1.01 }}
                    className="flex items-center gap-2.5 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2"
                  >
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                    <span className="text-xs text-red-300 font-medium">{criticalCount} critical {criticalCount === 1 ? "issue" : "issues"} require immediate attention</span>
                  </motion.div>
                )}
                {highCount > 0 && (
                  <motion.div
                    whileHover={{ scale: 1.01 }}
                    className="flex items-center gap-2.5 rounded-lg border border-orange-500/20 bg-orange-500/10 px-3 py-2"
                  >
                    <Bug className="w-3.5 h-3.5 text-orange-400 shrink-0" />
                    <span className="text-xs text-orange-300 font-medium">{highCount} high-severity {highCount === 1 ? "issue" : "issues"} should be addressed soon</span>
                  </motion.div>
                )}
              </div>
            </div>
          )}

          {/* Most Affected Technologies */}
          {affectedCategories.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-2.5">
                Most Affected Areas
              </h4>
              <div className="space-y-1.5">
                {affectedCategories.slice(0, 4).map((cat) => {
                  const Icon = cat.icon
                  const maxCount = affectedCategories[0]?.count || 1
                  const barPct = (cat.count / maxCount) * 100
                  return (
                    <motion.button
                      key={cat.key}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => onCategoryClick?.(activeCategory === cat.key ? "" : cat.key)}
                      className={cn(
                        "w-full flex items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition-all",
                        cat.bg, cat.border,
                        activeCategory === cat.key && "ring-2 ring-white/20"
                      )}
                    >
                      <Icon className={cn("w-3.5 h-3.5 shrink-0", cat.color)} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className={cn("text-[11px] font-medium", cat.color)}>{cat.label}</span>
                          <span className="text-[10px] text-white/40">{cat.count}</span>
                        </div>
                        <div className="h-1 rounded-full bg-white/5 overflow-hidden">
                          <div
                            className={cn("h-full rounded-full transition-all duration-500", cat.bg.replace("/10", "/40"))}
                            style={{ width: `${barPct}%` }}
                          />
                        </div>
                      </div>
                    </motion.button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Scanned Technologies */}
          {techs.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-2.5">
                Detected Technologies
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {techs.map((tech) => (
                  <span
                    key={tech}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] text-white/60"
                  >
                    <Box className="w-3 h-3 text-white/30" />
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Next Actions */}
          {actions.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-2.5">
                Recommended Next Actions
              </h4>
              <div className="space-y-1.5">
                {actions.map((action, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-2.5 rounded-lg bg-white/[0.03] border border-white/5 px-3 py-2"
                  >
                    <CircleDot className={cn("w-3 h-3 shrink-0", actionSeverityColors[action.severity].split(" ")[0])} />
                    <span className="text-[11px] text-white/60 flex-1">{action.label}</span>
                    <ArrowRight className="w-3 h-3 text-white/20" />
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Summary footer */}
          <div className="flex items-center gap-3 text-[11px] text-white/30 border-t border-white/5 pt-3">
            <span className="flex items-center gap-1">
              <Files className="w-3 h-3" />
              {totalFiles} {totalFiles === 1 ? "file" : "files"} affected
            </span>
            <span className="flex items-center gap-1">
              <List className="w-3 h-3" />
              {totalFindings} total {totalFindings === 1 ? "finding" : "findings"}
            </span>
          </div>
        </div>
      )}
    </motion.div>
  )
})

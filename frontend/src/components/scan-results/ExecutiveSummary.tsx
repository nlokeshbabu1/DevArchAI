import { useMemo } from "react"
import { motion } from "framer-motion"
import {
  AlertTriangle, Bug, AlertCircle, Info,
  Shield, Code2, Database, GanttChartSquare,
  Globe, Key, Files, List, Box, Braces,
  Server, Container
} from "lucide-react"
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
  { key: "secrets", label: "Secrets", icon: Key, color: "text-pink-400", bg: "bg-pink-500/10", border: "border-pink-500/20" },
  { key: "container", label: "Container", icon: Container, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
  { key: "iac", label: "IaC", icon: GanttChartSquare, color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20" },
  { key: "cicd", label: "CI/CD", icon: Globe, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20" },
  { key: "kubernetes", label: "Kubernetes", icon: Server, color: "text-cyan-400", bg: "bg-cyan-500/10", border: "border-cyan-500/20" },
  { key: "sast", label: "SAST", icon: Code2, color: "text-indigo-400", bg: "bg-indigo-500/10", border: "border-indigo-500/20" },
  { key: "sca", label: "SCA", icon: Database, color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20" },
  { key: "license", label: "License Compliance", icon: Braces, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
]

function matchSecurityCategory(finding: any, catKey: string): boolean {
  return classifyFindingScanner(finding) === catKey
}

export function ExecutiveSummary({
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
          if (f.file_path) files[cat.key].add(f.file_path)
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
      if (f.file_path) unique.add(f.file_path)
    }
    return unique.size
  }, [findings])

  const techs = detectedTechnologies.length > 0 ? detectedTechnologies : []

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
          {/* Severity Breakdown */}
          <div>
            <h4 className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-2.5">
              Severity Breakdown
            </h4>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
              {Object.entries(severityConfig).map(([key, config]) => {
                const Icon = config.icon
                const count = severityCounts[key] || 0
                return (
                  <motion.div
                    key={key}
                    whileHover={{ scale: 1.02 }}
                    className={cn(
                      "rounded-lg border p-2.5 transition-all duration-200",
                      config.bg, config.border
                    )}
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <Icon className={cn("w-3 h-3", config.color)} />
                      <span className={cn("text-[10px] font-medium", config.color)}>
                        {config.label}
                      </span>
                    </div>
                    <span className={cn("text-lg font-bold", config.color)}>{count}</span>
                  </motion.div>
                )
              })}
            </div>
          </div>

          {/* Scanned Technologies */}
          {techs.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-2.5">
                Scanned Technologies
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

          {/* Security Categories */}
          <div>
            <h4 className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-2.5">
              Security Categories
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {categoryConfig.map((cat) => {
                const Icon = cat.icon
                const findingsCount = categoryStats.counts[cat.key] || 0
                const filesScanned = categoryStats.fileCounts[cat.key] || 0
                const isActive = activeCategory === cat.key
                return (
                  <motion.button
                    key={cat.key}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onCategoryClick?.(isActive ? '' : cat.key)}
                    className={cn(
                      "rounded-lg border p-2.5 text-left transition-all duration-200 cursor-pointer",
                      cat.bg, cat.border,
                      isActive && "ring-2 ring-white/30"
                    )}
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <Icon className={cn("w-3 h-3", cat.color)} />
                      <span className={cn("text-[10px] font-semibold", cat.color)}>{cat.label}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-white/50">
                      <span className="flex items-center gap-0.5">
                        <Files className="w-2.5 h-2.5 text-white/30" />
                        {filesScanned}
                      </span>
                      <span className="flex items-center gap-0.5">
                        <List className="w-2.5 h-2.5 text-white/30" />
                        {findingsCount}
                      </span>
                    </div>
                  </motion.button>
                )
              })}
            </div>
          </div>

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
}

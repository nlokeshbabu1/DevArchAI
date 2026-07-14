import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Shield, Cloud, Server, GanttChartSquare,
  Globe, Lock, Package2, Code2,
  CheckCircle2, AlertCircle, HelpCircle, XCircle,
  Layers, ChevronDown, ChevronRight,
} from "lucide-react"
import {
  cn, TECHNOLOGY_COVERAGE, getScannerPurpose,
  classifyFindingTechnology, getTechnologySeverityCounts, getSeverityColor,
} from "../../lib/utils"
import type { ScannerExecution } from "../../types"

interface DetectionCoverageProps {
  scannerExecutions?: ScannerExecution[]
  findings?: any[]
}

const techIcons: Record<string, typeof Shield> = {
  container: Cloud,
  dockerfile: Code2,
  kubernetes: Server,
  terraform: GanttChartSquare,
  cicd: Globe,
  secrets: Lock,
  dependencies: Package2,
}

const CARD_STATUS: Record<string, { label: string; icon: typeof Shield; color: string; border: string }> = {
  DETECTED: { label: "Detected", icon: CheckCircle2, color: "text-emerald-400", border: "border-emerald-500/20 bg-emerald-500/[0.03]" },
  CLEAN: { label: "Clear", icon: CheckCircle2, color: "text-white/30", border: "border-white/5 bg-white/[0.02]" },
  UNAVAILABLE: { label: "Unavailable", icon: HelpCircle, color: "text-zinc-400", border: "border-zinc-500/10 bg-zinc-500/[0.02]" },
  NOT_APPLICABLE: { label: "Not Applicable", icon: XCircle, color: "text-amber-400", border: "border-amber-500/10 bg-amber-500/[0.02]" },
  FAILED: { label: "Failed", icon: AlertCircle, color: "text-red-400", border: "border-red-500/10 bg-red-500/[0.02]" },
}

const SEVERITY_LABELS = ["critical", "high", "medium", "low"] as const

function getScannerStatusLabel(status: string): string {
  if (["COMPLETED", "COMPLETED_WITH_FINDINGS"].includes(status)) return "Completed"
  if (status === "COMPLETED_NO_FINDINGS") return "Clear"
  if (status === "SKIPPED_NOT_APPLICABLE") return "Not Applicable"
  if (status === "UNAVAILABLE" || status === "DISABLED") return "Unavailable"
  if (status === "FAILED") return "Failed"
  if (status === "RUNNING") return "Running"
  return status
}

function getStatusReason(exec: ScannerExecution): string {
  if (exec.status === "UNAVAILABLE") return exec.skipped_reason || `CLI not installed`
  if (exec.status === "DISABLED") return exec.skipped_reason || "Scanner not enabled on current worker"
  if (exec.status === "SKIPPED_NOT_APPLICABLE") return exec.skipped_reason || "Not applicable"
  if (exec.status === "FAILED") return exec.error_message || ""
  return ""
}

interface ScannerInfo {
  id: string
  name: string
  status: string
  findings: number
  reason: string
  purpose: string
}

interface TechAgg {
  techFindingCount: number
  severityCounts: Record<string, number>
  scannerCount: number
  activeScannerCount: number
  scannerStatus: string
  scanners: ScannerInfo[]
}

function aggregateTechData(
  tech: typeof TECHNOLOGY_COVERAGE[number],
  executions: ScannerExecution[],
  techFindings: any[],
): TechAgg | null {
  const memberExecs = executions.filter(e => tech.scannerIds.includes(e.scanner_id))
  if (memberExecs.length === 0 && techFindings.length === 0) return null

  const scanners = memberExecs.map(exec => {
    const findings = exec.findings_count ?? 0
    return {
      id: exec.scanner_id,
      name: exec.scanner_name,
      status: exec.status,
      findings,
      reason: getStatusReason(exec),
      purpose: getScannerPurpose(exec.scanner_id),
    }
  })

  const activeScannerCount = scanners.filter(s =>
    ["COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS"].includes(s.status)
  ).length

  const running = memberExecs.find(e => e.status === "RUNNING")
  const failed = memberExecs.find(e => e.status === "FAILED")
  const unavailable = memberExecs.find(e => e.status === "UNAVAILABLE" || e.status === "DISABLED")
  const skipped = memberExecs.find(e => e.status === "SKIPPED_NOT_APPLICABLE")

  let scannerStatus: string
  if (techFindings.length > 0) scannerStatus = "DETECTED"
  else if (running) scannerStatus = "RUNNING"
  else if (failed) scannerStatus = "FAILED"
  else if (unavailable && !activeScannerCount) scannerStatus = "UNAVAILABLE"
  else if (skipped && !activeScannerCount) scannerStatus = "SKIPPED_NOT_APPLICABLE"
  else scannerStatus = "COMPLETED_NO_FINDINGS"

  return {
    techFindingCount: techFindings.length,
    severityCounts: getTechnologySeverityCounts(techFindings, tech.key),
    scannerCount: scanners.length,
    activeScannerCount,
    scannerStatus,
    scanners,
  }
}

function renderSeverityBadge(sev: string, count: number): React.ReactNode {
  const colors = getSeverityColor(sev)
  return (
    <span key={sev} className={cn("font-mono text-[10px]", colors.text)}>
      {count} {sev}
    </span>
  )
}

export function DetectionCoverage({ scannerExecutions = [], findings = [] }: DetectionCoverageProps) {
  const [expandedTech, setExpandedTech] = useState<string | null>(null)

  const techData = useMemo(() => {
    return TECHNOLOGY_COVERAGE.map(tech => {
      const techFindings = findings.filter(f => classifyFindingTechnology(f) === tech.key)
      const agg = aggregateTechData(tech, scannerExecutions, techFindings)
      return { tech, agg, techFindings }
    })
  }, [scannerExecutions, findings])

  const configuredTechs = techData.filter(t => t.agg !== null)
  const totalTechFindings = configuredTechs.reduce((s, t) => s + (t.agg?.techFindingCount ?? 0), 0)

  if (scannerExecutions.length === 0 && findings.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-yellow-500/10 bg-yellow-500/[0.02] backdrop-blur-xl p-5"
      >
        <div className="flex items-center gap-2 mb-2">
          <Layers className="w-4 h-4 text-yellow-400/60" />
          <h3 className="text-sm font-semibold text-yellow-400/70 uppercase tracking-wider">
            Technology Coverage
          </h3>
        </div>
        <p className="text-xs text-yellow-300/40">
          Coverage data will appear after the scan completes.
        </p>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
            Technology Coverage
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-white/30">
          <span>{configuredTechs.length} technologies</span>
          {totalTechFindings > 0 && (
            <>
              <span className="text-white/10">|</span>
              <span className="text-orange-400/70">
                {totalTechFindings} finding{totalTechFindings !== 1 ? "s" : ""}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {configuredTechs.map(({ tech, agg, techFindings }, i) => {
          if (!agg) return null
          const Icon = techIcons[tech.key] || Shield
          const isExpanded = expandedTech === tech.key
          const cardStatus = agg.scannerStatus as keyof typeof CARD_STATUS
          const statusCfg = CARD_STATUS[cardStatus] ?? CARD_STATUS.CLEAN
          const StatusIcon = statusCfg.icon
          const sevCounts = agg.severityCounts
          const hasSevBreakdown = SEVERITY_LABELS.some(s => (sevCounts[s] ?? 0) > 0)

          return (
            <motion.div
              key={tech.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <div
                onClick={() => setExpandedTech(isExpanded ? null : tech.key)}
                className={cn(
                  "rounded-xl border p-3.5 transition-all duration-200 cursor-pointer",
                  statusCfg.border,
                  "hover:border-white/20"
                )}
              >
                <div className="flex items-center gap-2 mb-2.5">
                  <div className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                    cardStatus === "DETECTED" ? "bg-indigo-500/10" : "bg-white/[0.02]"
                  )}>
                    <Icon className={cn(
                      "w-4 h-4",
                      cardStatus === "DETECTED" ? "text-indigo-400" : "text-white/20"
                    )} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={cn(
                      "text-xs font-semibold leading-tight",
                      cardStatus === "DETECTED" ? "text-white/80" : "text-white/40"
                    )}>
                      {tech.label}
                    </div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <StatusIcon className={cn("w-2.5 h-2.5", statusCfg.color)} />
                      <span className={cn("text-[9px]", statusCfg.color)}>{statusCfg.label}</span>
                    </div>
                  </div>
                  <div className="shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5 text-white/20" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-white/20" />
                    )}
                  </div>
                </div>

                {/* Severity breakdown */}
                {hasSevBreakdown && (
                  <div className="flex flex-wrap gap-x-2 gap-y-0.5 mb-1.5">
                    {SEVERITY_LABELS.map(sev => {
                      const count = sevCounts[sev] ?? 0
                      if (count === 0) return null
                      return renderSeverityBadge(sev, count)
                    })}
                  </div>
                )}

                <div className="flex items-center gap-3 text-[10px]">
                  {agg.techFindingCount > 0 ? (
                    <span className="font-mono font-bold text-orange-400/80">
                      {agg.techFindingCount} finding{agg.techFindingCount !== 1 ? "s" : ""}
                    </span>
                  ) : (
                    <span className="text-emerald-400/50">No security issues</span>
                  )}
                  <span className="text-white/30">
                    {agg.activeScannerCount}/{agg.scannerCount} scanners
                  </span>
                </div>

                {cardStatus === "UNAVAILABLE" && (
                  <div className="mt-2 text-[9px] text-zinc-400/60 italic leading-tight">
                    {agg.scanners.some(s => s.id === "gitleaks" || s.id === "checkov")
                      ? `${agg.scanners.find(s => s.id === "gitleaks" || s.id === "checkov")?.name} CLI not installed`
                      : "Scanner not enabled on current worker"}
                  </div>
                )}
                {cardStatus === "NOT_APPLICABLE" && (
                  <div className="mt-2 text-[9px] text-amber-400/60 italic leading-tight">
                    Technology not detected in repository
                  </div>
                )}
              </div>

              {/* Expanded scanner details */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-1 rounded-xl border border-white/10 bg-white/[0.03] overflow-hidden">
                      <table className="w-full text-[10px]">
                        <thead>
                          <tr className="border-b border-white/5">
                            <th className="text-left py-2 px-3 text-[9px] text-white/30 font-semibold uppercase tracking-wider">Scanner</th>
                            <th className="text-left py-2 px-3 text-[9px] text-white/30 font-semibold uppercase tracking-wider">Status</th>
                            <th className="text-right py-2 px-3 text-[9px] text-white/30 font-semibold uppercase tracking-wider">Findings</th>
                            <th className="text-left py-2 px-3 text-[9px] text-white/30 font-semibold uppercase tracking-wider">Purpose</th>
                          </tr>
                        </thead>
                        <tbody>
                          {agg.scanners.map(scanner => {
                            const isCompleted = ["COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS"].includes(scanner.status)
                            const isNA = scanner.status === "SKIPPED_NOT_APPLICABLE"
                            const isUnavail = scanner.status === "UNAVAILABLE" || scanner.status === "DISABLED"
                            const isFailed = scanner.status === "FAILED"
                            return (
                              <tr key={scanner.id} className="border-b border-white/[0.02] last:border-0">
                                <td className="py-2 px-3">
                                  <span className="text-white/70 font-medium">{scanner.name}</span>
                                </td>
                                <td className="py-2 px-3">
                                  <span className={cn(
                                    "inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-medium",
                                    isCompleted ? "text-emerald-400 bg-emerald-500/10" :
                                    isNA ? "text-amber-400 bg-amber-500/10" :
                                    isUnavail ? "text-zinc-400 bg-zinc-500/10" :
                                    isFailed ? "text-red-400 bg-red-500/10" :
                                    "text-white/30 bg-white/[0.03]"
                                  )}>
                                    {getScannerStatusLabel(scanner.status)}
                                  </span>
                                </td>
                                <td className="py-2 px-3 text-right">
                                  {isCompleted ? (
                                    scanner.findings > 0 ? (
                                      <span className="font-mono font-bold text-orange-400/80">{scanner.findings}</span>
                                    ) : (
                                      <span className="text-emerald-400/50">Clear</span>
                                    )
                                  ) : (
                                    <span className="text-white/20">—</span>
                                  )}
                                </td>
                                <td className="py-2 px-3 text-white/40 max-w-[140px] truncate" title={scanner.purpose}>
                                  {scanner.purpose}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                      {agg.scanners.some(s => s.reason) && (
                        <div className="px-3 py-2 border-t border-white/5 space-y-1">
                          {agg.scanners.filter(s => s.reason).map(s => (
                            <div key={s.id} className="flex items-center gap-1.5 text-[9px] text-white/30">
                              <span className="text-white/50">{s.name}:</span>
                              <span>{s.reason}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

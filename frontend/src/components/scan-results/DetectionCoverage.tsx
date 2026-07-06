import { useMemo } from "react"
import { motion } from "framer-motion"
import {
  Shield, Lock, Server, Cloud,
  Globe, GanttChartSquare, ScanSearch, Code2,
  CheckCircle2, SkipForward, Ban, AlertCircle, Clock,
  Layers, Loader2, HelpCircle,
} from "lucide-react"
import {
  cn, SCANNER_FAMILIES,
} from "../../lib/utils"
import type { ScannerExecution } from "../../types"

interface DetectionCoverageProps {
  scannerExecutions?: ScannerExecution[]
  findings?: any[]
  detectedTechnologies?: string[]
}

const familyIcons: Record<string, typeof Shield> = {
  container: Cloud,
  kubernetes: Server,
  iac: GanttChartSquare,
  cicd: Globe,
  secrets: Lock,
  sca: Shield,
  dockerfile: Code2,
  sast: ScanSearch,
}

const STATUS_STYLES: Record<string, { label: string; icon: typeof Shield; color: string }> = {
  COMPLETED_WITH_FINDINGS: {
    label: "Completed",
    icon: CheckCircle2,
    color: "bg-emerald-500/10 text-emerald-400",
  },
  COMPLETED_NO_FINDINGS: {
    label: "Completed",
    icon: CheckCircle2,
    color: "bg-emerald-500/10 text-emerald-400",
  },
  COMPLETED: {
    label: "Completed",
    icon: CheckCircle2,
    color: "bg-emerald-500/10 text-emerald-400",
  },
  SKIPPED_NOT_APPLICABLE: {
    label: "Skipped",
    icon: SkipForward,
    color: "bg-amber-500/10 text-amber-400",
  },
  UNAVAILABLE: {
    label: "Unavailable",
    icon: HelpCircle,
    color: "bg-amber-500/10 text-amber-400",
  },
  DISABLED: {
    label: "Disabled",
    icon: Ban,
    color: "bg-zinc-500/10 text-zinc-400",
  },
  FAILED: {
    label: "Failed",
    icon: AlertCircle,
    color: "bg-red-500/10 text-red-400",
  },
  RUNNING: {
    label: "Running",
    icon: Clock,
    color: "bg-indigo-500/10 text-indigo-400",
  },
  DISCOVERED: {
    label: "Discovered",
    icon: Clock,
    color: "bg-blue-500/10 text-blue-400",
  },
  INITIALIZING: {
    label: "Initializing",
    icon: Loader2,
    color: "bg-blue-500/10 text-blue-400",
  },
}

function getStatusStyle(status: string) {
  return STATUS_STYLES[status] ?? STATUS_STYLES.DISCOVERED
}

const PER_SCANNER_STATUS_STYLES: Record<string, { icon: typeof Shield; color: string }> = {
  COMPLETED_WITH_FINDINGS: { icon: CheckCircle2, color: "text-emerald-400" },
  COMPLETED_NO_FINDINGS: { icon: CheckCircle2, color: "text-emerald-500" },
  COMPLETED: { icon: CheckCircle2, color: "text-emerald-400" },
  SKIPPED_NOT_APPLICABLE: { icon: SkipForward, color: "text-amber-400" },
  UNAVAILABLE: { icon: HelpCircle, color: "text-amber-400" },
  DISABLED: { icon: Ban, color: "text-zinc-400" },
  FAILED: { icon: AlertCircle, color: "text-red-400" },
  RUNNING: { icon: Loader2, color: "text-indigo-400" },
  DISCOVERED: { icon: Clock, color: "text-blue-400" },
  INITIALIZING: { icon: Loader2, color: "text-blue-400" },
}

interface ScannerInfo {
  id: string
  name: string
  status: string
  rawFindings: number
  skippedReason?: string
}

interface FamilyAgg {
  rawFindings: number
  durationMs: number
  scanners: ScannerInfo[]
  status: string
  tooltip: string
}

function getScannerStatusReason(exec: ScannerExecution): string {
  if (exec.status === "UNAVAILABLE") return exec.skipped_reason || "CLI tool not installed"
  if (exec.status === "DISABLED") return exec.skipped_reason || "Scanner disabled in configuration"
  if (exec.status === "SKIPPED_NOT_APPLICABLE") return exec.skipped_reason || "Not applicable"
  if (exec.status === "FAILED") return exec.error_message || ""
  return ""
}

function aggregateFamily(
  familyKey: string,
  family: typeof SCANNER_FAMILIES[number] | undefined,
  executions: ScannerExecution[],
): FamilyAgg | null {
  if (!family) return null

  const memberExecs = executions.filter(e => family.scannerIds.includes(e.scanner_id))
  if (memberExecs.length === 0) return null

  const primaryFamily = getPrimaryFamilyForScanner(memberExecs[0].scanner_id)
  const isPrimary = familyKey === primaryFamily

  let rawFindings = 0
  let durationMs = 0
  const scanners: ScannerInfo[] = []

  for (const exec of memberExecs) {
    const execPrimary = getPrimaryFamilyForScanner(exec.scanner_id)
    scanners.push({
      id: exec.scanner_id,
      name: exec.scanner_name,
      status: exec.status,
      rawFindings: exec.findings_count ?? 0,
      skippedReason: getScannerStatusReason(exec) || undefined,
    })
    if (execPrimary === familyKey) {
      rawFindings += exec.findings_count ?? 0
      durationMs += exec.duration_ms ?? 0
    }
  }

  const running = memberExecs.find(e => e.status === "RUNNING")
  const failed = memberExecs.find(e => e.status === "FAILED")
  const completedWith = memberExecs.find(e => e.status === "COMPLETED_WITH_FINDINGS")
  const completedNo = memberExecs.find(e => e.status === "COMPLETED_NO_FINDINGS")
  const unavailable = memberExecs.find(e => e.status === "UNAVAILABLE")
  const disabled = memberExecs.find(e => e.status === "DISABLED")
  const skipped = memberExecs.find(e => e.status === "SKIPPED_NOT_APPLICABLE")

  let status: string
  let tooltip: string

  if (running) {
    status = "RUNNING"
    tooltip = "Scanner is running"
  } else if (failed) {
    status = "FAILED"
    tooltip = failed.error_message || "Scanner failed"
  } else if (completedWith) {
    status = "COMPLETED_WITH_FINDINGS"
    tooltip = `${rawFindings} total raw finding(s)`
  } else if (completedNo) {
    status = "COMPLETED_NO_FINDINGS"
    tooltip = "All scans completed with no findings"
  } else if (unavailable) {
    status = "UNAVAILABLE"
    tooltip = unavailable.skipped_reason ?? "CLI tool not installed"
  } else if (disabled) {
    status = "DISABLED"
    tooltip = disabled.skipped_reason ?? "Scanner disabled in configuration"
  } else if (skipped) {
    status = "SKIPPED_NOT_APPLICABLE"
    tooltip = skipped.skipped_reason ?? "Technology not detected"
  } else {
    status = "DISCOVERED"
    tooltip = "Scanner discovered but not started"
  }

  return { rawFindings, durationMs, scanners, status, tooltip }
}

function getPrimaryFamilyForScanner(scannerId: string): string {
  for (const family of SCANNER_FAMILIES) {
    if (family.scannerIds.includes(scannerId)) return family.key
  }
  if (scannerId.startsWith("trivy")) return "container"
  return "sast"
}

export function DetectionCoverage({ scannerExecutions = [], detectedTechnologies = [] }: DetectionCoverageProps) {
  const familyData = useMemo(() => {
    return SCANNER_FAMILIES.map(family => {
      const agg = aggregateFamily(family.key, family, scannerExecutions)
      return { family, agg }
    })
  }, [scannerExecutions, detectedTechnologies])

  const configuredFamilies = familyData.filter(f => f.agg !== null)
  const rawTotal = configuredFamilies.reduce((s, f) => s + (f.agg?.rawFindings ?? 0), 0)
  const totalDuration = configuredFamilies.reduce((s, f) => s + (f.agg?.durationMs ?? 0), 0)

  if (scannerExecutions.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-yellow-500/10 bg-yellow-500/[0.02] backdrop-blur-xl p-5"
      >
        <div className="flex items-center gap-2 mb-2">
          <Clock className="w-4 h-4 text-yellow-400/60" />
          <h3 className="text-sm font-semibold text-yellow-400/70 uppercase tracking-wider">
            Detection Coverage
          </h3>
        </div>
        <p className="text-xs text-yellow-300/40">
          Scanner execution data will appear after the scan completes.
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
            Detection Coverage
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-white/30">
          <span>{configuredFamilies.length} families</span>
          <span className="text-white/10">|</span>
          <span>{rawTotal} raw findings</span>
          <span className="text-white/10">|</span>
          <span>{totalDuration < 1000 ? `${totalDuration}ms` : `${(totalDuration / 1000).toFixed(1)}s`}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {configuredFamilies.map(({ family, agg }, i) => {
          if (!agg) return null
          const Icon = familyIcons[family.key] || Shield
          const statusStyle = getStatusStyle(agg.status)
          const StatusIcon = statusStyle.icon
          const isCompleted = agg.status === "COMPLETED_WITH_FINDINGS" || agg.status === "COMPLETED_NO_FINDINGS" || agg.status === "COMPLETED"
          const hasFindings = agg.rawFindings > 0
          const isSkipped = agg.status === "SKIPPED_NOT_APPLICABLE"
          const isUnavailable = agg.status === "UNAVAILABLE"
          const isDisabled = agg.status === "DISABLED"
          const isFailed = agg.status === "FAILED"
          const isRunning = agg.status === "RUNNING"

          const activeScanners = agg.scanners.filter(s =>
            s.status !== "UNAVAILABLE" && s.status !== "DISABLED" && s.status !== "SKIPPED_NOT_APPLICABLE" && s.status !== "DISCOVERED" && s.status !== "INITIALIZING"
          )

          return (
            <motion.div
              key={family.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              title={agg.tooltip}
              className={cn(
                "rounded-xl border p-3.5 transition-all duration-200",
                isCompleted && hasFindings
                  ? "border-indigo-500/20 bg-indigo-500/[0.03] hover:border-indigo-500/30"
                  : isCompleted && !hasFindings
                    ? "border-emerald-500/10 bg-emerald-500/[0.02]"
                    : isFailed
                      ? "border-red-500/10 bg-red-500/[0.02]"
                      : isSkipped || isUnavailable
                        ? "border-amber-500/10 bg-amber-500/[0.02]"
                        : "border-white/5 bg-white/[0.02]"
              )}
            >
              <div className="flex items-center gap-2 mb-2.5">
                <div className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                  hasFindings ? "bg-indigo-500/10" : isCompleted ? "bg-emerald-500/10" : "bg-white/[0.02]"
                )}>
                  <Icon className={cn(
                    "w-4 h-4",
                    hasFindings ? "text-indigo-400" : isCompleted ? "text-emerald-400" : isFailed ? "text-red-400" : "text-white/20"
                  )} />
                </div>
                <div>
                  <div className={cn(
                    "text-xs font-semibold leading-tight",
                    hasFindings ? "text-white/80" : isCompleted ? "text-white/50" : "text-white/30"
                  )}>
                    {family.label}
                  </div>
                  {activeScanners.length > 0 && (
                    <div className="text-[9px] text-white/20 mt-0.5">
                      {activeScanners.map(s => s.name).join(" + ")}
                    </div>
                  )}
                </div>
              </div>

              <div className="mb-2">
                <span className={cn(
                  "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider",
                  statusStyle.color,
                )}>
                  <StatusIcon className={cn("w-2.5 h-2.5", isRunning && "animate-spin")} />
                  {statusStyle.label}
                </span>
              </div>

              {(isCompleted || isRunning) && (
                <div className="space-y-1">
                  {hasFindings ? (
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-base font-bold font-mono tabular-nums text-white/90">
                        {agg.rawFindings}
                      </span>
                      <span className="text-[9px] text-white/20">raw findings</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[10px] text-emerald-400/60">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Completed (0 findings)</span>
                    </div>
                  )}
                  <div className="flex gap-2 text-[9px] text-white/20">
                    <span>{agg.scanners.length} scanner{agg.scanners.length !== 1 ? "s" : ""}</span>
                    {agg.durationMs > 0 && (
                      <>
                        <span className="text-white/10">·</span>
                        <span>{agg.durationMs < 1000 ? `${agg.durationMs}ms` : `${(agg.durationMs / 1000).toFixed(1)}s`}</span>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Per-scanner breakdown */}
              <div className="mt-2 space-y-1">
                {agg.scanners.map(s => {
                  const ps = PER_SCANNER_STATUS_STYLES[s.status]
                  const PIcon = ps?.icon || HelpCircle
                  const reason = s.skippedReason
                  return (
                    <div key={s.id} className="flex items-center gap-1.5" title={reason}>
                      <PIcon className={cn("w-2.5 h-2.5 shrink-0", ps?.color || "text-white/20")} />
                      <span className="text-[9px] text-white/40 truncate">{s.name}</span>
                      {reason && (
                        <span className="text-[7px] text-white/20 truncate ml-auto">{reason}</span>
                      )}
                    </div>
                  )
                })}
              </div>

              {isSkipped && (
                <div className="text-[9px] text-amber-400/60 mt-1 italic leading-tight">
                  {agg.scanners.map(s => s.skippedReason).filter(Boolean).join("; ")}
                </div>
              )}

              {isUnavailable && (
                <div className="text-[9px] text-amber-400/60 mt-1 italic leading-tight">
                  {agg.scanners.map(s => s.skippedReason).filter(Boolean).join("; ")}
                </div>
              )}

              {isDisabled && (
                <div className="text-[9px] text-zinc-400/60 mt-1 italic leading-tight">
                  {agg.scanners.map(s => s.skippedReason).filter(Boolean).join("; ")}
                </div>
              )}

              {isFailed && (
                <div className="text-[9px] text-red-400/60 mt-1 italic leading-tight truncate">
                  {agg.tooltip}
                </div>
              )}
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

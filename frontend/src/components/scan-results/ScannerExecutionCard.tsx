import { useState, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Shield, CheckCircle2, AlertCircle, Clock, SkipForward, Ban, Loader2,
  Timer, Calendar, FileText, Bug, Package2, Layers, FolderTree,
  ChevronDown, ChevronRight, ExternalLink, Sparkles, BarChart3,
  GitMerge, Terminal, Eye, List, Lock, HelpCircle,
} from "lucide-react"
import { cn, formatDuration } from "../../lib/utils"
import type { ScannerExecution, Finding } from "../../types"

interface ScannerExecutionCardProps {
  execution: ScannerExecution
  findings?: Finding[]
  allFindingsCount?: number
  scanId?: string
}

const STATUS_STYLES: Record<string, { label: string; icon: typeof Shield; color: string; bg: string }> = {
  COMPLETED_WITH_FINDINGS: {
    label: "Completed", icon: CheckCircle2,
    color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20",
  },
  COMPLETED_NO_FINDINGS: {
    label: "Completed", icon: CheckCircle2,
    color: "text-emerald-500", bg: "bg-emerald-500/10 border-emerald-500/15",
  },
  COMPLETED: {
    label: "Completed", icon: CheckCircle2,
    color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20",
  },
  SKIPPED_NOT_APPLICABLE: {
    label: "Skipped", icon: SkipForward,
    color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20",
  },
  UNAVAILABLE: {
    label: "Unavailable", icon: HelpCircle,
    color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20",
  },
  DISABLED: {
    label: "Disabled", icon: Ban,
    color: "text-zinc-400", bg: "bg-zinc-500/10 border-zinc-500/20",
  },
  FAILED: {
    label: "Failed", icon: AlertCircle,
    color: "text-red-400", bg: "bg-red-500/10 border-red-500/20",
  },
  RUNNING: {
    label: "Running", icon: Loader2,
    color: "text-indigo-400", bg: "bg-indigo-500/10 border-indigo-500/20",
  },
  DISCOVERED: {
    label: "Discovered", icon: Clock,
    color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20",
  },
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—"
  try {
    const d = new Date(iso)
    return d.toLocaleString("en-US", {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    })
  } catch {
    return "—"
  }
}

function StatRow({ icon: Icon, label, value, color }: {
  icon: typeof Shield; label: string; value: string | number | null | undefined; color?: string
}) {
  if (value == null || value === "" || value === "—") return null
  return (
    <div className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-white/[0.015]">
      <Icon className={cn("w-3.5 h-3.5 shrink-0", color ?? "text-white/30")} />
      <span className="text-[11px] text-white/40 min-w-[100px]">{label}</span>
      <span className={cn("text-[11px] font-medium text-white/70 font-mono ml-auto", color)}>{value}</span>
    </div>
  )
}

interface PerScannerMetrics {
  vulnCount: number
  packageCount: number
  secretCount: number
  misconfigCount: number
  cveCount: number
  criticalCount: number
  highCount: number
  mediumCount: number
  lowCount: number
  resourceTypes: string[]
  uniquePackages: string[]
  uniqueFiles: string[]
}

function computeMetrics(execution: ScannerExecution, findings?: Finding[]): PerScannerMetrics {
  const empty: PerScannerMetrics = {
    vulnCount: 0, packageCount: 0, secretCount: 0, misconfigCount: 0, cveCount: 0,
    criticalCount: 0, highCount: 0, mediumCount: 0, lowCount: 0,
    resourceTypes: [], uniquePackages: [], uniqueFiles: [],
  }
  if (!findings || findings.length === 0) return empty

  const scannerName = execution.scanner_name?.toLowerCase() || ""
  const relevant = findings.filter(f => {
    const sn = (f.scanner_name || "").toLowerCase()
    return sn.includes(scannerName) || sn.includes(execution.scanner_id?.toLowerCase() || "")
  })

  if (relevant.length === 0) return empty

  const severityCounts = { critical: 0, high: 0, medium: 0, low: 0 }
  const packages = new Set<string>()
  const resourceTypes = new Set<string>()
  const files = new Set<string>()

  for (const f of relevant) {
    const sev = (f.severity || "").toLowerCase()
    if (sev === "critical") severityCounts.critical++
    else if (sev === "high") severityCounts.high++
    else if (sev === "medium") severityCounts.medium++
    else if (sev === "low") severityCounts.low++

    if (f.package) packages.add(f.package)
    if (f.file_path) files.add(f.file_path)

    const rid = (f.rule_id || "").toLowerCase()
    if (rid.includes("deployment") || rid.includes("daemonset") || rid.includes("statefulset") ||
        rid.includes("service") || rid.includes("ingress") || rid.includes("configmap") ||
        rid.includes("secret") || rid.includes("namespace") || rid.includes("pod")) {
      const types = ["Deployment", "DaemonSet", "StatefulSet", "Service", "Ingress", "ConfigMap", "Secret", "Namespace", "Pod"]
      for (const t of types) {
        if (rid.includes(t.toLowerCase())) resourceTypes.add(t)
      }
    }
  }

  return {
    vulnCount: relevant.filter(f => (f.cve || "").startsWith("CVE-")).length,
    packageCount: packages.size,
    secretCount: relevant.filter(f => (f.rule_id || "").toLowerCase().includes("secret")).length,
    misconfigCount: relevant.filter(f => (f.category || "").toLowerCase().includes("misconfig")).length,
    cveCount: new Set(relevant.filter(f => f.cve).map(f => f.cve)).size,
    criticalCount: severityCounts.critical,
    highCount: severityCounts.high,
    mediumCount: severityCounts.medium,
    lowCount: severityCounts.low,
    resourceTypes: Array.from(resourceTypes),
    uniquePackages: Array.from(packages),
    uniqueFiles: Array.from(files),
  }
}

export function ScannerExecutionCard({ execution, findings, allFindingsCount, scanId }: ScannerExecutionCardProps) {
  const [expanded, setExpanded] = useState(false)
  const cfg = STATUS_STYLES[execution.status] || STATUS_STYLES.DISCOVERED
  const Icon = cfg.icon
  const isCompleted = execution.status === "COMPLETED" || execution.status === "COMPLETED_WITH_FINDINGS" || execution.status === "COMPLETED_NO_FINDINGS"
  const hasFindings = (execution.findings_count ?? 0) > 0
  const isSkipped = execution.status === "SKIPPED_NOT_APPLICABLE"
  const isUnavailable = execution.status === "UNAVAILABLE"
  const isDisabled = execution.status === "DISABLED"
  const isFailed = execution.status === "FAILED"
  const isRunning = execution.status === "RUNNING"

  const metrics = useMemo(() => computeMetrics(execution, findings), [execution, findings])

  const scannerIdLower = (execution.scanner_id || "").toLowerCase()
  const isTrivy = scannerIdLower.includes("trivy")
  const isSca = ["npm_audit", "pip_audit", "govulncheck", "dependency_check"].includes(scannerIdLower)
  const isK8s = scannerIdLower.includes("kube_score") || scannerIdLower.includes("checkov")
  const isTerraform = scannerIdLower.includes("tfsec") || scannerIdLower.includes("checkov")
  const isGitleaks = scannerIdLower.includes("gitleaks")

  return (
    <motion.div
      layout
      className={cn(
        "rounded-xl border transition-all duration-200 overflow-hidden",
        isCompleted && hasFindings ? "border-indigo-500/20 bg-indigo-500/[0.02] hover:border-indigo-500/30" :
        isCompleted && !hasFindings ? "border-emerald-500/10 bg-emerald-500/[0.02]" :
        isFailed ? "border-red-500/10 bg-red-500/[0.02]" :
        isSkipped ? "border-amber-500/10 bg-amber-500/[0.02]" :
        isUnavailable ? "border-amber-500/10 bg-amber-500/[0.02]" :
        isDisabled ? "border-zinc-500/10 bg-zinc-500/[0.02]" :
        "border-white/5 bg-white/[0.02]"
      )}
    >
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-3.5 text-left hover:bg-white/[0.01] transition-colors"
      >
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0", cfg.bg)}>
          <Icon className={cn("w-4 h-4", isRunning && "animate-spin", cfg.color)} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white/80">{execution.scanner_name}</span>
            {execution.version && (
              <span className="text-[9px] text-white/30 font-mono bg-white/5 px-1.5 py-0.5 rounded">
                v{execution.version}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={cn(
              "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium",
              cfg.color, "bg-white/[0.03]"
            )}>
              {cfg.label}
            </span>
            {execution.duration_ms != null && (
              <span className="text-[9px] text-white/30 flex items-center gap-1">
                <Timer className="w-2.5 h-2.5" />
                {formatDuration(execution.duration_ms / 1000)}
              </span>
            )}
            {hasFindings && (
              <span className="text-[9px] text-orange-400/70 font-mono">
                {execution.findings_count} finding{(execution.findings_count ?? 0) !== 1 ? "s" : ""}
              </span>
            )}
              {!hasFindings && isCompleted && (
              <span className="text-[9px] text-emerald-400/60">Completed (0 findings)</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {hasFindings && isCompleted && (
            <div className="flex -space-x-1">
              {metrics.criticalCount > 0 && (
                <span className="w-5 h-5 rounded-full bg-red-500/20 border border-red-500/30 text-[8px] font-bold text-red-400 flex items-center justify-center" title={`${metrics.criticalCount} critical`}>
                  {metrics.criticalCount}
                </span>
              )}
              {metrics.highCount > 0 && (
                <span className="w-5 h-5 rounded-full bg-orange-500/20 border border-orange-500/30 text-[8px] font-bold text-orange-400 flex items-center justify-center" title={`${metrics.highCount} high`}>
                  {metrics.highCount}
                </span>
              )}
            </div>
          )}
          {expanded ? <ChevronDown className="w-4 h-4 text-white/20" /> : <ChevronRight className="w-4 h-4 text-white/20" />}
        </div>
      </button>

      {/* Expanded details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-white/5"
          >
            <div className="p-4 space-y-4">
              {/* Status-specific messages */}
              {isSkipped && execution.skipped_reason && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10">
                  <SkipForward className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[11px] font-medium text-amber-300">Scanner skipped</p>
                    <p className="text-[10px] text-amber-400/70 mt-0.5">{execution.skipped_reason}</p>
                  </div>
                </div>
              )}

              {isUnavailable && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10">
                  <HelpCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[11px] font-medium text-amber-300">CLI tool not installed</p>
                    <p className="text-[10px] text-amber-400/70 mt-0.5">
                      {execution.skipped_reason || "CLI tool not available on system PATH."}
                    </p>
                  </div>
                </div>
              )}

              {isDisabled && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-zinc-500/5 border border-zinc-500/10">
                  <Ban className="w-4 h-4 text-zinc-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[11px] font-medium text-zinc-300">Scanner disabled</p>
                    <p className="text-[10px] text-zinc-400/70 mt-0.5">
                      {execution.skipped_reason || "Scanner disabled in configuration."}
                    </p>
                  </div>
                </div>
              )}

              {isFailed && execution.error_message && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/5 border border-red-500/10">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[11px] font-medium text-red-300">Scanner failed</p>
                    <p className="text-[10px] text-red-400/70 mt-0.5">{execution.error_message}</p>
                  </div>
                </div>
              )}

              {isCompleted && !hasFindings && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <p className="text-[11px] text-emerald-300">Completed (0 findings)</p>
                </div>
              )}

              {/* Generic metadata grid */}
              <div>
                <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-2">Execution Details</h4>
                <div className="grid grid-cols-2 gap-1.5">
                  <StatRow icon={Calendar} label="Started" value={formatDateTime(execution.execution_start)} />
                  <StatRow icon={Calendar} label="Ended" value={formatDateTime(execution.execution_end)} />
                  <StatRow icon={Timer} label="Duration" value={execution.duration_ms ? formatDuration(execution.duration_ms / 1000) : "—"} />
                  <StatRow icon={FolderTree} label="Files Scanned" value={execution.files_scanned} />
                  <StatRow icon={Layers} label="Rules Executed" value={execution.rules_executed} />
                  <StatRow icon={BarChart3} label="Raw Findings" value={execution.findings_count} />
                  <StatRow icon={GitMerge} label="Normalized Findings" value={allFindingsCount ?? execution.findings_count} />
                  <StatRow icon={Bug} label="Duplicates Removed" value={
                    (execution.findings_count ?? 0) - (allFindingsCount ?? execution.findings_count ?? 0) > 0
                      ? String((execution.findings_count ?? 0) - (allFindingsCount ?? execution.findings_count ?? 0))
                      : "0"
                  } />
                </div>
              </div>

              {/* Scanner-specific details */}
              {isTrivy && hasFindings && (
                <div>
                  <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-2">Trivy Scan Results</h4>
                  <div className="grid grid-cols-2 gap-1.5">
                    <StatRow icon={Bug} label="Vulnerabilities" value={metrics.vulnCount} color="text-red-400" />
                    <StatRow icon={Package2} label="Unique Packages" value={metrics.packageCount} />
                    <StatRow icon={Shield} label="Secrets" value={metrics.secretCount} color="text-amber-400" />
                    <StatRow icon={FileText} label="Misconfigurations" value={metrics.misconfigCount} color="text-orange-400" />
                    <StatRow icon={BarChart3} label="Critical" value={metrics.criticalCount} color="text-red-400" />
                    <StatRow icon={BarChart3} label="High" value={metrics.highCount} color="text-orange-400" />
                    <StatRow icon={BarChart3} label="Medium" value={metrics.mediumCount} color="text-yellow-400" />
                    <StatRow icon={BarChart3} label="Low" value={metrics.lowCount} color="text-blue-400" />
                  </div>
                </div>
              )}

              {isSca && hasFindings && (
                <div>
                  <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-2">SCA Scan Results</h4>
                  <div className="grid grid-cols-2 gap-1.5">
                    <StatRow icon={Package2} label="Vulnerable Packages" value={metrics.packageCount} />
                    <StatRow icon={Bug} label="Vulnerabilities" value={metrics.vulnCount} color="text-red-400" />
                    <StatRow icon={BarChart3} label="Critical" value={metrics.criticalCount} color="text-red-400" />
                    <StatRow icon={BarChart3} label="High" value={metrics.highCount} color="text-orange-400" />
                    <StatRow icon={BarChart3} label="Medium" value={metrics.mediumCount} color="text-yellow-400" />
                    <StatRow icon={BarChart3} label="Low" value={metrics.lowCount} color="text-blue-400" />
                  </div>
                  {metrics.uniquePackages.length > 0 && (
                    <div className="mt-2">
                      <p className="text-[9px] text-white/30 mb-1">Affected packages:</p>
                      <div className="flex flex-wrap gap-1">
                        {metrics.uniquePackages.map(pkg => (
                          <span key={pkg} className="px-1.5 py-0.5 rounded bg-white/5 text-[9px] text-white/50 font-mono">
                            {pkg}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {isK8s && hasFindings && (
                <div>
                  <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-2">Kubernetes Resources</h4>
                  <div className="grid grid-cols-2 gap-1.5">
                    <StatRow icon={Layers} label="Resources Scanned" value={execution.files_scanned ?? "—"} />
                    <StatRow icon={FileText} label="Misconfigurations" value={metrics.misconfigCount} color="text-orange-400" />
                    <StatRow icon={BarChart3} label="Critical" value={metrics.criticalCount} color="text-red-400" />
                    <StatRow icon={BarChart3} label="High" value={metrics.highCount} color="text-orange-400" />
                  </div>
                  {metrics.resourceTypes.length > 0 && (
                    <div className="mt-2">
                      <p className="text-[9px] text-white/30 mb-1">Resource types affected:</p>
                      <div className="flex flex-wrap gap-1">
                        {metrics.resourceTypes.map(rt => (
                          <span key={rt} className="px-1.5 py-0.5 rounded bg-white/5 text-[9px] text-white/50">
                            {rt}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {isTerraform && hasFindings && !isK8s && (
                <div>
                  <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-2">Terraform Scan</h4>
                  <div className="grid grid-cols-2 gap-1.5">
                    <StatRow icon={FolderTree} label="Files Scanned" value={execution.files_scanned ?? metrics.uniqueFiles.length} />
                    <StatRow icon={FileText} label="Misconfigurations" value={metrics.misconfigCount} color="text-orange-400" />
                    <StatRow icon={BarChart3} label="Critical" value={metrics.criticalCount} color="text-red-400" />
                    <StatRow icon={BarChart3} label="High" value={metrics.highCount} color="text-orange-400" />
                    <StatRow icon={BarChart3} label="Medium" value={metrics.mediumCount} color="text-yellow-400" />
                    <StatRow icon={BarChart3} label="Low" value={metrics.lowCount} color="text-blue-400" />
                  </div>
                </div>
              )}

              {isGitleaks && (
                <div>
                  <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider mb-2">Secrets Scan</h4>
                  <div className="grid grid-cols-2 gap-1.5">
                    <StatRow icon={FolderTree} label="Files Scanned" value={execution.files_scanned ?? metrics.uniqueFiles.length} />
                    <StatRow icon={Lock} label="Secrets Found" value={hasFindings ? execution.findings_count : 0} color={hasFindings ? "text-amber-400" : "text-emerald-400"} />
                    <StatRow icon={BarChart3} label="Critical" value={metrics.criticalCount} color="text-red-400" />
                    <StatRow icon={BarChart3} label="High" value={metrics.highCount} color="text-orange-400" />
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
                {isCompleted && (
                  <>
                    <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] font-medium text-white/60 hover:text-white/80 transition-colors">
                      <Eye className="w-3 h-3" />
                      View Findings
                    </button>
                    <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] font-medium text-white/60 hover:text-white/80 transition-colors">
                      <List className="w-3 h-3" />
                      Normalized View
                    </button>
                  </>
                )}
                {isFailed && (
                  <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-[10px] font-medium text-red-300 hover:text-red-200 transition-colors">
                    <Terminal className="w-3 h-3" />
                    View Logs
                  </button>
                )}
                <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] font-medium text-white/60 hover:text-white/80 transition-colors">
                  <ExternalLink className="w-3 h-3" />
                  Raw Output
                </button>
                {(isSkipped || isUnavailable || isDisabled) && (
                  <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 text-[10px] font-medium text-indigo-300 hover:text-indigo-200 transition-colors">
                    <Sparkles className="w-3 h-3" />
                    AI Analysis
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}



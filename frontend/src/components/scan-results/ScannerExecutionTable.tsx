import { Shield, CheckCircle2, AlertCircle, Clock, XCircle, HelpCircle, Loader2 } from "lucide-react"

import { cn, formatDuration, getScannerPurpose, isScannerOptional } from "../../lib/utils"
import type { ScannerExecution } from "../../types"

interface ScannerHealthProps {
  executions: ScannerExecution[]
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Shield }> = {
  COMPLETED: { label: "Completed", color: "text-emerald-400 bg-emerald-500/10", icon: CheckCircle2 },
  COMPLETED_WITH_FINDINGS: { label: "Completed", color: "text-emerald-400 bg-emerald-500/10", icon: CheckCircle2 },
  COMPLETED_NO_FINDINGS: { label: "Clear", color: "text-white/30 bg-white/5", icon: CheckCircle2 },
  FAILED: { label: "Failed", color: "text-red-400 bg-red-500/10", icon: AlertCircle },
  RUNNING: { label: "Running", color: "text-indigo-400 bg-indigo-500/10", icon: Loader2 },
  DISCOVERED: { label: "Running", color: "text-indigo-400 bg-indigo-500/10", icon: Loader2 },
  INITIALIZING: { label: "Running", color: "text-indigo-400 bg-indigo-500/10", icon: Loader2 },
  SKIPPED_NOT_APPLICABLE: { label: "Not Applicable", color: "text-amber-400 bg-amber-500/10", icon: XCircle },
  UNAVAILABLE: { label: "Unavailable", color: "text-zinc-400 bg-zinc-500/10", icon: HelpCircle },
}

function getHealthStatus(exec: ScannerExecution): { label: string; color: string; icon: typeof Shield } {
  // DISABLED and UNAVAILABLE map to "Optional" (supplementary) or "Unavailable" (core)
  if (exec.status === "DISABLED" || exec.status === "UNAVAILABLE") {
    if (isScannerOptional(exec.scanner_id)) {
      return { label: "Optional", color: "text-amber-400 bg-amber-500/10", icon: HelpCircle }
    }
    return { label: "Unavailable", color: "text-zinc-400 bg-zinc-500/10", icon: HelpCircle }
  }
  const cfg = STATUS_CONFIG[exec.status]
  if (cfg) {return cfg}
  return { label: exec.status, color: "text-white/30 bg-white/[0.03]", icon: Clock }
}

const NOT_APPLICABLE_REASONS: Record<string, string> = {
  govulncheck: "No Go modules detected",
  pip_audit: "No Python requirements detected",
  npm_audit: "No Node.js dependencies detected",
  dependency_check: "No supported dependencies detected",
  hadolint: "No Dockerfiles found",
  kube_score: "No Kubernetes manifests found",
  tfsec: "No Terraform configs found",
  gitleaks: "No Git repository data available",
  trivy: "No container images or filesystem to scan",
  trivy_filesystem: "No container images or filesystem to scan",
  trivy_config: "No misconfiguration targets found",
  checkov: "No applicable IaC files found",
}

function getDefaultNotApplicableReason(scannerId: string): string {
  return NOT_APPLICABLE_REASONS[scannerId] || "Not applicable"
}

function getReason(exec: ScannerExecution): string {
  if (exec.status === "SKIPPED_NOT_APPLICABLE") {return exec.skipped_reason || getDefaultNotApplicableReason(exec.scanner_id)}
  if (exec.status === "UNAVAILABLE") {return exec.skipped_reason || `CLI not installed`}
  if (exec.status === "DISABLED") {
    if (isScannerOptional(exec.scanner_id)) {return "Scanner can improve coverage but is not required"}
    return exec.skipped_reason || "Scanner not enabled on current worker"
  }
  if (exec.status === "FAILED") {return exec.error_message || ""}
  if (exec.status === "COMPLETED_NO_FINDINGS") {return "No security issues found"}
  return ""
}

function formatExecDuration(ms: number | null): string {
  if (ms === null || ms === undefined) {return "—"}
  return formatDuration(ms / 1000)
}

export function ScannerExecutionTable({ executions }: ScannerHealthProps) {
  if (!executions || executions.length === 0) {return null}

  const ordered = [...executions].sort((a, b) => {
    const order = ["COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS", "FAILED", "RUNNING", "SKIPPED_NOT_APPLICABLE", "UNAVAILABLE"]
    return (order.indexOf(a.status) - order.indexOf(b.status))
  })

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-4 h-4 text-white/40" />
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Scanner Health</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <Th className="text-left">Scanner</Th>
              <Th className="text-left">Purpose</Th>
              <Th className="text-center">Installed</Th>
              <Th className="text-center">Executed</Th>
              <Th className="text-left">Status</Th>
              <Th className="text-right">Time</Th>
              <Th className="text-left">Reason</Th>
            </tr>
          </thead>
          <tbody>
            {ordered.map(exec => {
              const health = getHealthStatus(exec)
              const Icon = health.icon
              const isCompleted = ["COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS"].includes(exec.status)
              const ran = isCompleted || exec.status === "FAILED"
              const installed = exec.status !== "UNAVAILABLE" && exec.status !== "DISABLED"
              const reason = getReason(exec)

              return (
                <tr
                  key={exec.scanner_id}
                  className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
                >
                  <Td className="font-medium text-white/80 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className={cn("w-5 h-5 rounded flex items-center justify-center", health.color)}>
                        <Icon className="w-3 h-3" />
                      </div>
                      <span>{exec.scanner_name}</span>
                    </div>
                  </Td>
                  <Td className="text-white/40 max-w-[160px]">
                    <span className="text-[10px]">{getScannerPurpose(exec.scanner_id)}</span>
                  </Td>
                  <Td className="text-center">
                    <span className={cn(
                      "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium",
                      installed ? "text-emerald-400 bg-emerald-500/10" : "text-zinc-400 bg-zinc-500/10"
                    )}>
                      {installed ? "Yes" : "No"}
                    </span>
                  </Td>
                  <Td className="text-center">
                    <span className={cn(
                      "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium",
                      ran ? "text-emerald-400 bg-emerald-500/10" : "text-zinc-400 bg-zinc-500/10"
                    )}>
                      {ran ? "Yes" : "No"}
                    </span>
                  </Td>
                  <Td>
                    <span className={cn(
                      "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium",
                      health.color,
                    )}>
                      <Icon className="w-2.5 h-2.5" />
                      {health.label}
                    </span>
                  </Td>
                  <Td className="text-right text-white/50 font-mono whitespace-nowrap text-[10px]">
                    {formatExecDuration(exec.duration_ms)}
                  </Td>
                  <Td className="max-w-[200px]">
                    {reason ? (
                      <span className="text-[9px] text-white/40" title={reason}>
                        {reason.length > 50 ? reason.slice(0, 50) + "…" : reason}
                      </span>
                    ) : (
                      <span className="text-[9px] text-emerald-400/40">Healthy</span>
                    )}
                  </Td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Th({ children, className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th className={cn("py-2 px-2 text-[9px] font-semibold text-white/30 uppercase tracking-wider", className)} {...props}>
      {children}
    </th>
  )
}

function Td({ children, className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("py-2.5 px-2 text-xs", className)} {...props}>
      {children}
    </td>
  )
}

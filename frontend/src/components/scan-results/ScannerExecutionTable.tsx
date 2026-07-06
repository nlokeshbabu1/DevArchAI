import { useMemo } from "react"
import { motion } from "framer-motion"
import {
  Shield, CheckCircle2, AlertCircle,
  Clock, SkipForward, Ban, Loader2,
  Timer, Info, HelpCircle,
} from "lucide-react"
import { cn } from "../../lib/utils"
import type { ScannerExecution } from "../../types"

interface ScannerExecutionTableProps {
  executions: ScannerExecution[]
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Shield }> = {
  DISCOVERED: { label: "Discovered", color: "text-blue-400 bg-blue-500/10", icon: Clock },
  INITIALIZING: { label: "Initializing", color: "text-blue-400 bg-blue-500/10", icon: Loader2 },
  RUNNING: { label: "Running", color: "text-indigo-400 bg-indigo-500/10", icon: Loader2 },
  COMPLETED: { label: "Completed", color: "text-emerald-400 bg-emerald-500/10", icon: CheckCircle2 },
  COMPLETED_WITH_FINDINGS: { label: "Completed", color: "text-emerald-400 bg-emerald-500/10", icon: CheckCircle2 },
  COMPLETED_NO_FINDINGS: { label: "Completed", color: "text-emerald-400 bg-emerald-500/10", icon: CheckCircle2 },
  SKIPPED_NOT_APPLICABLE: { label: "Skipped", color: "text-amber-400 bg-amber-500/10", icon: SkipForward },
  UNAVAILABLE: { label: "Unavailable", color: "text-amber-400 bg-amber-500/10", icon: HelpCircle },
  DISABLED: { label: "Disabled", color: "text-zinc-400 bg-zinc-500/10", icon: Ban },
  FAILED: { label: "Failed", color: "text-red-400 bg-red-500/10", icon: AlertCircle },
}

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "—"
  if (ms < 1000) return `${ms}ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)}s`
  return `${Math.floor(s / 60)}m ${Math.floor(s % 60)}s`
}

export function ScannerExecutionTable({ executions }: ScannerExecutionTableProps) {
  const totalDuration = useMemo(() => {
    return executions.reduce((sum, e) => sum + (e.duration_ms || 0), 0)
  }, [executions])

  const totalFindings = useMemo(() => {
    return executions.reduce((sum, e) => sum + (e.findings_count || 0), 0)
  }, [executions])

  if (!executions || executions.length === 0) {
    return null
  }

  const completedCount = executions.filter(e =>
    e.status === "COMPLETED" || e.status === "COMPLETED_WITH_FINDINGS" || e.status === "COMPLETED_NO_FINDINGS"
  ).length

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
            Scanner Execution
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-white/30">
          <span>{completedCount}/{executions.length} completed</span>
          <span className="text-white/10">|</span>
          <span>{totalFindings} raw findings</span>
          <span className="text-white/10">|</span>
          <span>{formatDuration(totalDuration)} total</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <Th className="text-left">Scanner</Th>
              <Th className="text-left">Version</Th>
              <Th className="text-left">Status</Th>
              <Th className="text-center">Raw Findings</Th>
              <Th className="text-center">Files</Th>
              <Th className="text-center">Rules</Th>
              <Th className="text-right">Duration</Th>
              <Th className="text-left">Details</Th>
            </tr>
          </thead>
          <tbody>
            {executions.map((exec) => {
              const cfg = STATUS_CONFIG[exec.status] || STATUS_CONFIG.DISCOVERED
              const Icon = cfg.icon
              const hasError = exec.status === "FAILED" && exec.error_message
              const isSkipped = exec.status === "SKIPPED_NOT_APPLICABLE" && exec.skipped_reason
              const hasNoFindings = exec.status === "COMPLETED_NO_FINDINGS"
              const isUnavailable = exec.status === "UNAVAILABLE"
              const isDisabled = exec.status === "DISABLED"

              return (
                <motion.tr
                  key={exec.scanner_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
                >
                  <Td className="font-medium text-white/80 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className={cn("w-5 h-5 rounded flex items-center justify-center", cfg.color)}>
                        <Icon className="w-3 h-3" />
                      </div>
                      {exec.scanner_name}
                    </div>
                  </Td>
                  <Td className="text-white/40 font-mono">{exec.version || "—"}</Td>
                  <Td>
                    <span className={cn(
                      "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium",
                      cfg.color,
                    )}>
                      <Icon className="w-2.5 h-2.5" />
                      {cfg.label}
                    </span>
                  </Td>
                  <Td className="text-center">
                    {hasNoFindings ? (
                      <span className="text-emerald-400/60 text-[9px] cursor-help" title="Scanner completed but found no issues">
                        0
                      </span>
                    ) : (
                      <span className={cn(
                        "font-mono font-bold",
                        exec.findings_count > 0 ? "text-orange-400" : "text-white/30",
                      )}>
                        {exec.findings_count}
                      </span>
                    )}
                    {exec.findings_count > 0 && (
                      <div className="text-[8px] text-white/20 mt-0.5">raw</div>
                    )}
                  </Td>
                  <Td className="text-center text-white/50 font-mono">{exec.files_scanned ?? "—"}</Td>
                  <Td className="text-center text-white/50 font-mono">{exec.rules_executed ?? "—"}</Td>
                  <Td className="text-right text-white/50 font-mono whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1">
                      <Timer className="w-2.5 h-2.5 text-white/20" />
                      {formatDuration(exec.duration_ms)}
                    </div>
                  </Td>
                  <Td className="text-white/40 max-w-[200px]">
                    {hasError && (
                      <span className="text-red-400/80 text-[9px]" title={exec.error_message!}>
                        {exec.error_message!.length > 40
                          ? exec.error_message!.slice(0, 40) + "…"
                          : exec.error_message}
                      </span>
                    )}
                    {isSkipped && (
                      <span className="text-amber-400/60 text-[9px]" title={exec.skipped_reason!}>
                        {exec.skipped_reason!.length > 55
                          ? exec.skipped_reason!.slice(0, 55) + "…"
                          : exec.skipped_reason}
                      </span>
                    )}
                    {isUnavailable && (
                      <span className="text-amber-400/60 text-[9px]" title={exec.skipped_reason ?? ""}>
                        {exec.skipped_reason && exec.skipped_reason.length > 55
                          ? exec.skipped_reason.slice(0, 55) + "…"
                          : exec.skipped_reason || "CLI tool not installed"}
                      </span>
                    )}
                    {!hasError && !isSkipped && !isUnavailable && isDisabled && (
                      <span className="text-zinc-400/60 text-[9px]" title={exec.skipped_reason ?? ""}>
                        {exec.skipped_reason || "Scanner disabled in configuration"}
                      </span>
                    )}
                    {!hasError && !isSkipped && !isUnavailable && !isDisabled && hasNoFindings && (
                      <span className="text-emerald-400/40 text-[9px]">Completed (0 findings)</span>
                    )}
                    {!hasError && !isSkipped && !isUnavailable && !isDisabled && !hasNoFindings && (
                      <span className="text-white/20 text-[9px]">—</span>
                    )}
                  </Td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </motion.div>
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

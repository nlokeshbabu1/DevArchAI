import { motion, AnimatePresence } from "framer-motion"
import { Shield, AlertTriangle, FileCode, Clock, Zap, GitPullRequest, TrendingUp } from "lucide-react"
import { Finding } from "../../types"
import { cn, getSeverityColor } from "../../lib/utils"
import { Button } from "../ui-animated"

interface FixTheseFirstProps {
  findings: Finding[]
  currentScore: number
  onSelect?: (id: string) => void
  onGenerateFix?: (id: string) => void
  onCreatePR?: (id: string) => void
  selectedId?: string | null
}

function estimateScoreAfterFix(finding: Finding, currentScore: number): { score: number; boost: number } {
  const boost = finding.severity === "critical" ? 15 : finding.severity === "high" ? 10 : finding.severity === "medium" ? 5 : 2
  return { score: Math.min(100, currentScore + boost), boost }
}

function estimateFixTime(finding: Finding): string {
  if (finding.severity === "critical") return "5 min"
  if (finding.severity === "high") return "10 min"
  if (finding.severity === "medium") return "15 min"
  if (finding.severity === "low") return "30 min"
  return "—"
}

export function FixTheseFirst({ findings, currentScore, onSelect, onGenerateFix, onCreatePR, selectedId }: FixTheseFirstProps) {
  const displayFindings = findings.slice(0, 5)

  if (displayFindings.length === 0) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6">
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">
          Fix These First
        </h3>
        <div className="flex items-center justify-center h-24 text-white/30 text-sm">
          <Shield className="w-5 h-5 mr-2" />
          No critical or high issues found
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Fix These First
        </h3>
        <span className="text-xs text-white/30">{displayFindings.length} highest risk</span>
      </div>

      <div className="space-y-2">
        <AnimatePresence mode="popLayout">
          {displayFindings.map((finding, i) => {
            const findingId = finding.id ?? finding.rule_id
            const severityColor = getSeverityColor(finding.severity)
            const isSelected = selectedId === findingId
            const impact = estimateScoreAfterFix(finding, currentScore)
            return (
              <motion.div
                key={findingId}
                layout
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: i * 0.05 }}
                className={cn(
                  "rounded-xl border transition-all duration-200",
                  isSelected
                    ? "border-indigo-500/40 bg-indigo-500/10"
                    : "border-white/5 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.05]"
                )}
              >
                <button
                  onClick={() => onSelect?.(findingId)}
                  className="w-full text-left p-4"
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold",
                      severityColor.bg,
                      severityColor.text
                    )}>
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn(
                          "px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider",
                          severityColor.bg,
                          severityColor.text
                        )}>
                          {finding.severity}
                        </span>
                        <span className="text-xs text-white/40 font-mono truncate">
                          {finding.rule_id}
                        </span>
                        <span className="text-[10px] text-white/20 capitalize">{finding.category}</span>
                      </div>
                      <p className="text-sm text-white/80 line-clamp-1">
                        {finding.summary || finding.message || finding.rule_name}
                      </p>
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="flex items-center gap-1 text-[11px] text-white/30">
                          <FileCode className="w-3 h-3" />
                          {finding.file_path?.split("/").pop() ?? "unknown"}
                          {finding.line_number && `:${finding.line_number}`}
                        </span>
                        <span className="flex items-center gap-1 text-[11px] text-white/30">
                          <Clock className="w-3 h-3" />
                          Fix: {estimateFixTime(finding)}
                        </span>
                        <span className="flex items-center gap-1 text-[11px] text-emerald-400/60">
                          <TrendingUp className="w-3 h-3" />
                          +{impact.boost} pts
                        </span>
                      </div>
                    </div>
                  </div>
                </button>

                {/* Action buttons */}
                <div className="px-4 pb-3 flex items-center gap-1.5 border-t border-white/5 pt-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onSelect?.(findingId)}
                    className="text-[11px] h-7 px-2"
                  >
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    Details
                  </Button>
                  {onGenerateFix && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onGenerateFix(findingId)}
                      className="text-[11px] h-7 px-2"
                    >
                      <Zap className="w-3 h-3 mr-1" />
                      Fix
                    </Button>
                  )}
                  {onCreatePR && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onCreatePR(findingId)}
                      className="text-[11px] h-7 px-2"
                    >
                      <GitPullRequest className="w-3 h-3 mr-1" />
                      PR
                    </Button>
                  )}
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

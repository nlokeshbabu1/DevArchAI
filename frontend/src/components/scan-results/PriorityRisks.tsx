import { useState } from "react"
import { motion } from "framer-motion"
import { Shield, FileCode, Sparkles } from "lucide-react"
import { Finding } from "../../types"
import { cn, getSeverityColor, getFileName, sanitizePath } from "../../lib/utils"

interface FixTheseFirstProps {
  findings: Finding[]
  currentScore: number
  onSelect?: (id: string) => void
  selectedId?: string | null
}

export function FixTheseFirst({ findings, onSelect, selectedId }: FixTheseFirstProps) {
  const displayFindings = findings.slice(0, 5)

  if (displayFindings.length === 0) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5">
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
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Fix These First
        </h3>
        <span className="text-xs text-white/30">{displayFindings.length} highest risk</span>
      </div>

      <div className="space-y-1.5">
        {displayFindings.map((finding, i) => {
          const findingId = finding.id ?? finding.rule_id
          const severityColor = getSeverityColor(finding.severity)
          const isSelected = selectedId === findingId
          return (
            <motion.div
              key={findingId}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={cn(
                "rounded-lg border transition-all duration-200 cursor-pointer",
                isSelected
                  ? "border-indigo-500/40 bg-indigo-500/10"
                  : "border-white/5 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.05]"
              )}
              onClick={() => onSelect?.(findingId)}
            >
              <div className="p-3 space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <span className={cn(
                    "px-1 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider",
                    severityColor.bg, severityColor.text
                  )}>
                    {finding.severity}
                  </span>
                  <span className="text-[10px] text-white/30 font-mono truncate">{finding.rule_id}</span>
                  <span className="text-[10px] text-white/30 capitalize">{finding.category}</span>
                </div>
                <p className="text-sm text-white/80 leading-snug">
                  {finding.summary || finding.message || finding.rule_name}
                </p>
                <div className="flex items-center gap-2 text-[10px] text-white/30">
                  <span className="flex items-center gap-1 font-mono" title={sanitizePath(finding.file_path) || ''}>
                    <FileCode className="w-3 h-3" />
                    {getFileName(finding.file_path)}
                  </span>
                  {finding.fix_code && (
                    <span className="flex items-center gap-1 text-emerald-400/60">
                      <Sparkles className="w-3 h-3" />
                      Auto-Fix
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

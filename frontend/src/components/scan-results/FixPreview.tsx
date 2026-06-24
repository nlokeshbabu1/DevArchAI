import { motion } from "framer-motion"
import { X, FileCode, Zap, GitPullRequest } from "lucide-react"
import { Finding } from "../../types"
import { cn, getSeverityColor } from "../../lib/utils"
import { Button } from "../ui-animated"
import { DiffViewer } from "../DiffViewer"

interface FixPreviewProps {
  finding: Finding
  currentScore: number
  isOpen: boolean
  onClose: () => void
  onCreatePR: () => void
}

export function FixPreview({ finding, currentScore, isOpen, onClose, onCreatePR }: FixPreviewProps) {
  if (!isOpen) return null

  const severityColor = getSeverityColor(finding.severity)

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-white/10 bg-slate-900 shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            <Zap className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white/90">Fix Preview</h3>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white/60 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Finding Info */}
          <div className="flex items-center gap-3">
            <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider", severityColor.bg, severityColor.text)}>
              {finding.severity}
            </span>
            <span className="text-xs text-white/40 font-mono">{finding.rule_id}</span>
            <span className="text-xs text-white/20">·</span>
            <span className="text-xs text-white/40 truncate">{finding.file_path?.split("/").pop()}{finding.line_number ? `:${finding.line_number}` : ""}</span>
          </div>

          {/* Current Code */}
          {finding.before_code && (
            <div>
              <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">Current Code</h4>
              <pre className="p-4 bg-black/40 border border-white/5 rounded-xl overflow-x-auto max-h-[200px] text-sm">
                <code className="text-red-300/80 font-mono whitespace-pre">{finding.before_code}</code>
              </pre>
            </div>
          )}

          {/* Recommended Change */}
          {finding.fix_code && (
            <div>
              <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">Recommended Change</h4>
              <pre className="p-4 bg-black/40 border border-emerald-500/20 rounded-xl overflow-x-auto max-h-[200px] text-sm">
                <code className="text-emerald-300 font-mono whitespace-pre">{finding.fix_code}</code>
              </pre>
            </div>
          )}

          {/* Diff View */}
          {(finding.before_code || finding.after_code || finding.unified_diff) && (
            <div>
              <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">Diff View</h4>
              <div className="rounded-xl border border-white/5 overflow-hidden">
                <DiffViewer
                  beforeCode={finding.before_code}
                  afterCode={finding.after_code}
                  unifiedDiff={finding.unified_diff}
                  filename={finding.file_path || "file"}
                />
              </div>
            </div>
          )}

          {/* Lines changed summary */}
          {finding.before_code && finding.fix_code && (
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-center">
                <div className="text-[10px] text-red-400/60 uppercase">Lines Removed</div>
                <div className="text-xl font-bold text-red-400">
                  {finding.before_code.split("\n").length}
                </div>
              </div>
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 text-center">
                <div className="text-[10px] text-emerald-400/60 uppercase">Lines Added</div>
                <div className="text-xl font-bold text-emerald-400">
                  {finding.fix_code.split("\n").length}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/5">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={onCreatePR} glow>
            <GitPullRequest className="w-4 h-4 mr-1.5" />
            Create Pull Request
          </Button>
        </div>
      </motion.div>
    </motion.div>
  )
}
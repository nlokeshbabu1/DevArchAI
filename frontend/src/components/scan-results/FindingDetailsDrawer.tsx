import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  X, AlertTriangle, Sparkles, Shield,
  Copy, Check, Download, GitPullRequest, Eye,
  TrendingUp, ArrowRight
} from "lucide-react"
import { Finding } from "../../types"
import { cn, getSeverityColor } from "../../lib/utils"
import { Button } from "../ui-animated"
import { DiffViewer } from "../DiffViewer"
import { FixPreview } from "./FixPreview"

interface FindingDetailsDrawerProps {
  finding: Finding | null
  isOpen: boolean
  onClose: () => void
  currentScore: number
  onCopyFix: (code: string) => void
  onDownloadPatch: (finding: Finding) => void
  onCreatePR: (finding: Finding) => void
}

interface PRConfirmation {
  show: boolean
  affectedFiles: number
}

export function FindingDetailsDrawer({
  finding, isOpen, onClose, currentScore,
  onCopyFix, onDownloadPatch, onCreatePR
}: FindingDetailsDrawerProps) {
  const [copied, setCopied] = useState(false)
  const [prConfirm, setPrConfirm] = useState<PRConfirmation | null>(null)
  const [showFixPreview, setShowFixPreview] = useState(false)

  if (!finding) return null

  const severityColor = getSeverityColor(finding.severity)

  const handleCopy = async () => {
    if (!finding.fix_code) return
    await navigator.clipboard.writeText(finding.fix_code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    onCopyFix(finding.fix_code)
  }

  const handleCreatePR = () => {
    setShowFixPreview(false)
    setPrConfirm({
      show: true,
      affectedFiles: 1,
    })
  }

  const confirmPR = () => {
    setPrConfirm(null)
    onCreatePR(finding)
  }

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-xl bg-[#0a0a10] border-l border-white/10 overflow-hidden flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider", severityColor.bg, severityColor.text)}>
                    {finding.severity}
                  </span>
                  <span className="text-xs text-white/40 font-mono truncate">{finding.rule_id}</span>
                </div>
                <button onClick={onClose} className="text-white/30 hover:text-white/60 transition-colors flex-shrink-0">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Scrollable content */}
              <div className="flex-1 overflow-y-auto">
                <div className="p-6 space-y-5">
                  {/* Issue title */}
                  <div>
                    <h2 className="text-base font-semibold text-white/90">
                      {finding.summary || finding.message || finding.rule_name}
                    </h2>
                    <p className="text-xs text-white/40 mt-1 font-mono">
                      {finding.file_path?.split("/").pop()}{finding.line_number ? `:${finding.line_number}` : ""}
                      <span className="text-white/20 mx-2">·</span>
                      {finding.category}
                    </p>
                  </div>

                  {/* Why This Matters */}
                  {finding.summary && (
                    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                      <div className="flex items-start gap-3">
                        <Sparkles className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-1">Why This Matters</h4>
                          <p className="text-sm text-white/70 leading-relaxed">{finding.summary}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Security Impact */}
                  {(finding.risk || finding.impact) && (
                    <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 p-4">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <h4 className="text-xs font-semibold text-orange-300 uppercase tracking-wider mb-1">Security Impact</h4>
                          {finding.risk && <p className="text-sm text-orange-200/70 leading-relaxed">{finding.risk}</p>}
                          {finding.impact && <p className="text-sm text-orange-200/50 leading-relaxed mt-1">{finding.impact}</p>}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Current Code */}
                  {finding.before_code && (
                    <div>
                      <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">Current Code</h4>
                      <pre className="p-4 bg-black/40 border border-white/5 rounded-xl overflow-x-auto max-h-[300px] text-sm">
                        <code className="text-red-300/80 font-mono whitespace-pre">{finding.before_code}</code>
                      </pre>
                    </div>
                  )}

                  {/* Recommended Change */}
                  {finding.fix_code && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Recommended Change</h4>
                        {finding.confidence != null && (
                          <span className={cn(
                            "text-[10px] font-medium px-1.5 py-0.5 rounded",
                            finding.confidence >= 0.8 ? "bg-emerald-500/10 text-emerald-400" : "bg-yellow-500/10 text-yellow-400"
                          )}>
                            {(finding.confidence * 100).toFixed(0)}% confident
                          </span>
                        )}
                      </div>
                      <pre className="p-4 bg-black/40 border border-emerald-500/20 rounded-xl overflow-x-auto max-h-[300px] text-sm">
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

                  {/* Best Practices */}
                  {finding.best_practices && finding.best_practices.length > 0 && (
                    <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Shield className="w-4 h-4 text-indigo-400" />
                        <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">Best Practices</h4>
                      </div>
                      <ul className="space-y-1.5">
                        {finding.best_practices.map((practice, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm text-indigo-200/60">
                            <span className="text-indigo-400 mt-0.5">•</span>
                            {practice}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Description fallback */}
                  {finding.description && !finding.summary && (
                    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                      <p className="text-sm text-white/60 leading-relaxed">{finding.description}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Action bar */}
              <div className="flex-shrink-0 border-t border-white/5 bg-white/[0.02] px-6 py-4">
                <div className="flex items-center gap-2">
                  {finding.fix_code && (
                    <Button variant="secondary" size="sm" onClick={handleCopy}>
                      {copied ? <><Check className="w-4 h-4 mr-1.5" /> Copied</> : <><Copy className="w-4 h-4 mr-1.5" /> Copy Fix</>}
                    </Button>
                  )}
                  {finding.fix_code && (
                    <Button variant="ghost" size="sm" onClick={() => onDownloadPatch(finding)}>
                      <Download className="w-4 h-4 mr-1.5" />
                      Patch
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={handleCreatePR}>
                    <GitPullRequest className="w-4 h-4 mr-1.5" />
                    PR
                  </Button>
                  {finding.fix_code && (
                    <Button variant="ghost" size="sm" onClick={() => setShowFixPreview(true)}>
                      <Eye className="w-4 h-4 mr-1.5" />
                      Preview
                    </Button>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Fix Preview Modal */}
      <FixPreview
        finding={finding}
        currentScore={currentScore}
        isOpen={showFixPreview}
        onClose={() => setShowFixPreview(false)}
        onCreatePR={handleCreatePR}
      />

      {/* PR Confirmation Modal */}
      <AnimatePresence>
        {prConfirm?.show && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl"
            >
              <div className="flex items-center gap-2 mb-4">
                <GitPullRequest className="w-5 h-5 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white/90">Create Pull Request</h3>
              </div>

              <p className="text-xs text-white/40 mb-5">
                This will create a patch-based PR fixing only the lines related to this finding.
                No unrelated code will be modified.
              </p>

              <div className="space-y-3 mb-5">
                <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-4 py-3">
                  <span className="text-sm text-white/60">Affected Files</span>
                  <span className="text-sm font-bold text-white/80">{prConfirm.affectedFiles}</span>
                </div>
              </div>

              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => setPrConfirm(null)} className="flex-1">
                  Cancel
                </Button>
                <Button variant="primary" size="sm" onClick={confirmPR} glow className="flex-1">
                  <GitPullRequest className="w-4 h-4 mr-1.5" />
                  Create Patch PR
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  X, AlertTriangle, Sparkles, Shield,
  Copy, Check, Download, GitPullRequest,
  TrendingUp, Clock, Target,
  FileCode, BookOpen, ExternalLink, MessageSquare,
  HelpCircle, GitBranch, BadgeCheck, ScanSearch,
  Zap, Search, GitMerge
} from "lucide-react"
import { Finding } from "../../types"
import { cn, getSeverityColor, sanitizePath } from "../../lib/utils"
import { Button } from "../ui-animated"
import { DiffViewer } from "../DiffViewer"

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
  scoreImprovement: number
}

const estimateFixTime = (finding: Finding): string => {
  if (finding.estimated_fix_time) return finding.estimated_fix_time
  if (finding.fix_code) return "~5 min"
  const map: Record<string, string> = {
    critical: "~45 min",
    high: "~25 min",
    medium: "~10 min",
    low: "~5 min",
    info: "~5 min",
  }
  return map[finding.severity] || "~15 min"
}

const computeRiskReduction = (finding: Finding): number => {
  if (finding.risk_reduction_score != null) return finding.risk_reduction_score
  const map: Record<string, number> = { critical: 90, high: 65, medium: 35, low: 10, info: 5 }
  return map[finding.severity] || 0
}

const computePredictedScore = (currentScore: number, finding: Finding): number => {
  if (finding.predicted_score_after_fix != null) return finding.predicted_score_after_fix
  const reduction = computeRiskReduction(finding)
  const improvement = Math.round((reduction / 100) * (100 - currentScore) * 0.3)
  return Math.min(100, currentScore + improvement)
}

const severityBorderColors: Record<string, string> = {
  critical: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-500",
  info: "border-l-gray-500",
}

export function FindingDetailsDrawer({
  finding, isOpen, onClose, currentScore,
  onCopyFix, onDownloadPatch, onCreatePR
}: FindingDetailsDrawerProps) {
  const [copied, setCopied] = useState(false)
  const [prConfirm, setPrConfirm] = useState<PRConfirmation | null>(null)

  if (!finding) return null

  const severityColor = getSeverityColor(finding.severity)
  const riskReduction = computeRiskReduction(finding)
  const predictedScore = computePredictedScore(currentScore, finding)
  const improvement = predictedScore - currentScore
  const repoPath = sanitizePath(finding.file_path)
  const severityBorder = severityBorderColors[finding.severity] || "border-l-gray-500"

  const handleCopy = async () => {
    if (!finding.fix_code) return
    await navigator.clipboard.writeText(finding.fix_code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    onCopyFix(finding.fix_code)
  }

  const handleCreatePR = () => {
    setPrConfirm({
      show: true,
      affectedFiles: 1,
      scoreImprovement: improvement,
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
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            />

            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-2xl bg-[#0a0a10] border-l border-white/10 overflow-hidden flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={cn(
                    "px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider",
                    severityColor.bg, severityColor.text
                  )}>
                    {finding.severity}
                  </span>
                  <span className="text-xs text-white/40 font-mono truncate">{finding.rule_id}</span>
                  {finding.confidence != null && (
                    <span className={cn(
                      "text-[10px] font-medium px-1.5 py-0.5 rounded",
                      finding.confidence >= 0.8 ? "bg-emerald-500/10 text-emerald-400" :
                      finding.confidence >= 0.5 ? "bg-yellow-500/10 text-yellow-400" :
                      "bg-gray-500/10 text-gray-400"
                    )}>
                      {(finding.confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
                <button onClick={onClose} className="text-white/30 hover:text-white/60 transition-colors flex-shrink-0">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Scrollable content */}
              <div className="flex-1 overflow-y-auto">
                <div className="p-6 space-y-5">

                  {/* 1. Finding Metadata */}
                  <div>
                    <h2 className="text-base font-semibold text-white/90">
                      {finding.summary || finding.message || finding.rule_name}
                    </h2>
                    <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Category</div>
                        <div className="text-xs font-medium text-white/70 capitalize truncate">{finding.category}</div>
                      </div>
                      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Sources</div>
                        <div className="text-xs font-medium text-white/70 truncate">
                          {finding.scanner_name || "DevArchAI"}
                        </div>
                      </div>
                      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">File Path</div>
                        <div className="text-xs font-medium text-white/70 font-mono truncate" title={repoPath}>
                          {repoPath || "\u2014"}
                        </div>
                      </div>
                      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Est. Fix Time</div>
                        <div className="text-xs font-medium text-white/70">{estimateFixTime(finding)}</div>
                      </div>
                      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Risk Reduction</div>
                        <div className={cn(
                          "text-xs font-bold",
                          riskReduction >= 60 ? "text-emerald-400" :
                          riskReduction >= 30 ? "text-yellow-400" : "text-blue-400"
                        )}>
                          +{riskReduction}%
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 2. Why This Matters */}
                  {(finding.description || finding.risk) && (
                    <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <HelpCircle className="w-4 h-4 text-amber-400" />
                        <h4 className="text-xs font-semibold text-amber-300 uppercase tracking-wider">Why This Matters</h4>
                      </div>
                      <p className="text-sm text-amber-200/70 leading-relaxed">
                        {finding.description || finding.risk}
                      </p>
                    </div>
                  )}

                  {/* 3. Security Impact */}
                  <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="w-4 h-4 text-orange-400" />
                      <h4 className="text-xs font-semibold text-orange-300 uppercase tracking-wider">Security Impact</h4>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-lg bg-black/20 p-3">
                        <div className="text-[10px] text-orange-300/50 uppercase tracking-wider mb-1">Risk Level</div>
                        <div className={cn(
                          "text-sm font-bold",
                          (finding.risk_level || finding.severity) === "critical" ? "text-red-400" :
                          (finding.risk_level || finding.severity) === "high" ? "text-orange-400" :
                          (finding.risk_level || finding.severity) === "medium" ? "text-yellow-400" : "text-blue-400"
                        )}>
                          {(finding.risk_level || finding.severity).toUpperCase()}
                        </div>
                      </div>
                      <div className="rounded-lg bg-black/20 p-3">
                        <div className="text-[10px] text-orange-300/50 uppercase tracking-wider mb-1">Attack Scenario</div>
                        <p className="text-xs text-orange-200/70 leading-relaxed">{finding.attack_scenario || finding.risk || "\u2014"}</p>
                      </div>
                      <div className="rounded-lg bg-black/20 p-3">
                        <div className="text-[10px] text-orange-300/50 uppercase tracking-wider mb-1">Business Impact</div>
                        <p className="text-xs text-orange-200/70 leading-relaxed">{finding.business_impact || finding.impact || "\u2014"}</p>
                      </div>
                      <div className="rounded-lg bg-black/20 p-3">
                        <div className="text-[10px] text-orange-300/50 uppercase tracking-wider mb-1">Environment Impact</div>
                        <p className="text-xs text-orange-200/70 leading-relaxed">{finding.environment_impact || "\u2014"}</p>
                      </div>
                    </div>
                  </div>

                  {/* 4. Current Code */}
                  {finding.before_code && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <FileCode className="w-3.5 h-3.5 text-white/40" />
                        <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Current Code</h4>
                      </div>
                      <div className={cn(
                        "rounded-xl border border-white/5 bg-black/40 overflow-hidden",
                        "border-l-2", severityBorder
                      )}>
                        <pre className="p-4 overflow-x-auto max-h-[300px] text-sm">
                          <code className="text-red-300/80 font-mono whitespace-pre">{finding.before_code}</code>
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* 5. Recommended Code */}
                  {finding.fix_code && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                        <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Recommended Code</h4>
                      </div>
                      <div className="rounded-xl border border-emerald-500/20 bg-black/40 border-l-2 border-l-emerald-500 overflow-hidden">
                        <pre className="p-4 overflow-x-auto max-h-[300px] text-sm">
                          <code className="text-emerald-300 font-mono whitespace-pre">{finding.fix_code}</code>
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* 6. Diff View */}
                  {(finding.before_code || finding.after_code || finding.unified_diff) && (
                    <div>
                      <DiffViewer
                        beforeCode={finding.before_code}
                        afterCode={finding.after_code}
                        unifiedDiff={finding.unified_diff}
                        filename={repoPath || "file"}
                      />
                    </div>
                  )}

                  {/* 7. Best Practices */}
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

                  {/* 8. AI Explanation */}
                  {finding.ai_explanation && (
                    <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <MessageSquare className="w-4 h-4 text-purple-400" />
                        <h4 className="text-xs font-semibold text-purple-300 uppercase tracking-wider">AI Explanation</h4>
                      </div>
                      <p className="text-sm text-purple-200/70 leading-relaxed">{finding.ai_explanation}</p>
                    </div>
                  )}

                  {/* 9. References */}
                  {finding.documentation_url && (
                    <div className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/[0.02] p-3">
                      <BookOpen className="w-4 h-4 text-white/30" />
                      <span className="text-xs text-white/50 flex-1">References</span>
                      <a
                        href={finding.documentation_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        View Documentation
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}

                  {/* 10. AI Analysis Pipeline */}
                  <div className="rounded-xl border border-indigo-500/10 bg-gradient-to-b from-indigo-950/20 to-slate-900/30 p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
                      <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Analysis Pipeline</h4>
                    </div>
                    <div className="relative">
                      {(() => {
                        const stages = [
                          { icon: ScanSearch, label: "Scanner Detection", description: `Identified by ${finding.scanner_name || "DevArchAI"}`, active: true },
                          { icon: GitMerge, label: "Finding Normalization", description: "Standardized into common format across scanners", active: true },
                          { icon: Search, label: "AI Analysis", description: "Deep security context analysis", active: !!finding.ai_explanation },
                          { icon: Zap, label: "Risk Scoring", description: `${finding.severity.toUpperCase()} severity — ${computeRiskReduction(finding)}% risk reduction if fixed`, active: true },
                          { icon: Shield, label: "Business Impact", description: finding.business_impact || finding.impact || "Contextual business risk assessment", active: !!finding.business_impact },
                          { icon: Sparkles, label: "Fix Generation", description: "AI-powered remediation", active: !!finding.fix_code },
                          { icon: GitPullRequest, label: "One-Click PR", description: "Create patch PR with a single click", active: true },
                        ]
                        return stages.map((stage, idx) => (
                          <div key={idx} className="flex items-start gap-3 pb-4 last:pb-0 relative">
                            {idx < stages.length - 1 && (
                              <div className="absolute left-[11px] top-6 bottom-0 w-px bg-gradient-to-b from-indigo-500/20 to-indigo-500/5" />
                            )}
                            <div className={cn(
                              "w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 z-10 ring-2 ring-[#0a0a10]",
                              stage.active
                                ? "bg-indigo-500/20 border border-indigo-500/30"
                                : "bg-white/5 border border-white/10"
                            )}>
                              {stage.active ? (
                                <stage.icon className="w-2.5 h-2.5 text-indigo-400" />
                              ) : (
                                <div className="w-1.5 h-1.5 rounded-full bg-white/20" />
                              )}
                            </div>
                            <div className="flex-1 min-w-0 pt-0.5">
                              <div className="flex items-center gap-2">
                                <span className={cn(
                                  "text-xs font-medium",
                                  stage.active ? "text-white/70" : "text-white/30"
                                )}>
                                  {stage.label}
                                </span>
                                {stage.active && (
                                  <BadgeCheck className="w-3 h-3 text-emerald-400/60 shrink-0" />
                                )}
                              </div>
                              {stage.description && (
                                <p className={cn(
                                  "text-[10px] leading-relaxed mt-0.5",
                                  stage.active ? "text-white/30" : "text-white/20"
                                )}>
                                  {stage.description}
                                </p>
                              )}
                            </div>
                          </div>
                        ))
                      })()}
                    </div>
                  </div>

                  {/* 11. Security Improvement */}
                  <div className="rounded-xl border border-white/5 bg-gradient-to-br from-indigo-950/30 to-slate-900/50 p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <TrendingUp className="w-4 h-4 text-indigo-400" />
                      <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Security Improvement</h4>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="rounded-lg border border-white/5 bg-white/[0.03] p-4 text-center">
                        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Current</div>
                        <div className="text-2xl font-bold text-white/60">{currentScore}</div>
                      </div>
                      <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-4 text-center">
                        <div className="text-[10px] text-indigo-300/50 uppercase tracking-wider mb-1">After Fix</div>
                        <div className="text-2xl font-bold text-indigo-300">{predictedScore}</div>
                      </div>
                      <div className={cn(
                        "rounded-lg border p-4 text-center",
                        improvement > 0 ? "border-emerald-500/20 bg-emerald-500/5" : "border-white/5 bg-white/[0.03]"
                      )}>
                        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Delta</div>
                        <div className={cn(
                          "text-2xl font-bold flex items-center justify-center gap-1",
                          improvement > 0 ? "text-emerald-400" : "text-white/40"
                        )}>
                          {improvement > 0 ? <>+{improvement}</> : "\u2014"}
                        </div>
                      </div>
                    </div>
                  </div>
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
                  {finding.documentation_url && (
                    <Button variant="ghost" size="sm" onClick={() => window.open(finding.documentation_url, '_blank')}>
                      <ExternalLink className="w-4 h-4 mr-1.5" />
                      Docs
                    </Button>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

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
              </p>

              <div className="space-y-3 mb-5">
                <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-4 py-3">
                  <span className="text-sm text-white/60">Affected Files</span>
                  <span className="text-sm font-bold text-white/80">{prConfirm.affectedFiles}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
                  <span className="text-sm text-emerald-300/80">Score Improvement</span>
                  <span className="text-sm font-bold text-emerald-400">+{prConfirm.scoreImprovement}</span>
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

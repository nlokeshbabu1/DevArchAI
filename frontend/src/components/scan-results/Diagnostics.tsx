import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown, ChevronRight, Terminal, Activity, GitMerge, Layers, FileText } from "lucide-react"
import { cn } from "../../lib/utils"
import { ScanTimeline } from "./ScanTimeline"
import { RepositoryStats } from "./RepositoryStats"

interface DiagnosticsProps {
  repoName: string
  filesCount: number
  directoriesCount?: number
  findingsCount: number
  rulesCount: number
  technologiesCount: number
  scanDuration?: number
  completedAt?: string
  branch?: string
  commitHash?: string
  rawFindingsCount?: number
  aiSuggestionsCount?: number
  scannersCount?: number
  // ScanTimeline props
  currentStep?: number
  totalScanners?: number
  completedScanners?: number
  aiStatus?: "pending" | "processing" | "completed" | "failed"
  scanStatus?: string
}

export function Diagnostics(props: DiagnosticsProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded-2xl border border-white/5 bg-white/[0.02] backdrop-blur-xl p-5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-white/30" />
          <h3 className="text-sm font-semibold text-white/40 uppercase tracking-wider">
            Diagnostics
          </h3>
          <span className="text-[9px] text-white/20">Pipeline logs, raw output, &amp; metadata</span>
        </div>
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-white/20" />
        ) : (
          <ChevronRight className="w-4 h-4 text-white/20" />
        )}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 space-y-4">
              {/* Scan Pipeline */}
              <ScanTimeline
                currentStep={props.currentStep ?? 8}
                totalScanners={props.totalScanners ?? 0}
                completedScanners={props.completedScanners ?? 0}
                aiStatus={props.aiStatus ?? "completed"}
                scanStatus={props.scanStatus ?? "completed"}
              />

              {/* Repository Statistics */}
              <RepositoryStats
                repoName={props.repoName}
                filesCount={props.filesCount}
                directoriesCount={props.directoriesCount}
                findingsCount={props.findingsCount}
                rulesCount={props.rulesCount}
                technologiesCount={props.technologiesCount}
                scanDuration={props.scanDuration}
                completedAt={props.completedAt}
                branch={props.branch}
                commitHash={props.commitHash}
                rawFindingsCount={props.rawFindingsCount}
                aiSuggestionsCount={props.aiSuggestionsCount}
                scannersCount={props.scannersCount}
              />

              {/* Raw output & pipeline info */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Terminal className="w-3.5 h-3.5 text-white/30" />
                    <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider">Raw Output</h4>
                  </div>
                  <p className="text-[9px] text-white/30">
                    Raw scanner JSON output, execution logs, and CLI output available in backend logs.
                  </p>
                </div>
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <GitMerge className="w-3.5 h-3.5 text-white/30" />
                    <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider">Normalization</h4>
                  </div>
                  <p className="text-[9px] text-white/30">
                    Scanner outputs standardized into a common schema with CWE mapping and severity alignment.
                  </p>
                </div>
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Layers className="w-3.5 h-3.5 text-white/30" />
                    <h4 className="text-[10px] font-semibold text-white/30 uppercase tracking-wider">Deduplication</h4>
                  </div>
                  <p className="text-[9px] text-white/30">
                    Duplicate findings across scanners merged. Each issue appears once with all scanner sources listed.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

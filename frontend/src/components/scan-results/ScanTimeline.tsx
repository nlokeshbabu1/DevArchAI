import { motion } from "framer-motion"
import {
  Search, CheckCircle2, Clock, Loader2, AlertCircle,
  ArrowRight, Cpu, Shield, GitMerge, Sparkles, FileText, Flag,
} from "lucide-react"
import { cn } from "../../lib/utils"

interface ScanTimelineProps {
  currentStep?: number
  totalScanners?: number
  completedScanners?: number
  aiStatus?: "pending" | "processing" | "completed" | "failed"
  scanStatus?: string
}

const STEPS = [
  { id: "detection", label: "Technology Detection", icon: Search },
  { id: "selection", label: "Scanner Selection", icon: Cpu },
  { id: "execution", label: "Scanner Execution", icon: Shield },
  { id: "normalization", label: "Normalization", icon: FileText },
  { id: "deduplication", label: "Deduplication", icon: GitMerge },
  { id: "ai", label: "AI Recommendation", icon: Sparkles },
  { id: "report", label: "Report Generation", icon: FileText },
  { id: "completed", label: "Completed", icon: Flag },
]

function getStepState(
  stepIndex: number,
  currentStep: number,
  aiStatus: string,
  scanStatus: string,
): "done" | "current" | "pending" | "error" {
  if (scanStatus === "failed") return "error"
  if (stepIndex < currentStep) return "done"
  if (stepIndex === currentStep) {
    if (stepIndex === 5 && aiStatus === "failed") return "error"
    if (stepIndex === 5 && aiStatus === "processing") return "current"
    return "current"
  }
  return "pending"
}

export function ScanTimeline({
  currentStep = 8,
  totalScanners = 0,
  completedScanners = 0,
  aiStatus = "completed",
  scanStatus = "completed",
}: ScanTimelineProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center gap-2 mb-4">
        <Cpu className="w-4 h-4 text-white/40" />
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Scan Pipeline
        </h3>
      </div>

      <div className="flex flex-wrap gap-y-3">
        {STEPS.map((step, i) => {
          const StepIcon = step.icon
          const state = getStepState(i, currentStep, aiStatus, scanStatus)

          return (
            <div key={step.id} className="flex items-center">
              <div className="flex items-center gap-2">
                <div className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all duration-300",
                  state === "done" && "bg-emerald-500/20 border border-emerald-500/30",
                  state === "current" && "bg-indigo-500/20 border border-indigo-500/30 ring-2 ring-indigo-500/20",
                  state === "pending" && "bg-white/5 border border-white/10",
                  state === "error" && "bg-red-500/20 border border-red-500/30",
                )}>
                  {state === "done" ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : state === "current" ? (
                    <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                  ) : state === "error" ? (
                    <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                  ) : (
                    <StepIcon className="w-3.5 h-3.5 text-white/20" />
                  )}
                </div>
                <span className={cn(
                  "text-[10px] font-medium whitespace-nowrap transition-colors",
                  state === "done" && "text-emerald-300",
                  state === "current" && "text-indigo-300",
                  state === "pending" && "text-white/30",
                  state === "error" && "text-red-300",
                )}>
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={cn(
                  "mx-2 h-px w-6 transition-colors",
                  state === "done" ? "bg-emerald-500/30" : "bg-white/10"
                )} />
              )}
            </div>
          )
        })}
      </div>

      {/* Summary footer */}
      {(scanStatus === "completed" || aiStatus === "completed") && (
        <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-3 text-[10px] text-white/30">
          {totalScanners > 0 && (
            <span>{completedScanners}/{totalScanners} scanners completed</span>
          )}
          {aiStatus === "completed" && (
            <>
              <span className="text-white/10">|</span>
              <span className="text-indigo-400/60">AI recommendations generated</span>
            </>
          )}
          {currentStep >= 7 && (
            <>
              <span className="text-white/10">|</span>
              <span className="text-emerald-400/60 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Pipeline complete
              </span>
            </>
          )}
        </div>
      )}
    </motion.div>
  )
}

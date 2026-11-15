import { motion } from "framer-motion"
import { Shield, ShieldCheck, ShieldAlert, Scale, FileCheck, BookCheck } from "lucide-react"

import { cn } from "../../lib/utils"

interface ComplianceScore {
  framework: string
  standard: string
  score: number
  status: "passed" | "partial" | "failed"
  findings: number
}

interface ComplianceDashboardProps {
  scores?: ComplianceScore[]
  hasFindings?: boolean
}

const defaultScores: ComplianceScore[] = [
  { framework: "CIS Benchmark", standard: "CIS", score: 84, status: "partial", findings: 3 },
  { framework: "SOC 2", standard: "SOC2", score: 91, status: "passed", findings: 1 },
  { framework: "ISO 27001", standard: "ISO27001", score: 88, status: "partial", findings: 2 },
  { framework: "NIST SP 800-53", standard: "NIST", score: 76, status: "partial", findings: 5 },
  { framework: "PCI DSS", standard: "PCI DSS", score: 82, status: "partial", findings: 3 },
  { framework: "AWS Well-Architected", standard: "AWS WA", score: 79, status: "partial", findings: 4 },
]

const statusConfig = {
  passed: { icon: ShieldCheck, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20", label: "Compliant" },
  partial: { icon: ShieldAlert, color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20", label: "At Risk" },
  failed: { icon: ShieldAlert, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", label: "Non-Compliant" },
}

export function ComplianceDashboard({ scores = defaultScores, hasFindings = true }: ComplianceDashboardProps) {
  if (!hasFindings) {return null}

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Compliance Mapping
        </h3>
        <div className="flex items-center gap-1.5 text-xs text-white/30">
          <Scale className="w-3.5 h-3.5" />
          Framework Alignment
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {scores.map((item, i) => {
          const status = statusConfig[item.status]
          const Icon = status.icon
          return (
            <motion.div
              key={item.framework}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.04 }}
              className={cn(
                "rounded-xl border p-3.5 transition-all duration-200 hover:scale-[1.02]",
                status.bg, status.border
              )}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon className={cn("w-4 h-4 flex-shrink-0", status.color)} />
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-white/70 truncate">{item.framework}</div>
                    <div className="text-[10px] text-white/30">{item.standard}</div>
                  </div>
                </div>
                <span className={cn(
                  "text-lg font-bold font-mono flex-shrink-0 ml-2",
                  item.score >= 90 ? "text-emerald-400" : item.score >= 80 ? "text-yellow-400" : "text-red-400"
                )}>
                  {item.score}%
                </span>
              </div>

              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden mb-2">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${item.score}%` }}
                  transition={{ duration: 1, delay: i * 0.08 }}
                  className={cn(
                    "h-full rounded-full",
                    item.score >= 90 ? "bg-emerald-500" : item.score >= 80 ? "bg-yellow-500" : "bg-red-500"
                  )}
                />
              </div>

              <div className="flex items-center justify-between">
                <span className={cn("text-[10px] font-medium", status.color)}>
                  {status.label}
                </span>
                <span className="text-[10px] text-white/30">
                  {item.findings > 0 ? `${item.findings} gap${item.findings !== 1 ? "s" : ""}` : "No gaps"}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

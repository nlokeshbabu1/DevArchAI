import { memo } from "react"
import { motion } from "framer-motion"
import { AlertTriangle, Bug, AlertCircle, Info, Shield } from "lucide-react"
import { cn } from "../../lib/utils"

interface RiskDistributionProps {
  riskDistribution: { critical: number; high: number; medium: number; low: number; info: number }
  totalFindings: number
}

const severityConfig = [
  { key: "critical", icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", label: "Critical" },
  { key: "high", icon: Bug, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", label: "High" },
  { key: "medium", icon: AlertCircle, color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20", label: "Medium" },
  { key: "low", icon: Info, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", label: "Low" },
  { key: "info", icon: Info, color: "text-gray-400", bg: "bg-gray-500/10", border: "border-gray-500/20", label: "Info" },
]

export const RiskDistribution = memo(function RiskDistribution({
  riskDistribution,
  totalFindings,
}: RiskDistributionProps) {
  const hasData = totalFindings > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 h-full"
    >
      <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">
        Risk Distribution
      </h3>

      {!hasData ? (
        <div className="flex items-center justify-center h-24 text-white/30 text-sm">
          <Shield className="w-5 h-5 mr-2" />
          No issues found
        </div>
      ) : (
        <div className="space-y-3">
          {/* Severity bar */}
          <div className="flex h-2 gap-0.5 rounded-full overflow-hidden bg-white/5">
            {severityConfig.map(({ key }) => {
              const count = riskDistribution[key as keyof typeof riskDistribution] || 0
              if (count === 0) { return null }
              const pct = (count / totalFindings) * 100
              return (
                <motion.div
                  key={key}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                  className={cn("h-full rounded-full", `bg-${key === "critical" ? "red" : key === "high" ? "orange" : key === "medium" ? "yellow" : key === "low" ? "blue" : "gray"}-500/40`)}
                />
              )
            })}
          </div>

          {/* Severity list */}
          <div className="space-y-2">
            {severityConfig.map(({ key, icon: Icon, color, bg, border, label }) => {
              const count = riskDistribution[key as keyof typeof riskDistribution] || 0
              if (count === 0) { return null }
              const pct = ((count / totalFindings) * 100).toFixed(0)
              return (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn("flex items-center gap-3 rounded-lg border px-3 py-2", bg, border)}
                >
                  <Icon className={cn("w-4 h-4 shrink-0", color)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className={cn("text-xs font-medium", color)}>{label}</span>
                      <span className="text-xs text-white/40">{count}</span>
                    </div>
                    <div className="h-1 rounded-full bg-white/5 overflow-hidden mt-1">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.5, ease: "easeOut" }}
                        className={cn("h-full rounded-full", `bg-${key === "critical" ? "red" : key === "high" ? "orange" : key === "medium" ? "yellow" : key === "low" ? "blue" : "gray"}-500/30`)}
                      />
                    </div>
                  </div>
                  <span className="text-[10px] text-white/30 font-mono">{pct}%</span>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}
    </motion.div>
  )
})

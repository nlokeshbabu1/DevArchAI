import { motion } from "framer-motion"
import {
  AlertTriangle, Bug, AlertCircle, Info,
  Shield, Code2, Database, Globe, Lock, Server, Cloud,
  Key, Package, Container, FileCode
} from "lucide-react"
import { Finding, CategoryScore } from "../../types"
import { cn } from "../../lib/utils"

interface ExecutiveSummaryProps {
  severityCounts: Record<string, number>
  categoryScores?: CategoryScore[]
  findings: Finding[]
  categoryCounts?: Record<string, number>
}

const severityConfig = {
  critical: { icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", label: "Critical" },
  high: { icon: Bug, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", label: "High" },
  medium: { icon: AlertCircle, color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20", label: "Medium" },
  low: { icon: Info, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", label: "Low" },
}

const categoryCards = [
  { key: "secrets", label: "Secrets", icon: Key, color: "text-pink-400", bg: "bg-pink-500/10", border: "border-pink-500/20" },
  { key: "sca", label: "Dependencies", icon: Package, color: "text-cyan-400", bg: "bg-cyan-500/10", border: "border-cyan-500/20" },
  { key: "docker", label: "Docker", icon: Container, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
  { key: "terraform", label: "Terraform", icon: FileCode, color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20" },
  { key: "kubernetes", label: "Kubernetes", icon: Server, color: "text-cyan-400", bg: "bg-cyan-500/10", border: "border-cyan-500/20" },
  { key: "cicd", label: "CI/CD", icon: Globe, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20" },
]

function AnimatedCounter({ value, label }: { value: number; label: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center"
    >
      <motion.span
        className="text-2xl font-bold"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {value}
      </motion.span>
      <span className="text-xs text-white/50 mt-0.5">{label}</span>
    </motion.div>
  )
}

export function ExecutiveSummary({ severityCounts = {}, categoryScores = [], findings, categoryCounts = {} }: ExecutiveSummaryProps) {
  const hasData = Object.keys(severityCounts).length > 0 || categoryScores.length > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-5">
        Executive Summary
      </h3>

      {!hasData ? (
        <div className="flex items-center justify-center h-24 text-white/30 text-sm">
          <Shield className="w-5 h-5 mr-2" />
          No issues found — your codebase looks clean
        </div>
      ) : (
        <>
          {/* Severity cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
            {Object.entries(severityConfig).map(([key, config]) => {
              const Icon = config.icon
              const count = severityCounts[key] || 0
              return (
                <motion.div
                  key={key}
                  whileHover={{ scale: 1.02 }}
                  className={cn(
                    "rounded-xl border p-3 transition-all duration-200",
                    config.bg, config.border
                  )}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <Icon className={cn("w-4 h-4", config.color)} />
                    <span className={cn("text-xs font-medium", config.color)}>
                      {config.label}
                    </span>
                  </div>
                  <AnimatedCounter value={count} label={count === 1 ? "finding" : "findings"} />
                </motion.div>
              )
            })}
          </div>

          {/* Category metric cards */}
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-4">
            {categoryCards.map((cat) => {
              const Icon = cat.icon
              const count = categoryCounts[cat.key] ?? 0
              return (
                <motion.div
                  key={cat.key}
                  whileHover={{ scale: 1.03 }}
                  className={cn(
                    "rounded-lg border p-2.5 text-center transition-all duration-200",
                    cat.bg, cat.border
                  )}
                >
                  <Icon className={cn("w-3.5 h-3.5 mx-auto mb-1", cat.color)} />
                  <div className={cn("text-sm font-bold", cat.color)}>{count}</div>
                  <div className="text-[9px] text-white/40 mt-0.5">{cat.label}</div>
                </motion.div>
              )
            })}
          </div>
        </>
      )}

      {/* Category score bars */}
      {categoryScores.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-white/40 uppercase tracking-wider mb-3">
            Category Scores
          </h4>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
            {categoryScores.map((cat, i) => {
              const score = cat.score || 0
              const scoreColor = score >= 80 ? "text-emerald-400" : score >= 60 ? "text-yellow-400" : "text-red-400"
              return (
                <motion.div
                  key={cat.category}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/[0.02] p-2"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] text-white/70 capitalize truncate">{cat.category}</div>
                    <div className="mt-1 h-1 rounded-full bg-white/5 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${score}%` }}
                        transition={{ duration: 1, delay: i * 0.08 }}
                        className={cn("h-full rounded-full", score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-yellow-500" : "bg-red-500")}
                      />
                    </div>
                  </div>
                  <span className={cn("text-xs font-mono font-medium", scoreColor)}>{score}%</span>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}
    </motion.div>
  )
}

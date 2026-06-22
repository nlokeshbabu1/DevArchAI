import { motion } from "framer-motion"
import { Shield, Code2, Database, Lock, Server, Cloud, Globe, FileText, Activity } from "lucide-react"
import { cn } from "../../lib/utils"

interface CoverageItem {
  type: string
  label: string
  icon: typeof Shield
  enabled: boolean
  score: number
  description: string
  filesScanned?: number
  rulesExecuted?: number
}

interface SecurityCoverageProps {
  scores: Record<string, number>
  filesByCategory?: Record<string, number>
}

const coverageTypes: Omit<CoverageItem, "score" | "filesScanned">[] = [
  { type: "sast", label: "Code Analysis (SAST)", icon: Code2, enabled: true, description: "Static analysis for vulnerability patterns" },
  { type: "sca", label: "Dependency Scan (SCA)", icon: Database, enabled: true, description: "Open source dependency scanning" },
  { type: "secrets", label: "Secrets Detection", icon: Lock, enabled: true, description: "Credential and secret detection" },
  { type: "iac", label: "IaC Scan (Terraform)", icon: Server, enabled: true, description: "Infrastructure as Code analysis" },
  { type: "containers", label: "Container Scan", icon: Cloud, enabled: true, description: "Docker image vulnerability scanning" },
  { type: "dast", label: "DAST", icon: Globe, enabled: true, description: "Dynamic application security testing" },
]

export function SecurityCoverage({ scores, filesByCategory = {} }: SecurityCoverageProps) {
  const items: CoverageItem[] = coverageTypes.map(item => ({
    ...item,
    score: scores[item.type] ?? 0,
    filesScanned: filesByCategory[item.type] ?? 0,
    rulesExecuted: Math.floor((scores[item.type] ?? 0) * 2.5),
  }))

  const avgScore = items.length > 0 ? Math.round(items.reduce((s, i) => s + i.score, 0) / items.length) : 0
  const totalFiles = Object.values(filesByCategory).reduce((s, v) => s + v, 0) || items.reduce((s, i) => s + (i.filesScanned ?? 0), 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Security Coverage
        </h3>
        <div className="flex items-center gap-3 text-xs text-white/30">
          <span className="flex items-center gap-1"><FileText className="w-3 h-3" /> {totalFiles} files</span>
          <span className="flex items-center gap-1"><Activity className="w-3 h-3" /> {avgScore}% avg</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {items.map((item, i) => {
          const Icon = item.icon
          const scoreColor = item.score >= 80 ? "text-emerald-400" : item.score >= 60 ? "text-yellow-400" : "text-red-400"
          const barColor = item.score >= 80 ? "bg-emerald-500" : item.score >= 60 ? "bg-yellow-500" : "bg-red-500"
          return (
            <motion.div
              key={item.type}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="rounded-xl border border-white/5 bg-white/[0.02] p-3.5 hover:border-white/10 transition-colors"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className={cn(
                  "w-9 h-9 rounded-lg flex items-center justify-center",
                  item.score >= 80 ? "bg-emerald-500/10" : item.score >= 60 ? "bg-yellow-500/10" : "bg-red-500/10"
                )}>
                  <Icon className={cn("w-4 h-4", scoreColor)} />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-white/80">{item.label}</span>
                  <p className="text-[10px] text-white/30 truncate">{item.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-3 mb-2">
                <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${item.score}%` }}
                    transition={{ duration: 1, delay: i * 0.08, ease: "easeOut" }}
                    className={cn("h-full rounded-full", barColor)}
                  />
                </div>
                <span className={cn("text-xs font-mono font-medium flex-shrink-0", scoreColor)}>
                  {item.score}%
                </span>
              </div>

              <div className="flex items-center justify-between text-[10px] text-white/20">
                <span>{item.filesScanned} files</span>
                <span>{item.rulesExecuted} rules</span>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

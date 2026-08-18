import { useMemo } from "react"
import { motion } from "framer-motion"
import { Lightbulb, AlertTriangle, Server, Key, Container, FileCode, Globe, Package, ArrowRight, Shield } from "lucide-react"
import { Finding } from "../../types"
import { cn } from "../../lib/utils"

interface Recommendation {
  id: number
  title: string
  description: string
  priority: "critical" | "high" | "medium" | "low"
  category: string
  affectedCount: number
  icon: any
}

const categoryIcons: Record<string, any> = {
  secrets: Key,
  sca: Package,
  docker: Container,
  terraform: FileCode,
  kubernetes: Server,
  cicd: Globe,
}

const categoryLabels: Record<string, string> = {
  secrets: "Secret Detection",
  sca: "Dependencies",
  docker: "Docker",
  terraform: "Terraform",
  kubernetes: "Kubernetes",
  cicd: "CI/CD",
}

export function FixRoadmap({
  currentScore,
  findings = [],
  categoryCounts = {},
}: {
  currentScore: number
  findings?: Finding[]
  categoryCounts?: Record<string, number>
}) {
  const recommendations = useMemo(() => {
    const recs: Recommendation[] = []

    if (findings.length === 0) return recs

    const criticalCount = findings.filter(f => f.severity === "critical").length
    if (criticalCount > 0) {
      recs.push({
        id: 1,
        title: `Fix ${criticalCount} Critical ${criticalCount === 1 ? "Issue" : "Issues"} Immediately`,
        description: `Critical-severity vulnerabilities require urgent remediation. Prioritize these findings to prevent potential security breaches.`,
        priority: "critical",
        category: "general",
        affectedCount: criticalCount,
        icon: AlertTriangle,
      })
    }

    const highCount = findings.filter(f => f.severity === "high").length
    if (highCount > 0) {
      recs.push({
        id: 2,
        title: `Address ${highCount} High-Risk ${highCount === 1 ? "Finding" : "Findings"}`,
        description: `High-severity issues should be resolved in the current sprint to maintain a strong security posture.`,
        priority: "high",
        category: "general",
        affectedCount: highCount,
        icon: AlertTriangle,
      })
    }

    for (const [catKey, count] of Object.entries(categoryCounts)) {
      if (count === 0) continue
      const Icon = categoryIcons[catKey] || Lightbulb
      const label = categoryLabels[catKey] || catKey
      const severity = findings
        .filter(f => {
          const cat = (f.category ?? "").toLowerCase()
          return cat.includes(catKey)
        })
        .reduce((max, f) => {
          const order: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 }
          return Math.max(max, order[f.severity] || 0)
        }, 0)

      const priority: Recommendation["priority"] =
        severity >= 4 ? "critical" : severity >= 3 ? "high" : severity >= 2 ? "medium" : "low"

      recs.push({
        id: recs.length + 1,
        title: `Review ${label} Configuration${count > 1 ? "s" : ""}`,
        description: `${count} ${count === 1 ? "issue was" : "issues were"} found in your ${label.toLowerCase()} configuration. Review and apply recommended fixes to improve security.`,
        priority,
        category: catKey,
        affectedCount: count,
        icon: Icon,
      })
    }

    const mediumCount = findings.filter(f => f.severity === "medium").length
    if (mediumCount > 0 && recs.length < 4) {
      recs.push({
        id: recs.length + 1,
        title: `Plan ${mediumCount} Medium-Priority Fixes`,
        description: `Medium-severity issues should be addressed in upcoming sprints. Schedule these alongside feature work.`,
        priority: "medium",
        category: "general",
        affectedCount: mediumCount,
        icon: Lightbulb,
      })
    }

    return recs.slice(0, 5)
  }, [findings, categoryCounts])

  const priorityColors = {
    critical: { text: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", pill: "bg-red-500/20 text-red-300" },
    high: { text: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", pill: "bg-orange-500/20 text-orange-300" },
    medium: { text: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20", pill: "bg-yellow-500/20 text-yellow-300" },
    low: { text: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", pill: "bg-blue-500/20 text-blue-300" },
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-4 h-4 text-indigo-400" />
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Recommended Actions
        </h3>
      </div>

      {recommendations.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Shield className="w-8 h-8 text-white/20 mb-3" />
          <p className="text-sm text-white/40">No issues found — your codebase looks clean!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {recommendations.map((rec, i) => {
            const colors = priorityColors[rec.priority]
            const Icon = rec.icon
            return (
              <motion.div
                key={rec.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className={cn(
                  "rounded-xl border p-4 transition-all duration-200",
                  colors.bg, colors.border
                )}
              >
                <div className="flex items-start gap-3">
                  <div className={cn("flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center", colors.bg)}>
                    <Icon className={cn("w-4 h-4", colors.text)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-white/90">{rec.title}</span>
                      <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider", colors.pill)}>
                        {rec.priority}
                      </span>
                    </div>
                    <p className="text-xs text-white/50">{rec.description}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-[11px] text-white/30">
                        {rec.affectedCount} affected {rec.affectedCount === 1 ? "finding" : "findings"}
                      </span>
                      {rec.category !== "general" && (
                        <span className="text-[11px] text-white/20 capitalize">{rec.category}</span>
                      )}
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-white/20 flex-shrink-0 mt-2" />
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </motion.div>
  )
}

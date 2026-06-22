import { motion } from "framer-motion"
import { Zap, Shield, Activity, TrendingUp, ArrowRight } from "lucide-react"

interface FixRoadmapProps {
  currentScore: number
}

const suggestions = [
  {
    icon: Zap,
    title: "Add CI Security Tests",
    description: "Integrate SAST scanning into CI pipeline to catch vulnerabilities before deployment",
    points: 4,
    color: "text-yellow-400",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/20",
  },
  {
    icon: Shield,
    title: "Pin Docker Base Images",
    description: "Use specific version tags instead of 'latest' for reproducible and auditable builds",
    points: 2,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
  },
  {
    icon: Activity,
    title: "Enable Build Caching",
    description: "Configure layer caching to speed up builds and reduce unnecessary dependency fetches",
    points: 1,
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/20",
  },
]

export function FixRoadmap({ currentScore }: FixRoadmapProps) {
  const totalPoints = suggestions.reduce((sum, s) => sum + s.points, 0)
  const potentialScore = Math.min(100, currentScore + totalPoints)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-4 h-4 text-emerald-400" />
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Recommended Actions
        </h3>
      </div>

      <div className="flex items-center gap-2 mb-5 px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-500/10 to-indigo-500/10 border border-emerald-500/20">
        <span className="text-xs text-white/40">Score:</span>
        <span className="text-sm font-bold text-white/70">{currentScore}</span>
        <ArrowRight className="w-3.5 h-3.5 text-white/20" />
        <span className="text-sm font-bold text-emerald-400">{potentialScore}</span>
        <span className="text-[11px] text-emerald-400/60">(+{totalPoints} possible)</span>
      </div>

      <div className="space-y-2">
        {suggestions.map((item) => {
          const Icon = item.icon
          return (
            <motion.div
              key={item.title}
              className={`rounded-xl border ${item.border} ${item.bg} p-3.5 flex items-center gap-3`}
            >
              <div className={`flex-shrink-0 w-8 h-8 rounded-lg ${item.bg} border ${item.border} flex items-center justify-center`}>
                <Icon className={`w-4 h-4 ${item.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white/80">{item.title}</span>
                  <span className={`text-xs font-bold ${item.color}`}>+{item.points}</span>
                </div>
                <p className="text-[11px] text-white/40 mt-0.5">{item.description}</p>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

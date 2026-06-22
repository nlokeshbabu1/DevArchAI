import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, ArrowUp, ArrowDown } from "lucide-react"
import { cn } from "../../lib/utils"

interface SecurityTrendsProps {
  previousScore?: number
  currentScore: number
  criticalTrend?: { previous: number; current: number }
  highTrend?: { previous: number; current: number }
  mediumTrend?: { previous: number; current: number }
}

export function SecurityTrends({
  previousScore,
  currentScore,
  criticalTrend,
  highTrend,
  mediumTrend,
}: SecurityTrendsProps) {
  const scoreDiff = previousScore !== undefined ? currentScore - previousScore : 0
  const hasScoreData = previousScore !== undefined
  const hasTrendData = criticalTrend || highTrend || mediumTrend

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-5">
        Security Improvement
      </h3>

      {/* Score Comparison */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 text-center">
          <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Previous</div>
          <div className="text-2xl font-bold text-white/50">
            {hasScoreData ? previousScore : "—"}
          </div>
        </div>
        <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-center">
          <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Current</div>
          <div className="text-2xl font-bold text-white/90">{currentScore}</div>
        </div>
        <div className={cn(
          "rounded-xl border p-4 text-center",
          scoreDiff > 0 ? "border-emerald-500/20 bg-emerald-500/5" :
          scoreDiff < 0 ? "border-red-500/20 bg-red-500/5" :
          "border-white/5 bg-white/[0.02]"
        )}>
          <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Change</div>
          <div className={cn(
            "text-2xl font-bold flex items-center justify-center gap-1",
            scoreDiff > 0 ? "text-emerald-400" :
            scoreDiff < 0 ? "text-red-400" :
            "text-white/50"
          )}>
            {hasScoreData ? (
              <>
                {scoreDiff > 0 ? <ArrowUp className="w-5 h-5" /> : scoreDiff < 0 ? <ArrowDown className="w-5 h-5" /> : <Minus className="w-5 h-5" />}
                {scoreDiff > 0 ? "+" : ""}{scoreDiff}
              </>
            ) : "—"}
          </div>
        </div>
      </div>

      {/* Trend Cards */}
      {hasTrendData && (
        <div className="space-y-2">
          {criticalTrend && (
            <TrendCard
              label="Critical"
              previous={criticalTrend.previous}
              current={criticalTrend.current}
              color="red"
            />
          )}
          {highTrend && (
            <TrendCard
              label="High"
              previous={highTrend.previous}
              current={highTrend.current}
              color="orange"
            />
          )}
          {mediumTrend && (
            <TrendCard
              label="Medium"
              previous={mediumTrend.previous}
              current={mediumTrend.current}
              color="yellow"
            />
          )}
        </div>
      )}

      {!hasTrendData && !hasScoreData && (
        <div className="flex items-center justify-center h-20 text-white/20 text-sm">
          Run a previous scan to see improvement trends
        </div>
      )}
    </motion.div>
  )
}

function TrendCard({
  label, previous, current, color
}: {
  label: string
  previous: number
  current: number
  color: "red" | "orange" | "yellow"
}) {
  const diff = current - previous
  const improved = diff < 0

  const colorMap = {
    red: { text: "text-red-300", bg: "bg-red-500/5", border: "border-red-500/20", badge: "bg-red-500/10 text-red-400" },
    orange: { text: "text-orange-300", bg: "bg-orange-500/5", border: "border-orange-500/20", badge: "bg-orange-500/10 text-orange-400" },
    yellow: { text: "text-yellow-300", bg: "bg-yellow-500/5", border: "border-yellow-500/20", badge: "bg-yellow-500/10 text-yellow-400" },
  }
  const c = colorMap[color]

  return (
    <div className={cn("flex items-center justify-between rounded-lg border px-4 py-3", c.bg, c.border)}>
      <span className={cn("text-sm font-medium", c.text)}>{label}</span>
      <div className="flex items-center gap-3">
        <span className="text-sm text-white/40">{previous}</span>
        <span className="text-xs text-white/20">→</span>
        <span className={cn("text-sm font-bold", current === 0 ? "text-emerald-400" : c.text)}>{current}</span>
        {diff !== 0 && (
          <span className={cn(
            "flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded",
            improved ? "bg-emerald-500/10 text-emerald-400" : c.badge
          )}>
            {improved ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}
            {Math.abs(diff)}
          </span>
        )}
      </div>
    </div>
  )
}

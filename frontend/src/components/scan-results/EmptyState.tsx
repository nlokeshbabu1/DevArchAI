import { motion } from "framer-motion"
import { Shield, ShieldCheck, CheckCircle2, RotateCcw } from "lucide-react"
import { ScoreCircle, Button } from "../ui-animated"

interface EmptyStateProps {
  score: number
  repoName: string
  filesAnalyzed: number
  coveragePercent?: number
  rulesExecuted?: number
  onRescan?: () => void
}

export function EmptyState({ score, repoName, filesAnalyzed, coveragePercent = 100, rulesExecuted = 0, onRescan }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-emerald-950/30 via-slate-900/50 to-slate-950/50 backdrop-blur-xl"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-emerald-500/10 via-transparent to-transparent" />
      <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-60 h-60 bg-indigo-500/5 rounded-full blur-3xl" />

      <div className="relative z-10 p-8 lg:p-12 flex flex-col items-center text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
          className="mb-6"
        >
          <div className="relative">
            <ScoreCircle score={score} size="xl" />
            <motion.div
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.8 }}
              className="absolute -top-1 -right-1"
            >
              <ShieldCheck className="w-8 h-8 text-emerald-400" />
            </motion.div>
          </div>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-2xl font-bold text-white/90 mb-2"
        >
          Excellent Security Posture
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="text-white/50 max-w-lg mb-8"
        >
          {repoName} passed with flying colors. No critical or high-severity issues found
          across {filesAnalyzed.toLocaleString()} analyzed files. Your security practices
          are in great shape!
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="grid grid-cols-3 gap-4 mb-8"
        >
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
            <div className="text-2xl font-bold text-emerald-300">{score}%</div>
            <div className="text-[10px] text-emerald-400/60 mt-1">Security Score</div>
          </div>
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
            <div className="text-2xl font-bold text-emerald-300">{coveragePercent}%</div>
            <div className="text-[10px] text-emerald-400/60 mt-1">Coverage</div>
          </div>
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
            <div className="text-2xl font-bold text-emerald-300">{rulesExecuted}</div>
            <div className="text-[10px] text-emerald-400/60 mt-1">Rules</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="flex flex-wrap items-center justify-center gap-3"
        >
          <p className="text-xs text-white/30 max-w-md mb-6">
            Security scan completed. {rulesExecuted > 0 ? `${rulesExecuted} security rules executed` : "All applicable security rules evaluated"}; no violations detected.{" "}
            {filesAnalyzed > 0 && `${filesAnalyzed.toLocaleString()} files scanned across all categories.`}
            {" "}Your configurations, dependencies, secrets, and infrastructure code have been checked.
          </p>

          {["Code Security", "Dependency Security", "Secret Detection", "Infrastructure Security"].map((item, i) => (
            <motion.div
              key={item}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.8 + i * 0.1 }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {item}
            </motion.div>
          ))}
        </motion.div>

        {onRescan && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.0 }}
            className="mt-8"
          >
            <Button variant="primary" size="md" onClick={onRescan} glow>
              <RotateCcw className="w-4 h-4 mr-1.5" />
              Run New Scan
            </Button>
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

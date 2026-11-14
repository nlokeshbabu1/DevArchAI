import { motion } from "framer-motion"
import { GitBranch, Clock, FileText, Tag, Files, List } from "lucide-react"

import type { ScoreSource } from "../../lib/security-score"
import { formatDuration, getRelativeTime } from "../../lib/utils"
import { SecurityScore } from "../ui/SecurityScore"

interface SecurityHeroProps {
  /** Canonical score fields from API */
  scoreData: ScoreSource
  repoName: string
  branch?: string
  commitHash?: string
  completedAt?: string
  totalFindings: number
  filesAnalyzed: number
  affectedFiles?: number
  analysisDuration?: number
  techStack?: string[]
}

export function SecurityHero({
  scoreData, repoName, branch, commitHash, completedAt,
  totalFindings, filesAnalyzed, affectedFiles,
  analysisDuration, techStack
}: SecurityHeroProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-indigo-950/60 via-slate-900/80 to-slate-950/90 backdrop-blur-xl"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-emerald-500/5 via-transparent to-transparent" />

      <div className="relative z-10 p-4 lg:p-5">
        {/* Top row: repo identity + score */}
        <div className="flex items-center justify-between gap-4 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 shrink-0">
              <GitBranch className="h-4 w-4 text-indigo-400" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-semibold text-white/90 truncate">{repoName}</h1>
              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-white/40">
                <span className="font-mono px-1.5 py-0.5 rounded border border-white/[0.08] bg-white/[0.04] text-indigo-300/80">
                  {branch || 'main'}
                </span>
                {commitHash && (
                  <span className="font-mono truncate max-w-[120px]" title={commitHash}>
                    {commitHash.slice(0, 7)}
                  </span>
                )}
                {completedAt && (
                  <span>{getRelativeTime(completedAt)}</span>
                )}
              </div>
            </div>
          </div>

          <SecurityScore data={scoreData} size="md" showGrade showLabel />
        </div>

        {/* Bottom row: metadata pills */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-white/50">
          <span className="flex items-center gap-1">
            <List className="w-3 h-3 text-white/30" />
            {totalFindings} {totalFindings === 1 ? "finding" : "findings"}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="w-3 h-3 text-white/30" />
            {filesAnalyzed} files scanned
          </span>
          {affectedFiles != null && affectedFiles !== filesAnalyzed && (
            <span className="flex items-center gap-1">
              <Files className="w-3 h-3 text-white/30" />
              {affectedFiles} affected
            </span>
          )}
          {analysisDuration != null && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-white/30" />
              {formatDuration(analysisDuration)}
            </span>
          )}
          {techStack && techStack.length > 0 && (
            <span className="flex items-center gap-1.5 ml-1">
              <Tag className="w-3 h-3 text-white/20" />
              {techStack.map((tech) => (
                <span
                  key={tech}
                  className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/50"
                >
                  {tech}
                </span>
              ))}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}

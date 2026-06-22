import { motion } from "framer-motion"
import { Shield, Github, GitBranch, Clock, FileText, Zap, Calendar } from "lucide-react"
import { ScoreCircle } from "../ui-animated"
import { cn, formatDuration } from "../../lib/utils"

interface SecurityHeroProps {
  overallScore: number
  repoName: string
  branch?: string
  techStack?: string[]
  filesAnalyzed: number
  totalFindings: number
  completedAt?: string
  analysisDuration?: number
}

function getGrade(score: number): { letter: string; color: string } {
  if (score >= 90) return { letter: "A", color: "text-emerald-400" }
  if (score >= 80) return { letter: "B", color: "text-green-400" }
  if (score >= 70) return { letter: "C", color: "text-yellow-400" }
  if (score >= 60) return { letter: "D", color: "text-orange-400" }
  return { letter: "F", color: "text-red-400" }
}

export function SecurityHero({ overallScore, repoName, branch, techStack, filesAnalyzed, totalFindings, completedAt, analysisDuration }: SecurityHeroProps) {
  const grade = getGrade(overallScore)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-indigo-950/60 via-slate-900/80 to-slate-950/90 backdrop-blur-xl"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-emerald-500/5 via-transparent to-transparent" />

      <div className="relative z-10 p-6 lg:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center gap-6 lg:gap-10">
          <div className="flex-shrink-0">
            <ScoreCircle score={overallScore} size="xl" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center gap-2 text-white/60">
                <Github className="w-5 h-5" />
                <span className="font-mono text-sm">{repoName}</span>
              </div>
              {branch && (
                <div className="flex items-center gap-1.5 text-white/40 text-xs">
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>{branch}</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 mb-4">
              <span className={cn("text-4xl font-bold tracking-tight", grade.color)}>
                {grade.letter}
              </span>
            </div>

            {techStack && techStack.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {techStack.map((tech) => (
                  <span
                    key={tech}
                    className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/5 border border-white/10 text-white/50"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex-shrink-0 flex flex-col gap-2 text-sm text-white/50">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>{filesAnalyzed?.toLocaleString() || 0} files</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              <span>{totalFindings || 0} findings</span>
            </div>
            {analysisDuration && (
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>{formatDuration(analysisDuration)}</span>
              </div>
            )}
            {completedAt && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>{new Date(completedAt).toLocaleDateString()}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

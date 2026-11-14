import { motion } from "framer-motion"
import {
  GitBranch, GitCommit, Files, FolderTree,
  List, Shield, Code2, Clock, Activity, BarChart3,
  ScanSearch, Layers, Sparkles,
} from "lucide-react"

import { cn, formatDuration, getRelativeTime } from "../../lib/utils"

interface RepositoryStatsProps {
  repoName: string
  filesCount: number
  directoriesCount?: number
  findingsCount: number
  rulesCount: number
  technologiesCount: number
  scanDuration?: number
  completedAt?: string
  branch?: string
  commitHash?: string
  rawFindingsCount?: number
  aiSuggestionsCount?: number
  scannersCount?: number
}

const statItems = [
  { key: "files", icon: Files, label: "Files Scanned", color: "text-indigo-400", bg: "bg-indigo-500/10" },
  { key: "directories", icon: FolderTree, label: "Directories", color: "text-cyan-400", bg: "bg-cyan-500/10" },
  { key: "findings", icon: List, label: "Findings", color: "text-rose-400", bg: "bg-rose-500/10" },
  { key: "rawFindings", icon: BarChart3, label: "Raw Scanner Findings", color: "text-orange-400", bg: "bg-orange-500/10" },
  { key: "rules", icon: Shield, label: "Rules Executed", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  { key: "technologies", icon: Code2, label: "Technologies", color: "text-purple-400", bg: "bg-purple-500/10" },
  { key: "scanners", icon: ScanSearch, label: "Scanners", color: "text-sky-400", bg: "bg-sky-500/10" },
  { key: "aiSuggestions", icon: Sparkles, label: "AI Suggestions", color: "text-pink-400", bg: "bg-pink-500/10" },
  { key: "duration", icon: Clock, label: "Scan Duration", color: "text-amber-400", bg: "bg-amber-500/10" },
  { key: "scanned", icon: GitCommit, label: "Last Scanned", color: "text-blue-400", bg: "bg-blue-500/10" },
]

export function RepositoryStats({
  repoName, filesCount, directoriesCount, findingsCount,
  rulesCount, technologiesCount, scanDuration, completedAt, branch, commitHash,
  rawFindingsCount, aiSuggestionsCount, scannersCount,
}: RepositoryStatsProps) {
  const items = [
    { value: filesCount.toLocaleString(), display: statItems[0] },
    { value: directoriesCount != null ? directoriesCount.toLocaleString() : "—", display: statItems[1] },
    { value: findingsCount.toLocaleString(), display: statItems[2] },
    {
      value: rawFindingsCount != null ? rawFindingsCount.toLocaleString() : "—",
      display: statItems[3],
    },
    { value: rulesCount.toLocaleString(), display: statItems[4] },
    { value: technologiesCount.toString(), display: statItems[5] },
    { value: scannersCount != null ? String(scannersCount) : "—", display: statItems[6] },
    { value: aiSuggestionsCount != null ? String(aiSuggestionsCount) : "—", display: statItems[7] },
    { value: scanDuration != null ? formatDuration(scanDuration) : "—", display: statItems[8] },
    {
      value: (
        <span className="flex flex-col items-center gap-0.5">
          <span>{getRelativeTime(completedAt)}</span>
          {commitHash && (
            <span className="text-[9px] text-white/20 font-mono" title={commitHash}>
              {commitHash.slice(0, 7)}
            </span>
          )}
        </span>
      ),
      display: statItems[9]
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
            Repository Statistics
          </h3>
        </div>
        {branch && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] text-indigo-300">
            <GitBranch className="w-3 h-3" />
            {branch}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {items.map((item, i) => {
          const Icon = item.display.icon
          return (
            <motion.div
              key={item.display.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-center hover:border-white/10 transition-colors"
            >
              <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center mx-auto mb-2",
                item.display.bg
              )}>
                <Icon className={cn("w-4 h-4", item.display.color)} />
              </div>
              <div className="text-sm font-bold text-white/90 font-mono tabular-nums">
                {item.value}
              </div>
              <div className="text-[9px] text-white/30 mt-0.5 uppercase tracking-wider">
                {item.display.label}
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

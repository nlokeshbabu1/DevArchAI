import { motion } from "framer-motion"
import { FileCode } from "lucide-react"
import { memo } from "react"

import { cn, getFileName, getSeverityColor, sanitizePath } from "../../lib/utils"

interface TopAffectedFilesProps {
  topFiles: { file_path: string; findings_count: number; severities: Record<string, number> }[]
}

export const TopAffectedFiles = memo(function TopAffectedFiles({
  topFiles,
}: TopAffectedFilesProps) {
  if (!topFiles || topFiles.length === 0) { return null }

  const maxCount = topFiles[0]?.findings_count || 1

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 h-full"
    >
      <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">
        Top Affected Files
      </h3>

      <div className="space-y-2">
        {topFiles.slice(0, 8).map((file, i) => {
          const barPct = (file.findings_count / maxCount) * 100
          const hasHigh = (file.severities.critical || 0) > 0 || (file.severities.high || 0) > 0
          return (
            <motion.div
              key={file.file_path}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={cn(
                "rounded-lg border px-3 py-2 transition-all",
                hasHigh
                  ? "border-red-500/20 bg-red-500/5"
                  : "border-white/5 bg-white/[0.02]"
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <FileCode className={cn("w-3 h-3 shrink-0", hasHigh ? "text-red-400/60" : "text-white/20")} />
                <span className="text-xs text-white/70 truncate flex-1" title={sanitizePath(file.file_path)}>
                  {getFileName(file.file_path)}
                </span>
                <span className={cn(
                  "text-[10px] font-mono font-bold shrink-0",
                  hasHigh ? "text-red-400" : "text-white/40"
                )}>
                  {file.findings_count}
                </span>
              </div>
              <div className="flex items-center gap-1 ml-5">
                <div className="h-1 flex-1 rounded-full bg-white/5 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${barPct}%` }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className={cn("h-full rounded-full", hasHigh ? "bg-red-500/30" : "bg-white/10")}
                  />
                </div>
                {Object.entries(file.severities).map(([sev, count]) => {
                  if (count === 0) { return null }
                  const colors = getSeverityColor(sev)
                  return (
                    <span key={sev} className={cn("text-[9px] font-mono", colors.text)}>
                      {count} {sev}
                    </span>
                  )
                })}
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
})

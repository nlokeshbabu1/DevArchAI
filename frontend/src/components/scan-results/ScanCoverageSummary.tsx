import { motion } from "framer-motion"
import {
  FileText, FolderTree, Shield, Code2, Clock,
  LineChart, HardDrive, Activity, Cpu
} from "lucide-react"
import { cn, formatDuration } from "../../lib/utils"

interface ScanCoverageSummaryProps {
  filesScanned: number
  directoriesScanned?: number
  rulesExecuted: number
  technologiesCount: number
  scannersUsed?: number
  scanDuration?: number
  linesAnalyzed?: number
  repoSize?: string
}

const metrics = [
  { key: "files", icon: FileText, label: "Files Scanned", color: "text-indigo-400", bg: "bg-indigo-500/10" },
  { key: "directories", icon: FolderTree, label: "Directories", color: "text-cyan-400", bg: "bg-cyan-500/10" },
  { key: "rules", icon: Shield, label: "Rules Executed", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  { key: "technologies", icon: Code2, label: "Technologies", color: "text-purple-400", bg: "bg-purple-500/10" },
  { key: "scanners", icon: Cpu, label: "Scanners Used", color: "text-amber-400", bg: "bg-amber-500/10" },
  { key: "duration", icon: Clock, label: "Scan Duration", color: "text-rose-400", bg: "bg-rose-500/10" },
  { key: "size", icon: HardDrive, label: "Repository Size", color: "text-blue-400", bg: "bg-blue-500/10" },
]

export function ScanCoverageSummary({
  filesScanned, directoriesScanned, rulesExecuted,
  technologiesCount, scannersUsed, scanDuration, repoSize
}: ScanCoverageSummaryProps) {
  const items = [
    { value: filesScanned.toLocaleString(), display: metrics[0] },
    { value: directoriesScanned != null ? directoriesScanned.toLocaleString() : "—", display: metrics[1] },
    { value: rulesExecuted.toLocaleString(), display: metrics[2] },
    { value: technologiesCount.toString(), display: metrics[3] },
    { value: scannersUsed != null ? scannersUsed.toString() : "—", display: metrics[4] },
    { value: scanDuration != null ? formatDuration(scanDuration) : "—", display: metrics[5] },
    { value: repoSize || "—", display: metrics[6] },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-4 h-4 text-white/40" />
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Scan Coverage Summary
        </h3>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        {items.map((item, i) => {
          const Icon = item.display.icon
          return (
            <motion.div
              key={item.display.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
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

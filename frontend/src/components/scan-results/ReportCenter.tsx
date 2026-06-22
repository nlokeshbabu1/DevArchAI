import { motion } from "framer-motion"
import { Download, FileJson, FileText, Table, Shield, Share2, FileSpreadsheet, FileCode } from "lucide-react"
import { cn } from "../../lib/utils"
import { Button } from "../ui-animated"
import { useState } from "react"

interface ReportCenterProps {
  onDownload: (format: "pdf" | "excel" | "json" | "sarif") => void
  onShare?: () => void
}

const formats = [
  { id: "pdf" as const, label: "PDF Report", icon: FileText, desc: "Formatted security report", color: "text-red-400", bg: "bg-red-500/10" },
  { id: "excel" as const, label: "Excel", icon: FileSpreadsheet, desc: "Spreadsheet with findings", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  { id: "json" as const, label: "JSON", icon: FileJson, desc: "Machine-readable data", color: "text-yellow-400", bg: "bg-yellow-500/10" },
  { id: "sarif" as const, label: "SARIF", icon: FileCode, desc: "Static analysis results format", color: "text-indigo-400", bg: "bg-indigo-500/10" },
]

export function ReportCenter({ onDownload, onShare }: ReportCenterProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Report Center
        </h3>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        {formats.map((format, i) => {
          const Icon = format.icon
          return (
            <motion.button
              key={format.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onDownload(format.id)}
              className="rounded-xl border border-white/5 p-4 text-left transition-all duration-200 hover:border-white/20 bg-white/[0.02] hover:bg-white/[0.05]"
            >
              <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center mb-2", format.bg)}>
                <Icon className={cn("w-4 h-4", format.color)} />
              </div>
              <div className="text-sm font-medium text-white/70">{format.label}</div>
              <div className="text-[10px] text-white/30 mt-0.5">{format.desc}</div>
            </motion.button>
          )
        })}
      </div>

      <div className="flex items-center gap-3">
        {onShare && (
          <button
            onClick={onShare}
            className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/60 transition-colors"
          >
            <Share2 className="w-3.5 h-3.5" />
            Share Report
          </button>
        )}
      </div>
    </motion.div>
  )
}

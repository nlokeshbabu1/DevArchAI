import { useMemo } from "react"
import { motion } from "framer-motion"
import {
  Shield, Code2, Database, Lock, Server, Cloud,
  Globe, Braces, GanttChartSquare, ScanSearch, Bug,
  CheckCircle2, XCircle, Clock
} from "lucide-react"
import { cn, classifyFindingScanner, SCANNER_DEFINITIONS, getScannerStatus } from "../../lib/utils"

interface DetectionCoverageProps {
  findings: any[]
  detectedTechnologies: string[]
}

const scannerIcons: Record<string, typeof Shield> = {
  container: Cloud,
  kubernetes: Server,
  iac: GanttChartSquare,
  cicd: Globe,
  secrets: Lock,
  sast: Code2,
  sca: Database,
  dast: ScanSearch,
  api_security: Braces,
  license: Shield,
  malware: Bug,
}

function getScannerFindingsCount(findings: any[], scannerKey: string): number {
  return findings.filter(f => classifyFindingScanner(f) === scannerKey).length
}

export function DetectionCoverage({ findings = [], detectedTechnologies = [] }: DetectionCoverageProps) {
  const scannerEntries = useMemo(() => {
    return SCANNER_DEFINITIONS.map(def => {
      const status = getScannerStatus(def.key, detectedTechnologies)
      const matchingFindings = status === "active" ? getScannerFindingsCount(findings, def.key) : 0
      return { ...def, status, matchingFindings }
    })
  }, [findings, detectedTechnologies])

  const totalActive = scannerEntries.filter(s => s.status === "active").length
  const totalFindingsMapped = scannerEntries.reduce((s, e) => s + e.matchingFindings, 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
            Detection Coverage
          </h3>
        </div>
        <div className="flex items-center gap-2 text-xs text-white/30">
          <span>{totalActive} scanners active</span>
          <span className="text-white/10">|</span>
          <span>{totalFindingsMapped} findings mapped</span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2.5">
        {scannerEntries.map((entry, i) => {
          const Icon = scannerIcons[entry.key] || Shield
          const isActive = entry.status === "active"
          const isComingSoon = entry.status === "coming_soon"

          return (
            <motion.div
              key={entry.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className={cn(
                "rounded-xl border p-3 transition-all duration-200",
                isActive
                  ? "border-indigo-500/20 bg-indigo-500/[0.03] hover:border-indigo-500/30"
                  : isComingSoon
                    ? "border-amber-500/10 bg-amber-500/[0.02]"
                    : "border-white/5 bg-white/[0.02]"
              )}
            >
              {/* Header: icon + label */}
              <div className="flex items-center gap-2 mb-2">
                <div className={cn(
                  "w-7 h-7 rounded-lg flex items-center justify-center shrink-0",
                  isActive && entry.matchingFindings > 0
                    ? "bg-indigo-500/10"
                    : isActive
                      ? "bg-white/5"
                      : "bg-white/[0.02]"
                )}>
                  <Icon className={cn(
                    "w-3.5 h-3.5",
                    isActive && entry.matchingFindings > 0 ? "text-indigo-400" :
                    isActive ? "text-white/30" :
                    isComingSoon ? "text-amber-400/50" :
                    "text-white/20"
                  )} />
                </div>
                <span className={cn(
                  "text-[10px] font-semibold leading-tight",
                  isActive ? "text-white/70" :
                  isComingSoon ? "text-amber-300/60" :
                  "text-white/30"
                )}>
                  {entry.label}
                </span>
              </div>

              {/* Status badge */}
              <div className="mb-2">
                {isActive ? (
                  <span className={cn(
                    "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider",
                    entry.matchingFindings > 0
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-white/5 text-white/30"
                  )}>
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    Active
                  </span>
                ) : isComingSoon ? (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider bg-amber-500/10 text-amber-400/70">
                    <Clock className="w-2.5 h-2.5" />
                    Coming Soon
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider bg-white/5 text-white/25">
                    <XCircle className="w-2.5 h-2.5" />
                    Disabled
                  </span>
                )}
              </div>

              {/* Findings count (active scanners only) */}
              {isActive ? (
                <div>
                  <span className={cn(
                    "text-base font-bold font-mono tabular-nums",
                    entry.matchingFindings > 0 ? "text-white/90" : "text-white/20"
                  )}>
                    {entry.matchingFindings}
                  </span>
                  <div className="text-[9px] text-white/20 mt-0.5">
                    {entry.matchingFindings === 1 ? "finding" : "findings"}
                  </div>
                </div>
              ) : isComingSoon ? (
                <div className="text-[10px] text-amber-400/40 italic mt-1">
                  Not yet implemented
                </div>
              ) : (
                <div className="text-[10px] text-white/20 mt-1">
                  Not configured
                </div>
              )}
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

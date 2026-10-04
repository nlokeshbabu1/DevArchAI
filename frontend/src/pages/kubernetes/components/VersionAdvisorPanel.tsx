import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle, ArrowRight, CheckCircle2, ChevronDown, ChevronRight,
  Loader2, Shield, Zap,
} from 'lucide-react'
import { kubernetesApi, type ClusterAIJob } from '@/api/endpoints/kubernetes'
import { cn } from '@/lib/utils'

const RUNNING = new Set(['queued', 'running', 'collecting', 'checking_cache', 'rag_retrieving', 'mcp_retrieving', 'generating'])

interface Props {
  connectionId: string
  advisor: Record<string, unknown> | null
  onAdvisorUpdate?: (data: Record<string, unknown>) => void
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    blocking: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    compatible: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  }
  return (
    <span className={cn('text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border', colors[severity] || colors.medium)}>
      {severity}
    </span>
  )
}

function ScoreRing({ score }: { score: number }) {
  const color = score >= 75 ? 'text-emerald-400' : score >= 50 ? 'text-amber-400' : 'text-red-400'
  return (
    <div className="relative flex items-center justify-center w-20 h-20">
      <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/10" />
        <circle
          cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="2"
          strokeDasharray={`${score} 100`} strokeLinecap="round" className={color}
        />
      </svg>
      <span className={cn('absolute text-xl font-bold', color)}>{score}</span>
    </div>
  )
}

export function VersionAdvisorPanel({ connectionId, advisor, onAdvisorUpdate }: Props) {
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null)
  const [versionDetail, setVersionDetail] = useState<Record<string, unknown> | null>(null)
  const [upgradeJob, setUpgradeJob] = useState<ClusterAIJob | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [expandedPhase, setExpandedPhase] = useState<number | null>(null)
  const [showBreak, setShowBreak] = useState(false)

  const pathVersions = (advisor?.upgrade_path_versions as string[]) || (advisor?.recommended_sequence as string[]) || []
  const upgradeResult = upgradeJob?.status === 'completed' ? upgradeJob.result : null
  const display = upgradeResult ? { ...advisor, ...upgradeResult } : advisor

  const pollJob = useCallback((jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await kubernetesApi.getUpgradeAnalysis(connectionId, jobId)
        setUpgradeJob(job)
        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(interval)
          setAnalyzing(false)
          if (job.status === 'completed' && job.result) {
            onAdvisorUpdate?.(job.result as Record<string, unknown>)
          }
        }
      } catch {
        clearInterval(interval)
        setAnalyzing(false)
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [connectionId, onAdvisorUpdate])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const job = await kubernetesApi.startUpgradeAnalysis(connectionId)
      setUpgradeJob(job)
      pollJob(job.id)
    } catch {
      setAnalyzing(false)
    }
  }

  const handleVersionClick = async (version: string) => {
    setSelectedVersion(version)
    try {
      const detail = await kubernetesApi.versionAdvisor(connectionId, version)
      setVersionDetail(detail.version_detail as Record<string, unknown> || detail)
    } catch {
      setVersionDetail({ target_version: version, status: 'unavailable' })
    }
  }

  useEffect(() => {
    if (!advisor) return
    const versions = (advisor.upgrade_path_versions as string[]) || (advisor.recommended_sequence as string[])
    if (versions.length && !selectedVersion) {
      setSelectedVersion(versions[versions.length - 1])
    }
  }, [advisor, selectedVersion])

  if (!display) {
    return <p className="text-sm text-muted-foreground">Version information unavailable.</p>
  }

  const readinessScore = Number(display.readiness_score ?? 0)
  const blocking = (display.blocking_issues as Record<string, unknown>[]) || []
  const warnings = (display.warnings as Record<string, unknown>[]) || []
  const whatCouldBreak = display.what_could_break as { categories?: Record<string, unknown>[] } | undefined
  const upgradePlan = display.upgrade_plan as { phases?: Record<string, unknown>[] } | undefined
  const upgradePath = (display.upgrade_path as Record<string, unknown>[]) || []

  return (
    <div className="space-y-6">
      {/* Header metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-white/10 bg-card/60 p-4 flex items-center gap-4">
          <ScoreRing score={readinessScore} />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Readiness</div>
            <div className="text-sm font-medium mt-0.5">Score / 100</div>
            <SeverityBadge severity={String(display.risk || 'medium')} />
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Current</div>
          <div className="text-lg font-bold mt-1">{String(display.current_version)}</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Recommended</div>
          <div className="text-lg font-bold mt-1">{String(display.recommended_version)}</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Status</div>
          <div className="text-sm font-semibold mt-1 capitalize">{String(display.upgrade_status || '').replace(/_/g, ' ')}</div>
          <div className="text-xs text-muted-foreground mt-1">{String(display.impact_summary)}</div>
        </div>
      </div>

      {/* Analyze button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={analyzing}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          Analyze Upgrade
        </button>
        {analyzing && upgradeJob && (
          <span className="text-xs text-muted-foreground">
            {upgradeJob.status.replace(/_/g, ' ')}...
          </span>
        )}
        {upgradeJob?.status === 'failed' && (
          <span className="text-xs text-red-400">{upgradeJob.error_message || 'Analysis failed'}</span>
        )}
      </div>

      {/* Upgrade path */}
      {pathVersions.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <h3 className="text-sm font-semibold mb-3">Upgrade Path</h3>
          <div className="flex flex-wrap items-center gap-1">
            <button
              type="button"
              onClick={() => handleVersionClick(String(display.current_version))}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-mono border transition-colors',
                selectedVersion === display.current_version
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-white/10 hover:border-white/20',
              )}
            >
              {String(display.current_version)}
            </button>
            {pathVersions.map((v, i) => {
              const step = upgradePath[i]
              const stepStatus = step?.status as string || 'unknown'
              return (
                <div key={v} className="flex items-center gap-1">
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <button
                    type="button"
                    onClick={() => handleVersionClick(v)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-mono border transition-colors',
                      selectedVersion === v
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-white/10 hover:border-white/20',
                    )}
                  >
                    {v}
                    {step && (
                      <span className="ml-1.5">
                        {stepStatus === 'compatible' ? (
                          <CheckCircle2 className="inline h-3 w-3 text-emerald-400" />
                        ) : (
                          <AlertTriangle className="inline h-3 w-3 text-amber-400" />
                        )}
                      </span>
                    )}
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Version detail */}
      <AnimatePresence>
        {selectedVersion && versionDetail && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="rounded-xl border border-white/10 bg-card/60 p-4"
          >
            <h3 className="text-sm font-semibold mb-2">
              Impact Analysis: {selectedVersion}
            </h3>
            {versionDetail.status === 'analysis_required' ? (
              <p className="text-xs text-muted-foreground">Run Analyze Upgrade for detailed compatibility data.</p>
            ) : (
              <div className="space-y-2 text-xs">
                <div className="flex gap-2 items-center">
                  <span className="text-muted-foreground">Status:</span>
                  <SeverityBadge severity={String(versionDetail.status || versionDetail.risk || 'unknown')} />
                </div>
                {((versionDetail.breaking_changes as string[]) || []).map((c, i) => (
                  <div key={i} className="text-muted-foreground">• {c}</div>
                ))}
                {((versionDetail.recommended_remediation as string[]) || []).map((r, i) => (
                  <div key={i} className="text-emerald-400/80">→ {r}</div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Issues summary */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            Blocking ({blocking.length})
          </h3>
          {blocking.length === 0 ? (
            <p className="text-xs text-muted-foreground">No blocking issues detected</p>
          ) : (
            <div className="space-y-2">
              {blocking.slice(0, 5).map((b, i) => (
                <div key={i} className="text-xs border border-red-500/20 rounded-lg p-2 bg-red-500/5">
                  <div className="font-medium">{String(b.api || b.name)}</div>
                  <div className="text-muted-foreground">{String(b.reason || b.migration || '')}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Shield className="h-4 w-4 text-amber-400" />
            Warnings ({warnings.length})
          </h3>
          {warnings.length === 0 ? (
            <p className="text-xs text-muted-foreground">No warnings</p>
          ) : (
            <div className="space-y-2">
              {warnings.slice(0, 5).map((w, i) => (
                <div key={i} className="text-xs border border-amber-500/20 rounded-lg p-2 bg-amber-500/5">
                  <div className="font-medium">{String(w.api || w.name)}</div>
                  <div className="text-muted-foreground">{String(w.reason || w.migration || '')}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* What Could Break */}
      {whatCouldBreak?.categories && whatCouldBreak.categories.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <button
            type="button"
            onClick={() => setShowBreak(!showBreak)}
            className="flex items-center gap-2 text-sm font-semibold w-full"
          >
            {showBreak ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            What Could Break?
          </button>
          <AnimatePresence>
            {showBreak && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 space-y-2">
                {whatCouldBreak.categories.map((cat, i) => (
                  <div key={i} className="rounded-lg border border-white/10 p-3 text-xs">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium capitalize">{String(cat.category)}</span>
                      <SeverityBadge severity={String(cat.severity)} />
                    </div>
                    <div className="text-muted-foreground">{String(cat.explanation)}</div>
                    <div className="text-emerald-400/80 mt-1">→ {String(cat.recommended_action)}</div>
                    <div className="text-muted-foreground mt-0.5">{Number(cat.affected_count)} affected</div>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Upgrade Plan */}
      {upgradePlan?.phases && upgradePlan.phases.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-card/60 p-4">
          <h3 className="text-sm font-semibold mb-3">Recommended Upgrade Plan</h3>
          <div className="space-y-2">
            {upgradePlan.phases.map((phase) => {
              const p = Number(phase.phase)
              const isOpen = expandedPhase === p
              return (
                <div key={p} className="border border-white/10 rounded-lg overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setExpandedPhase(isOpen ? null : p)}
                    className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-white/5"
                  >
                    {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    <span className="font-medium">Phase {p}: {String(phase.title)}</span>
                    {phase.blocking && <SeverityBadge severity="blocking" />}
                  </button>
                  {isOpen && (
                    <div className="px-3 pb-3 text-xs text-muted-foreground space-y-1">
                      <p>{String(phase.description)}</p>
                      <ul className="list-disc list-inside mt-2">
                        {((phase.checklist as string[]) || []).map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

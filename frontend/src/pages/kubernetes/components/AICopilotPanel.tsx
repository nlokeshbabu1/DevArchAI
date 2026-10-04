import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Brain, ChevronDown, ChevronRight, Loader2, MessageSquare, Search,
} from 'lucide-react'
import { kubernetesApi, type ClusterAIJob } from '@/api/endpoints/kubernetes'
import { cn } from '@/lib/utils'

const RUNNING = new Set(['queued', 'running', 'collecting', 'checking_cache', 'rag_retrieving', 'mcp_retrieving', 'generating'])

interface Props {
  connectionId: string
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color = score >= 75 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{score}</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}

function SeveritySection({
  title,
  items,
  color,
}: {
  title: string
  items: Record<string, unknown>[]
  color: string
}) {
  const [open, setOpen] = useState(items.length > 0 && items.length <= 3)
  if (items.length === 0) return null
  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-white/5"
      >
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <span className={cn('font-medium', color)}>{title}</span>
        <span className="text-xs text-muted-foreground ml-auto">{items.length}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          {items.map((item, i) => (
            <div key={i} className="rounded-lg border border-white/10 p-3 text-xs space-y-1.5">
              <div className="font-semibold">{String(item.title || item.finding || item.issue)}</div>
              {item.affected_resource != null ? (
                <div className="text-muted-foreground font-mono">
                  {String(item.namespace)}{item.namespace ? '/' : ''}{String(item.affected_resource)}
                </div>
              ) : null}
              {item.explanation != null ? <div>{String(item.explanation)}</div> : null}
              {item.recommended_action != null ? (
                <div className="text-emerald-400/80">→ {String(item.recommended_action)}</div>
              ) : null}
              <div className="flex gap-3 text-muted-foreground">
                {item.confidence != null ? <span>Confidence: {String(item.confidence)}</span> : null}
                {item.source != null ? <span>Source: {String(item.source)}</span> : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function AICopilotPanel({ connectionId }: Props) {
  const [aiJob, setAiJob] = useState<ClusterAIJob | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<'copilot' | 'troubleshoot'>('copilot')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startPolling = useCallback((jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const updated = await kubernetesApi.getAiAnalysis(connectionId, jobId)
        setAiJob(updated)
        if (updated.status === 'completed' || updated.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current)
          pollRef.current = null
          setLoading(false)
        }
      } catch {
        if (pollRef.current) clearInterval(pollRef.current)
        pollRef.current = null
        setLoading(false)
      }
    }, 3000)
  }, [connectionId])

  useEffect(() => {
    kubernetesApi.getAiAnalysisLatest(connectionId).then((job) => {
      if (job) {
        setAiJob(job)
        if (RUNNING.has(job.status)) {
          setLoading(true)
          startPolling(job.id)
        }
      }
    }).catch(() => {})
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [connectionId, startPolling])

  const handleRun = async () => {
    setLoading(true)
    setError(null)
    try {
      const job = mode === 'troubleshoot' && question
        ? await kubernetesApi.startAiAnalysis(connectionId, { question, analysis_type: 'troubleshoot' })
        : await kubernetesApi.startAiAnalysis(connectionId, { analysis_type: 'copilot' })
      setAiJob(job)
      startPolling(job.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start analysis')
      setLoading(false)
    }
  }

  const result = aiJob?.result
  const healthScores = result?.health_scores as Record<string, number> | undefined
  const bySeverity = result?.findings_by_severity as Record<string, Record<string, unknown>[]> | undefined
  const troubleshoot = result?.root_cause != null

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => { setMode('copilot'); handleRun() }}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          {loading && mode === 'copilot' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
          Run Copilot Analysis
        </button>
        {loading && (
          <span className="text-xs text-muted-foreground">
            {aiJob?.status?.replace(/_/g, ' ') || 'Starting...'}
          </span>
        )}
      </div>

      {/* Troubleshoot input */}
      <div className="rounded-xl border border-white/10 bg-card/60 p-4 space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Troubleshooting Agent
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Why is payment-api failing?"
            className="flex-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm focus:outline-none focus:border-primary/50"
          />
          <button
            type="button"
            onClick={() => { setMode('troubleshoot'); handleRun() }}
            disabled={loading || !question.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 text-sm hover:bg-white/5 disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            Investigate
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {/* Health scores */}
      {healthScores ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-white/10 bg-card/60 p-4"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">Cluster Health</h3>
            <div className="text-2xl font-bold">{healthScores.overall}<span className="text-sm text-muted-foreground">/100</span></div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <ScoreBar label="Reliability" score={healthScores.reliability} />
            <ScoreBar label="Security" score={healthScores.security} />
            <ScoreBar label="Configuration" score={healthScores.configuration} />
            <ScoreBar label="Upgrade Readiness" score={healthScores.upgrade_readiness} />
          </div>
        </motion.div>
      ) : null}

      {/* Troubleshoot result */}
      {troubleshoot ? (
        <div className="rounded-xl border border-white/10 bg-card/60 p-4 space-y-3">
          <h3 className="text-sm font-semibold">Investigation Result</h3>
          <div className="text-xs space-y-2">
            <div><span className="text-muted-foreground">Root Cause:</span> {String(result?.root_cause)}</div>
            <div><span className="text-muted-foreground">Confidence:</span> {String(result?.confidence)}</div>
            {result?.recommended_fix != null ? (
              <div className="text-emerald-400/80">→ {String(result.recommended_fix)}</div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Findings by severity */}
      {bySeverity ? (
        <div className="space-y-2">
          <SeveritySection title="Critical" items={bySeverity.critical || []} color="text-red-400" />
          <SeveritySection title="High" items={bySeverity.high || []} color="text-orange-400" />
          <SeveritySection title="Medium" items={bySeverity.medium || []} color="text-amber-400" />
          <SeveritySection title="Informational" items={bySeverity.informational || []} color="text-muted-foreground" />
        </div>
      ) : null}

      {aiJob?.status === 'completed' && !bySeverity && !troubleshoot && result?.summary != null ? (
        <p className="text-sm">{String(result.summary)}</p>
      ) : null}

      {aiJob?.status === 'failed' && (
        <div className="space-y-2">
          <p className="text-sm text-red-400">{aiJob.error_message || 'Analysis failed'}</p>
          <button type="button" onClick={handleRun} className="text-xs text-primary hover:underline">Retry</button>
        </div>
      )}

      {!aiJob && !loading && (
        <p className="text-sm text-muted-foreground">
          Run Copilot Analysis for evidence-based cluster recommendations, or ask a troubleshooting question.
        </p>
      )}
    </div>
  )
}

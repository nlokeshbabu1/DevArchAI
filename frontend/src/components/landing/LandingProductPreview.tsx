import { motion, useReducedMotion } from 'framer-motion'
import { AlertTriangle, Brain, CheckCircle2, Sparkles } from 'lucide-react'
import { memo } from 'react'

import demoData from '../../data/demoScan.json'
import { cn } from '../../lib/utils'

const severityStyles: Record<string, string> = {
  critical: 'bg-red-500/15 text-red-300 border-red-500/25',
  high: 'bg-orange-500/15 text-orange-300 border-orange-500/25',
  medium: 'bg-amber-500/15 text-amber-200 border-amber-500/25',
  low: 'bg-sky-500/15 text-sky-300 border-sky-500/25',
  info: 'bg-slate-500/15 text-slate-300 border-slate-500/25',
}

/** Compact preview for hero column — uses sanitized demo scan JSON */
export const HeroProductPreview = memo(function HeroProductPreview() {
  const reduced = useReducedMotion()
  const topFindings = demoData.findings.slice(0, 2)
  const counts = demoData.severity_counts

  return (
    <motion.div
      className="relative w-full max-w-lg mx-auto lg:mx-0 lg:ml-auto"
      initial={reduced ? undefined : { opacity: 0, y: 20 }}
      animate={reduced ? undefined : { opacity: 1, y: 0 }}
      transition={{ duration: 0.55, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
      aria-label="Example scan results preview"
    >
      <div className="rounded-2xl border border-white/[0.1] bg-[#0a0f1e]/90 shadow-[0_32px_64px_-24px_rgba(0,0,0,0.65)] overflow-hidden">
        <div className="flex items-center gap-2 border-b border-white/[0.08] px-4 py-2.5 bg-white/[0.02]">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" aria-hidden />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" aria-hidden />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" aria-hidden />
          <span className="ml-2 text-[11px] font-mono text-slate-500 truncate">
            {demoData.repository_name} · scan results
          </span>
        </div>

        <div className="p-4 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs text-slate-500">Security score (example)</p>
              <p className="text-2xl font-semibold text-white tabular-nums">{demoData.security_score}</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(['critical', 'high', 'medium'] as const).map((sev) => (
                <span
                  key={sev}
                  className={cn('rounded-md border px-2 py-0.5 text-[10px] font-medium uppercase', severityStyles[sev])}
                >
                  {sev} {counts[sev]}
                </span>
              ))}
            </div>
          </div>

          <ul className="space-y-2">
            {topFindings.map((f) => (
              <li
                key={f.rule_id}
                className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3"
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-orange-300 shrink-0 mt-0.5" aria-hidden />
                  <div className="min-w-0">
                    <p className="text-xs font-mono text-slate-500">{f.rule_id}</p>
                    <p className="text-sm font-medium text-white truncate">{f.rule_name}</p>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-0.5">{f.description}</p>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/[0.06] p-3 flex gap-2">
            <Brain className="h-4 w-4 text-indigo-300 shrink-0" aria-hidden />
            <div>
              <p className="text-xs font-medium text-indigo-200">AI remediation (eligible findings)</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Suggestions run after the scan completes; informational items stay visible without LLM analysis.
              </p>
            </div>
          </div>
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-slate-500">Illustrative UI — sample data from product demo</p>
    </motion.div>
  )
})

export function LandingProductPreview() {
  const reduced = useReducedMotion()
  const findings = demoData.findings.slice(0, 4)

  return (
    <section id="product-preview" className="py-16 lg:py-24 scroll-mt-20" aria-labelledby="product-preview-heading">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-10 max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 mb-4">
            <Sparkles className="h-3.5 w-3.5 text-violet-400" aria-hidden />
            <span className="text-xs font-medium text-slate-300">Product preview</span>
          </div>
          <h2 id="product-preview-heading" className="display-lg text-white mb-3">
            Results you can act on — immediately
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            Connect a repository, watch real scan progress, and review severities, rule IDs, and AI suggestions in
            the same dashboard you use after sign-up.
          </p>
        </div>

        <motion.div
          className="mx-auto max-w-5xl rounded-2xl border border-white/[0.1] bg-[#0a0f1e]/80 overflow-hidden"
          initial={reduced ? undefined : { opacity: 0, y: 24 }}
          whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="grid lg:grid-cols-[220px_1fr] border-b border-white/[0.08]">
            <aside className="p-5 border-b lg:border-b-0 lg:border-r border-white/[0.08] bg-white/[0.02]">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Example scan</p>
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-slate-500 text-xs">Repository</dt>
                  <dd className="text-white font-medium">{demoData.repository_name}</dd>
                </div>
                <div>
                  <dt className="text-slate-500 text-xs">Branch</dt>
                  <dd className="text-slate-300">{demoData.branch}</dd>
                </div>
                <div>
                  <dt className="text-slate-500 text-xs">Status</dt>
                  <dd className="flex items-center gap-1.5 text-emerald-300">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                    Completed
                  </dd>
                </div>
              </dl>
              <p className="mt-4 text-[11px] text-slate-500 leading-relaxed">
                Sanitized demo dataset — no private repo names or tokens.
              </p>
            </aside>
            <div className="p-5 sm:p-6">
              <motion.ul className="space-y-3" role="list">
                {findings.map((f) => (
                  <li
                    key={f.rule_id}
                    className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className={cn('rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase', severityStyles[f.severity])}>
                        {f.severity}
                      </span>
                      <span className="text-xs font-mono text-slate-500">{f.rule_id}</span>
                      {f.file_path && (
                        <span className="text-xs text-slate-500 truncate">{f.file_path}</span>
                      )}
                    </div>
                    <p className="text-sm font-semibold text-white">{f.rule_name}</p>
                    <p className="text-sm text-slate-400 mt-1 leading-relaxed">{f.description}</p>
                  </li>
                ))}
              </motion.ul>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
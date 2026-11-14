import { motion } from 'framer-motion'
import {
  ArrowRight, Brain, Check, FileText, GitPullRequest, Search, Shield, Sparkles,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { formatConfigLimits, type ProductConfig } from '../../hooks/useProductConfig'
import { Button } from '../ui-animated'

const INCLUDED = [
  { icon: Search, text: 'Repository scanning and findings explorer' },
  { icon: Brain, text: 'Full AI suggestions and remediation (no blur)' },
  { icon: GitPullRequest, text: 'Pull request automation when permissions allow' },
  { icon: FileText, text: 'Reports and exports within configured limits' },
  { icon: Shield, text: 'Same security and authorization as production' },
]

type BetaAccessSectionProps = {
  config: ProductConfig
}

export function BetaAccessSection({ config }: BetaAccessSectionProps) {
  const navigate = useNavigate()
  const limits = formatConfigLimits(config.limits)
  const title = config.beta_label || 'DevArchAI Beta — Free Access'

  return (
    <section className="py-16 lg:py-24" aria-labelledby="beta-access-heading">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-4xl mx-auto">
          <motion.div
            className="text-center mb-10 space-y-4"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500/10 border border-cyan-500/25">
              <Sparkles className="h-4 w-4 text-cyan-300" aria-hidden />
              <span className="text-sm font-medium text-cyan-200">{title}</span>
            </div>
            <h2 id="beta-access-heading" className="display-lg text-white">
              Build and scan during Beta — no payment required
            </h2>
            <p className="text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
              Register for free access to scanning, AI analysis, remediation, and reports. Usage stays within
              server-enforced limits configured for the Beta program.
            </p>
          </motion.div>

          <motion.div
            className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6 sm:p-8 mb-8"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-40px' }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <h3 className="text-lg font-semibold text-white mb-4">What&apos;s included</h3>
            <ul className="grid sm:grid-cols-2 gap-3 mb-6">
              {INCLUDED.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-start gap-2.5 text-sm text-slate-300">
                  <Check className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" aria-hidden />
                  <span>{text}</span>
                </li>
              ))}
            </ul>

            {limits.length > 0 && (
              <>
                <h4 className="text-sm font-semibold text-slate-200 mb-3">Current Beta limits</h4>
                <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {limits.map(({ label, value }) => (
                    <div
                      key={label}
                      className="rounded-xl border border-white/[0.06] bg-black/20 px-3 py-2.5"
                    >
                      <dt className="text-[11px] uppercase tracking-wide text-slate-500">{label}</dt>
                      <dd className="text-lg font-semibold text-white tabular-nums">{value}</dd>
                    </div>
                  ))}
                </dl>
              </>
            )}

            <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
              <Button
                variant="primary"
                size="lg"
                className="btn-premium h-[50px] px-7"
                onClick={() => navigate('/register')}
              >
                Join Beta — Create account
                <ArrowRight className="h-4 w-4 ml-1.5" />
              </Button>
              <Button
                variant="secondary"
                size="lg"
                className="btn-secondary-premium h-[50px] px-7"
                onClick={() => navigate('/scan')}
              >
                Try a scan
              </Button>
            </div>
          </motion.div>

          <motion.div
            className="p-6 rounded-2xl bg-primary/[0.04] border border-primary/15"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
          >
            <h3 className="text-lg font-bold text-white text-center mb-2">AI remediation during Beta</h3>
            <p className="text-sm text-slate-400 text-center max-w-2xl mx-auto leading-relaxed">
              Beta accounts receive full AI fix visibility and remediation workflows subject to the same authentication
              and repository permissions as paid plans. No upgrade is required to unlock fixes during the Beta program.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

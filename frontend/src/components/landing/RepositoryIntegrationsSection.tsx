import { motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, Cloud, Github, GitBranch, Shield } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { COMING_SOON_CLOUD, VERIFIED_INTEGRATIONS } from '../../lib/supported-capabilities'
import { Button } from '../ui-animated'

const ICONS: Record<string, typeof Github> = {
  github: Github,
  gitlab: GitBranch,
  aws: Cloud,
}

export function RepositoryIntegrationsSection() {
  const reduced = useReducedMotion()
  const navigate = useNavigate()

  return (
    <section id="integrations" className="py-16 lg:py-24 scroll-mt-20" aria-labelledby="integrations-heading">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center mb-10">
          <p className="text-sm font-medium text-violet-400 mb-3">Integrations</p>
          <h2 id="integrations-heading" className="display-lg text-white mb-3">
            Connect repositories and cloud accounts
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            OAuth and scoped permissions only — DevArchAI reads repository content to scan; tokens are not shown in the
            UI. Review permissions on the integrations screen before connecting.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3 max-w-4xl mx-auto mb-8">
          {VERIFIED_INTEGRATIONS.map((item, index) => {
            const Icon = ICONS[item.id] ?? Shield
            return (
              <motion.div
                key={item.id}
                className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5"
                initial={reduced ? undefined : { opacity: 0, y: 12 }}
                whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.06, duration: 0.4 }}
              >
                <Icon className="h-6 w-6 text-cyan-300 mb-3" aria-hidden />
                <h3 className="text-base font-semibold text-white">{item.name}</h3>
                <p className="text-sm text-slate-400 mt-1">{item.blurb}</p>
                <p className="mt-3 text-xs text-emerald-400/90 font-medium">Available</p>
              </motion.div>
            )
          })}
        </div>

        <motion.div
          className="max-w-4xl mx-auto rounded-2xl border border-indigo-500/20 bg-indigo-500/[0.04] p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
          initial={reduced ? undefined : { opacity: 0, y: 12 }}
          whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div>
            <p className="text-sm font-semibold text-white">Cloud expansions</p>
            <p className="text-sm text-slate-400 mt-1">
              {COMING_SOON_CLOUD.map((c) => c.name).join(' and ')} match the &quot;Coming soon&quot; entries in app
              navigation — not marketed as live integrations.
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="shrink-0"
            onClick={() => navigate('/integrations')}
          >
            Manage integrations
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </motion.div>
      </div>
    </section>
  )
}
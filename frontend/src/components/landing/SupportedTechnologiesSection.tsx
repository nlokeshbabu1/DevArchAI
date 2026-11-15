import { motion, useReducedMotion } from 'framer-motion'
import { memo } from 'react'

import { TECHNOLOGY_SHOWCASE, type ShowcaseItem } from '../../lib/supported-capabilities'
import { cn } from '../../lib/utils'

function kindLabel(kind: ShowcaseItem['kind']): string | null {
  switch (kind) {
    case 'scan_engine':
      return 'Scanner'
    case 'integration':
      return 'Integration'
    case 'iac_detection':
      return 'Detection'
    case 'coming_soon':
      return 'Coming soon'
    default:
      return null
  }
}

const TechTile = memo(function TechTile({ item }: { item: ShowcaseItem }) {
  const Icon = item.icon
  const badge = kindLabel(item.kind)
  const muted = item.kind === 'coming_soon'

  return (
    <div
      className={cn(
        'flex gap-3 rounded-xl border p-3.5 transition-colors',
        muted
          ? 'border-white/[0.06] bg-white/[0.02] opacity-80'
          : 'border-white/[0.08] bg-white/[0.03] hover:border-cyan-500/25 hover:bg-white/[0.04]',
      )}
    >
      <div
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border',
          muted ? 'border-white/[0.06] bg-white/[0.03]' : 'border-cyan-500/20 bg-cyan-500/[0.08]',
        )}
      >
        <Icon className={cn('h-5 w-5', muted ? 'text-slate-500' : 'text-cyan-300')} aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-white">{item.name}</p>
          {badge && (
            <span
              className={cn(
                'rounded-md px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide',
                item.kind === 'coming_soon'
                  ? 'bg-indigo-500/15 text-indigo-300'
                  : 'bg-white/[0.06] text-slate-400',
              )}
            >
              {badge}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{item.blurb}</p>
      </div>
    </div>
  )
})

export function SupportedTechnologiesSection() {
  const reduced = useReducedMotion()

  return (
    <section id="technologies" className="py-16 lg:py-24 scroll-mt-20" aria-labelledby="technologies-heading">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 max-w-3xl text-center">
          <p className="mb-3 text-sm font-medium text-cyan-400/90">Supported technologies</p>
          <h2 id="technologies-heading" className="display-lg text-white mb-4">
            What DevArchAI actually scans
          </h2>
          <p className="text-base text-slate-400 leading-relaxed">
            Verified repository, IaC, and integration coverage — grouped by capability. Scan engines are listed
            separately so they are not confused with the platforms you deploy.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-2">
          {TECHNOLOGY_SHOWCASE.map((category, catIndex) => (
            <motion.article
              key={category.id}
              className="rounded-2xl border border-white/[0.08] bg-[#0c1224]/60 p-6 shadow-[0_24px_80px_-40px_rgba(0,0,0,0.8)]"
              initial={reduced ? undefined : { opacity: 0, y: 16 }}
              whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.45, delay: catIndex * 0.05, ease: [0.16, 1, 0.3, 1] }}
            >
              <h3 className="text-lg font-semibold text-white">{category.title}</h3>
              <p className="mt-1 mb-4 text-sm text-slate-400 leading-relaxed">{category.description}</p>
              <ul className="grid gap-2 sm:grid-cols-2">
                {category.items.map((item) => (
                  <li key={item.id}>
                    <TechTile item={item} />
                  </li>
                ))}
              </ul>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  )
}
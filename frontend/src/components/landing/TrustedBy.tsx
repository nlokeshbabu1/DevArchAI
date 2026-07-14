import { motion } from 'framer-motion'

const logos = [
  { name: 'Terraform', abbr: 'TF' },
  { name: 'Kubernetes', abbr: 'K8s' },
  { name: 'Docker', abbr: 'DK' },
  { name: 'GitHub Actions', abbr: 'GH' },
  { name: 'AWS', abbr: 'AWS' },
  { name: 'Azure', abbr: 'AZ' },
  { name: 'GitLab', abbr: 'GL' },
  { name: 'Helm', abbr: 'HM' },
]

export function TrustedBy() {
  return (
    <section className="py-12 border-y border-white/[0.04]" aria-label="Trusted by leading platforms">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <motion.p
          className="text-center text-sm text-slate-400 mb-8"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Supports the tools you already use
        </motion.p>

        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {logos.map((logo, index) => (
            <motion.div
              key={logo.name}
              className="flex items-center gap-2 text-slate-400/60 hover:text-slate-400 transition-colors duration-200"
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.05, duration: 0.4 }}
            >
              <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-xs font-mono font-medium">
                {logo.abbr}
              </div>
              <span className="text-sm font-medium">{logo.name}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
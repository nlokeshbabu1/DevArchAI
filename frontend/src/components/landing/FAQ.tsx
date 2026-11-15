import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { useState, memo } from 'react'

const faqs = [
  {
    question: 'How does DevArchAI detect security issues?',
    answer: 'DevArchAI parses your infrastructure-as-code files (Terraform, Kubernetes, Docker, CI/CD configs) and evaluates them against 500+ security rules covering CIS benchmarks, OWASP guidelines, and cloud provider best practices. The AI layer adds context-aware analysis that understands your specific infrastructure.',
  },
  {
    question: 'What technologies and frameworks are supported?',
    answer: 'DevArchAI scans Terraform, Kubernetes, Helm charts, Docker, GitHub Actions, GitLab CI, Jenkins pipeline files, and related dependencies with Checkov, Trivy, Gitleaks, and other registered scanners. AWS cloud integration is available today; Azure and GCP integrations are marked Coming Soon in the product navigation.',
  },
  {
    question: 'How long does a scan take?',
    answer: 'Most repositories complete scanning in under 30 seconds. Larger repositories with many files may take up to 2 minutes. The scan runs entirely in our secure infrastructure — no code leaves your repository.',
  },
  {
    question: 'Is my code stored or shared?',
    answer: 'No. Your code is read-only scanned and never stored permanently. We fetch your repository, analyze the files, generate results, and immediately discard the source code. Only the scan findings and metadata are retained for your dashboard.',
  },
  {
    question: 'Can I use DevArchAI in my CI/CD pipeline?',
    answer: 'Repository scans analyze GitHub Actions, GitLab CI, and Jenkins files in your codebase. Use the dashboard or API to run scans on push; native CI marketplace actions are evolving — check documentation for the current integration path.',
  },
  {
    question: 'What is the difference between Free, Plus, and Pro?',
    answer: 'Free gives you 3 scans per month with basic results. Plus ($12/mo) unlocks AI remediation suggestions, PDF reports, and 50 scans. Pro ($29/mo) adds unlimited scans, SARIF/JSON exports, GitHub PR automation, and API access.',
  },
]

const FaqItem = memo(function FaqItem({
  faq, isOpen, onToggle,
}: {
  faq: typeof faqs[0]; isOpen: boolean; onToggle: () => void
}) {
  return (
    <div className="border-b border-white/[0.06] last:border-0">
      <button
        className="flex items-center justify-between w-full py-5 text-left group"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="text-base font-medium text-white pr-4 group-hover:text-primary transition-colors duration-200">
          {faq.question}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="flex-shrink-0"
        >
          <ChevronDown className="h-5 w-5 text-slate-400" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <p className="pb-5 text-sm text-slate-400 leading-relaxed">
              {faq.answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
})

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  return (
    <section className="py-16 lg:py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12">
          {/* Left: Header */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <p className="text-sm font-medium text-primary mb-3">FAQ</p>
              <h2 className="display-lg text-white mb-4">
                Common questions
              </h2>
              <p className="text-base text-slate-400 max-w-lg leading-relaxed">
                Everything you need to know about getting started with DevArchAI.
              </p>
            </motion.div>
          </div>

          {/* Right: FAQ List */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          >
            {faqs.map((faq, index) => (
              <FaqItem
                key={faq.question}
                faq={faq}
                isOpen={openIndex === index}
                onToggle={() => setOpenIndex(openIndex === index ? null : index)}
              />
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
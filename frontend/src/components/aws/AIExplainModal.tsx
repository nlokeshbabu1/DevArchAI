import { Check, Copy, Loader2, X } from 'lucide-react'
import { useState } from 'react'

import { AwsFindingExplanation } from '../../api/endpoints/aws'
import { copyToClipboard } from '../../lib/utils'
import { Button } from '../ui'

function CodeBlock({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    await copyToClipboard(value)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className="relative rounded-lg border border-white/10 bg-black/30">
      <button
        type="button"
        onClick={copy}
        className="absolute right-2 top-2 rounded-md border border-white/10 bg-white/5 p-1.5 text-muted-foreground transition hover:text-foreground"
        aria-label="Copy code"
      >
        {copied ? <Check className="h-4 w-4 text-green-300" /> : <Copy className="h-4 w-4" />}
      </button>
      <pre className="max-h-72 overflow-auto p-4 pr-12 text-xs leading-6 text-blue-100">
        <code>{value}</code>
      </pre>
    </div>
  )
}

export function AIExplainModal({
  explanation,
  loading,
  error,
  onClose,
}: {
  explanation: AwsFindingExplanation | null
  loading: boolean
  error: string | null
  onClose: () => void
}) {
  if (!loading && !explanation && !error) {return null}

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-xl border border-white/10 bg-card shadow-2xl shadow-black/60">
        <div className="flex items-start justify-between gap-4 border-b border-white/10 p-5">
          <div>
            <p className="text-xs uppercase tracking-wide text-primary">AI Explanation</p>
            <h2 className="mt-1 text-xl font-semibold text-foreground">
              {explanation?.title || 'Generating explanation...'}
            </h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-muted-foreground transition hover:bg-white/5 hover:text-foreground" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="max-h-[calc(88vh-88px)] overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-5 text-sm text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              Generating explanation...
            </div>
          ) : error ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</div>
          ) : explanation ? (
            <div className="space-y-5">
              <section>
                <h3 className="font-semibold text-foreground">Overview</h3>
                <p className="mt-2 text-sm text-muted-foreground">{explanation.summary}</p>
              </section>
              <section>
                <h3 className="font-semibold text-foreground">Risk</h3>
                <p className="mt-2 text-sm text-muted-foreground">{explanation.risk}</p>
              </section>
              <section>
                <h3 className="font-semibold text-foreground">Attack Scenario</h3>
                <p className="mt-2 text-sm text-muted-foreground">{explanation.attack_scenario}</p>
              </section>
              <section>
                <h3 className="font-semibold text-foreground">Fix Steps</h3>
                <ol className="mt-2 space-y-2 text-sm text-muted-foreground">
                  {explanation.fix_steps.map((step, index) => <li key={step}>{index + 1}. {step}</li>)}
                </ol>
              </section>
              <section>
                <h3 className="mb-2 font-semibold text-foreground">AWS CLI</h3>
                <CodeBlock value={explanation.cli_commands.join('\n')} />
              </section>
              <section>
                <h3 className="mb-2 font-semibold text-foreground">Terraform</h3>
                <CodeBlock value={explanation.terraform_example} />
              </section>
              <section>
                <h3 className="font-semibold text-foreground">Best Practices</h3>
                <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
                  {explanation.best_practices.map((item) => <li key={item}>- {item}</li>)}
                </ul>
              </section>
              <div className="flex justify-end border-t border-white/10 pt-4">
                <Button variant="secondary" onClick={onClose}>Close</Button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { AwsAccount } from '../../api/endpoints/aws'
import { cn } from '../../lib/utils'

const stages = [
  ['validating credentials', 8],
  ['collecting inventory', 35],
  ['analyzing IAM', 55],
  ['checking security', 70],
  ['calculating costs', 88],
  ['generating recommendations', 100],
] as const

export function AwsScanProgressModal({ account }: { account?: AwsAccount }) {
  if (!account || !['queued', 'running', 'failed'].includes(account.scan_status)) return null
  const failed = account.scan_status === 'failed'
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-white/10 bg-card p-6 shadow-2xl shadow-black/50">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">AWS scan {failed ? 'failed' : 'in progress'}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{account.last_error || 'Polling scan progress with live stage visibility.'}</p>
          </div>
          {failed ? <XCircle className="h-6 w-6 text-red-300" /> : <Loader2 className="h-6 w-6 animate-spin text-blue-300" />}
        </div>
        <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/10">
          <div className={cn('h-full rounded-full transition-all', failed ? 'bg-red-400' : 'bg-blue-400')} style={{ width: `${account.scan_progress}%` }} />
        </div>
        <div className="mt-5 space-y-3">
          {stages.map(([label, threshold]) => {
            const done = account.scan_progress >= threshold && !failed
            const active = account.scan_progress < threshold && account.scan_progress >= threshold - 20 && !failed
            return (
              <div key={label} className="flex items-center gap-3 text-sm">
                {done ? <CheckCircle2 className="h-4 w-4 text-green-300" /> : active ? <Loader2 className="h-4 w-4 animate-spin text-blue-300" /> : <span className="h-4 w-4 rounded-full border border-white/20" />}
                <span className={cn('capitalize', done ? 'text-foreground' : 'text-muted-foreground')}>{label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

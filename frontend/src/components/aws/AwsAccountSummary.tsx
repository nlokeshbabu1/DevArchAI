import { ChevronDown, Cloud, Eye, Loader2, Play, Power, RefreshCw } from 'lucide-react'
import { AwsAccount } from '../../api/endpoints/aws'
import { Button } from '../ui'
import { cn } from '../../lib/utils'

function formatDate(value?: string | null) {
  if (!value) return 'Not scanned'
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function accountTag(account: AwsAccount) {
  const source = `${account.account_alias || ''} ${account.account_id}`.toLowerCase()
  if (source.includes('prod')) return 'Production'
  if (source.includes('stage')) return 'Staging'
  if (source.includes('dev')) return 'Development'
  return 'Sandbox'
}

export function AwsAccountSummary({
  account,
  accounts,
  totalResources,
  lastUpdated,
  onSelect,
  onRefresh,
  onScan,
  onDisconnect,
  onExpandConnect,
  busy,
}: {
  account: AwsAccount
  accounts: AwsAccount[]
  totalResources: number
  lastUpdated?: string | null
  onSelect: (accountId: string) => void
  onRefresh: () => void
  onScan: () => void
  onDisconnect: () => void
  onExpandConnect: () => void
  busy: boolean
}) {
  const scanning = account.scan_status === 'queued' || account.scan_status === 'running'
  return (
    <div className="rounded-xl border border-white/10 bg-card/70 p-5 shadow-2xl shadow-black/20">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <div className="rounded-lg border border-amber-300/30 bg-amber-400/10 p-3">
            <Cloud className="h-6 w-6 text-amber-300" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-xl font-semibold text-foreground">{account.account_alias || account.account_id}</h2>
              <span className="rounded-full border border-primary/30 bg-primary/15 px-2.5 py-1 text-xs font-medium text-primary">{accountTag(account)}</span>
              <span className={cn('rounded-full border px-2.5 py-1 text-xs font-medium capitalize', scanning ? 'border-blue-400/30 bg-blue-500/10 text-blue-200' : account.scan_status === 'failed' ? 'border-red-500/30 bg-red-500/10 text-red-200' : 'border-green-500/30 bg-green-500/10 text-green-200')}>
                {scanning && <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />}
                {account.scan_status}
              </span>
            </div>
            <div className="mt-3 grid gap-3 text-sm text-muted-foreground sm:grid-cols-2 xl:grid-cols-4">
              <span>Account ID: <strong className="text-foreground">{account.account_id}</strong></span>
              <span>Region: <strong className="text-foreground">{account.default_region}</strong></span>
              <span>Resources: <strong className="text-foreground">{totalResources}</strong></span>
              <span>Last sync: <strong className="text-foreground">{formatDate(lastUpdated || account.last_scanned_at)}</strong></span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {accounts.length > 1 && (
            <div className="relative">
              <select className="input min-w-[220px] appearance-none pr-9" value={account.id} onChange={(event) => onSelect(event.target.value)}>
                {accounts.map((item) => <option key={item.id} value={item.id}>{item.account_alias || item.account_id}</option>)}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </div>
          )}
          <Button variant="secondary" onClick={onScan} disabled={busy || scanning}><Play className="mr-2 h-4 w-4" />Scan Now</Button>
          <Button variant="secondary" onClick={onRefresh} disabled={busy}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
          <Button variant="secondary" onClick={onExpandConnect}><Eye className="mr-2 h-4 w-4" />Details</Button>
          <Button variant="secondary" onClick={onDisconnect} disabled={busy}><Power className="mr-2 h-4 w-4" />Disconnect</Button>
        </div>
      </div>
    </div>
  )
}

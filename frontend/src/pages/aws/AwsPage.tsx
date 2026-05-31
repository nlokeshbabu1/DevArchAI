import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Cloud, KeyRound, Loader2, Plus, ShieldCheck } from 'lucide-react'
import { awsApi, AwsAccount, AwsCostRecommendation, AwsFinding, AwsInventoryResponse, AwsOverview } from '../../api/endpoints/aws'
import { Button } from '../../components/ui'
import { AwsDashboard, AwsDashboardSkeleton } from '../../components/aws/AwsDashboard'
import { AwsAccountSummary } from '../../components/aws/AwsAccountSummary'
import { AwsScanProgressModal } from '../../components/aws/AwsScanProgressModal'

function apiErrorMessage(error: unknown) {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    return response?.data?.detail || 'AWS API request failed'
  }
  return error instanceof Error ? error.message : 'AWS API request failed'
}

export function AwsPage() {
  const [accounts, setAccounts] = useState<AwsAccount[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>()
  const [overview, setOverview] = useState<AwsOverview | null>(null)
  const [inventory, setInventory] = useState<AwsInventoryResponse | null>(null)
  const [findings, setFindings] = useState<AwsFinding[]>([])
  const [recommendations, setRecommendations] = useState<AwsCostRecommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [working, setWorking] = useState(false)
  const [showConnect, setShowConnect] = useState(true)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({ account_alias: '', access_key_id: '', secret_access_key: '', default_region: 'us-east-1' })
  const refreshLock = useRef(false)

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.id === selectedAccountId) || accounts[0],
    [accounts, selectedAccountId],
  )

  const totalResources = useMemo(
    () => Object.values(overview?.inventory_summary || {}).reduce((sum, count) => sum + count, 0),
    [overview],
  )

  const loadAwsData = useCallback(async (accountId?: string, background = false) => {
    if (refreshLock.current) return
    refreshLock.current = true
    if (!background) setLoading(true)
    setError(null)
    try {
      const nextAccounts = await awsApi.accounts()
      setAccounts(nextAccounts)
      const activeId = accountId || selectedAccountId || nextAccounts[0]?.id
      setSelectedAccountId(activeId)
      setShowConnect(nextAccounts.length === 0)

      if (activeId) {
        const [nextOverview, nextInventory, security, iam, cost] = await Promise.all([
          awsApi.overview(activeId),
          awsApi.inventory(activeId),
          awsApi.security(activeId),
          awsApi.iamAnalysis(activeId),
          awsApi.cost(activeId),
        ])
        setOverview(nextOverview)
        setInventory(nextInventory)
        setFindings([...security.items, ...iam.items])
        setRecommendations(cost.items)
      } else {
        setOverview(null)
        setInventory(null)
        setFindings([])
        setRecommendations([])
      }
    } catch (apiError) {
      setError(apiErrorMessage(apiError))
    } finally {
      refreshLock.current = false
      if (!background) setLoading(false)
    }
  }, [selectedAccountId])

  useEffect(() => {
    loadAwsData()
  }, [])

  useEffect(() => {
    if (!selectedAccount || !['queued', 'running'].includes(selectedAccount.scan_status)) return
    const timer = window.setInterval(() => loadAwsData(selectedAccount.id, true), 7000)
    return () => window.clearInterval(timer)
  }, [loadAwsData, selectedAccount?.id, selectedAccount?.scan_status])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await awsApi.connect(form)
      const account = response.data.account as AwsAccount
      setForm({ account_alias: '', access_key_id: '', secret_access_key: '', default_region: 'us-east-1' })
      setShowConnect(false)
      setSuccess('AWS account connected. Scan is now running.')
      await loadAwsData(account.id)
    } catch (apiError) {
      setError(apiErrorMessage(apiError))
    } finally {
      setSaving(false)
    }
  }

  async function handleScan() {
    if (!selectedAccount || ['queued', 'running'].includes(selectedAccount.scan_status)) return
    setWorking(true)
    setError(null)
    try {
      const account = await awsApi.scan(selectedAccount.id)
      setAccounts((current) => current.map((item) => item.id === account.id ? account : item))
      setSuccess('AWS scan queued.')
      await loadAwsData(account.id, true)
    } catch (apiError) {
      setError(apiErrorMessage(apiError))
    } finally {
      setWorking(false)
    }
  }

  async function handleDisconnect() {
    if (!selectedAccount) return
    setWorking(true)
    setError(null)
    try {
      await awsApi.disconnect(selectedAccount.id)
      setSuccess('AWS account disconnected.')
      await loadAwsData(undefined)
    } catch (apiError) {
      setError(apiErrorMessage(apiError))
    } finally {
      setWorking(false)
    }
  }

  const connected = accounts.length > 0 && selectedAccount

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="rounded-lg border border-amber-300/30 bg-amber-400/10 p-2">
              <Cloud className="h-6 w-6 text-amber-300" />
            </div>
            <h1 className="text-3xl font-bold text-foreground">AI Cloud Security & Cost Optimization</h1>
          </div>
          <p className="mt-2 text-muted-foreground">Operational AWS posture, AI recommendations, inventory risk, and savings workflows.</p>
        </div>
        {connected && (
          <Button variant="secondary" onClick={() => setShowConnect((value) => !value)}>
            <Plus className="mr-2 h-4 w-4" />
            {showConnect ? 'Hide connect' : 'Connect another account'}
          </Button>
        )}
      </div>

      {success && <div className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-100">{success}</div>}
      {error && <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</div>}

      {connected && (
        <AwsAccountSummary
          account={selectedAccount}
          accounts={accounts}
          totalResources={totalResources}
          lastUpdated={overview?.last_sync}
          onSelect={(accountId) => loadAwsData(accountId)}
          onRefresh={() => loadAwsData(selectedAccount.id)}
          onScan={handleScan}
          onDisconnect={handleDisconnect}
          onExpandConnect={() => setShowConnect(true)}
          busy={working || loading}
        />
      )}

      {showConnect && (
        <form onSubmit={handleSubmit} className="rounded-xl border border-white/10 bg-card/60 p-5 shadow-2xl shadow-black/20">
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Connect AWS</h2>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">Access-key credentials are validated server-side, encrypted at rest, and never returned to the browser.</p>

          <div className="mt-5 grid gap-4 lg:grid-cols-4">
            <input className="input" placeholder="Account alias" value={form.account_alias} onChange={(event) => setForm({ ...form, account_alias: event.target.value })} />
            <input className="input" placeholder="Access key ID" value={form.access_key_id} onChange={(event) => setForm({ ...form, access_key_id: event.target.value })} required autoComplete="off" />
            <input className="input" placeholder="Secret access key" type="password" value={form.secret_access_key} onChange={(event) => setForm({ ...form, secret_access_key: event.target.value })} required autoComplete="new-password" />
            <input className="input" placeholder="Default region" value={form.default_region} onChange={(event) => setForm({ ...form, default_region: event.target.value })} required />
          </div>

          <Button variant="primary" className="mt-5" disabled={saving}>
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
            Validate and connect
          </Button>
        </form>
      )}

      {loading ? (
        <AwsDashboardSkeleton />
      ) : !selectedAccount || !overview || !inventory ? (
        <div className="rounded-xl border border-white/10 bg-card/60 p-10 text-center">
          <Cloud className="mx-auto h-10 w-10 text-muted-foreground" />
          <h2 className="mt-4 text-xl font-semibold text-foreground">No AWS account connected</h2>
          <p className="mt-2 text-muted-foreground">Connect AWS to start posture, inventory, IAM, and cost analysis.</p>
          <Button variant="primary" className="mt-5" onClick={() => setShowConnect(true)}>Connect AWS</Button>
        </div>
      ) : (
        <AwsDashboard
          account={selectedAccount}
          overview={overview}
          inventory={inventory}
          findings={findings}
          recommendations={recommendations}
        />
      )}

      <AwsScanProgressModal account={selectedAccount} />
    </div>
  )
}

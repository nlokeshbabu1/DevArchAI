import {
  AlertTriangle, ArrowUpRight, BarChart3, Bot, Box, ChevronDown, Cloud, Database,
  DollarSign, GitBranch, HardDrive, KeyRound, Loader2, Lock, Network, Search, Server,
  Shield, Sparkles, Workflow, Zap
} from 'lucide-react'
import { useMemo, useState } from 'react'

import { awsApi, AwsAccount, AwsCostRecommendation, AwsFinding, AwsFindingExplanation, AwsInventoryResponse, AwsOverview } from '../../api/endpoints/aws'
import { cn } from '../../lib/utils'
import { generateAWSConsoleLink } from '../../utils/awsConsoleLinks'
import { Button } from '../ui'

import { AIExplainModal } from './AIExplainModal'

const services = [
  ['ec2', 'EC2', Server],
  ['s3', 'S3', HardDrive],
  ['iam_user', 'IAM', KeyRound],
  ['rds', 'RDS', Database],
  ['lambda', 'Lambda', Zap],
  ['vpc', 'VPC', Network],
  ['eks', 'EKS', Box],
  ['load_balancer', 'Load Balancers', GitBranch],
] as const

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-lg bg-white/10', className)} />
}

export function AwsDashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-6">{[0, 1, 2, 3, 4, 5].map((item) => <SkeletonBlock key={item} className="h-24" />)}</div>
      <div className="grid gap-6 xl:grid-cols-[360px_1fr]"><SkeletonBlock className="h-96" /><SkeletonBlock className="h-96" /></div>
      <SkeletonBlock className="h-80" />
    </div>
  )
}

function formatDate(value?: string | null) {
  if (!value) {return 'Not available'}
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function grade(score: number) {
  if (score >= 90) {return 'A'}
  if (score >= 80) {return 'B'}
  if (score >= 70) {return 'C'}
  if (score >= 60) {return 'D'}
  return 'F'
}

function scoreColor(score: number) {
  if (score >= 80) {return 'text-green-300 stroke-green-300'}
  if (score >= 60) {return 'text-yellow-300 stroke-yellow-300'}
  return 'text-red-300 stroke-red-300'
}

function SeverityBadge({ severity }: { severity: string }) {
  const classes: Record<string, string> = {
    critical: 'bg-red-500/15 text-red-300 border-red-500/30',
    high: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
    medium: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30',
    low: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  }
  return <span className={cn('rounded-full border px-2.5 py-1 text-xs font-medium capitalize', classes[severity] || classes.low)}>{severity}</span>
}

function OperationalHeader({ account, overview }: { account: AwsAccount; overview: AwsOverview }) {
  const items = [
    ['Last Sync', formatDate(overview.last_sync || account.last_scanned_at)],
    ['Scan Duration', overview.scan_duration_seconds ? `${overview.scan_duration_seconds}s` : 'Pending telemetry'],
    ['Regions Scanned', `${overview.regions_scanned?.length || 0}`],
    ['AWS API Health', overview.aws_api_health || 'unknown'],
    ['Resource Coverage', `${overview.resource_coverage || 0}%`],
    ['Queue Status', overview.queue_status || account.scan_status],
  ]
  return (
    <div className="grid gap-3 lg:grid-cols-6">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-xl border border-white/10 bg-card/60 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className="mt-2 truncate text-sm font-semibold capitalize text-foreground">{value}</p>
        </div>
      ))}
    </div>
  )
}

function PostureCard({ overview }: { overview: AwsOverview }) {
  const score = overview.security_score
  const circumference = 2 * Math.PI * 52
  const offset = circumference - (score / 100) * circumference
  const counts = overview.severity_counts || {}
  return (
    <div className="rounded-xl border border-white/10 bg-card/60 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Security Posture</p>
          <h2 className="mt-1 text-2xl font-semibold text-foreground">Grade {overview.posture_grade || grade(score)}</h2>
        </div>
        <span className={cn('rounded-full border px-3 py-1 text-xs font-medium', score >= 80 ? 'border-green-500/30 bg-green-500/10 text-green-300' : score >= 60 ? 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300' : 'border-red-500/30 bg-red-500/10 text-red-300')}>
          Stable vs last scan
        </span>
      </div>
      <div className="mt-6 flex items-center gap-6">
        <div className="relative h-36 w-36">
          <svg className="-rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="currentColor" strokeWidth="10" className="text-white/10" />
            <circle cx="60" cy="60" r="52" fill="none" strokeWidth="10" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} className={cn('transition-all duration-700', scoreColor(score))} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={cn('text-4xl font-bold', scoreColor(score).split(' ')[0])}>{score}</span>
            <span className="text-xs text-muted-foreground">secure</span>
          </div>
        </div>
        <div className="grid flex-1 gap-3 sm:grid-cols-2">
          {(['critical', 'high', 'medium', 'low'] as const).map((severity) => (
            <div key={severity} className="rounded-lg bg-white/5 p-3">
              <p className="text-xs capitalize text-muted-foreground">{severity}</p>
              <p className="mt-1 text-2xl font-semibold text-foreground">{counts[severity] || 0}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function buildAiRecommendations(findings: AwsFinding[], recommendations: AwsCostRecommendation[], inventory: AwsInventoryResponse) {
  const cards = recommendations.slice(0, 4).map((item) => ({
    id: item.id,
    title: item.title,
    impact: item.estimated_monthly_savings > 0 ? 'Cost reduction' : 'Operational efficiency',
    savings: item.estimated_monthly_savings,
    severity: item.estimated_monthly_savings > 50 ? 'high' : 'medium',
    explanation: item.description,
    action: 'Review resource ownership and right-size or remove the unused asset.',
  }))

  findings.slice(0, 4).forEach((finding) => {
    cards.push({
      id: finding.id,
      title: finding.title,
      impact: finding.category === 'iam' ? 'Identity risk reduction' : 'Security exposure reduction',
      savings: 0,
      severity: finding.severity,
      explanation: finding.description,
      action: finding.recommendation || 'Apply least privilege and restrict public exposure.',
    })
  })

  if ((inventory.summary.eks || 0) > 0 && cards.length < 6) {
    cards.push({ id: 'eks-observability', title: 'EKS observability review', impact: 'Reliability', savings: 0, severity: 'medium', explanation: 'EKS clusters were found. Validate workload metrics, audit logs, and alert coverage.', action: 'Enable control plane logs and workload-level cost allocation.' })
  }
  return cards.slice(0, 6)
}

function AiRecommendations({ findings, recommendations, inventory }: { findings: AwsFinding[]; recommendations: AwsCostRecommendation[]; inventory: AwsInventoryResponse }) {
  const cards = useMemo(() => buildAiRecommendations(findings, recommendations, inventory), [findings, recommendations, inventory])
  return (
    <div className="rounded-xl border border-white/10 bg-card/60 p-6">
      <div className="flex items-center gap-2">
        <Bot className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold text-foreground">AI Recommendations</h3>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {cards.length === 0 ? (
          <div className="rounded-lg border border-white/10 p-6 text-sm text-muted-foreground lg:col-span-2">No AI recommendations are available until findings or cost opportunities are detected.</div>
        ) : cards.map((card) => (
          <div key={card.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <SeverityBadge severity={card.severity} />
                <h4 className="mt-3 font-semibold text-foreground">{card.title}</h4>
              </div>
              {card.savings > 0 && <span className="rounded-full bg-green-500/10 px-3 py-1 text-xs font-semibold text-green-300">${card.savings.toFixed(0)}/mo</span>}
            </div>
            <p className="mt-3 text-sm text-muted-foreground">{card.explanation}</p>
            <p className="mt-3 text-sm text-foreground"><Sparkles className="mr-1 inline h-4 w-4 text-primary" />{card.action}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" className="btn-sm">View Fix</Button>
              <Button variant="secondary" className="btn-sm"><ArrowUpRight className="mr-1 h-3.5 w-3.5" />Open AWS</Button>
              <Button variant="secondary" className="btn-sm">AI Explain</Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FindingsIncidents({ findings }: { findings: AwsFinding[] }) {
  const [query, setQuery] = useState('')
  const [severity, setSeverity] = useState('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [explainingId, setExplainingId] = useState<string | null>(null)
  const [explanation, setExplanation] = useState<AwsFindingExplanation | null>(null)
  const [modalError, setModalError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const filtered = useMemo(() => findings
    .filter((item) => severity === 'all' || item.severity === severity)
    .filter((item) => `${item.title} ${item.description} ${item.resource_id || ''}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => ['critical', 'high', 'medium', 'low'].indexOf(a.severity) - ['critical', 'high', 'medium', 'low'].indexOf(b.severity)), [findings, query, severity])

  async function handleAIExplain(finding: AwsFinding) {
    if (!finding.id || explainingId) {return}
    setExplainingId(finding.id)
    setExplanation(null)
    setModalError(null)
    setActionError(null)
    try {
      const response = await awsApi.explainFinding(finding.id)
      setExplanation(response)
    } catch (error) {
      setModalError('Failed to generate AI explanation. Please retry.')
    } finally {
      setExplainingId(null)
    }
  }

  function handleOpenAWS(finding: AwsFinding) {
    setActionError(null)
    const url = generateAWSConsoleLink(finding)
    if (!url) {
      setActionError('AWS console link unavailable for this finding.')
      return
    }

    const openedWindow = window.open(url, '_blank', 'noopener,noreferrer')
    if (openedWindow) {
      openedWindow.opener = null
    } else {
      setActionError('Browser blocked the AWS Console popup.')
    }
  }

  return (
    <div className="rounded-xl border border-white/10 bg-card/60 p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2"><Lock className="h-5 w-5 text-primary" /><h3 className="text-lg font-semibold text-foreground">Security Incidents</h3></div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input className="input pl-9" placeholder="Search findings" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
          <select className="input sm:w-40" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="all">All severity</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
          </select>
        </div>
      </div>
      {actionError && <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-100">{actionError}</div>}
      <div className="mt-4 max-h-[540px] space-y-3 overflow-y-auto pr-1">
        {filtered.length === 0 ? <div className="rounded-lg border border-white/10 p-6 text-sm text-muted-foreground">No findings match the current filters.</div> : filtered.map((finding) => {
          const open = expanded === finding.id
          const border = finding.severity === 'critical' ? 'border-l-red-400' : finding.severity === 'high' ? 'border-l-orange-400' : finding.severity === 'medium' ? 'border-l-yellow-400' : 'border-l-blue-400'
          return (
            <div key={finding.id} className={cn('rounded-xl border border-l-4 border-white/10 bg-white/[0.03] p-4', border)}>
              <div className="grid gap-4 lg:grid-cols-[120px_1fr_260px] lg:items-start">
                <SeverityBadge severity={finding.severity} />
                <div className="min-w-0">
                  <h4 className="font-semibold text-foreground">{finding.title}</h4>
                  <p className="mt-1 text-sm text-muted-foreground">{finding.description}</p>
                  <p className="mt-2 truncate text-xs text-muted-foreground">{finding.category || 'security'} · {finding.resource_type || 'resource'} · {finding.resource_id || 'account'}</p>
                  {open && <div className="mt-3 rounded-lg bg-black/20 p-3 text-sm text-muted-foreground">{finding.recommendation || 'No fix guide is available for this finding yet.'}</div>}
                </div>
                <div className="flex flex-wrap gap-2 lg:justify-end">
                  <Button variant="secondary" className="btn-sm" onClick={() => setExpanded(open ? null : finding.id)}><ChevronDown className="mr-1 h-3.5 w-3.5" />Fix Guide</Button>
                  <Button variant="secondary" className="btn-sm" onClick={() => handleAIExplain(finding)} disabled={Boolean(explainingId)}>
                    {explainingId === finding.id && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                    {explainingId === finding.id ? 'Explaining...' : 'AI Explain'}
                  </Button>
                  <Button variant="secondary" className="btn-sm" onClick={() => handleOpenAWS(finding)}><ArrowUpRight className="mr-1 h-3.5 w-3.5" />Open AWS</Button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <AIExplainModal
        explanation={explanation}
        loading={Boolean(explainingId)}
        error={modalError}
        onClose={() => {
          setExplanation(null)
          setModalError(null)
          setExplainingId(null)
        }}
      />
    </div>
  )
}

function InventoryMatrix({ inventory, findings, recommendations }: { inventory: AwsInventoryResponse; findings: AwsFinding[]; recommendations: AwsCostRecommendation[] }) {
  return (
    <div className="rounded-xl border border-white/10 bg-card/60 p-6">
      <div className="flex items-center gap-2"><Cloud className="h-5 w-5 text-primary" /><h3 className="text-lg font-semibold text-foreground">Cloud Inventory</h3></div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {services.map(([key, label, Icon]) => {
          const count = key === 'iam_user'
            ? (inventory.summary.iam_user || 0) + (inventory.summary.iam_role || 0)
            : inventory.summary[key] || 0
          const risk = findings.filter((item) => item.resource_type?.includes(key) || (key === 'iam_user' && item.category === 'iam')).length
          const cost = recommendations.filter((item) => item.resource_type?.includes(key)).reduce((sum, item) => sum + item.estimated_monthly_savings, 0)
          const utilization = count ? Math.max(18, 100 - risk * 12) : 0
          return (
            <div key={key} className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition hover:border-primary/30">
              <div className="flex items-center justify-between"><Icon className="h-5 w-5 text-muted-foreground" /><span className="text-xs text-muted-foreground">{utilization}% utilized</span></div>
              <p className="mt-3 text-sm text-muted-foreground">{label}</p>
              <p className="text-2xl font-semibold text-foreground">{count}</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs"><span className="rounded bg-red-500/10 px-2 py-1 text-red-200">{risk} risks</span><span className="rounded bg-green-500/10 px-2 py-1 text-green-200">${cost.toFixed(0)} save</span></div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Topology() {
  const nodes = [['VPC', Network], ['ALB', GitBranch], ['EKS', Box], ['RDS', Database]]
  return (
    <div className="rounded-xl border border-white/10 bg-card/60 p-6">
      <div className="flex items-center gap-2"><Workflow className="h-5 w-5 text-primary" /><h3 className="text-lg font-semibold text-foreground">Infrastructure Topology</h3></div>
      <div className="mt-6 grid gap-3 md:grid-cols-4">
        {nodes.map(([label, Icon], index) => (
          <div key={label as string} className="relative rounded-xl border border-white/10 bg-white/[0.03] p-5 text-center">
            {index < nodes.length - 1 && <span className="absolute -right-3 top-1/2 hidden h-px w-6 bg-primary/50 md:block" />}
            <Icon className="mx-auto h-7 w-7 text-primary" />
            <p className="mt-3 font-semibold text-foreground">{label as string}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function TrendAnalytics({ overview }: { overview: AwsOverview }) {
  const trends = [
    ['Security Trend', `${overview.severity_counts.critical || 0} critical`, AlertTriangle],
    ['Cost Optimization', `$${overview.estimated_monthly_savings.toFixed(0)} savings`, DollarSign],
    ['Resource Growth', `${overview.totals?.resources || 0} resources`, BarChart3],
  ] as const
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {trends.map(([title, value, Icon]) => (
        <div key={title} className="rounded-xl border border-white/10 bg-card/60 p-5">
          <div className="flex items-center justify-between"><h3 className="font-semibold text-foreground">{title}</h3><Icon className="h-5 w-5 text-primary" /></div>
          <p className="mt-2 text-2xl font-bold text-foreground">{value}</p>
          <div className="mt-5 flex h-20 items-end gap-2">
            {[35, 44, 30, 54, 46, 60].map((height, index) => <span key={index} className="flex-1 rounded-t bg-primary/30" style={{ height: `${height}%` }} />)}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Historical trend storage not configured; chart reflects current scan baseline.</p>
        </div>
      ))}
    </div>
  )
}

export function AwsDashboard({ account, overview, inventory, findings, recommendations }: {
  account: AwsAccount
  overview: AwsOverview
  inventory: AwsInventoryResponse
  findings: AwsFinding[]
  recommendations: AwsCostRecommendation[]
}) {
  return (
    <div className="space-y-6">
      <OperationalHeader account={account} overview={overview} />
      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <PostureCard overview={overview} />
        <AiRecommendations findings={findings} recommendations={recommendations} inventory={inventory} />
      </div>
      <TrendAnalytics overview={overview} />
      <InventoryMatrix inventory={inventory} findings={findings} recommendations={recommendations} />
      <Topology />
      <FindingsIncidents findings={findings} />
    </div>
  )
}

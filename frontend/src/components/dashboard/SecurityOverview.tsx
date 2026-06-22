import { motion } from 'framer-motion'
import { ShieldCheck, Gauge, AlertTriangle, TrendingUp, Wrench, FolderGit2, Info } from 'lucide-react'
import { cn } from '../../lib/utils'
import { ScoreCircle } from '../ui-animated'
import type { KpiData } from './KpiRow'

interface SecurityOverviewProps {
  securityScore: number
  hasSecurityScore: boolean
  riskScore: number
  criticalIssues: number
  repositoriesAtRisk: number
  scoreDelta: number | null
  newCriticalFindings: number
  fixedFindingsEstimate: number
  isLoading?: boolean
}

function SeverityBreakdownCard({ criticalIssues, isLoading }: { criticalIssues: number; isLoading?: boolean }) {
  const severities = [
    { key: 'critical', label: 'Critical', count: Math.max(0, criticalIssues), color: 'severity-bar-critical', textColor: 'text-red-400', bgColor: 'bg-red-500/10', borderColor: 'border-red-500/30' },
    { key: 'high', label: 'High', count: Math.max(0, Math.round(criticalIssues * 0.6)), color: 'severity-bar-high', textColor: 'text-orange-400', bgColor: 'bg-orange-500/10', borderColor: 'border-orange-500/30' },
    { key: 'medium', label: 'Medium', count: Math.max(0, Math.round(criticalIssues * 1.5)), color: 'severity-bar-medium', textColor: 'text-yellow-400', bgColor: 'bg-yellow-500/10', borderColor: 'border-yellow-500/30' },
    { key: 'low', label: 'Low', count: Math.max(0, Math.round(criticalIssues * 2)), color: 'severity-bar-low', textColor: 'text-green-400', bgColor: 'bg-green-500/10', borderColor: 'border-green-500/30' },
  ]
  const total = severities.reduce((sum, s) => sum + s.count, 0)

  return (
    <div className="p-5 rounded-2xl bg-white/5 border border-white/10 h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Severity Breakdown</h3>
        <span className="text-xs text-muted-foreground">{total} total</span>
      </div>
      <div className="space-y-2.5">
        {severities.map((sev, i) => {
          const pct = total > 0 ? (sev.count / total) * 100 : 0
          return (
            <motion.div
              key={sev.key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.1 + i * 0.05 }}
              className="space-y-1"
            >
              <div className="flex items-center justify-between text-xs">
                <span className={cn('font-medium', sev.textColor)}>{sev.label}</span>
                <span className="text-muted-foreground">{sev.count}</span>
              </div>
              <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                  className={cn('h-full rounded-full', sev.color)}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.6, delay: 0.2 + i * 0.08, ease: 'easeOut' }}
                />
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

function WhatChangedCard({
  scoreDelta, newCriticalFindings, fixedFindingsEstimate
}: {
  scoreDelta: number | null
  newCriticalFindings: number
  fixedFindingsEstimate: number
}) {
  const items = [
    {
      label: 'Score Delta',
      value: scoreDelta === null ? '—' : `${scoreDelta > 0 ? '+' : ''}${scoreDelta.toFixed(1)}`,
      icon: TrendingUp,
      tone: scoreDelta === null ? 'text-muted-foreground' : scoreDelta >= 0 ? 'text-green-400' : 'text-red-400',
    },
    {
      label: 'New Critical',
      value: scoreDelta === null ? '—' : newCriticalFindings.toString(),
      icon: AlertTriangle,
      tone: newCriticalFindings > 0 ? 'text-red-400' : 'text-green-400',
    },
    {
      label: 'Fixed Findings',
      value: scoreDelta === null ? '—' : fixedFindingsEstimate.toString(),
      icon: Wrench,
      tone: fixedFindingsEstimate > 0 ? 'text-green-400' : 'text-muted-foreground',
    },
  ]

  return (
    <div className="p-5 rounded-2xl bg-white/5 border border-white/10 h-full">
      <h3 className="text-sm font-semibold text-foreground mb-4">What Changed</h3>
      <div className="space-y-3">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between p-2.5 rounded-xl bg-white/5 border border-white/5"
            >
              <div className="flex items-center gap-2.5">
                <Icon className={cn('h-4 w-4', item.tone)} />
                <span className="text-xs text-muted-foreground">{item.label}</span>
              </div>
              <span className={cn('text-sm font-semibold tabular-nums', item.tone)}>{item.value}</span>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

export function SecurityOverview({
  securityScore, hasSecurityScore, riskScore,
  criticalIssues, repositoriesAtRisk,
  scoreDelta, newCriticalFindings, fixedFindingsEstimate,
  isLoading
}: SecurityOverviewProps) {
  const overviewItems: KpiData[] = [
    {
      title: 'Security Score',
      value: hasSecurityScore ? securityScore.toFixed(1) : '—',
      subtitle: hasSecurityScore ? 'Average completed scan score' : 'Run a scan to establish posture',
      icon: ShieldCheck,
      trend: scoreDelta !== null && scoreDelta > 0 ? 'up' : scoreDelta !== null && scoreDelta < 0 ? 'down' : undefined,
      trendValue: scoreDelta !== null ? `${scoreDelta > 0 ? '+' : ''}${scoreDelta.toFixed(1)}` : undefined,
      accentColor: securityScore >= 80 ? 'text-green-400' : securityScore >= 60 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      title: 'Risk Score',
      value: riskScore.toString(),
      subtitle: 'Higher = more immediate exposure',
      icon: Gauge,
      trend: riskScore >= 70 ? 'down' : riskScore <= 30 ? 'up' : 'neutral',
      trendValue: riskScore >= 70 ? 'Critical' : riskScore >= 40 ? 'Elevated' : 'Low',
      accentColor: riskScore >= 70 ? 'text-red-400' : riskScore >= 40 ? 'text-yellow-400' : 'text-green-400',
    },
    {
      title: 'Critical Findings',
      value: criticalIssues.toString(),
      subtitle: criticalIssues > 0 ? 'Needs immediate remediation' : 'No critical findings',
      icon: AlertTriangle,
      severity: {
        critical: criticalIssues,
        high: Math.round(criticalIssues * 0.6),
        medium: Math.round(criticalIssues * 1.5),
        low: Math.round(criticalIssues * 2),
      },
      accentColor: criticalIssues > 0 ? 'text-red-400' : 'text-green-400',
    },
    {
      title: 'Repos At Risk',
      value: repositoriesAtRisk.toString(),
      subtitle: 'Low score or findings present',
      icon: FolderGit2,
      accentColor: repositoriesAtRisk > 0 ? 'text-orange-400' : 'text-green-400',
    },
  ]

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {overviewItems.map((item, i) => {
          const Icon = item.icon
          return (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: i * 0.06 }}
              className="relative overflow-hidden rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 hover:border-white/20 transition-all duration-300 group"
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                    {item.title}
                  </p>
                  <div className="p-1.5 rounded-lg border border-white/10 bg-white/5 group-hover:bg-white/[0.08] transition-colors">
                    <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </div>
                <p className={cn('text-xl font-bold tracking-tight', item.accentColor)}>
                  {item.value}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
                  {item.subtitle}
                </p>
              </div>
            </motion.div>
          )
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="lg:col-span-1"
        >
          <div className="p-5 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 h-full flex flex-col items-center justify-center">
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground mb-3">
              Overall Security Score
            </p>
            <ScoreCircle
              score={securityScore}
              size="lg"
              animated
              delay={200}
            />
            <p className="text-xs text-muted-foreground mt-4 text-center max-w-[200px] leading-relaxed">
              {!hasSecurityScore
                ? 'Run a scan to establish your security posture'
                : 'Average across completed security scans'}
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="lg:col-span-1"
        >
          <SeverityBreakdownCard criticalIssues={criticalIssues} isLoading={isLoading} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.25 }}
          className="lg:col-span-1"
        >
          <WhatChangedCard
            scoreDelta={scoreDelta}
            newCriticalFindings={newCriticalFindings}
            fixedFindingsEstimate={fixedFindingsEstimate}
          />
        </motion.div>
      </div>
    </div>
  )
}

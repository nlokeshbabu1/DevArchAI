import { motion } from 'framer-motion'
import { Box, Shield, DollarSign, AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react'
import type { CloudOverview as CloudOverviewData } from '@/api/endpoints/cloud'

interface Props {
  data: CloudOverviewData
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/10 border-red-500/30',
  high: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  low: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
}

function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={radius} fill="none" stroke="currentColor" strokeWidth="6" className="text-white/5" />
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={color}
            style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold text-foreground">{Math.round(score)}</span>
        </div>
      </div>
      <span className="text-xs text-muted-foreground font-medium">{label}</span>
    </div>
  )
}

export function CloudOverview({ data }: Props) {
  const { connection, resource_summary, finding_summary, cost_summary, compliance_results, security_score } = data

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Score Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <ScoreCard
          icon={Box}
          label="Total Resources"
          value={resource_summary.total.toLocaleString()}
          subtext={`${Object.keys(resource_summary.by_service).length} services`}
          color="text-blue-400"
        />
        <ScoreCard
          icon={Shield}
          label="Security Findings"
          value={finding_summary.total.toLocaleString()}
          subtext={`${finding_summary.by_severity.critical || 0} critical`}
          color="text-orange-400"
        />
        <ScoreCard
          icon={DollarSign}
          label="Potential Savings"
          value={`$${(cost_summary.total_monthly_savings || 0).toFixed(0)}`}
          subtext={`${cost_summary.total} recommendations`}
          color="text-green-400"
        />
        <ScoreCard
          icon={CheckCircle}
          label="Compliance Score"
          value={`${compliance_results.length > 0 ? Math.round(compliance_results.reduce((a, c) => a + c.score, 0) / compliance_results.length) : 100}%`}
          subtext={`${compliance_results.length} frameworks`}
          color="text-purple-400"
        />
      </div>

      {/* Score Rings + Severity */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-6 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-semibold text-foreground mb-4">Security & Cost Scores</h3>
          <div className="flex items-center justify-around">
            <ScoreRing score={security_score || 0} label="Security" color="text-orange-400" />
            <ScoreRing
              score={Math.min(100, cost_summary.total > 0 ? 60 : 100)}
              label="Cost"
              color="text-green-400"
            />
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-semibold text-foreground mb-4">Findings by Severity</h3>
          <div className="space-y-2">
            {['critical', 'high', 'medium', 'low'].map((severity) => {
              const count = finding_summary.by_severity[severity] || 0
              const maxCount = Math.max(...Object.values(finding_summary.by_severity), 1)
              return (
                <div key={severity} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-16 capitalize">{severity}</span>
                  <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(count / maxCount) * 100}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                      className={cn('h-full rounded-full', severity === 'critical' ? 'bg-red-500' : severity === 'high' ? 'bg-orange-500' : severity === 'medium' ? 'bg-yellow-500' : 'bg-blue-500')}
                    />
                  </div>
                  <span className="text-xs font-mono text-foreground w-8 text-right">{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Resource Breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-6 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-semibold text-foreground mb-4">Resources by Service</h3>
          <div className="space-y-2">
            {Object.entries(resource_summary.by_service)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 8)
              .map(([service, count]) => (
                <div key={service} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground uppercase">{service}</span>
                  <span className="text-xs font-mono text-foreground">{count}</span>
                </div>
              ))}
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-semibold text-foreground mb-4">Resources by Region</h3>
          <div className="space-y-2">
            {Object.entries(resource_summary.by_region)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 8)
              .map(([region, count]) => (
                <div key={region} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{region}</span>
                  <span className="text-xs font-mono text-foreground">{count}</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function ScoreCard({
  icon: Icon,
  label,
  value,
  subtext,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  subtext: string
  color: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-5 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-muted-foreground mb-1">{label}</p>
          <p className="text-2xl font-bold text-foreground">{value}</p>
          <p className="text-xs text-muted-foreground mt-1">{subtext}</p>
        </div>
        <div className={cn('p-2 rounded-xl', color.replace('text-', 'bg-').replace('400', '500/10'))}>
          <Icon className={cn('h-5 w-5', color)} />
        </div>
      </div>
    </motion.div>
  )
}

function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}

import { motion } from 'framer-motion'
import { ShieldCheck, AlertTriangle, TrendingUp, FolderGit2, Info } from 'lucide-react'
import { cn } from '../../lib/utils'
import { ScoreCircle } from '../ui-animated'
import type { KpiData } from './KpiRow'

interface SecurityOverviewProps {
  securityScore: number
  hasSecurityScore: boolean
  criticalIssues: number
  repositoriesAtRisk: number
  scoreDelta: number | null
  isLoading?: boolean
}

export function SecurityOverview({
  securityScore, hasSecurityScore,
  criticalIssues, repositoriesAtRisk,
  scoreDelta, isLoading
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
      title: 'Critical Findings',
      value: criticalIssues.toString(),
      subtitle: criticalIssues > 0 ? 'Needs immediate remediation' : 'No critical findings',
      icon: AlertTriangle,
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
      <div className="grid gap-4 sm:grid-cols-3">
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

      <div className="grid gap-4 lg:grid-cols-1">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
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
      </div>
    </div>
  )
}

import { motion } from 'framer-motion'
import { FileCheck, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'

import { cloudApi, type CloudComplianceResult } from '@/api/endpoints/cloud'
import { cn } from '@/lib/utils'
import { useCloudStore } from '@/stores/cloud-store'

interface Props {
  connectionId: string
}

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-green-500' :
    score >= 60 ? 'bg-yellow-500' :
    score >= 40 ? 'bg-orange-500' :
    'bg-red-500'

  return (
    <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${score}%` }}
        transition={{ duration: 1, ease: 'easeOut' }}
        className={cn('h-full rounded-full', color)}
      />
    </div>
  )
}

export function ComplianceView({ connectionId }: Props) {
  const { compliance, setCompliance } = useCloudStore()
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await cloudApi.compliance(connectionId)
      setCompliance(data.results)
    } catch {
      // ignore
    }
    setLoading(false)
  }, [connectionId, setCompliance])

  useEffect(() => {
    load()
  }, [load])

  const avgScore = compliance.length > 0
    ? compliance.reduce((a, c) => a + c.score, 0) / compliance.length
    : 0

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-32 rounded-xl bg-card/60 border border-white/10 animate-pulse" />
        ))}
      </div>
    )
  }

  if (compliance.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <FileCheck className="h-10 w-10 text-muted-foreground mb-3" />
        <p className="text-sm text-muted-foreground">No compliance data yet. Run a scan to check compliance.</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Average Score */}
      <div className="p-6 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-4">
          <div className="relative w-20 h-20">
            <svg className="w-20 h-20 -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="6" className="text-white/5" />
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                strokeDasharray={2 * Math.PI * 40}
                strokeDashoffset={2 * Math.PI * 40 - (avgScore / 100) * 2 * Math.PI * 40}
                strokeLinecap="round"
                className={avgScore >= 80 ? 'text-green-400' : avgScore >= 60 ? 'text-yellow-400' : 'text-red-400'}
                style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xl font-bold text-foreground">{Math.round(avgScore)}%</span>
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Average Compliance Score</h3>
            <p className="text-xs text-muted-foreground">{compliance.length} framework{compliance.length !== 1 ? 's' : ''} evaluated</p>
          </div>
        </div>
      </div>

      {/* Framework Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {compliance.map((fw) => (
          <motion.div
            key={fw.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-5 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10"
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-foreground">{fw.framework}</h4>
              <span className={cn(
                'text-lg font-bold',
                fw.score >= 80 ? 'text-green-400' : fw.score >= 60 ? 'text-yellow-400' : 'text-red-400',
              )}>
                {Math.round(fw.score)}%
              </span>
            </div>

            <ScoreBar score={fw.score} />

            <div className="grid grid-cols-3 gap-3 mt-4">
              <div className="flex items-center gap-1.5">
                <CheckCircle className="h-3.5 w-3.5 text-green-400" />
                <span className="text-xs text-muted-foreground">{fw.passed} passed</span>
              </div>
              <div className="flex items-center gap-1.5">
                <XCircle className="h-3.5 w-3.5 text-red-400" />
                <span className="text-xs text-muted-foreground">{fw.failed} failed</span>
              </div>
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-yellow-400" />
                <span className="text-xs text-muted-foreground">{fw.warnings} warn</span>
              </div>
            </div>

            <p className="text-[10px] text-muted-foreground mt-3">
              {fw.total_controls} total control{fw.total_controls !== 1 ? 's' : ''}
            </p>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

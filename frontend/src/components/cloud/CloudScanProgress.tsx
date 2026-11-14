import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

interface Props {
  stage: string
  progress: number
}

const STAGE_LABELS: Record<string, string> = {
  initialize: 'Initializing',
  scan_resources: 'Scanning Resources',
  security_analysis: 'Security Analysis',
  cost_analysis: 'Cost Analysis',
  compliance_check: 'Compliance Check',
  finalize: 'Finalizing',
}

export function CloudScanProgress({ stage, progress }: Props) {
  const label = STAGE_LABELS[stage] || stage

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="p-4 rounded-2xl bg-blue-500/5 border border-blue-500/20"
    >
      <div className="flex items-center gap-3 mb-3">
        <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
        <span className="text-sm font-medium text-foreground">Scanning: {label}</span>
        <span className="text-xs text-muted-foreground ml-auto">{Math.round(progress)}%</span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
          className="h-full rounded-full bg-blue-500"
        />
      </div>
    </motion.div>
  )
}

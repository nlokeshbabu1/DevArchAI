import { motion } from 'framer-motion'
import { Brain, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { useEffect, useState, useRef } from 'react'
import { cn } from '../../lib/utils'

interface AIProgressBannerProps {
  scanId?: string
  onAIComplete?: () => void
}

export function AIProgressBanner({ scanId, onAIComplete }: AIProgressBannerProps) {
  const [status, setStatus] = useState<'processing' | 'completed' | 'failed'>('processing')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!scanId) return

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/scans/${scanId}`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        })
        const data = await res.json()
        if (data.ai_status === 'completed') {
          setStatus('completed')
          onAIComplete?.()
          if (pollRef.current) clearInterval(pollRef.current)
        } else if (data.ai_status === 'failed') {
          setStatus('failed')
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch {
        // ignore poll errors
      }
    }, 4000)

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [scanId, onAIComplete])

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6"
    >
      <div className={cn(
        'rounded-xl border p-4',
        status === 'processing' && 'border-indigo-500/30 bg-indigo-500/10',
        status === 'completed' && 'border-emerald-500/30 bg-emerald-500/10',
        status === 'failed' && 'border-red-500/30 bg-red-500/10',
      )}>
        <div className="flex items-center gap-3">
          {status === 'processing' && (
            <>
              <Brain className="h-5 w-5 text-indigo-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-indigo-300">Static scan is complete</div>
                <div className="text-xs text-indigo-300/60">
                  AI suggestions are still generating in the background. This page refreshes automatically.
                </div>
              </div>
              <Loader2 className="h-4 w-4 text-indigo-400 animate-spin shrink-0" />
            </>
          )}
          {status === 'completed' && (
            <>
              <CheckCircle className="h-5 w-5 text-emerald-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-emerald-300">AI analysis complete</div>
                <div className="text-xs text-emerald-300/60">
                  AI-powered suggestions and recommendations are now available.
                </div>
              </div>
            </>
          )}
          {status === 'failed' && (
            <>
              <AlertCircle className="h-5 w-5 text-red-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-red-300">AI analysis failed</div>
                <div className="text-xs text-red-300/60">
                  AI-powered suggestions could not be generated. Static scan results are still available.
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </motion.div>
  )
}

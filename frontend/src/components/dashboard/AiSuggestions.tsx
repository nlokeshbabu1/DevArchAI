import { motion } from 'framer-motion'
import { Brain, Lightbulb, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { cn } from '../../lib/utils'
import { Button } from '../ui-animated'

interface AiSuggestion {
  id: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  confidence?: number
  category?: string
  status?: string
}

interface AiSuggestionsProps {
  suggestions: AiSuggestion[]
  isLoading?: boolean
}

const severityConfig = {
  critical: { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', glow: 'severity-glow-critical' },
  high: { bg: 'bg-orange-500/15', text: 'text-orange-400', border: 'border-orange-500/30', glow: 'severity-glow-high' },
  medium: { bg: 'bg-yellow-500/15', text: 'text-yellow-400', border: 'border-yellow-500/30', glow: 'severity-glow-medium' },
  low: { bg: 'bg-green-500/15', text: 'text-green-400', border: 'border-green-500/30', glow: 'severity-glow-low' },
  info: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30', glow: '' },
}

export function AiSuggestions({ suggestions, isLoading }: AiSuggestionsProps) {
  const navigate = useNavigate()

  const topRecs = [...suggestions]
    .filter((s) => s.status !== 'fixed' && s.status !== 'ignored')
    .sort((a, b) => {
      const order = { critical: 5, high: 4, medium: 3, low: 2, info: 1 }
      return (order[b.severity] || 0) - (order[a.severity] || 0)
    })
    .slice(0, 3)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.45 }}
    >
      <div className="rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 overflow-hidden">
        <div className="p-5 pb-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/30">
                <Brain className="h-3.5 w-3.5 text-primary" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">AI Suggestions</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Top remediation opportunities</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/ai-suggestions')}
              icon={<ArrowRight className="h-3.5 w-3.5" />}
            >
              <span className="text-xs">View All</span>
            </Button>
          </div>
        </div>

        <div className="px-5 pb-5">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-4 rounded-xl bg-white/5 border border-white/10 animate-pulse">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-5 w-16 rounded bg-white/10" />
                    <div className="h-5 w-12 rounded bg-white/10" />
                  </div>
                  <div className="h-4 w-3/4 rounded bg-white/10 mb-2" />
                  <div className="h-3 w-full rounded bg-white/5" />
                </div>
              ))}
            </div>
          ) : topRecs.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-3">
              {topRecs.map((rec, i) => {
                const sev = severityConfig[rec.severity in severityConfig ? rec.severity : 'info']
                return (
                  <motion.div
                    key={rec.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.06 }}
                    className={cn(
                      'p-4 rounded-xl border transition-all duration-200 cursor-pointer',
                      sev.bg, sev.border,
                      'hover:bg-white/[0.08] group'
                    )}
                    onClick={() => navigate('/ai-suggestions')}
                  >
                    <div className="flex items-center gap-2 mb-2.5">
                      <div className={cn('p-1 rounded-lg', sev.bg, sev.border)}>
                        <Lightbulb className={cn('h-3 w-3', sev.text)} />
                      </div>
                      <span className={cn(
                        'text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full border',
                        sev.bg, sev.text, sev.border
                      )}>
                        {rec.severity}
                      </span>
                      {typeof rec.confidence === 'number' && (
                        <span className="text-[10px] text-muted-foreground ml-auto">
                          {Math.round(rec.confidence * 100)}%
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-medium text-foreground line-clamp-2 mb-1.5">
                      {rec.title}
                    </h4>
                    <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                      {rec.description}
                    </p>
                    {rec.category && (
                      <p className="text-[10px] text-muted-foreground mt-2 truncate">
                        {rec.category}
                      </p>
                    )}
                  </motion.div>
                )
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-8">
              <div className="p-2 rounded-full bg-white/5 border border-white/10">
                <Brain className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium text-foreground">No open recommendations</p>
              <p className="text-xs text-muted-foreground text-center max-w-[280px]">
                AI-powered recommendations will appear after scans produce remediation guidance
              </p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

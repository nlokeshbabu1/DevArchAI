import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'
import { Brain, Lightbulb, Code, CheckCircle, ArrowRight } from 'lucide-react'
import { Button } from '../ui'
import { CodeBlock } from '../ui/code-block'

interface AISuggestion {
  id: string
  title: string
  description: string
  impact: string
  fixExample: string
  confidence: number
  category: string
}

interface AISuggestionsPanelProps {
  suggestions: AISuggestion[]
  onApplyFix?: (suggestion: AISuggestion) => void
  className?: string
}

export function AISuggestionsPanel({
  suggestions,
  onApplyFix,
  className,
}: AISuggestionsPanelProps) {
  if (suggestions.length === 0) {
    return (
      <div className={cn(
        'bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30',
        'rounded-2xl p-6',
        className
      )}>
        <div className="text-center py-8">
          <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">No AI suggestions</h3>
          <p className="text-muted-foreground">Run a scan to get AI-powered recommendations.</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center gap-2 mb-4">
        <Brain className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-semibold text-foreground">AI Suggestions</h2>
        <span className="text-sm text-muted-foreground">({suggestions.length})</span>
      </div>

      {suggestions.map((suggestion, index) => (
        <AISuggestionCard
          key={suggestion.id}
          suggestion={suggestion}
          delay={index * 0.1}
          onApplyFix={onApplyFix}
        />
      ))}
    </div>
  )
}

interface AISuggestionCardProps {
  suggestion: AISuggestion
  delay?: number
  onApplyFix?: (suggestion: AISuggestion) => void
}

function AISuggestionCard({ suggestion, delay = 0, onApplyFix }: AISuggestionCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className="bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 rounded-2xl p-6"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
            <Lightbulb className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">{suggestion.title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{suggestion.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-sm text-muted-foreground">
            {suggestion.confidence.toFixed(0)}% confidence
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-4 w-4 text-orange-400" />
            <span className="text-sm font-medium text-orange-400">Impact</span>
          </div>
          <p className="text-sm text-muted-foreground">{suggestion.impact}</p>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <Code className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">Suggested Fix</span>
          </div>
          <CodeBlock
            code={suggestion.fixExample}
            language="terraform"
            title="Example"
            showLineNumbers
          />
        </div>

        {onApplyFix && (
          <div className="flex justify-end">
            <Button variant="primary" onClick={() => onApplyFix(suggestion)}>
              Apply Fix
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function AlertCircle({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  )
}

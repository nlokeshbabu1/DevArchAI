/**
 * AI Suggestion Panel - Production Grade Component
 * 
 * Features:
 * - Always shows AI section (with fallback if not available)
 * - Confidence bar with visual indicator
 * - Expandable full example
 * - Copy buttons for code snippets
 * - Feedback (thumbs up/down)
 * - Fallback message when AI not available
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Brain, CheckCircle, Code, Copy, ThumbsUp, ThumbsDown, 
  AlertTriangle, Sparkles, FileText, Terminal, ChevronDown, ChevronUp,
  ExternalLink, BookOpen
} from 'lucide-react'
import { Button } from '../ui-animated'
import { Badge, Card } from '../ui'
import { cn, copyToClipboard } from '../../lib/utils'

interface AISuggestionPanelProps {
  finding: {
    rule_id: string
    rule_name: string
    severity: string
    category: string
    description: string
    recommendation: string
    file_path?: string
    line_number?: number
    // AI Fix Generator fields
    summary?: string
    risk?: string
    impact?: string
    fix_code?: string
    fix_example?: string
    full_example?: string
    best_practices?: string[]
    confidence?: number
    confidence_score?: number
    ai_generated?: boolean
    ai_explanation?: string
    documentation_url?: string
  }
  userPlan?: string
  onUpgrade?: () => void
  index?: number
}

export function AISuggestionPanel({ 
  finding, 
  userPlan = 'free', 
  onUpgrade,
  index = 0 
}: AISuggestionPanelProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)

  const isPaidUser = ['plus', 'pro', 'enterprise'].includes(userPlan)
  const isPreviewFinding = index < 2 // Free users see first 2 AI suggestions

  // Get confidence level
  const confidence = finding.confidence ?? finding.confidence_score
  const confidenceLevel = confidence != null
    ? confidence >= 0.8 ? 'high' : confidence >= 0.6 ? 'medium' : 'low'
    : null

  const confidenceConfig = {
    high: { color: 'bg-green-500', text: 'text-green-400', label: 'High' },
    medium: { color: 'bg-yellow-500', text: 'text-yellow-400', label: 'Medium' },
    low: { color: 'bg-gray-500', text: 'text-gray-400', label: 'Low' },
  }

  const config = confidenceLevel ? confidenceConfig[confidenceLevel] : null

  // Check if AI data is available
  const hasAIData = finding.ai_generated || finding.summary || finding.fix_code || finding.ai_explanation

  // Get the best available fix code
  const fixCode = finding.fix_code || finding.fix_example || finding.full_example

  const handleCopy = async (text: string) => {
    if (text) {
      await copyToClipboard(text)
    }
  }

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedback(type)
    // TODO: Send feedback to backend
    console.log(`Feedback ${type} for finding ${finding.rule_id}`)
  }

  const getLanguageFromPath = (path: string): string => {
    if (!path) return 'plaintext'
    if (path.endsWith('.tf') || path.endsWith('.tfvars')) return 'hcl'
    if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml'
    if (path.toLowerCase().includes('dockerfile')) return 'dockerfile'
    if (path.endsWith('.sh')) return 'bash'
    if (path.endsWith('.json')) return 'json'
    return 'plaintext'
  }

  // Render fallback when AI not available
  if (!hasAIData) {
    return (
      <Card className="p-4 border-dashed" hover={false}>
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-gray-500/10 border border-gray-500/30">
            <Brain className="h-5 w-5 text-gray-400" />
          </div>
          <div className="flex-1">
            <h5 className="text-sm font-semibold text-foreground mb-2">
              AI Analysis Not Available
            </h5>
            <p className="text-sm text-muted-foreground mb-3">
              AI-powered suggestions are not available for this finding. Showing static remediation guidance instead.
            </p>
            {finding.recommendation && (
              <div className="p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="h-4 w-4 text-green-400" />
                  <span className="text-xs font-semibold text-green-400">Static Fix Recommendation</span>
                </div>
                <p className="text-sm text-muted-foreground">{finding.recommendation}</p>
              </div>
            )}
            {!isPaidUser && (
              <Button
                variant="primary"
                size="sm"
                className="mt-3"
                onClick={onUpgrade}
                icon={<Brain className="h-4 w-4" />}
              >
                Upgrade for AI Suggestions
              </Button>
            )}
          </div>
        </div>
      </Card>
    )
  }

  // Free user with limited preview
  if (!isPaidUser && !isPreviewFinding) {
    return (
      <Card className="p-4 blur-sm select-none" hover={false}>
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <span className="text-sm font-semibold">AI Suggestion</span>
          </div>
          <div className="h-4 bg-white/10 rounded w-3/4" />
          <div className="h-4 bg-white/10 rounded w-full" />
          <div className="h-4 bg-white/10 rounded w-5/6" />
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <Card className="p-4 text-center" hover={false}>
            <Brain className="h-8 w-8 text-primary mx-auto mb-2" />
            <h5 className="font-semibold mb-1">AI Fix Suggestion</h5>
            <p className="text-sm text-muted-foreground mb-3">
              Upgrade to see AI-powered remediation
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={onUpgrade}
              icon={<ExternalLink className="h-4 w-4" />}
            >
              Upgrade to Plus
            </Button>
          </Card>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-4" hover={false}>
      <div className="space-y-4">
        {/* Header with Confidence */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30">
              <Brain className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h5 className="text-sm font-semibold text-foreground">
                AI Suggestion
                {!finding.ai_generated && (
                  <Badge variant="secondary" className="ml-2 text-xs">
                    Static Analysis
                  </Badge>
                )}
              </h5>
              {config && confidence != null && (
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex items-center gap-1">
                    <div className="w-24 h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div 
                        className={cn('h-full rounded-full transition-all', config.color)}
                        style={{ width: `${confidence * 100}%` }}
                      />
                    </div>
                    <span className={cn('text-xs font-medium', config.text)}>
                      {config.label} ({Math.round(confidence * 100)}%)
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Feedback Buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => handleFeedback('up')}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                feedback === 'up' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'hover:bg-white/5 text-muted-foreground'
              )}
            >
              <ThumbsUp className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleFeedback('down')}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                feedback === 'down' 
                  ? 'bg-red-500/20 text-red-400' 
                  : 'hover:bg-white/5 text-muted-foreground'
              )}
            >
              <ThumbsDown className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Summary */}
        {finding.summary && (
          <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-primary" />
              <span className="text-xs font-semibold text-primary">Summary</span>
            </div>
            <p className="text-sm text-muted-foreground">{finding.summary}</p>
          </div>
        )}

        {/* Risk & Impact */}
        {(finding.risk || finding.impact) && (
          <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              <span className="text-xs font-semibold text-orange-400">Risk & Impact</span>
            </div>
            {finding.risk && (
              <p className="text-sm text-orange-300 mb-2">{finding.risk}</p>
            )}
            {finding.impact && (
              <p className="text-sm text-orange-300">{finding.impact}</p>
            )}
          </div>
        )}

        {/* Fix Code */}
        {fixCode && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Code className="h-4 w-4 text-green-400" />
                <span className="text-xs font-semibold text-foreground">Suggested Fix</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => handleCopy(fixCode)}
                icon={<Copy className="h-3 w-3" />}
              >
                Copy
              </Button>
            </div>
            <div className="rounded-lg bg-black/50 border border-white/10 overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border-b border-white/10">
                <Terminal className="h-4 w-4 text-green-400" />
                <span className="text-xs font-medium text-green-400">
                  {finding.file_path ? getLanguageFromPath(finding.file_path) : 'Code'}
                </span>
              </div>
              <pre className="p-3 overflow-x-auto max-h-[400px]">
                <code className="text-sm text-green-400 font-mono whitespace-pre">
                  {fixCode}
                </code>
              </pre>
            </div>
          </div>
        )}

        {/* Full Example (Expandable) */}
        {finding.full_example && (
          <div className="border border-white/10 rounded-lg overflow-hidden">
            <button
              onClick={() => setExpandedSection(expandedSection === 'full' ? null : 'full')}
              className="w-full flex items-center justify-between px-4 py-3 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-blue-400" />
                <span className="text-sm font-semibold text-foreground">Full Fix Example</span>
              </div>
              {expandedSection === 'full' ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
            <AnimatePresence>
              {expandedSection === 'full' && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-4 bg-black/50 border-t border-white/10">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Code className="h-4 w-4 text-blue-400" />
                        <span className="text-xs font-medium text-blue-400">Complete File</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => handleCopy(finding.full_example || '')}
                        icon={<Copy className="h-3 w-3" />}
                      >
                        Copy Full File
                      </Button>
                    </div>
                    <pre className="p-4 overflow-x-auto max-h-[600px] bg-black/30 rounded-lg">
                      <code className="text-sm text-blue-300 font-mono whitespace-pre">
                        {finding.full_example}
                      </code>
                    </pre>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Best Practices */}
        {finding.best_practices && finding.best_practices.length > 0 && (
          <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              <span className="text-xs font-semibold text-indigo-400">Best Practices</span>
            </div>
            <ul className="space-y-1.5">
              {finding.best_practices.map((practice, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle className="h-3.5 w-3.5 text-indigo-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-indigo-300">{practice}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Documentation Link */}
        {finding.documentation_url && (
          <div className="flex items-center justify-between pt-2 border-t border-white/10">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <BookOpen className="h-4 w-4" />
              <span>Official Documentation</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.open(finding.documentation_url, '_blank', 'noopener,noreferrer')}
              icon={<ExternalLink className="h-3 w-3" />}
            >
              Open
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}

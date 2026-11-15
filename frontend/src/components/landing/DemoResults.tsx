import { motion } from 'framer-motion'
import {
  AlertTriangle, AlertCircle, Info,
  Server, Cloud, GitBranch, Zap, ChevronDown, ChevronUp,
  Lock, ArrowRight, Code
} from 'lucide-react'
import { useState, memo, useCallback } from 'react'

import demoData from '../../data/demoScan.json'
import { cn, sanitizePath } from '../../lib/utils'
import { Card, Button } from '../ui-animated'

interface DemoResultsProps {
  onUnlock: () => void
}

const severityIcons: Record<string, React.ElementType> = {
  critical: AlertCircle,
  high: AlertTriangle,
  medium: Info,
  low: Info,
  info: Info,
}

const severityColors: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/30',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  info: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
}

const techIcons: Record<string, React.ElementType> = {
  docker: Server,
  terraform: Cloud,
  kubernetes: GitBranch,
  github_actions: Zap,
  aws: Cloud,
}

const FindingCard = memo(function FindingCard({
  finding,
  index,
  isExpanded,
  onToggle,
  onUnlock,
}: {
  finding: typeof demoData.findings[0]
  index: number
  isExpanded: boolean
  onToggle: () => void
  onUnlock: () => void
}) {
  const Icon = severityIcons[finding.severity]
  const colorClass = severityColors[finding.severity]

  return (
    <motion.div
      className="border border-white/[0.06] rounded-xl overflow-hidden bg-card/30"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div
        className="p-4 cursor-pointer hover:border-white/[0.12] transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start gap-4">
          <div className={cn('p-2 rounded-lg', colorClass)}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={cn('px-2 py-1 rounded-full text-xs font-medium border', colorClass)}>
                {finding.severity.toUpperCase()}
              </span>
              <span className="text-xs font-mono text-muted-foreground">
                {finding.rule_id}
              </span>
            </div>
            <h4 className="font-semibold text-foreground mb-1">
              {finding.rule_name}
            </h4>
            <p className="text-sm text-muted-foreground">
              {finding.description}
            </p>
          </div>
          <div className="flex items-center">
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
        </div>
      </div>

      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
          className="px-4 pb-4 border-t border-white/[0.06]"
        >
          <div className="pt-4 space-y-4">
            {finding.file_path && (
              <div>
                <h5 className="text-sm font-semibold text-foreground mb-2">Location</h5>
                <code className="text-sm text-muted-foreground bg-white/[0.04] px-3 py-2 rounded-lg block border border-white/[0.06]">
                  {sanitizePath(finding.file_path)}
                  {finding.line_number && ` (Line ${finding.line_number})`}
                </code>
              </div>
            )}

            <div>
              <h5 className="text-sm font-semibold text-foreground mb-2">Recommendation</h5>
              <p className="text-sm text-muted-foreground">{finding.recommendation}</p>
            </div>

            {finding.fix_example && (
              <div>
                <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                  <Code className="h-4 w-4 text-primary" />
                  Example Fix
                </h5>
                <div className="rounded-lg bg-black/30 border border-white/[0.06] overflow-hidden">
                  <pre className="p-3 overflow-x-auto">
                    <code className="text-sm text-green-400 font-mono">
                      {finding.fix_example}
                    </code>
                  </pre>
                </div>
              </div>
            )}

            <div className="flex gap-2 pt-4 border-t border-white/[0.06]">
              <Button
                variant="secondary"
                size="sm"
                onClick={onUnlock}
                icon={<Lock className="h-4 w-4" />}
              >
                Login to Fix
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onUnlock}
              >
                View Documentation
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
})

export function DemoResults({ onUnlock }: DemoResultsProps) {
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const data = demoData

  const getScoreColor = (score: number) => {
    if (score >= 80) {return 'text-green-400'}
    if (score >= 60) {return 'text-yellow-400'}
    if (score >= 50) {return 'text-orange-400'}
    return 'text-red-400'
  }

  const getScoreGrade = (score: number) => {
    if (score >= 90) {return 'A'}
    if (score >= 80) {return 'B'}
    if (score >= 70) {return 'C'}
    if (score >= 60) {return 'D'}
    return 'F'
  }

  const demoFindings = data.findings.slice(0, 3)
  const lockedFindingsCount = data.findings.length - 3

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        className="text-center space-y-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <h2 className="text-4xl font-bold text-foreground">
          See What We Found
        </h2>
        <p className="text-lg text-muted-foreground">
          This is a demo of what DevArchAI can find in your infrastructure
        </p>
      </motion.div>

      {/* Score Card */}
      <Card className="p-8" hover={false}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-2xl font-bold text-foreground">{data.repository_name}</h3>
            <p className="text-muted-foreground mt-1">{data.repository_url}</p>
          </div>
          <div className="text-right">
            <div className={cn('text-6xl font-bold', getScoreColor(data.security_score))}>
              {data.security_score.toFixed(1)}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Security Score • Grade: <span className={cn('font-bold', getScoreColor(data.security_score))}>
                {getScoreGrade(data.security_score)}
              </span>
            </div>
          </div>
        </div>

        {/* Severity Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 pt-6 border-t border-white/[0.06]">
          {Object.entries(data.severity_counts).map(([severity, count]) => (
            <div key={severity} className="text-center">
              <div className={cn('text-3xl font-bold', severityColors[severity].split(' ')[1])}>
                {count}
              </div>
              <div className="text-xs text-muted-foreground mt-1 capitalize">{severity}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Tech Stack */}
      <Card className="p-6" hover={false}>
        <h3 className="text-lg font-semibold mb-4 text-foreground">Detected Technologies</h3>
        <div className="flex flex-wrap gap-3">
          {data.detected_technologies.map((tech) => {
            const Icon = techIcons[tech] || AlertTriangle
            return (
              <motion.div
                key={tech}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/10 border border-primary/20"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
              >
                <Icon className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-primary capitalize">
                  {tech.replace('_', ' ')}
                </span>
              </motion.div>
            )
          })}
        </div>
      </Card>

      {/* Findings Preview */}
      <Card className="p-6" hover={false}>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-foreground">
            Security Findings (Showing 3 of {data.findings_count})
          </h3>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Lock className="h-4 w-4" />
            <span>Login to see all {data.findings_count} findings</span>
          </div>
        </div>

        <div className="space-y-4">
          {demoFindings.map((finding, index) => (
            <FindingCard
              key={finding.rule_id}
              finding={finding}
              index={index}
              isExpanded={expandedFinding === finding.rule_id}
              onToggle={() => setExpandedFinding(expandedFinding === finding.rule_id ? null : finding.rule_id)}
              onUnlock={onUnlock}
            />
          ))}
        </div>

        {/* Locked Findings CTA */}
        {lockedFindingsCount > 0 && (
          <motion.div
            className="mt-6 p-6 rounded-xl bg-primary/[0.04] border border-primary/15 text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <Lock className="h-8 w-8 text-primary mx-auto mb-3" />
            <h4 className="text-lg font-semibold text-foreground mb-2">
              {lockedFindingsCount} More Findings Available
            </h4>
            <p className="text-muted-foreground mb-4">
              Login to see all {data.findings_count} findings, download reports, and get AI-powered fix suggestions.
            </p>
            <Button
              variant="primary"
              size="lg"
              onClick={onUnlock}
              icon={<ArrowRight className="h-5 w-5" />}
              glow
            >
              Unlock Full Report
            </Button>
          </motion.div>
        )}
      </Card>

      {/* Download CTA */}
      <motion.div
        className="p-6 rounded-xl bg-card/30 border border-white/[0.08] text-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <h4 className="text-lg font-semibold text-foreground mb-2">
          Download Full Report
        </h4>
        <p className="text-muted-foreground mb-4">
          Get a comprehensive PDF or Excel report with all findings and recommendations.
        </p>
        <Button
          variant="secondary"
          size="lg"
          onClick={onUnlock}
          icon={<Lock className="h-4 w-4" />}
        >
          Login to Download
        </Button>
      </motion.div>
    </div>
  )
}

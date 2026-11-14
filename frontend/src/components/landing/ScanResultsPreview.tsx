import { motion } from 'framer-motion'
import { Shield, AlertTriangle, AlertCircle, Info, Lock, Github, ArrowRight, Terminal, Cloud, Layers, CheckCircle } from 'lucide-react'
import { memo } from 'react'
import { useNavigate } from 'react-router-dom'

import { cn } from '../../lib/utils'
import { Badge } from '../ui'
import { Button, Card, ScoreCircle } from '../ui-animated'

interface Finding {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path?: string
  line_number?: number
}

interface ScanResultsPreviewProps {
  sessionId: string
  repositoryName: string
  securityScore: number
  severityCounts: {
    critical: number
    high: number
    medium: number
    low: number
  }
  findings: Finding[]
  detectedTechnologies?: string[]
}

const severityIcons = {
  critical: AlertCircle,
  high: AlertTriangle,
  medium: Info,
  low: Info,
  info: Info,
}

const severityColors = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/30',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  info: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
}

const FindingItem = memo(function FindingItem({
  finding,
  index,
}: {
  finding: Finding
  index: number
}) {
  const Icon = severityIcons[finding.severity]
  const colorClass = severityColors[finding.severity]

  return (
    <motion.div
      className="p-4 rounded-xl border border-white/[0.06] hover:border-white/[0.12] transition-colors bg-card/30"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.4 + index * 0.1, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="flex items-start gap-4">
        <div className={cn('p-2 rounded-lg', colorClass)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="secondary" className={cn('text-xs', colorClass)}>
              {finding.severity.toUpperCase()}
            </Badge>
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
      </div>
    </motion.div>
  )
})

export function ScanResultsPreview({
  sessionId,
  repositoryName,
  securityScore,
  severityCounts,
  findings,
  detectedTechnologies = [],
}: ScanResultsPreviewProps) {
  const navigate = useNavigate()

  const handleLogin = () => {
    sessionStorage.setItem('postLoginRedirect', `/scan/results/${sessionId}`)
    navigate('/login')
  }

  const getGrade = (score: number) => {
    if (score >= 90) {return 'A'}
    if (score >= 80) {return 'B'}
    if (score >= 70) {return 'C'}
    if (score >= 60) {return 'D'}
    return 'F'
  }

  const totalIssues = Object.values(severityCounts).reduce((a, b) => a + b, 0)

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h2 className="text-3xl font-bold text-foreground mb-2">
          Scan Results for {repositoryName}
        </h2>
        <p className="text-muted-foreground">
          Production Readiness Analysis Complete
        </p>
      </motion.div>

      {/* Score and Summary Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Security Score */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <Card className="p-8" hover={false}>
            <div className="text-center space-y-6">
              <h3 className="text-xl font-semibold text-foreground">
                Production Readiness Score
              </h3>
              <ScoreCircle
                score={securityScore}
                size="xl"
                animated
                delay={200}
              />
              <div className="text-center">
                <div className="text-4xl font-bold text-foreground">
                  {securityScore} / 100
                </div>
                <div className="text-lg text-muted-foreground mt-1">
                  Grade: <span className="font-bold text-foreground">{getGrade(securityScore)}</span>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Issue Summary */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <Card className="p-8" hover={false}>
            <h3 className="text-xl font-semibold text-foreground mb-6">
              Issue Summary
            </h3>
            <div className="space-y-4">
              {Object.entries(severityCounts).map(([severity, count]) => {
                const Icon = severityIcons[severity as keyof typeof severityIcons]
                const colorClass = severityColors[severity as keyof typeof severityColors]

                return (
                  <div
                    key={severity}
                    className={cn(
                      'flex items-center justify-between p-4 rounded-xl border capitalize',
                      colorClass
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="h-6 w-6" />
                      <span className="font-medium">{severity}</span>
                    </div>
                    <span className="text-2xl font-bold">{count}</span>
                  </div>
                )
              })}
            </div>

            <div className="mt-6 pt-6 border-t border-white/[0.06]">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Total Issues</span>
                <span className="text-foreground font-bold text-lg">{totalIssues}</span>
              </div>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Findings List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <Card className="p-6" hover={false}>
          <h3 className="text-xl font-semibold text-foreground mb-6">
            Detected Issues
          </h3>
          <div className="space-y-4">
            {findings.slice(0, 5).map((finding, index) => (
              <FindingItem key={finding.rule_id} finding={finding} index={index} />
            ))}
          </div>

          {findings.length > 5 && (
            <p className="text-center text-sm text-muted-foreground mt-4">
              + {findings.length - 5} more issues found
            </p>
          )}
        </Card>
      </motion.div>

      {/* AI Remediation - LOCKED (Conversion Trigger) */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <Card className="p-8" hover={false}>
          <div className="text-center space-y-6">
            <div className="inline-flex p-4 rounded-2xl bg-primary/10 border border-primary/20">
              <Lock className="h-8 w-8 text-primary" />
            </div>

            <div>
              <h3 className="text-2xl font-bold text-foreground mb-2">
                AI Remediation Locked
              </h3>
              <p className="text-muted-foreground">
                Get instant AI-powered fix recommendations for all detected issues
              </p>
            </div>

            {/* Blurred Code Preview */}
            <div className="relative max-w-2xl mx-auto">
              <div className="p-6 rounded-xl bg-black/30 border border-white/[0.06] overflow-hidden">
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="h-4 bg-white/[0.08] rounded animate-pulse"
                      style={{
                        width: `${80 - i * 10}%`,
                      }}
                    />
                  ))}
                </div>
              </div>

              <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm rounded-xl">
                <div className="text-center p-6">
                  <Lock className="h-12 w-12 text-primary mx-auto mb-3" />
                  <p className="text-lg font-semibold text-foreground mb-1">
                    Login to See AI Remediation
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Get copy-paste ready fixes for all issues
                  </p>
                </div>
              </div>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <Button
                variant="primary"
                size="lg"
                onClick={handleLogin}
                icon={<Github className="h-5 w-5" />}
                glow
              >
                Login with GitHub
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => navigate('/register')}
              >
                Create Free Account
                <ArrowRight className="h-5 w-5 ml-2" />
              </Button>
            </div>

            <p className="text-sm text-muted-foreground">
              <CheckCircle className="h-4 w-4 inline mr-1 text-green-400" />
              Free account includes 3 scans per month
            </p>
          </div>
        </Card>
      </motion.div>

      {/* Detected Technologies */}
      {detectedTechnologies.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <Card className="p-6" hover={false}>
            <h3 className="text-xl font-semibold text-foreground mb-6">
              Detected Technologies
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {detectedTechnologies.map((tech, index) => {
                const Icon = tech === 'Docker' ? Terminal : tech === 'Kubernetes' ? Cloud : Layers

                return (
                  <motion.div
                    key={tech}
                    className="flex flex-col items-center gap-3 p-4 rounded-xl bg-card/30 border border-white/[0.06] hover:border-primary/30 transition-all"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.7 + index * 0.05, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
                  >
                    <Icon className="h-8 w-8 text-primary" />
                    <span className="text-sm font-medium text-foreground">{tech}</span>
                  </motion.div>
                )
              })}
            </div>
          </Card>
        </motion.div>
      )}
    </div>
  )
}

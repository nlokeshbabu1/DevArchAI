import { motion } from 'framer-motion'
import { AlertTriangle, AlertCircle, CheckCircle, Info, ChevronRight } from 'lucide-react'

import { cn, sanitizePath } from '../../lib/utils'
import { Button } from '../ui'
import { SeverityBadge } from '../ui/severity-badge'

interface Issue {
  id: string
  ruleId: string
  ruleName: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  filePath: string
  status?: 'open' | 'fixed' | 'ignored'
}

interface IssuesTableProps {
  issues: Issue[]
  onViewIssue?: (issue: Issue) => void
  onFixIssue?: (issue: Issue) => void
}

export function IssuesTable({ issues, onViewIssue, onFixIssue }: IssuesTableProps) {
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return AlertTriangle
      case 'high':
        return AlertTriangle
      case 'medium':
        return AlertCircle
      case 'low':
        return CheckCircle
      default:
        return Info
    }
  }

  return (
    <div className="bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 rounded-2xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-6 py-4 text-left text-sm font-medium text-muted-foreground">Severity</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-muted-foreground">Rule</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-muted-foreground">Location</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-muted-foreground">Description</th>
              <th className="px-6 py-4 text-right text-sm font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, index) => {
              const SeverityIcon = getSeverityIcon(issue.severity)
              return (
                <motion.tr
                  key={issue.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  className="border-b border-white/5 hover:bg-white/5 transition-colors"
                >
                  <td className="px-6 py-4">
                    <SeverityBadge severity={issue.severity} size="sm" />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <SeverityIcon className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <div className="text-sm font-medium text-foreground">{issue.ruleName}</div>
                        <div className="text-xs text-muted-foreground font-mono">{issue.ruleId}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-foreground">{sanitizePath(issue.filePath)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-muted-foreground line-clamp-2 max-w-md">
                      {issue.description}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {onViewIssue && (
                        <Button variant="ghost" size="sm" onClick={() => onViewIssue(issue)}>
                          View
                          <ChevronRight className="h-3.5 w-3.5 ml-1" />
                        </Button>
                      )}
                      {onFixIssue && (
                        <Button variant="primary" size="sm" onClick={() => onFixIssue(issue)}>
                          Fix
                        </Button>
                      )}
                    </div>
                  </td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {issues.length === 0 && (
        <div className="text-center py-12">
          <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">No issues found</h3>
          <p className="text-muted-foreground">All scans are clean! Great job.</p>
        </div>
      )}
    </div>
  )
}

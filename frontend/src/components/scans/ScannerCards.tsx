import { motion, AnimatePresence } from 'framer-motion'
import {
  Loader2,
  CheckCircle2,
  XCircle,
  SkipForward,
  Shield,
  Box,
  Cloud,
  Lock,
  GitBranch,
  FileCode,
  Search,
  Terminal,
  Package,
  Server,
} from 'lucide-react'

import { cn } from '../../lib/utils'
import type { ScannerStatus } from '../../types'

interface ScannerCardsProps {
  scanners: Record<string, ScannerStatus>
  detectedStack: string[]
}

const SCANNER_INFO: Record<
  string,
  { label: string; icon: React.ReactNode; description: string }
> = {
  hadolint: {
    label: 'Docker',
    icon: <Box className="w-5 h-5" />,
    description: 'Dockerfile linting',
  },
  gitleaks: {
    label: 'Secrets',
    icon: <Lock className="w-5 h-5" />,
    description: 'Secret detection',
  },
  npm_audit: {
    label: 'npm',
    icon: <Package className="w-5 h-5" />,
    description: 'Node.js dependencies',
  },
  pip_audit: {
    label: 'pip',
    icon: <Package className="w-5 h-5" />,
    description: 'Python dependencies',
  },
  govulncheck: {
    label: 'Go',
    icon: <Terminal className="w-5 h-5" />,
    description: 'Go vulnerabilities',
  },
  dependency_check: {
    label: 'SCA',
    icon: <Search className="w-5 h-5" />,
    description: 'OWASP dependency check',
  },
  checkov: {
    label: 'IaC',
    icon: <Shield className="w-5 h-5" />,
    description: 'Infrastructure as Code',
  },
  tfsec: {
    label: 'Terraform',
    icon: <Cloud className="w-5 h-5" />,
    description: 'Terraform security',
  },
  kube_score: {
    label: 'Kubernetes',
    icon: <Server className="w-5 h-5" />,
    description: 'K8s best practices',
  },
  trivy_filesystem: {
    label: 'Trivy FS',
    icon: <FileCode className="w-5 h-5" />,
    description: 'Filesystem scan',
  },
  trivy_config: {
    label: 'Trivy Config',
    icon: <Shield className="w-5 h-5" />,
    description: 'Config scan',
  },
}

function getScannerInfo(scannerId: string) {
  return (
    SCANNER_INFO[scannerId] ?? {
      label: scannerId.replace(/_/g, ' '),
      icon: <GitBranch className="w-5 h-5" />,
      description: 'Security scan',
    }
  )
}

function getStatusConfig(status: ScannerStatus['status']) {
  switch (status) {
    case 'running':
      return {
        label: 'Running',
        border: 'border-l-indigo-500',
        badge: 'bg-indigo-500/15 text-indigo-400',
        icon: null,
      }
    case 'completed':
    case 'completed_no_findings':
      return {
        label: 'Completed',
        border: 'border-l-emerald-500',
        badge: 'bg-emerald-500/15 text-emerald-400',
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
      }
    case 'completed_with_findings':
      return {
        label: 'Completed',
        border: 'border-l-emerald-500',
        badge: 'bg-emerald-500/15 text-emerald-400',
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
      }
    case 'failed':
      return {
        label: 'Failed',
        border: 'border-l-red-500',
        badge: 'bg-red-500/15 text-red-400',
        icon: <XCircle className="w-4 h-4 text-red-400" />,
      }
    case 'skipped':
    case 'unavailable':
      return {
        label: status === 'skipped' ? 'Skipped' : 'Unavailable',
        border: 'border-l-neutral-500',
        badge: 'bg-neutral-500/15 text-neutral-400',
        icon: <SkipForward className="w-4 h-4 text-neutral-400" />,
      }
    default:
      return {
        label: 'Queued',
        border: 'border-l-neutral-600',
        badge: 'bg-neutral-500/10 text-neutral-500',
        icon: null,
      }
  }
}

function formatDuration(ms?: number): string {
  if (!ms) {return ''}
  const sec = ms / 1000
  if (sec < 60) {return `${sec.toFixed(1)} sec`}
  return `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`
}

function SkeletonCard() {
  return (
    <div className="bg-card border border-border rounded-lg p-4 border-l-4 border-l-neutral-700 animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-lg bg-white/[0.05]" />
        <div className="flex-1 space-y-2">
          <div className="h-3.5 w-20 rounded bg-white/[0.06]" />
          <div className="h-2.5 w-28 rounded bg-white/[0.04]" />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="h-5 w-16 rounded-full bg-white/[0.05]" />
        <div className="h-5 w-14 rounded bg-white/[0.04]" />
      </div>
    </div>
  )
}

export function ScannerCards({ scanners, detectedStack }: ScannerCardsProps) {
  const entries = Object.values(scanners)
  const isEmpty = entries.length === 0

  return (
    <div className="space-y-4">
      {detectedStack.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider mr-1">
            Detected
          </span>
          {detectedStack.map((tech) => (
            <span
              key={tech}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20"
            >
              <Shield className="w-3 h-3" />
              {tech}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <AnimatePresence mode="popLayout">
          {isEmpty
            ? Array.from({ length: 6 }).map((_, i) => (
                <motion.div
                  key={`skeleton-${i}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <SkeletonCard />
                </motion.div>
              ))
            : entries.map((scanner) => {
                const info = getScannerInfo(scanner.scanner_id)
                const statusConfig = getStatusConfig(scanner.status)
                const isRunning = scanner.status === 'running'

                return (
                  <motion.div
                    key={scanner.scanner_id}
                    layout
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className={cn(
                      'bg-card border border-border rounded-lg p-4 border-l-4 transition-colors',
                      statusConfig.border
                    )}
                  >
                    <div className="flex items-start gap-3 mb-3">
                      <div
                        className={cn(
                          'flex items-center justify-center w-9 h-9 rounded-lg shrink-0',
                          isRunning
                            ? 'bg-indigo-500/15'
                            : scanner.status.startsWith('completed')
                              ? 'bg-emerald-500/10'
                              : scanner.status === 'failed'
                                ? 'bg-red-500/10'
                                : 'bg-white/[0.05]'
                        )}
                      >
                        {isRunning ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{
                              repeat: Infinity,
                              duration: 1,
                              ease: 'linear',
                            }}
                          >
                            <Loader2 className="w-5 h-5 text-indigo-400" />
                          </motion.div>
                        ) : (
                          <span
                            className={cn(
                              scanner.status.startsWith('completed')
                                ? 'text-emerald-400/80'
                                : scanner.status === 'failed'
                                  ? 'text-red-400/80'
                                  : 'text-muted-foreground'
                            )}
                          >
                            {info.icon}
                          </span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-foreground truncate">
                          {info.label}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {info.description}
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                          statusConfig.badge
                        )}
                      >
                        {isRunning && (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        )}
                        {statusConfig.icon && !isRunning && statusConfig.icon}
                        {statusConfig.label}
                      </span>

                      {scanner.rules_count != null &&
                        scanner.rules_count > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {scanner.rules_count} rules
                          </span>
                        )}

                      {scanner.status.startsWith('completed') &&
                        scanner.findings_count > 0 && (
                          <span
                            className={cn(
                              'text-xs font-medium',
                              scanner.findings_count > 0
                                ? 'text-amber-400'
                                : 'text-muted-foreground'
                            )}
                          >
                            {scanner.findings_count} findings
                          </span>
                        )}

                      {scanner.duration_ms != null &&
                        scanner.duration_ms > 0 && (
                          <span className="text-xs text-muted-foreground ml-auto tabular-nums">
                            {formatDuration(scanner.duration_ms)}
                          </span>
                        )}
                    </div>

                    {scanner.error && (
                      <p className="mt-2 text-xs text-red-400/80 truncate" title={scanner.error}>
                        {scanner.error}
                      </p>
                    )}
                  </motion.div>
                )
              })}
        </AnimatePresence>
      </div>
    </div>
  )
}

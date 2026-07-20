import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Shield, Cloud, Server, GanttChartSquare,
  Globe, Lock, Package2,
  CheckCircle2, AlertCircle, HelpCircle, XCircle,
  Layers, ChevronDown, ChevronRight,
} from "lucide-react"
import {
  cn, getSeverityColor,
} from "../../lib/utils"
import type { ScannerExecution } from "../../types"

interface DetectionCoverageProps {
  scannerExecutions?: ScannerExecution[]
  findings?: any[]
  detectedTechnologies?: string[]
  technologyDetails?: { technology: string; files_count: number; findings_count: number; severity_counts: Record<string, number>; status: string }[]
}

const CARD_STATUS: Record<string, { label: string; icon: typeof Shield; color: string; border: string }> = {
  DETECTED: { label: "Detected", icon: CheckCircle2, color: "text-emerald-400", border: "border-emerald-500/20 bg-emerald-500/[0.03]" },
  CLEAN: { label: "Clear", icon: CheckCircle2, color: "text-white/30", border: "border-white/5 bg-white/[0.02]" },
  UNAVAILABLE: { label: "Unavailable", icon: HelpCircle, color: "text-zinc-400", border: "border-zinc-500/10 bg-zinc-500/[0.02]" },
  NOT_APPLICABLE: { label: "Not Applicable", icon: XCircle, color: "text-amber-400", border: "border-amber-500/10 bg-amber-500/[0.02]" },
  FAILED: { label: "Failed", icon: AlertCircle, color: "text-red-400", border: "border-red-500/10 bg-red-500/[0.02]" },
}

const SEVERITY_LABELS = ["critical", "high", "medium", "low"] as const

interface TechInfo {
  key: string
  label: string
  icon: typeof Shield
  scannerIds: string[]
}

const TECH_REGISTRY: TechInfo[] = [
  { key: "docker", label: "Docker", icon: Cloud, scannerIds: ["hadolint", "trivy_filesystem", "trivy", "checkov"] },
  { key: "terraform", label: "Terraform", icon: GanttChartSquare, scannerIds: ["tfsec", "checkov", "trivy_config"] },
  { key: "kubernetes", label: "Kubernetes", icon: Server, scannerIds: ["kube_score", "trivy_config", "checkov"] },
  { key: "helm", label: "Helm", icon: Server, scannerIds: ["kube_score", "trivy_config", "checkov"] },
  { key: "github_actions", label: "GitHub Actions", icon: Globe, scannerIds: ["gitleaks"] },
  { key: "gitlab_ci", label: "GitLab CI", icon: Globe, scannerIds: ["gitleaks"] },
  { key: "jenkins", label: "Jenkins", icon: Globe, scannerIds: ["gitleaks"] },
  { key: "circleci", label: "CircleCI", icon: Globe, scannerIds: ["gitleaks"] },
  { key: "azure_devops", label: "Azure DevOps", icon: Globe, scannerIds: ["gitleaks"] },
  { key: "travis_ci", label: "Travis CI", icon: Globe, scannerIds: ["gitleaks"] },
  { key: "drone_ci", label: "Drone CI", icon: Globe, scannerIds: ["gitleaks"] },
  { key: "docker_compose", label: "Docker Compose", icon: Cloud, scannerIds: ["hadolint", "trivy_filesystem", "checkov"] },
  { key: "ansible", label: "Ansible", icon: Package2, scannerIds: ["checkov"] },
  { key: "secrets", label: "Secret Detection", icon: Lock, scannerIds: ["gitleaks"] },
  { key: "dependencies", label: "Dependencies", icon: Package2, scannerIds: ["npm_audit", "pip_audit", "govulncheck", "dependency_check"] },
  { key: "aws", label: "AWS", icon: Cloud, scannerIds: ["checkov", "trivy_config"] },
  { key: "azure", label: "Azure", icon: Cloud, scannerIds: ["checkov", "trivy_config"] },
  { key: "gcp", label: "GCP", icon: Cloud, scannerIds: ["checkov", "trivy_config"] },
]

const techIconMap: Record<string, typeof Shield> = {
  docker: Cloud, terraform: GanttChartSquare, kubernetes: Server,
  helm: Server, github_actions: Globe, gitlab_ci: Globe,
  jenkins: Globe, circleci: Globe, azure_devops: Globe,
  travis_ci: Globe, drone_ci: Globe, docker_compose: Cloud,
  ansible: Package2, secrets: Lock, dependencies: Package2,
  aws: Cloud, azure: Cloud, gcp: Cloud,
}

function getScannerStatusLabel(status: string): string {
  if (["COMPLETED", "COMPLETED_WITH_FINDINGS"].includes(status)) return "Completed"
  if (status === "COMPLETED_NO_FINDINGS") return "Clear"
  if (status === "SKIPPED_NOT_APPLICABLE") return "Not Applicable"
  if (status === "UNAVAILABLE" || status === "DISABLED") return "Unavailable"
  if (status === "FAILED") return "Failed"
  if (status === "RUNNING") return "Running"
  return status
}

function getStatusReason(exec: ScannerExecution): string {
  if (exec.status === "UNAVAILABLE") {
    return exec.skipped_reason ?? "CLI not installed"
  }
  if (exec.status === "DISABLED") {
    return exec.skipped_reason ?? "Scanner not enabled on current worker"
  }
  if (exec.status === "SKIPPED_NOT_APPLICABLE") {
    return exec.skipped_reason ?? "Not applicable"
  }
  if (exec.status === "FAILED") {
    return exec.error_message ?? ""
  }
  return ""
}

function matchFindingToTech(finding: Record<string, unknown>, techKey: string): boolean {
  const scannerName = ((finding.scanner_name as string) ?? "").toLowerCase()
  const filePath = ((finding.file_path as string) ?? "").toLowerCase()
  const category = ((finding.category as string) ?? "").toLowerCase()

  switch (techKey) {
    case "docker": {
      return scannerName.includes("hadolint") || filePath.includes("dockerfile") || filePath.includes("docker") || category === "RELIABILITY"
    }
    case "terraform": {
      return scannerName.includes("tfsec") || filePath.endsWith(".tf") || filePath.includes("terraform") || category === "SCALABILITY"
    }
    case "kubernetes": {
      return scannerName.includes("kube_score") || filePath.includes("k8s") || filePath.includes("kubernetes") || filePath.includes("deployment")
    }
    case "helm": {
      return filePath.includes("chart.yaml") || filePath.includes("helm") || filePath.includes("values.yaml")
    }
    case "github_actions": {
      return filePath.includes(".github/workflows")
    }
    case "gitlab_ci": {
      return filePath.includes(".gitlab-ci")
    }
    case "jenkins": {
      return filePath.includes("jenkinsfile") || filePath.includes("jenkins")
    }
    case "circleci": {
      return filePath.includes(".circleci")
    }
    case "azure_devops": {
      return filePath.includes("azure-pipelines")
    }
    case "docker_compose": {
      return filePath.includes("docker-compose") || filePath.includes("compose.yml")
    }
    case "ansible": {
      return filePath.includes("ansible") || filePath.includes("playbook") || filePath.includes("roles/")
    }
    case "secrets": {
      return scannerName.includes("gitleaks") || (category === "SECURITY" && (!!finding.cve || !!finding.cwe))
    }
    case "dependencies": {
      return scannerName.includes("npm_audit") || scannerName.includes("pip_audit") || scannerName.includes("govulncheck") || scannerName.includes("dependency_check") || !!finding.package
    }
    case "aws": {
      return filePath.includes("aws") || filePath.includes("ec2") || filePath.includes("s3") || filePath.includes("lambda")
    }
    case "azure": {
      return filePath.includes("azure") || filePath.includes("aks")
    }
    case "gcp": {
      return filePath.includes("gcp") || filePath.includes("gke") || filePath.includes("google")
    }
    default: {
      return false
    }
  }
}

function renderSeverityBadge(sev: string, count: number): React.ReactNode {
  const colors = getSeverityColor(sev)
  return (
    <span key={sev} className={cn("font-mono text-[10px]", colors.text)}>
      {count} {sev}
    </span>
  )
}

export function DetectionCoverage({ scannerExecutions = [], findings = [], detectedTechnologies = [], technologyDetails = [] }: DetectionCoverageProps) {
  const [expandedTech, setExpandedTech] = useState<string | null>(null)

  const techCards = useMemo(() => {
    const techSet = new Set<string>()

    // Start from detected technologies
    for (const tech of detectedTechnologies) {
      techSet.add(tech.toLowerCase().replace(/[\s-]+/g, "_"))
    }

    // Also add technologies implied by scanner executions
    for (const exec of scannerExecutions) {
      const techInfo = TECH_REGISTRY.find(t => t.scannerIds.includes(exec.scanner_id))
      if (techInfo) {
        techSet.add(techInfo.key)
      }
    }

    // If secrets scanner ran, add secrets
    if (scannerExecutions.some(e => e.scanner_id === "gitleaks")) {
      techSet.add("secrets")
    }

    // If dependency scanners ran, add dependencies
    if (scannerExecutions.some(e => ["npm_audit", "pip_audit", "govulncheck", "dependency_check"].includes(e.scanner_id))) {
      techSet.add("dependencies")
    }

    // Build a map of backend-provided technology details
    const techDetailsMap = new Map<string, typeof technologyDetails[number]>()
    for (const td of technologyDetails) {
      techDetailsMap.set(td.technology.toLowerCase().replace(/[\s-]+/g, "_"), td)
    }

    return Array.from(techSet).map(techKey => {
      const techInfo = TECH_REGISTRY.find(t => t.key === techKey)
      const label = techInfo?.label ?? techKey.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())
      const icon = techIconMap[techKey] ?? Shield
      const scannerIds = techInfo?.scannerIds ?? []

      // Find associated scanner executions
      const memberExecs = scannerExecutions.filter(e =>
        scannerIds.includes(e.scanner_id) ||
        // Fallback: match by name
        e.scanner_name.toLowerCase().includes(techKey.replace(/_/g, ""))
      )

      // Get backend-computed details if available
      const backendDetails = techDetailsMap.get(techKey)
      const filesCount = backendDetails?.files_count ?? 0

      // Find findings for this technology (use backend tech if available, else fallback to client-side)
      const typedFindings = findings as Record<string, unknown>[]
      const techFindings = backendDetails
        ? typedFindings.filter(f => {
            const fTech = ((f.technology as string) ?? "").toLowerCase()
            return fTech === techKey || fTech === techKey.replace(/_/g, "")
          })
        : typedFindings.filter(f => matchFindingToTech(f, techKey))

      // Build scanner info
      const scanners = memberExecs.map(exec => ({
        id: exec.scanner_id,
        name: exec.scanner_name,
        status: exec.status,
        findings: exec.findings_count ?? 0,
        reason: getStatusReason(exec),
      }))

      const activeScannerCount = scanners.filter(s =>
        ["COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS"].includes(s.status)
      ).length

      // Severity counts: prefer backend, fallback to client-side
      const sevCounts: Record<string, number> = backendDetails?.severity_counts ?? {}
      if (!backendDetails || Object.keys(sevCounts).length === 0) {
        for (const f of techFindings) {
          const sev = ((f.severity as string) ?? "info").toLowerCase()
          sevCounts[sev] = (sevCounts[sev] ?? 0) + 1
        }
      }

      // Determine status: prefer backend, fallback to client-side
      let scannerStatus: string
      if (backendDetails?.status) {
        scannerStatus = backendDetails.status
      } else if (techFindings.length > 0) {
        scannerStatus = "DETECTED"
      } else if (memberExecs.some(e => e.status === "RUNNING")) {
        scannerStatus = "RUNNING"
      } else if (memberExecs.some(e => e.status === "FAILED")) {
        scannerStatus = "FAILED"
      } else if (memberExecs.some(e => (e.status === "UNAVAILABLE" || e.status === "DISABLED") && !activeScannerCount)) {
        scannerStatus = "UNAVAILABLE"
      } else if (memberExecs.some(e => e.status === "SKIPPED_NOT_APPLICABLE") && !activeScannerCount) {
        scannerStatus = "NOT_APPLICABLE"
      } else {
        scannerStatus = "CLEAN"
      }

      return {
        key: techKey,
        label,
        icon,
        filesCount,
        techFindings,
        sevCounts,
        scannerCount: scanners.length,
        activeScannerCount,
        scannerStatus,
        scanners,
      }
    }).filter(card =>
      // Only show cards that have scanner executions, findings, or backend details
      card.scannerCount > 0 || card.techFindings.length > 0 || card.filesCount > 0
    )
  }, [scannerExecutions, findings, detectedTechnologies, technologyDetails])

  const totalTechFindings = techCards.reduce((s, c) => s + c.techFindings.length, 0)

  if (scannerExecutions.length === 0 && findings.length === 0 && detectedTechnologies.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-yellow-500/10 bg-yellow-500/[0.02] backdrop-blur-xl p-5"
      >
        <div className="flex items-center gap-2 mb-2">
          <Layers className="w-4 h-4 text-yellow-400/60" />
          <h3 className="text-sm font-semibold text-yellow-400/70 uppercase tracking-wider">
            Technology Coverage
          </h3>
        </div>
        <p className="text-xs text-yellow-300/40">
          Coverage data will appear after the scan completes.
        </p>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
            Technology Coverage
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-white/30">
          <span>{techCards.length} technologies</span>
          {totalTechFindings > 0 && (
            <>
              <span className="text-white/10">|</span>
              <span className="text-orange-400/70">
                {totalTechFindings} finding{totalTechFindings !== 1 ? "s" : ""}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {techCards.map((card, i) => {
          const isExpanded = expandedTech === card.key
          const statusCfg = CARD_STATUS[card.scannerStatus] ?? CARD_STATUS.CLEAN
          const StatusIcon = statusCfg.icon
          const hasSevBreakdown = SEVERITY_LABELS.some(s => (card.sevCounts[s] ?? 0) > 0)

          return (
            <motion.div
              key={card.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <div
                onClick={() => setExpandedTech(isExpanded ? null : card.key)}
                className={cn(
                  "rounded-xl border p-3.5 transition-all duration-200 cursor-pointer",
                  statusCfg.border,
                  "hover:border-white/20"
                )}
              >
                <div className="flex items-center gap-2 mb-2.5">
                  <div className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                    card.scannerStatus === "DETECTED" ? "bg-indigo-500/10" : "bg-white/[0.02]"
                  )}>
                    <card.icon className={cn(
                      "w-4 h-4",
                      card.scannerStatus === "DETECTED" ? "text-indigo-400" : "text-white/20"
                    )} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={cn(
                      "text-xs font-semibold leading-tight",
                      card.scannerStatus === "DETECTED" ? "text-white/80" : "text-white/40"
                    )}>
                      {card.label}
                    </div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <StatusIcon className={cn("w-2.5 h-2.5", statusCfg.color)} />
                      <span className={cn("text-[9px]", statusCfg.color)}>{statusCfg.label}</span>
                    </div>
                  </div>
                  <div className="shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5 text-white/20" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-white/20" />
                    )}
                  </div>
                </div>

                {/* Severity breakdown */}
                {hasSevBreakdown && (
                  <div className="flex flex-wrap gap-x-2 gap-y-0.5 mb-1.5">
                    {SEVERITY_LABELS.map(sev => {
                      const count = card.sevCounts[sev] ?? 0
                      if (count === 0) return null
                      return renderSeverityBadge(sev, count)
                    })}
                  </div>
                )}

                <div className="flex items-center gap-3 text-[10px]">
                  {card.filesCount > 0 ? (
                    <span className="font-mono font-bold text-indigo-400/80">
                      {card.filesCount} file{card.filesCount !== 1 ? "s" : ""}
                    </span>
                  ) : card.techFindings.length > 0 ? (
                    <span className="font-mono font-bold text-orange-400/80">
                      {card.techFindings.length} finding{card.techFindings.length !== 1 ? "s" : ""}
                    </span>
                  ) : (
                    <span className="text-emerald-400/50">No security issues</span>
                  )}
                  {card.scannerCount > 0 && (
                    <span className="text-white/30">
                      {card.activeScannerCount}/{card.scannerCount} scanners
                    </span>
                  )}
                </div>

                {card.scannerStatus === "UNAVAILABLE" && (
                  <div className="mt-2 text-[9px] text-zinc-400/60 italic leading-tight">
                    {card.scanners.some(s => s.id === "gitleaks" || s.id === "checkov")
                      ? `${card.scanners.find(s => s.id === "gitleaks" || s.id === "checkov")?.name} CLI not installed`
                      : "Scanner not enabled on current worker"}
                  </div>
                )}
                {card.scannerStatus === "NOT_APPLICABLE" && (
                  <div className="mt-2 text-[9px] text-amber-400/60 italic leading-tight">
                    Technology not detected in repository
                  </div>
                )}
              </div>

              {/* Expanded scanner details */}
              <AnimatePresence>
                {isExpanded && card.scanners.length > 0 && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-1 rounded-xl border border-white/10 bg-white/[0.03] overflow-hidden">
                      <table className="w-full text-[10px]">
                        <thead>
                          <tr className="border-b border-white/5">
                            <th className="text-left py-2 px-3 text-[9px] text-white/30 font-semibold uppercase tracking-wider">Scanner</th>
                            <th className="text-left py-2 px-3 text-[9px] text-white/30 font-semibold uppercase tracking-wider">Status</th>
                            <th className="text-right py-2 px-3 text-[9px] text-white/30 font-semibold uppercase tracking-wider">Findings</th>
                          </tr>
                        </thead>
                        <tbody>
                          {card.scanners.map(scanner => {
                            const isCompleted = ["COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS"].includes(scanner.status)
                            const isNA = scanner.status === "SKIPPED_NOT_APPLICABLE"
                            const isUnavail = scanner.status === "UNAVAILABLE" || scanner.status === "DISABLED"
                            const isFailed = scanner.status === "FAILED"
                            return (
                              <tr key={scanner.id} className="border-b border-white/[0.02] last:border-0">
                                <td className="py-2 px-3">
                                  <span className="text-white/70 font-medium">{scanner.name}</span>
                                </td>
                                <td className="py-2 px-3">
                                  <span className={cn(
                                    "inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-medium",
                                    isCompleted ? "text-emerald-400 bg-emerald-500/10" :
                                    isNA ? "text-amber-400 bg-amber-500/10" :
                                    isUnavail ? "text-zinc-400 bg-zinc-500/10" :
                                    isFailed ? "text-red-400 bg-red-500/10" :
                                    "text-white/30 bg-white/[0.03]"
                                  )}>
                                    {getScannerStatusLabel(scanner.status)}
                                  </span>
                                </td>
                                <td className="py-2 px-3 text-right">
                                  {isCompleted ? (
                                    scanner.findings > 0 ? (
                                      <span className="font-mono font-bold text-orange-400/80">{scanner.findings}</span>
                                    ) : (
                                      <span className="text-emerald-400/50">Clear</span>
                                    )
                                  ) : (
                                    <span className="text-white/20">—</span>
                                  )}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                      {card.scanners.some(s => s.reason) && (
                        <div className="px-3 py-2 border-t border-white/5 space-y-1">
                          {card.scanners.filter(s => s.reason).map(s => (
                            <div key={s.id} className="flex items-center gap-1.5 text-[9px] text-white/30">
                              <span className="text-white/50">{s.name}:</span>
                              <span>{s.reason}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

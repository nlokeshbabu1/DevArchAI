import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds % 1 === 0 ? seconds : seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

const GRADE_THRESHOLDS = [
  { min: 90, letter: 'A', color: 'text-emerald-400' },
  { min: 80, letter: 'B', color: 'text-emerald-300' },
  { min: 70, letter: 'C', color: 'text-yellow-400' },
  { min: 60, letter: 'D', color: 'text-orange-400' },
  { min: 0, letter: 'F', color: 'text-red-400' },
] as const

export function getGrade(score: number): string {
  return GRADE_THRESHOLDS.find(t => score >= t.min)?.letter ?? 'F'
}

export function getGradeColor(score: number): string {
  return GRADE_THRESHOLDS.find(t => score >= t.min)?.color ?? 'text-red-400'
}

export function relativeTime(dateStr: string): string {
  if (!dateStr) return 'N/A'
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  if (isNaN(then)) return 'N/A'
  const diff = Math.max(0, Math.floor((now - then) / 1000))
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function getSeverityColor(severity: string): { bg: string; text: string } {
  const colors: Record<string, { bg: string; text: string }> = {
    critical: { bg: 'bg-red-500/20', text: 'text-red-400' },
    high: { bg: 'bg-orange-500/20', text: 'text-orange-400' },
    medium: { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
    low: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    info: { bg: 'bg-gray-500/20', text: 'text-gray-400' },
  }
  return colors[severity] || colors.info
}

interface HasFindings {
  findings_count?: number
  total_findings?: number
  findings?: unknown[]
}

export function getFindingsCount(result: HasFindings | null | undefined): number {
  if (!result) return 0
  return result.total_findings ?? result.findings_count ?? result.findings?.length ?? 0
}

const BACKEND_PATH_RE = /^(\/tmp\/|\/home\/|\/app\/|\/var\/|\/etc\/|\/usr\/|\.\/)/
const INVALID_VALUES = [null, undefined, NaN, Infinity, -Infinity]

export function isValidValue(value: unknown): boolean {
  if (value === null || value === undefined) return false
  if (typeof value === 'number' && !Number.isFinite(value)) return false
  if (typeof value === 'string' && (!value.trim() || BACKEND_PATH_RE.test(value))) return false
  return true
}

export function sanitizeDisplay(value: unknown, fallback = '—'): string {
  if (!isValidValue(value)) return fallback
  if (typeof value === 'number') {
    if (value < 0 || value > 10000) return fallback
    return String(value)
  }
  const str = String(value).trim()
  if (BACKEND_PATH_RE.test(str)) return fallback
  return str
}

export function sanitizePath(filePath: string | null | undefined): string {
  if (!filePath) return ''
  const cleaned = filePath
    .replace(/^\/tmp\/[^/]+\//, '')
    .replace(/^\/home\/[^/]+\//, '')
    .replace(/^\/app\/[^/]*\//, '')
    .replace(/^\/var\/[^/]+\//, '')
    .replace(/^\.\//, '')
    .replace(/^[a-fA-F0-9]{8,}_/, '')
  return cleaned
}

export function getFileName(filePath: string | null | undefined): string {
  const path = sanitizePath(filePath)
  if (!path) return 'unknown'
  return path.split('/').pop() || path
}

export function isValidScore(score: number | null | undefined): score is number {
  return typeof score === 'number' && Number.isFinite(score) && score >= 0 && score <= 100
}

export function isValidPercentage(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100
}

// --- Clipboard ---

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch { /* fall through to legacy method */ }
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}

// --- Scanner family and source utilities ---

export interface ScannerFamilyDef {
  key: string
  label: string
  scannerIds: string[]
  icon: string
}

export const SCANNER_FAMILIES: ScannerFamilyDef[] = [
  {
    key: "container",
    label: "Container",
    scannerIds: ["hadolint", "trivy_filesystem", "trivy_config", "checkov"],
    icon: "cloud",
  },
  {
    key: "kubernetes",
    label: "Kubernetes",
    scannerIds: ["kube_score", "trivy_config", "checkov"],
    icon: "server",
  },
  {
    key: "iac",
    label: "Infrastructure Security",
    scannerIds: ["checkov", "tfsec"],
    icon: "git-branch",
  },
  {
    key: "secrets",
    label: "Secret Detection",
    scannerIds: ["gitleaks"],
    icon: "lock",
  },
  {
    key: "sca",
    label: "Dependency Security",
    scannerIds: ["npm_audit", "pip_audit", "govulncheck", "dependency_check"],
    icon: "shield",
  },
  {
    key: "cicd",
    label: "CI/CD",
    scannerIds: ["gitleaks"],
    icon: "globe",
  },
  {
    key: "dockerfile",
    label: "Dockerfile",
    scannerIds: ["hadolint", "checkov"],
    icon: "code",
  },
  {
    key: "sast",
    label: "Code Security",
    scannerIds: [],
    icon: "search",
  },
]

export function getFamilyForScanner(scannerId: string): string {
  for (const family of SCANNER_FAMILIES) {
    if (family.scannerIds.includes(scannerId)) return family.key
  }
  if (scannerId.startsWith("trivy")) return "container"
  return "sast"
}

export function getScannerFamilyLabel(key: string): string {
  return SCANNER_FAMILIES.find(f => f.key === key)?.label ?? key
}

export function parseScannerSources(scannerName: string | null | undefined): string[] {
  if (!scannerName) return ["DevArchAI"]
  return scannerName.split(",").map(s => s.trim()).filter(Boolean)
}

// Maps a finding to the correct scanner based on backend metadata (scanner_name), falling back to heuristic.

const CI_CD_FILES = [".github/", "workflow", "gitlab-ci", "jenkins", ".circleci", ".drone", "azure-pipelines"]

function classifyByRuleId(ruleId: string): string | null {
  const r = (ruleId || "").toLowerCase()
  if (r.startsWith("docker-") || r.startsWith("dock-") || /^sec-.*docker/i.test(r)) return "container"
  if (r.startsWith("k8s-") || r.startsWith("helm-") || r.startsWith("kubernetes-")) return "kubernetes"
  if (r.startsWith("tf-") || r.startsWith("terraform-")) return "iac"
  if (r.startsWith("cicd-") || r.startsWith("ci/cd-")) return "cicd"
  if (r.startsWith("secret") || r.includes("hardcoded_secret") || r.includes("credential")) return "secrets"
  if (r.startsWith("cve-") || r.startsWith("ckv_")) return "sca"
  return null
}

function classifyByFilePath(filePath: string, summary: string): string | null {
  const fp = (filePath || "").toLowerCase()
  const s = (summary || "").toLowerCase()

  if (fp.includes("dockerfile") || fp.includes("docker-compose") || fp.includes("container")) return "container"
  if (fp.includes("terraform") || fp.endsWith(".tf") || fp.endsWith(".tfvars") || fp.includes(".tfstate")) return "iac"
  if (fp.includes("kubernetes") || fp.includes("k8s") || fp.endsWith(".yaml") || fp.endsWith(".yml")) {
    if (CI_CD_FILES.some(ci => fp.includes(ci))) return "cicd"
    if (s.includes("network") || s.includes("pod") || s.includes("deployment") || s.includes("service") || s.includes("namespace") || s.includes("configmap")) return "kubernetes"
  }
  if (CI_CD_FILES.some(ci => fp.includes(ci))) return "cicd"
  return null
}

function classifyBySummary(summary: string): string | null {
  const s = (summary || "").toLowerCase()
  if (s.includes("docker") || s.includes("container") || s.includes("image tag") || s.includes("latest tag")) return "container"
  if (s.includes("terraform") || s.includes("state file") || s.includes("tfstate") || s.includes("backend")) return "iac"
  if (s.includes("kubernetes") || s.includes("k8s") || s.includes("helm chart") || s.includes("helm ")) return "kubernetes"
  if (s.includes("ci/cd") || s.includes("pipeline") || s.includes("cache") || s.includes("workflow") || (s.includes("ci ") && s.includes("cd"))) return "cicd"
  if (s.includes("secret") || s.includes("credential") || s.includes("hardcoded") || s.includes("api key") || s.includes("password") || s.includes("token")) return "secrets"
  if (s.includes("cve") || s.includes("vulnerability") || s.includes("npm") || s.includes("package") || s.includes("dependency")) return "sca"
  return null
}

export function classifyFindingScanner(finding: any): string {
  const ruleId = finding.rule_id || ""
  const filePath = finding.file_path || ""
  const summary = finding.summary || finding.message || finding.rule_name || ""

  const byRuleId = classifyByRuleId(ruleId)
  if (byRuleId) return byRuleId
  const byFilePath = classifyByFilePath(filePath, summary)
  if (byFilePath) return byFilePath
  const bySummary = classifyBySummary(summary)
  if (bySummary) return bySummary

  const scannerName = finding.scanner_name
  if (scannerName && typeof scannerName === "string" && scannerName.trim()) {
    const firstSource = scannerName.split(",")[0].trim()
    return getFamilyForScanner(firstSource.toLowerCase().replace(/\s+/g, "_"))
  }

  return "sast"
}

export const SCANNER_DEFINITIONS = [
  { key: "container", label: "Container Scanner", techKeys: ["Docker", "Docker Compose"] },
  { key: "kubernetes", label: "Kubernetes Scanner", techKeys: ["Kubernetes", "Helm"] },
  { key: "iac", label: "Infrastructure Security Scanner", techKeys: ["Terraform", "Ansible", "CloudFormation"] },
  { key: "cicd", label: "CI/CD Scanner", techKeys: ["GitHub Actions", "GitLab CI", "Jenkins", "CircleCI", "Drone CI", "Azure DevOps", "Travis CI"] },
  { key: "secrets", label: "Secret Detection Scanner", techKeys: [] },
  { key: "sast", label: "Code Security Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "sca", label: "Dependency Security Scanner", techKeys: [], defaultStatus: "disabled" as const },
  { key: "dast", label: "Dynamic Security Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "api_security", label: "API Security Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "license", label: "License Compliance Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "malware", label: "Malware Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
]

export function getRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "—"
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  if (isNaN(then)) return "—"
  const diff = Math.max(0, Math.floor((now - then) / 1000))
  if (diff < 60) return "Just now"
  if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`
  if (diff < 7200) return "1 hour ago"
  if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`
  if (diff < 172800) return "Yesterday"
  if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`
  if (diff < 2592000) return `${Math.floor(diff / 604800)} weeks ago`
  return `${Math.floor(diff / 2592000)} months ago`
}

export interface TechnologyDef {
  key: string
  label: string
  scannerIds: string[]
  detectionLabel: string
}

export const TECHNOLOGY_COVERAGE: TechnologyDef[] = [
  { key: "container", label: "Container", scannerIds: ["hadolint", "trivy_filesystem", "trivy", "checkov"], detectionLabel: "Docker detected" },
  { key: "dockerfile", label: "Dockerfile", scannerIds: ["hadolint", "checkov"], detectionLabel: "Dockerfile found" },
  { key: "kubernetes", label: "Kubernetes", scannerIds: ["kube_score", "trivy_config", "checkov"], detectionLabel: "K8s manifests found" },
  { key: "terraform", label: "Terraform", scannerIds: ["tfsec", "checkov"], detectionLabel: "Terraform configs found" },
  { key: "cicd", label: "CI/CD", scannerIds: ["gitleaks"], detectionLabel: "CI/CD pipelines detected" },
  { key: "secrets", label: "Secret Detection", scannerIds: ["gitleaks"], detectionLabel: "Secrets scanning enabled" },
  { key: "dependencies", label: "Dependencies", scannerIds: ["npm_audit", "pip_audit", "govulncheck", "dependency_check"], detectionLabel: "Dependencies detected" },
]

export function getTechnologiesForScanner(scannerId: string): string[] {
  return TECHNOLOGY_COVERAGE
    .filter(t => t.scannerIds.includes(scannerId))
    .map(t => t.key)
}

export const SCANNER_PURPOSE: Record<string, string> = {
  trivy: "Container vulnerabilities",
  trivy_filesystem: "Container & filesystem scanning",
  trivy_config: "Misconfiguration scanning",
  checkov: "IaC Security",
  hadolint: "Docker Best Practices",
  gitleaks: "Secrets Detection",
  tfsec: "Terraform Security",
  kube_score: "Kubernetes Best Practices",
  npm_audit: "Node Dependency Security",
  pip_audit: "Python Dependency Security",
  govulncheck: "Go Dependency Security",
  dependency_check: "Dependency Vulnerability Scanning",
}

export function getScannerPurpose(scannerId: string): string {
  return SCANNER_PURPOSE[scannerId] || "Security scanning"
}

export const SCANNER_TECHNOLOGIES: Record<string, string[]> = {
  trivy: ["Container", "OS Packages", "Language Packages", "Filesystem"],
  trivy_filesystem: ["Container", "Filesystem"],
  trivy_config: ["Kubernetes", "Terraform", "Docker", "Cloud"],
  checkov: ["Terraform", "Kubernetes", "Docker", "CloudFormation", "ARM"],
  hadolint: ["Dockerfile"],
  gitleaks: ["Git", "CI/CD", "Config Files"],
  tfsec: ["Terraform", "OpenTofu"],
  kube_score: ["Kubernetes", "Helm"],
  npm_audit: ["Node.js", "npm"],
  pip_audit: ["Python", "pip"],
  govulncheck: ["Go"],
  dependency_check: ["Java", ".NET", "Python", "Node.js", "Ruby"],
}

export function getScannerTechnologies(scannerId: string): string[] {
  return SCANNER_TECHNOLOGIES[scannerId] || []
}

// Scanners that improve coverage but are not required for basic operation
const OPTIONAL_SCANNERS = new Set([
  "gitleaks", "hadolint", "kube_score", "tfsec",
  "govulncheck", "dependency_check", "pip_audit",
])

export function isScannerOptional(scannerId: string): boolean {
  return OPTIONAL_SCANNERS.has(scannerId)
}

const CLASSIFICATION_TO_TECH: Record<string, string> = {
  container: "container",
  iac: "terraform",
  kubernetes: "kubernetes",
  cicd: "cicd",
  secrets: "secrets",
  sca: "dependencies",
}

export function classifyFindingTechnology(finding: any): string {
  const classification = classifyFindingScanner(finding)
  const scannerName = (finding.scanner_name || "").toLowerCase()
  if (scannerName.includes("hadolint")) return "dockerfile"
  return CLASSIFICATION_TO_TECH[classification] || "container"
}

export function getTechnologySeverityCounts(findings: any[], techKey: string): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const f of findings) {
    if (classifyFindingTechnology(f) === techKey) {
      const sev = (f.severity || "info").toLowerCase()
      counts[sev] = (counts[sev] || 0) + 1
    }
  }
  return counts
}

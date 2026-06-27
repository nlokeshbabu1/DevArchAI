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

// --- Scanner mapping utilities ---
// Maps a finding to the correct scanner based on rule_id, file_path, and summary.

const CI_CD_FILES = [".github/", "workflow", "gitlab-ci", "jenkins", ".circleci", ".drone", "azure-pipelines"]
const CI_CD_EXTENSIONS = [".github/workflows/", ".gitlab-ci.yml", "Jenkinsfile"]

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

  return classifyByRuleId(ruleId)
    ?? classifyByFilePath(filePath, summary)
    ?? classifyBySummary(summary)
    ?? "sast"
}

export function mapCategoryToScanner(category: string): string {
  const c = (category || "").toLowerCase()
  if (c === "security") return "sast"
  if (c === "scalability") return "sast"
  if (c === "reliability") return "sast"
  if (c === "cost") return "sast"
  if (c === "observability") return "sast"
  return c
}

export const SCANNER_DEFINITIONS = [
  { key: "container", label: "Container Scanner", techKeys: ["Docker", "Docker Compose"] },
  { key: "kubernetes", label: "Kubernetes Scanner", techKeys: ["Kubernetes", "Helm"] },
  { key: "iac", label: "IaC Scanner", techKeys: ["Terraform", "Ansible", "CloudFormation"] },
  { key: "cicd", label: "CI/CD Scanner", techKeys: ["GitHub Actions", "GitLab CI", "Jenkins", "CircleCI", "Drone CI", "Azure DevOps", "Travis CI"] },
  { key: "secrets", label: "Secret Scanner", techKeys: [] },
  { key: "sast", label: "SAST Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "sca", label: "SCA Scanner", techKeys: [], defaultStatus: "disabled" as const },
  { key: "dast", label: "DAST Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "api_security", label: "API Security Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "license", label: "License Compliance Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
  { key: "malware", label: "Malware Scanner", techKeys: [], defaultStatus: "coming_soon" as const },
]

export function getScannerStatus(scannerKey: string, detectedTechnologies: string[]): "active" | "coming_soon" | "disabled" {
  const def = SCANNER_DEFINITIONS.find(s => s.key === scannerKey)
  if (!def) return "disabled"

  if (def.defaultStatus) return def.defaultStatus

  if (scannerKey === "secrets") return "active"

  return def.techKeys.some(t => detectedTechnologies.includes(t)) ? "active" : "disabled"
}

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

import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
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

export function isValidScore(score: number | null | undefined): score is number {
  return typeof score === 'number' && Number.isFinite(score) && score >= 0 && score <= 100
}

export function isValidPercentage(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100
}

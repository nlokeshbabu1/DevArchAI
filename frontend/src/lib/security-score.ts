/**
 * Canonical security score resolution for DevArchAI.
 *
 * Backend contract (scan_repository.py):
 * - `overall_score` — composite score from the scoring engine
 * - `security_score` — SECURITY category score only
 *
 * Product rule: display "Security Score" using `security_score` when present,
 * otherwise fall back to `overall_score`. Never show both as competing values.
 */

import { getGrade, getGradeColor, isValidScore } from './utils'

export interface ScoreSource {
  security_score?: number | null
  overall_score?: number | null
}

export interface ResolvedSecurityScore {
  value: number
  grade: string
  gradeColor: string
  source: 'security_score' | 'overall_score'
  label: string
}

export function resolveSecurityScore(
  data: ScoreSource | null | undefined,
): ResolvedSecurityScore | null {
  if (!data) return null

  if (isValidScore(data.security_score)) {
    const value = Math.round(data.security_score * 10) / 10
    return {
      value,
      grade: getGrade(value),
      gradeColor: getGradeColor(value),
      source: 'security_score',
      label: 'Security Score',
    }
  }

  if (isValidScore(data.overall_score)) {
    const value = Math.round(data.overall_score * 10) / 10
    return {
      value,
      grade: getGrade(value),
      gradeColor: getGradeColor(value),
      source: 'overall_score',
      label: 'Security Score',
    }
  }

  return null
}

export function formatSecurityScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

import { describe, expect, it } from 'vitest'

import { formatSecurityScore, resolveSecurityScore } from './security-score'

describe('resolveSecurityScore', () => {
  it('prefers security_score over overall_score', () => {
    const resolved = resolveSecurityScore({ security_score: 80, overall_score: 86 })
    expect(resolved?.value).toBe(80)
    expect(resolved?.source).toBe('security_score')
  })

  it('falls back to overall_score when security_score is missing', () => {
    const resolved = resolveSecurityScore({ overall_score: 86 })
    expect(resolved?.value).toBe(86)
    expect(resolved?.source).toBe('overall_score')
  })

  it('returns null for invalid scores', () => {
    expect(resolveSecurityScore({ security_score: -1, overall_score: 101 })).toBeNull()
    expect(resolveSecurityScore(null)).toBeNull()
  })
})

describe('formatSecurityScore', () => {
  it('formats integers without decimals', () => {
    expect(formatSecurityScore(80)).toBe('80')
  })

  it('formats fractional scores to one decimal', () => {
    expect(formatSecurityScore(86.25)).toBe('86.3')
  })
})

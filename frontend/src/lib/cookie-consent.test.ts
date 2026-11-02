import { describe, it, expect, beforeEach } from 'vitest'

import {
  CONSENT_STORAGE_KEY,
  CONSENT_VERSION,
  persistConsent,
  readStoredConsent,
  ESSENTIAL_ONLY_CONSENT,
  ALL_OPTIONAL_CONSENT,
} from './cookie-consent'

describe('cookie consent', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('persists accept-all choices', () => {
    persistConsent(ALL_OPTIONAL_CONSENT)
    const stored = readStoredConsent()
    expect(stored?.version).toBe(CONSENT_VERSION)
    expect(stored?.choices.analytics).toBe(true)
    expect(stored?.choices.essential).toBe(true)
  })

  it('persists reject-optional choices', () => {
    persistConsent(ESSENTIAL_ONLY_CONSENT)
    const stored = readStoredConsent()
    expect(stored?.choices.functional).toBe(false)
    expect(stored?.choices.essential).toBe(true)
  })

  it('stores under versioned key', () => {
    persistConsent(ESSENTIAL_ONLY_CONSENT)
    expect(window.localStorage.getItem(CONSENT_STORAGE_KEY)).toBeTruthy()
  })
})

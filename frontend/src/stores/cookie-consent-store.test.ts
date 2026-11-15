import { describe, it, expect, beforeEach } from 'vitest'

import {
  ALL_OPTIONAL_CONSENT,
  CONSENT_STORAGE_KEY,
  CONSENT_VERSION,
  ESSENTIAL_ONLY_CONSENT,
} from '../lib/cookie-consent'

import { useCookieConsentStore } from './cookie-consent-store'

function resetStore() {
  window.localStorage.clear()
  useCookieConsentStore.setState({
    status: 'undecided',
    choices: { essential: true, functional: false, analytics: false, advertising: false },
    customizeOpen: false,
  })
}

describe('Cookie Consent Store', () => {
  beforeEach(() => {
    resetStore()
  })

  it('initializes as undecided when no stored preference', () => {
    expect(useCookieConsentStore.getState().status).toBe('undecided')
    expect(useCookieConsentStore.getState().choices).toEqual({
      essential: true,
      functional: false,
      analytics: false,
      advertising: false,
    })
  })

  it('hydrates decided state from localStorage on acceptAll', () => {
    useCookieConsentStore.getState().acceptAll()
    expect(useCookieConsentStore.getState().status).toBe('decided')
    expect(useCookieConsentStore.getState().choices).toEqual(ALL_OPTIONAL_CONSENT)

    const raw = window.localStorage.getItem(CONSENT_STORAGE_KEY)
    expect(raw).toBeTruthy()
    const parsed = JSON.parse(raw!) as { version: number; choices: typeof ALL_OPTIONAL_CONSENT }
    expect(parsed.version).toBe(CONSENT_VERSION)
    expect(parsed.choices.analytics).toBe(true)
  })

  it('rejectOptional persists essential-only choices', () => {
    useCookieConsentStore.getState().rejectOptional()
    expect(useCookieConsentStore.getState().status).toBe('decided')
    expect(useCookieConsentStore.getState().choices).toEqual(ESSENTIAL_ONLY_CONSENT)

    const stored = window.localStorage.getItem(CONSENT_STORAGE_KEY)
    expect(stored).toContain('"analytics":false')
    expect(stored).toContain('"essential":true')
  })

  it('saveCustom persists customized optional categories', () => {
    useCookieConsentStore.getState().setCategory('analytics', true)
    useCookieConsentStore.getState().setCategory('functional', true)
    useCookieConsentStore.getState().saveCustom()

    expect(useCookieConsentStore.getState().status).toBe('decided')
    expect(useCookieConsentStore.getState().choices.analytics).toBe(true)
    expect(useCookieConsentStore.getState().choices.functional).toBe(true)
    expect(useCookieConsentStore.getState().choices.advertising).toBe(false)
  })

  it('does not toggle essential category via setCategory', () => {
    useCookieConsentStore.getState().setCategory('essential', false)
    expect(useCookieConsentStore.getState().choices.essential).toBe(true)
  })

  it('reopenSettings opens customize when a valid record exists', () => {
    useCookieConsentStore.getState().acceptAll()
    useCookieConsentStore.setState({ customizeOpen: false })
    useCookieConsentStore.getState().reopenSettings()
    expect(useCookieConsentStore.getState().customizeOpen).toBe(true)
  })
})

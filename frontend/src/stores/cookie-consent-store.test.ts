import { describe, it, expect, beforeEach } from 'vitest'
import { useCookieConsentStore } from './cookie-consent-store'

describe('Cookie Consent Store', () => {
  beforeEach(() => {
    window.localStorage.clear()
    useCookieConsentStore.setState({ status: 'undecided' })
  })

  it('initializes as undecided when no stored preference', () => {
    expect(useCookieConsentStore.getState().status).toBe('undecided')
  })

  it('accept persists the preference to localStorage', () => {
    useCookieConsentStore.getState().accept()
    expect(useCookieConsentStore.getState().status).toBe('accepted')
    expect(window.localStorage.getItem('devarchai:cookie-consent')).toBe('accepted')
  })

  it('reject persists the preference to localStorage', () => {
    useCookieConsentStore.getState().reject()
    expect(useCookieConsentStore.getState().status).toBe('rejected')
    expect(window.localStorage.getItem('devarchai:cookie-consent')).toBe('rejected')
  })
})

import '@testing-library/jest-dom'

import { CONSENT_STORAGE_KEY } from '../lib/cookie-consent'
import { fireEvent, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { CookieConsentBanner } from '../components/CookieConsentBanner'
import { useCookieConsentStore } from '../stores/cookie-consent-store'

import { renderWithProviders } from './test-utils'

describe('integration: cookie consent persistence', () => {
  beforeEach(() => {
    window.localStorage.clear()
    useCookieConsentStore.setState({
      status: 'undecided',
      choices: { essential: true, functional: false, analytics: false, advertising: false },
      customizeOpen: false,
    })
  })

  it('shows banner until user accepts and persists v2 consent record', () => {
    renderWithProviders(<CookieConsentBanner />)

    expect(screen.getByRole('button', { name: /accept all/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /accept all/i }))

    expect(useCookieConsentStore.getState().status).toBe('decided')
    const stored = window.localStorage.getItem(CONSENT_STORAGE_KEY)
    expect(stored).toBeTruthy()
    expect(JSON.parse(stored!).version).toBe(2)
    expect(useCookieConsentStore.getState().customizeOpen).toBe(false)
  })

  it('re-hydrates decided state from localStorage on remount', () => {
    useCookieConsentStore.getState().acceptAll()

    renderWithProviders(<CookieConsentBanner />)
    expect(screen.queryByRole('button', { name: /accept all/i })).not.toBeInTheDocument()
  })
})

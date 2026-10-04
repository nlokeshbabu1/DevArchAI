import { create } from 'zustand'

const CONSENT_STORAGE_KEY = 'devarchai:cookie-consent'

type ConsentStatus = 'undecided' | 'accepted' | 'rejected'

interface CookieConsentState {
  status: ConsentStatus
  accept: () => void
  reject: () => void
}

function readStoredStatus(): ConsentStatus {
  if (typeof window === 'undefined') {
    return 'undecided'
  }
  try {
    const stored = window.localStorage.getItem(CONSENT_STORAGE_KEY)
    if (stored === 'accepted' || stored === 'rejected') {
      return stored
    }
  } catch {
    // localStorage unavailable (e.g. blocked); treat as undecided.
    return 'undecided'
  }
  return 'undecided'
}

export const useCookieConsentStore = create<CookieConsentState>()((set) => ({
  status: readStoredStatus(),

  accept: () => {
    try {
      window.localStorage.setItem(CONSENT_STORAGE_KEY, 'accepted')
    } catch {
      // ignore storage failures
    }
    set({ status: 'accepted' })
  },

  reject: () => {
    try {
      window.localStorage.setItem(CONSENT_STORAGE_KEY, 'rejected')
    } catch {
      // ignore storage failures
    }
    set({ status: 'rejected' })
  },
}))

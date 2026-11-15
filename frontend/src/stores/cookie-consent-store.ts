import { create } from 'zustand'

import {
  ALL_OPTIONAL_CONSENT,
  CONSENT_VERSION,
  DEFAULT_CONSENT,
  ESSENTIAL_ONLY_CONSENT,
  type ConsentCategory,
  type ConsentChoices,
  hasValidConsentRecord,
  persistConsent,
  readStoredConsent,
} from '../lib/cookie-consent'

type ConsentUiStatus = 'undecided' | 'decided'

interface CookieConsentState {
  status: ConsentUiStatus
  choices: ConsentChoices
  customizeOpen: boolean
  acceptAll: () => void
  rejectOptional: () => void
  openCustomize: () => void
  closeCustomize: () => void
  setCategory: (category: ConsentCategory, enabled: boolean) => void
  saveCustom: () => void
  reopenSettings: () => void
}

function loadInitial(): { status: ConsentUiStatus; choices: ConsentChoices } {
  const stored = readStoredConsent()
  if (stored) {
    return { status: 'decided', choices: stored.choices }
  }
  return { status: 'undecided', choices: DEFAULT_CONSENT }
}

const initial = loadInitial()

export const useCookieConsentStore = create<CookieConsentState>()((set, get) => ({
  status: initial.status,
  choices: initial.choices,
  customizeOpen: false,

  acceptAll: () => {
    const record = persistConsent(ALL_OPTIONAL_CONSENT)
    set({ status: 'decided', choices: record.choices, customizeOpen: false })
  },

  rejectOptional: () => {
    const record = persistConsent(ESSENTIAL_ONLY_CONSENT)
    set({ status: 'decided', choices: record.choices, customizeOpen: false })
  },

  openCustomize: () => set({ customizeOpen: true }),

  closeCustomize: () => set({ customizeOpen: false }),

  setCategory: (category, enabled) => {
    if (category === 'essential') {
      return
    }
    set((state) => ({
      choices: {
        ...state.choices,
        [category]: enabled,
      },
    }))
  },

  saveCustom: () => {
    const record = persistConsent(get().choices)
    set({ status: 'decided', choices: record.choices, customizeOpen: false })
  },

  reopenSettings: () => {
    if (!hasValidConsentRecord()) {
      set({ status: 'undecided', customizeOpen: false })
      return
    }
    set({ customizeOpen: true })
  },
}))

export function consentVersion(): number {
  return CONSENT_VERSION
}

export const CONSENT_STORAGE_KEY = 'devarchai:cookie-consent-v2'
export const CONSENT_VERSION = 2

export type ConsentCategory = 'essential' | 'functional' | 'analytics' | 'advertising'

export type ConsentChoices = Record<ConsentCategory, boolean>

export interface StoredConsent {
  version: number
  choices: ConsentChoices
  updatedAt: string
}

export const DEFAULT_CONSENT: ConsentChoices = {
  essential: true,
  functional: false,
  analytics: false,
  advertising: false,
}

export const ALL_OPTIONAL_CONSENT: ConsentChoices = {
  essential: true,
  functional: true,
  analytics: true,
  advertising: true,
}

export const ESSENTIAL_ONLY_CONSENT: ConsentChoices = {
  essential: true,
  functional: false,
  analytics: false,
  advertising: false,
}

export function readStoredConsent(): StoredConsent | null {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    const raw = window.localStorage.getItem(CONSENT_STORAGE_KEY)
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as StoredConsent
    if (parsed.version !== CONSENT_VERSION || !parsed.choices) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function persistConsent(choices: ConsentChoices): StoredConsent {
  const record: StoredConsent = {
    version: CONSENT_VERSION,
    choices: { ...choices, essential: true },
    updatedAt: new Date().toISOString(),
  }
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(record))
  }
  return record
}

export function hasValidConsentRecord(): boolean {
  return readStoredConsent() !== null
}

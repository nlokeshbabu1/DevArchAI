import { motion, AnimatePresence } from 'framer-motion'
import { Cookie, X } from 'lucide-react'

import { useCookieConsentStore } from '../stores/cookie-consent-store'
import type { ConsentCategory } from '../lib/cookie-consent'

const CATEGORY_COPY: Record<
  ConsentCategory,
  { label: string; description: string; optional: boolean }
> = {
  essential: {
    label: 'Essential',
    description: 'Required for sign-in, security, and core application functionality.',
    optional: false,
  },
  functional: {
    label: 'Functional',
    description: 'Remembers preferences such as theme and UI settings.',
    optional: true,
  },
  analytics: {
    label: 'Analytics',
    description: 'Helps us understand product usage so we can improve DevArchAI.',
    optional: true,
  },
  advertising: {
    label: 'Advertising',
    description: 'Optional marketing or advertising measurement (not used by DevArchAI today).',
    optional: true,
  },
}

export function CookieConsentBanner() {
  const status = useCookieConsentStore((s) => s.status)
  const choices = useCookieConsentStore((s) => s.choices)
  const customizeOpen = useCookieConsentStore((s) => s.customizeOpen)
  const acceptAll = useCookieConsentStore((s) => s.acceptAll)
  const rejectOptional = useCookieConsentStore((s) => s.rejectOptional)
  const openCustomize = useCookieConsentStore((s) => s.openCustomize)
  const closeCustomize = useCookieConsentStore((s) => s.closeCustomize)
  const setCategory = useCookieConsentStore((s) => s.setCategory)
  const saveCustom = useCookieConsentStore((s) => s.saveCustom)

  const showBanner = status === 'undecided' && !customizeOpen

  return (
    <>
      <AnimatePresence>
        {showBanner && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="fixed bottom-4 left-4 right-4 sm:left-6 sm:right-auto sm:max-w-lg z-[300]"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cookie-consent-title"
          >
            <div className="rounded-2xl border border-white/10 bg-card/95 backdrop-blur-xl shadow-2xl p-5">
              <div className="flex items-start gap-3">
                <div className="shrink-0 h-9 w-9 rounded-xl bg-primary/15 flex items-center justify-center">
                  <Cookie className="h-4 w-4 text-primary" aria-hidden />
                </div>
                <div className="flex-1">
                  <h2 id="cookie-consent-title" className="text-sm font-semibold text-foreground mb-1">
                    Cookie preferences
                  </h2>
                  <p className="text-[13px] leading-relaxed text-slate-400">
                    We use essential cookies for secure sign-in and session protection. Optional cookies
                    are used only if you allow them. Authentication is independent of optional consent.
                  </p>
                </div>
              </div>

              <div className="mt-4 flex flex-col sm:flex-row gap-2">
                <button
                  type="button"
                  onClick={acceptAll}
                  className="flex-1 rounded-xl bg-primary text-white text-sm font-semibold py-2.5 hover:bg-primary/90 transition-colors"
                >
                  Accept All
                </button>
                <button
                  type="button"
                  onClick={rejectOptional}
                  className="flex-1 rounded-xl border border-white/10 text-slate-300 text-sm font-medium py-2.5 hover:bg-white/5 transition-colors"
                >
                  Reject Optional
                </button>
                <button
                  type="button"
                  onClick={openCustomize}
                  className="flex-1 rounded-xl border border-white/10 text-slate-300 text-sm font-medium py-2.5 hover:bg-white/5 transition-colors"
                >
                  Customize
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {customizeOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[301] flex items-end sm:items-center justify-center p-4 bg-black/60"
            role="presentation"
          >
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 16 }}
              className="w-full max-w-lg rounded-2xl border border-white/10 bg-card shadow-2xl p-6"
              role="dialog"
              aria-modal="true"
              aria-labelledby="cookie-customize-title"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 id="cookie-customize-title" className="text-lg font-semibold text-foreground">
                  Customize cookies
                </h2>
                <button
                  type="button"
                  onClick={closeCustomize}
                  className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5"
                  aria-label="Close cookie settings"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <ul className="space-y-4 mb-6">
                {(Object.keys(CATEGORY_COPY) as ConsentCategory[]).map((key) => {
                  const meta = CATEGORY_COPY[key]
                  const checked = choices[key]
                  return (
                    <li key={key} className="flex items-start justify-between gap-4 border-b border-white/5 pb-4 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-foreground">{meta.label}</p>
                        <p className="text-xs text-muted-foreground mt-1">{meta.description}</p>
                        <p className="text-[11px] text-muted-foreground/80 mt-1">
                          {meta.optional ? 'Optional' : 'Always enabled'}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={!meta.optional}
                        onChange={(e) => setCategory(key, e.target.checked)}
                        aria-label={`${meta.label} cookies`}
                        className="mt-1 h-4 w-4 rounded border-white/20"
                      />
                    </li>
                  )
                })}
              </ul>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={saveCustom}
                  className="flex-1 rounded-xl bg-primary text-white text-sm font-semibold py-2.5"
                >
                  Save preferences
                </button>
                <button
                  type="button"
                  onClick={() => {
                    rejectOptional()
                    closeCustomize()
                  }}
                  className="flex-1 rounded-xl border border-white/10 text-sm py-2.5"
                >
                  Essential only
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

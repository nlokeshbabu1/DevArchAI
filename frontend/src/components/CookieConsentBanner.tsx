import { motion, AnimatePresence } from 'framer-motion'
import { Cookie } from 'lucide-react'

import { useCookieConsentStore } from '../stores/cookie-consent-store'

export function CookieConsentBanner() {
  const status = useCookieConsentStore((s) => s.status)
  const accept = useCookieConsentStore((s) => s.accept)
  const reject = useCookieConsentStore((s) => s.reject)

  const visible = status === 'undecided'

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="fixed bottom-4 left-4 right-4 sm:left-6 sm:right-auto sm:max-w-md z-[300]"
          role="region"
          aria-label="Cookie consent"
        >
          <div className="rounded-2xl border border-white/10 bg-card/95 backdrop-blur-xl shadow-2xl p-5">
            <div className="flex items-start gap-3">
              <div className="shrink-0 h-9 w-9 rounded-xl bg-primary/15 flex items-center justify-center">
                <Cookie className="h-4.5 w-4.5 text-primary" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-foreground mb-1">We use cookies</h3>
                <p className="text-[13px] leading-relaxed text-slate-400">
                  DevArchAI uses an essential session cookie to keep you signed in securely.
                  By accepting, you allow us to store your login session. You can reject this if
                  you prefer, but you won&apos;t remain signed in across page reloads.
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={accept}
                className="w-full rounded-xl bg-primary text-white text-sm font-semibold py-2.5 hover:bg-primary/90 transition-colors"
              >
                Accept cookies
              </button>
              <button
                type="button"
                onClick={reject}
                className="w-full rounded-xl border border-white/10 text-slate-300 text-sm font-medium py-2.5 hover:bg-white/5 hover:text-white transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

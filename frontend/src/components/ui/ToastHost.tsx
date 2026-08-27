import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react'
import { useToast } from '../../hooks/useToast'
import { cn } from '../../lib/utils'

export function ToastHost() {
  const { toasts, dismiss } = useToast()

  return (
    <div
      className="fixed top-4 right-4 z-[200] flex flex-col gap-2 max-w-sm pointer-events-none"
      aria-live="polite"
      aria-relevant="additions"
    >
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 24, scale: 0.96 }}
            className={cn(
              'pointer-events-auto flex items-start gap-2 rounded-xl border px-3 py-2.5 shadow-lg backdrop-blur-xl text-sm',
              t.type === 'success' && 'border-emerald-500/30 bg-emerald-500/15 text-emerald-100',
              t.type === 'error' && 'border-red-500/30 bg-red-500/15 text-red-100',
              t.type === 'info' && 'border-white/10 bg-card/95 text-foreground',
            )}
          >
            {t.type === 'success' && <CheckCircle className="h-4 w-4 shrink-0 mt-0.5 text-emerald-400" />}
            {t.type === 'error' && <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-400" />}
            {t.type === 'info' && <Info className="h-4 w-4 shrink-0 mt-0.5 text-primary" />}
            <span className="flex-1">{t.message}</span>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="text-white/40 hover:text-white/80 transition-colors"
              aria-label="Dismiss notification"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

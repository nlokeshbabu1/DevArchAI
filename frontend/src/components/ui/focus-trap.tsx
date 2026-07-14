import { useEffect, useRef, useCallback, type ReactNode } from 'react'

interface FocusTrapProps {
  active: boolean
  onClose?: () => void
  children: ReactNode
  restoreFocus?: boolean
}

export function FocusTrap({ active, onClose, children, restoreFocus = true }: FocusTrapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (active) {
      previousFocusRef.current = document.activeElement as HTMLElement
      const container = containerRef.current
      if (container) {
        const focusable = container.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        focusable?.focus()
      }
    } else if (restoreFocus && previousFocusRef.current) {
      previousFocusRef.current.focus()
    }
  }, [active, restoreFocus])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && onClose) {
      onClose()
      return
    }
    if (e.key !== 'Tab') return
    const container = containerRef.current
    if (!container) return
    const focusable = Array.from(
      container.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    )
    if (focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }, [onClose])

  if (!active) return null

  return (
    <div ref={containerRef} onKeyDown={handleKeyDown} role="dialog" aria-modal="true">
      {children}
    </div>
  )
}

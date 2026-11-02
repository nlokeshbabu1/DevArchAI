import type { SelectHTMLAttributes } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '../../lib/utils'

const selectSurfaceClass =
  'appearance-none rounded-lg border border-white/10 bg-white/5 py-2 pl-3 pr-9 text-sm text-foreground shadow-sm ' +
  'outline-none transition-colors cursor-pointer ' +
  'hover:bg-white/[0.07] hover:border-white/15 ' +
  'focus:border-primary/50 focus:ring-2 focus:ring-primary/30 ' +
  'disabled:cursor-not-allowed disabled:opacity-50'

const optionClass = 'bg-slate-950 text-slate-100'

export type NativeSelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  wrapperClassName?: string
}

/** Themed native select for dark UI (dropdown list styling is browser-dependent). */
export function NativeSelect({
  className,
  wrapperClassName,
  children,
  ...props
}: NativeSelectProps) {
  return (
    <div className={cn('relative inline-flex min-w-[10rem]', wrapperClassName)}>
      <select {...props} className={cn(selectSurfaceClass, className)}>
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden
      />
    </div>
  )
}

export function nativeSelectOptionProps(className?: string) {
  return { className: cn(optionClass, className) }
}

export { optionClass as nativeSelectOptionClass, selectSurfaceClass as nativeSelectSurfaceClass }

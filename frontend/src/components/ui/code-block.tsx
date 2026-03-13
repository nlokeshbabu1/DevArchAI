import { cn } from '../../lib/utils'

interface CodeBlockProps {
  code: string
  language?: string
  title?: string
  showLineNumbers?: boolean
  className?: string
}

export function CodeBlock({
  code,
  language = 'text',
  title,
  showLineNumbers = true,
  className,
}: CodeBlockProps) {
  const lines = code.split('\n')

  return (
    <div className={cn(
      'rounded-xl overflow-hidden border border-white/10 bg-black/40 backdrop-blur-sm',
      className
    )}>
      {title && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-white/5">
          <div className="flex items-center gap-2">
            <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span className="text-sm font-medium text-muted-foreground">{title}</span>
          </div>
          <span className="text-xs text-muted-foreground uppercase">{language}</span>
        </div>
      )}
      <div className="p-4 overflow-x-auto">
        <pre className="text-sm font-mono">
          <code>
            {lines.map((line, index) => (
              <div key={index} className="flex">
                {showLineNumbers && (
                  <span className="text-muted-foreground select-none w-8 text-right pr-4 flex-shrink-0">
                    {index + 1}
                  </span>
                )}
                <span className="text-foreground">{line}</span>
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  )
}

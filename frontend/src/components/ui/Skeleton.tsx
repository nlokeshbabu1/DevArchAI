import { cn } from '../../lib/utils'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-white/10',
        className
      )}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/10 bg-card/50 p-6 space-y-4">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <div className="flex items-center gap-4 pt-4">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-24" />
      </div>
    </div>
  )
}

export function SkeletonTable() {
  return (
    <div className="rounded-xl border border-white/10 bg-card/50 p-6 space-y-4">
      <Skeleton className="h-8 w-1/3" />
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    </div>
  )
}

export function SkeletonChart() {
  return (
    <div className="rounded-xl border border-white/10 bg-card/50 p-6 space-y-4">
      <Skeleton className="h-8 w-1/4" />
      <Skeleton className="h-[300px] w-full" />
    </div>
  )
}

export function SkeletonStatCard() {
  return (
    <div className="rounded-xl border border-white/10 bg-card/50 p-6 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
    </div>
  )
}

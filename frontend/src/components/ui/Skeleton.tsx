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

export function StatCardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 bg-card/60 p-6">
      <div className="flex items-start justify-between">
        <div className="space-y-3 flex-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-10 w-10 rounded-xl" />
      </div>
    </div>
  )
}

export function TableRowSkeleton() {
  return (
    <div className="flex items-center gap-4 p-4 border-b border-white/10">
      <Skeleton className="h-6 w-16 rounded-full" />
      <Skeleton className="h-4 flex-1" />
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-4 w-16" />
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 bg-card/60 p-6 space-y-4">
      <Skeleton className="h-5 w-32" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-8 w-24" />
    </div>
  )
}

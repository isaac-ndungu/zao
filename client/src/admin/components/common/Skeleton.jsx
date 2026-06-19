export default function Skeleton({ className = '', lines = 1 }) {
  if (lines > 1) {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }, (_, i) => (
          <div key={i} className={`h-3 bg-surface-container-high rounded animate-pulse ${i === lines - 1 ? 'w-3/4' : 'w-full'}`} />
        ))}
      </div>
    )
  }
  return <div className={`bg-surface-container-high rounded animate-pulse ${className}`} />
}

export function TableSkeleton({ rows = 5, cols = 6 }) {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
      <div className="p-4 space-y-3">
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="flex gap-4">
            <Skeleton className="h-5 w-5 rounded" />
            {Array.from({ length: cols }, (_, j) => (
              <Skeleton key={j} className="h-5 flex-1 rounded" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function KpiSkeleton({ count = 4 }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="bg-surface-container-lowest border border-outline-variant p-5 rounded-xl">
          <div className="flex justify-between items-start mb-4">
            <Skeleton className="h-8 w-8 rounded-lg" />
          </div>
          <Skeleton className="h-3 w-20 mb-2" />
          <Skeleton className="h-6 w-16" />
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
      <Skeleton className="h-5 w-40 mb-4" />
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  )
}

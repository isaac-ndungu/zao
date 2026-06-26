const widths = ['70%', '85%', '60%', '90%', '75%', '80%']

export function CardSkeleton({ lines = 3 }) {
  return (
    <div className="bg-surface-container rounded-xl border border-outline-variant p-4 space-y-3">
      <div className="animate-pulse bg-gray-200 rounded-lg h-5 w-3/4" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="animate-pulse bg-gray-200 rounded-lg h-4 w-full" style={{ width: widths[i % widths.length] }} />
      ))}
    </div>
  )
}

export function ListSkeleton({ count = 5 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} lines={3} />
      ))}
    </div>
  )
}

export function KpiSkeleton() {
  return (
    <div className="grid grid-cols-3 gap-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="bg-surface-container rounded-xl border border-outline-variant p-4 space-y-2">
          <div className="animate-pulse bg-gray-200 rounded-lg h-3 w-16" />
          <div className="animate-pulse bg-gray-200 rounded-lg h-6 w-20" />
        </div>
      ))}
    </div>
  )
}

export default function ProgressTracker({ graded, total }) {
  if (total === 0) {
    return (
      <div className="bg-primary-container/20 border border-primary/20 rounded-xl px-4 py-3 mb-6 flex items-center gap-3">
        <span className="material-symbols-outlined text-primary text-[20px]">check_circle</span>
        <span className="text-label-md font-medium text-primary">All done for today</span>
      </div>
    )
  }

  const percent = Math.round((graded / total) * 100)
  const isComplete = graded >= total
  const barBg = isComplete ? 'bg-primary' : 'bg-surface-container-high'

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-label-md text-on-surface-variant font-medium">Today's Progress</span>
        <span className="text-label-md font-bold text-on-surface">
          {graded} / {total}
        </span>
      </div>
      <div className="h-2 bg-surface-container-high rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barBg}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="text-label-sm text-on-surface-variant mt-1.5">
        {isComplete
          ? `${graded} of ${total} deliveries graded — all caught up`
          : `${graded} of ${total} deliveries graded`}
      </p>
    </div>
  )
}

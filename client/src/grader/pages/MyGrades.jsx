import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import ErrorState from '../../shared/components/ErrorState'
import StatusBadge from '../../admin/components/common/StatusBadge'

export default function MyGrades() {
  const [page, setPage] = useState(1)
  const { data, loading, error, refetch } = useApi(`/api/grades/?page=${page}&page_size=20&ordering=-created_at`)

  const grades = data?.results || []
  const total = data?.count || 0

  if (loading) {
    return (
      <div>
        <header className="mb-6">
          <h2 className="font-headline-lg text-display-md text-primary mb-1">My Grades</h2>
        </header>
        <TableSkeleton rows={6} cols={4} />
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <header className="mb-6">
          <h2 className="font-headline-lg text-display-md text-primary mb-1">My Grades</h2>
        </header>
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      </div>
    )
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">My Grades</h2>
        <p className="text-on-surface-variant font-body-md">{total} total</p>
      </header>

      {grades.length === 0 ? (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
          <span className="material-symbols-outlined text-[48px] text-on-surface-variant">fact_check</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface mt-4">No grades yet</h3>
          <p className="text-body-md text-on-surface-variant mt-2">Grades you assign will appear here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {grades.map((grade) => (
            <div
              key={grade.id}
              className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 flex items-center gap-4"
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                grade.grade_letter === 'REJECTED' ? 'bg-error-container' : 'bg-primary-container'
              }`}>
                <span className={`material-symbols-outlined text-[20px] ${
                  grade.grade_letter === 'REJECTED' ? 'text-error' : 'text-primary'
                }`}>
                  {grade.grade_letter === 'REJECTED' ? 'close' : 'grading'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <p className="text-body-md text-on-surface font-medium truncate">
                    {grade.batch_id || grade.delivery || '-'}
                  </p>
                  <StatusBadge
                    status={grade.grade_letter === 'REJECTED' ? 'rejected' : grade.grade_letter?.toLowerCase()}
                    label={grade.grade_letter || '-'}
                  />
                </div>
                <p className="text-label-md text-on-surface-variant truncate">
                  {grade.farmer_name || 'Unknown farmer'}
                  {grade.price_per_unit ? ` · KES ${grade.price_per_unit}/unit` : ''}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-label-md text-on-surface-variant">
                  {grade.created_at ? new Date(grade.created_at).toLocaleString() : '-'}
                </p>
                {grade.is_overridden && (
                  <p className="text-label-sm text-warning mt-0.5">Overridden</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {data?.count > 20 && (
        <div className="flex justify-center gap-2 mt-6">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold disabled:opacity-50">Previous</button>
          <span className="px-4 py-2 text-body-md text-on-surface-variant self-center">Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={!data?.next} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold disabled:opacity-50">Next</button>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import ErrorState from '../../shared/components/ErrorState'
import StatusBadge from '../../admin/components/common/StatusBadge'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'

const gradeOptions = ['PREMIUM', 'STANDARD', 'A', 'B', 'C']

export default function MyGrades() {
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [editGrade, setEditGrade] = useState('')
  const [editPrice, setEditPrice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { showToast } = useToast()
  const { data, loading, error, refetch } = useApi(`/api/grades/?page=${page}&page_size=20&ordering=-created_at`)

  const grades = data?.results || []
  const total = data?.count || 0

  const openEdit = (grade) => {
    setEditing(grade)
    setEditGrade(grade.grade_letter || '')
    setEditPrice(grade.price_per_unit || '')
  }

  const handleEdit = async () => {
    if (!editGrade) { showToast({ type: 'error', message: 'Select a grade.' }); return }
    setSubmitting(true)
    try {
      const body = { grade_letter: editGrade }
      if (editPrice) body.price_per_unit = editPrice
      const res = await apiFetch(`/api/grades/${editing.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ')) }
      showToast({ type: 'success', message: 'Grade updated.' })
      setEditing(null)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSubmitting(false) }
  }

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/grades/${deleting.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Grade deleted.' })
      setDeleting(null)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

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
          <span className="material-symbols-outlined text-[48px] text-on-surface-variant" aria-hidden="true">fact_check</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface mt-4">No grades yet</h3>
          <p className="text-body-md text-on-surface-variant mt-2">Grades you assign will appear here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {grades.map((grade) => (
            <div
              key={grade.id}
              className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 flex items-center gap-4 group"
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                grade.grade_letter === 'REJECTED' ? 'bg-error-container' : 'bg-primary-container'
              }`}>
                <span aria-hidden="true" className={`material-symbols-outlined text-[20px] ${
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
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => openEdit(grade)} aria-label="Edit Grade" className="text-on-surface-variant hover:text-primary p-1">
                  <span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span>
                </button>
                <button onClick={() => setDeleting(grade)} aria-label="Delete Grade" className="text-error hover:text-error/80 p-1">
                  <span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span>
                </button>
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

      {editing && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => { if (!submitting) setEditing(null) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">Edit Grade</h3>
              <button onClick={() => setEditing(null)} aria-label="Close" className="p-1 rounded-lg hover:bg-surface-container text-on-surface-variant" disabled={submitting}>
                <span className="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Grade Letter</label>
                <select
                  value={editGrade}
                  onChange={(e) => setEditGrade(e.target.value)}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  disabled={submitting}
                >
                  <option value="">Select grade</option>
                  {gradeOptions.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Price per Unit (KES)</label>
                <input
                  type="number" step="0.01" min="0"
                  value={editPrice}
                  onChange={(e) => setEditPrice(e.target.value)}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  disabled={submitting}
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setEditing(null)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-higher transition-colors" disabled={submitting}>
                  Cancel
                </button>
                <button onClick={handleEdit} disabled={submitting || !editGrade} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2">
                  {submitting && <span aria-hidden="true" className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                  {submitting ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!deleting}
        title="Delete Grade"
        message={`Delete grade for ${deleting?.farmer_name || 'this delivery'} (${deleting?.batch_id || ''})?`}
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  )
}

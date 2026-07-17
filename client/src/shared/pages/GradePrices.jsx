import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

const gradeOptions = ['A', 'B', 'C', 'PREMIUM', 'STANDARD']

export default function GradePrices() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const { data, loading, error, refetch } = useApi(`/api/grade-prices/?page=${page}&page_size=20&ordering=-effective_from`)

  const prices = data?.results || []

  const openCreate = () => {
    setEditing(null)
    setShowForm(true)
  }

  const openEdit = (price) => {
    setEditing(price)
    setShowForm(true)
  }

  const { formAction: priceAction } = useFormAction(async (prev, formData) => {
    const body = formDataToObject(formData)
    const url = editing ? `/api/grade-prices/${editing.id}/` : '/api/grade-prices/'
    const method = editing ? 'PATCH' : 'POST'
    const res = await apiFetch(url, { method, body: JSON.stringify(body) })
    if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ')) }
    showToast({ type: 'success', message: editing ? 'Price updated.' : 'Price created.' })
    setShowForm(false)
    setEditing(null)
    refetch()
    return { success: true }
  }, {})

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/grade-prices/${deleting.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Price deleted.' })
      setDeleting(null)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const columns = [
    { key: 'grade_letter', label: 'Grade', render: (v, _r) => <span className="font-bold">{v}</span> },
    { key: 'price_per_unit', label: 'Price (KES/unit)' },
    { key: 'effective_from', label: 'Effective From', render: (v, _r) => v ? new Date(v).toLocaleDateString() : '-' },
    { key: 'created_at', label: 'Created', render: (v, _r) => v ? new Date(v).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (_v, row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button onClick={(e) => { e.stopPropagation(); openEdit(row) }} aria-label="Edit" className="text-on-surface-variant hover:text-primary"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span></button>
          <button onClick={(e) => { e.stopPropagation(); setDeleting(row) }} aria-label="Delete" className="text-error hover:text-error/80"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span></button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <header className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Grade Prices</h2>
          <p className="text-on-surface-variant font-body-md">Manage pricing tiers per grade letter</p>
        </div>
        <button onClick={openCreate} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">add</span>Add Price
        </button>
      </header>

      {loading ? <TableSkeleton rows={8} cols={5} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable columns={columns} data={prices} emptyMessage="No grade prices configured." />
          <Pagination page={page} pageSize={20} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={() => {}} />
        </>
      )}

      {showForm && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30 cursor-pointer" onClick={() => { setShowForm(false); setEditing(null) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-md w-full mx-4 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="grade-price-title">
            <div className="flex items-center justify-between mb-6">
              <h3 id="grade-price-title" className="font-headline-sm text-headline-sm text-on-surface">{editing ? 'Edit Price' : 'New Price'}</h3>
              <button onClick={() => { setShowForm(false); setEditing(null) }} aria-label="Close" className="p-1 rounded-lg hover:bg-surface-container text-on-surface-variant">
                <span className="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
              </button>
            </div>
            <form action={priceAction} className="space-y-4">
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Grade Letter *</label>
                <select
                  name="grade_letter"
                  defaultValue={editing?.grade_letter || ''}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  required
                >
                  <option value="">Select grade</option>
                  {gradeOptions.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Price per Unit (KES) *</label>
                <input
                  name="price_per_unit"
                  type="number" step="0.01" min="0" required
                  defaultValue={editing?.price_per_unit || ''}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                />
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Effective From *</label>
                <input
                  name="effective_from"
                  type="date" required
                  defaultValue={editing?.effective_from || ''}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setEditing(null) }}
                  className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-higher transition-colors"
                >
                  Cancel
                </button>
                <SubmitButton className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors">
                  {editing ? 'Update Price' : 'Create Price'}
                </SubmitButton>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!deleting}
        title="Delete Price"
        message={`Delete price for grade ${deleting?.grade_letter || ''} (KES ${deleting?.price_per_unit || ''})?`}
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  )
}

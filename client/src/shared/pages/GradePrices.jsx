import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

const gradeOptions = ['A', 'B', 'C', 'PREMIUM', 'STANDARD']

export default function GradePrices() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [formLoading, setFormLoading] = useState(false)
  const { data, loading, error, refetch } = useApi(`/api/grade-prices/?page=${page}&page_size=20&ordering=-effective_from`)
  const [form, setForm] = useState({ grade_letter: '', price_per_unit: '', effective_from: '' })

  const prices = data?.results || []

  const openCreate = () => {
    setEditing(null)
    setForm({ grade_letter: '', price_per_unit: '', effective_from: '' })
    setShowForm(true)
  }

  const openEdit = (price) => {
    setEditing(price)
    setForm({
      grade_letter: price.grade_letter,
      price_per_unit: price.price_per_unit,
      effective_from: price.effective_from,
    })
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormLoading(true)
    try {
      const body = { ...form }
      const url = editing ? `/api/grade-prices/${editing.id}/` : '/api/grade-prices/'
      const method = editing ? 'PATCH' : 'POST'
      const res = await apiFetch(url, { method, body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ')) }
      showToast({ type: 'success', message: editing ? 'Price updated.' : 'Price created.' })
      setShowForm(false)
      setEditing(null)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setFormLoading(false) }
  }

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
    { key: 'grade_letter', label: 'Grade', render: (v) => <span className="font-bold">{v}</span> },
    { key: 'price_per_unit', label: 'Price (KES/unit)' },
    { key: 'effective_from', label: 'Effective From', render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    { key: 'created_at', label: 'Created', render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (_v, row) => (
        <div className="flex items-center justify-end gap-1">
          <button onClick={(e) => { e.stopPropagation(); openEdit(row) }} className="text-on-surface-variant hover:text-primary" title="Edit"><span className="material-symbols-outlined text-[18px]">edit</span></button>
          <button onClick={(e) => { e.stopPropagation(); setDeleting(row) }} className="text-error hover:text-error/80" title="Delete"><span className="material-symbols-outlined text-[18px]">delete</span></button>
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
          <span className="material-symbols-outlined text-[18px]">add</span>Add Price
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
        <div className="fixed inset-0 z-[70] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => { if (!formLoading) { setShowForm(false); setEditing(null) } }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">{editing ? 'Edit Price' : 'New Price'}</h3>
              <button onClick={() => { setShowForm(false); setEditing(null) }} className="p-1 rounded-lg hover:bg-surface-container text-on-surface-variant" disabled={formLoading}>
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Grade Letter *</label>
                <select
                  value={form.grade_letter}
                  onChange={(e) => setForm(f => ({ ...f, grade_letter: e.target.value }))}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  disabled={formLoading}
                  required
                >
                  <option value="">Select grade</option>
                  {gradeOptions.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Price per Unit (KES) *</label>
                <input
                  type="number" step="0.01" min="0" required
                  value={form.price_per_unit}
                  onChange={(e) => setForm(f => ({ ...f, price_per_unit: e.target.value }))}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  disabled={formLoading}
                />
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Effective From *</label>
                <input
                  type="date" required
                  value={form.effective_from}
                  onChange={(e) => setForm(f => ({ ...f, effective_from: e.target.value }))}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  disabled={formLoading}
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setEditing(null) }}
                  className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-higher transition-colors"
                  disabled={formLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {formLoading && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                  {formLoading ? 'Saving...' : editing ? 'Update Price' : 'Create Price'}
                </button>
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

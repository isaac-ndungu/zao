import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

export default function Routes() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState('name')
  const [sortOrder, setSortOrder] = useState('asc')
  const [detailRoute, setDetailRoute] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(null)
  const [showDelete, setShowDelete] = useState(null)
  const { showToast } = useToast()

  const sortParam = sortOrder === 'desc' ? `-${sortField}` : sortField
  const queryParams = new URLSearchParams({ page, page_size: pageSize, ordering: sortParam })
  if (search) queryParams.set('search', search)

  const { data, loading, error, refetch } = useApi(`/api/routes/?${queryParams}`)

  const handleSort = (key) => {
    if (sortField === key) setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    else { setSortField(key); setSortOrder('asc') }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const body = Object.fromEntries(fd.entries())
    try {
      const res = await apiFetch('/api/routes/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to create') }
      showToast({ type: 'success', message: 'Route created.' })
      setShowCreate(false); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const body = Object.fromEntries(fd.entries())
    try {
      const res = await apiFetch(`/api/routes/${showEdit.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to update') }
      showToast({ type: 'success', message: 'Route updated.' })
      setShowEdit(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/routes/${showDelete.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Route deleted.' })
      setShowDelete(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const items = data?.results || []
  const total = data?.count || 0

  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'description', label: 'Description', render: (row) => row.description || '-' },
    { key: 'created_at', label: 'Created', sortable: true, render: (row) => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button onClick={(e) => { e.stopPropagation(); setShowEdit(row) }} className="text-primary hover:text-primary/80" aria-label={`Edit ${row.name}`}><span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span></button>
          <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error hover:text-error/80" aria-label={`Delete ${row.name}`}><span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span></button>
        </div>
      ),
    },
  ]

  const routeForm = (defaults = {}, onSubmit, submitLabel) => (
    <form onSubmit={onSubmit} className="space-y-4">
      <div><label htmlFor="create-name" className="block text-label-md text-on-surface-variant mb-1">Name</label><input id="create-name" name="name" defaultValue={defaults.name || ''} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      <div><label htmlFor="create-description" className="block text-label-md text-on-surface-variant mb-1">Description</label><textarea id="create-description" name="description" defaultValue={defaults.description || ''} rows={3} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      <button type="submit" className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">{submitLabel}</button>
    </form>
  )

  return (
    <div>
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Routes</h2>
          <p className="text-on-surface-variant font-body-md">{total} total</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">add</span>Add Route
        </button>
      </header>

      <div className="mb-4">
        <form onSubmit={(e) => { e.preventDefault(); setSearch(new FormData(e.target).get('search') || ''); setPage(1) }} className="flex gap-2">
          <label htmlFor="routes-search" className="sr-only">Search routes</label>
          <input id="routes-search" name="search" defaultValue={search} placeholder="Search routes..." className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-64"/>
          <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Search</button>
        </form>
      </div>

      {loading ? <TableSkeleton rows={10} cols={4} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={items}
            sortField={sortField}
            sortOrder={sortOrder}
            onSort={handleSort}
            onRowClick={(row) => setDetailRoute(row)}
            emptyMessage="No routes found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailRoute} onClose={() => setDetailRoute(null)} title="Route Details" width="max-w-xl">
        {detailRoute && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['name', 'description', 'created_at'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">{String(detailRoute[f] ?? '-')}</p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>

      <SlideOutPanel open={showCreate} onClose={() => setShowCreate(false)} title="New Route" width="max-w-md">
        {routeForm({}, handleCreate, 'Create Route')}
      </SlideOutPanel>

      <SlideOutPanel open={!!showEdit} onClose={() => setShowEdit(null)} title="Edit Route" width="max-w-md">
        {showEdit && routeForm(showEdit, handleEdit, 'Update Route')}
      </SlideOutPanel>

      <ConfirmModal open={!!showDelete} title="Delete Route" message={`Delete route "${showDelete?.name}"?`} confirmLabel="Delete" destructive onConfirm={handleDelete} onCancel={() => setShowDelete(null)} />
    </div>
  )
}

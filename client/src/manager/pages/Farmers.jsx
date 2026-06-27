import { useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch, exportCsv } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

export default function Farmers() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [sortField, setSortField] = useState('first_name')
  const [sortOrder, setSortOrder] = useState('asc')
  const [selectedIds, setSelectedIds] = useState([])
  const [detailFarmer, setDetailFarmer] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(null)
  const [showDelete, setShowDelete] = useState(null)
  const [showImport, setShowImport] = useState(false)
  const [importPreview, setImportPreview] = useState(null)
  const [importFile, setImportFile] = useState(null)
  const [formData, setFormData] = useState({ first_name: '', last_name: '', phone_number: '', id_number: '', county: '', payment_method: 'MPESA' })
  const { showToast } = useToast()

  const sortParam = sortOrder === 'desc' ? `-${sortField}` : sortField
  const queryParams = new URLSearchParams({ page, page_size: pageSize, ordering: sortParam })
  if (search) queryParams.set('search', search)

  const { data, loading, error, refetch } = useApi(`/api/farmers/?${queryParams}`)
  const { data: stats } = useApi('/api/farmers/stats/')
  const { data: counties } = useApi('/api/cooperatives/enums/')

  const handleSearch = useCallback((e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const q = fd.get('search') || ''
    setSearch(q)
    setPage(1)
    setSearchParams(q ? { search: q } : {})
  }, [setSearchParams])

  const handleSort = useCallback((key) => {
    if (sortField === key) setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    else { setSortField(key); setSortOrder('asc') }
  }, [sortField])

  const handleCreate = async (e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const body = Object.fromEntries(fd.entries())
    try {
      const res = await apiFetch('/api/farmers/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to create') }
      showToast({ type: 'success', message: 'Farmer created.' })
      setShowCreate(false); setFormData({ first_name: '', last_name: '', phone_number: '', id_number: '', county: '', payment_method: 'MPESA' })
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const body = Object.fromEntries(fd.entries())
    try {
      const res = await apiFetch(`/api/farmers/${showEdit.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to update') }
      showToast({ type: 'success', message: 'Farmer updated.' })
      setShowEdit(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/farmers/${showDelete.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Farmer deleted.' })
      setShowDelete(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleImportSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImportFile(file)
    const reader = new FileReader()
    reader.onload = (evt) => {
      const text = evt.target.result
      const lines = text.split('\n').filter(Boolean)
      const headers = lines[0]?.split(',') || []
      const rows = lines.slice(1).map((line, i) => {
        const vals = line.split(',')
        const row = {}
        headers.forEach((h, j) => { row[h.trim()] = vals[j]?.trim() || '' })
        return { index: i + 2, ...row, valid: !!row.phone_number && !!row.first_name, reason: !row.phone_number ? 'Missing phone' : !row.first_name ? 'Missing name' : null }
      })
      setImportPreview({ headers, rows, total: rows.length, valid: rows.filter(r => r.valid).length, invalid: rows.filter(r => !r.valid).length })
    }
    reader.readAsText(file)
  }

  const handleImportConfirm = async () => {
    if (!importFile) return
    const fd = new FormData()
    fd.append('file', importFile)
    try {
      const res = await apiFetch('/api/farmers/import_csv/', { method: 'POST', headers: {}, body: fd })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Import failed') }
      const result = await res.json()
      showToast({ type: 'success', message: `Imported ${result.created_farmers || 0} farmers.` })
      setShowImport(false); setImportPreview(null); setImportFile(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }



  const columns = [
    { key: 'member_number', label: 'Member #', sortable: true },
    { key: 'first_name', label: 'First Name', sortable: true },
    { key: 'last_name', label: 'Last Name', sortable: true },
    { key: 'phone_number', label: 'Phone', sortable: true },
    { key: 'is_active', label: 'Status', render: (v) => <StatusBadge status={v} label={v ? 'Active' : 'Inactive'} /> },
    { key: 'date_joined', label: 'Joined', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (_, row) => (
        <div className="flex gap-2">
          <button onClick={(e) => { e.stopPropagation(); setShowEdit(row) }} className="text-primary text-label-md hover:underline">Edit</button>
          <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error text-label-md hover:underline">Delete</button>
        </div>
      ),
    },
  ]

  const createForm = (
    <form onSubmit={handleCreate} className="space-y-4">
      <div><label className="block text-label-md text-on-surface-variant mb-1">First Name</label><input name="first_name" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      <div><label className="block text-label-md text-on-surface-variant mb-1">Last Name</label><input name="last_name" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      <div><label className="block text-label-md text-on-surface-variant mb-1">Phone</label><input name="phone_number" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      <div><label className="block text-label-md text-on-surface-variant mb-1">ID Number</label><input name="id_number" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      <div><label className="block text-label-md text-on-surface-variant mb-1">County</label><input name="county" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      <div><label className="block text-label-md text-on-surface-variant mb-1">Payment Method</label><select name="payment_method" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option>MPESA</option><option>BANK</option><option>CASH</option></select></div>
      <button type="submit" className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">Create Farmer</button>
    </form>
  )

  const editForm = showEdit && (
    <form onSubmit={handleEdit} className="space-y-4">
      {['first_name','last_name','phone_number','id_number','county'].map(f => (
        <div key={f}><label className="block text-label-md text-on-surface-variant mb-1 capitalize">{f.replace('_',' ')}</label><input name={f} defaultValue={showEdit[f] || ''} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
      ))}
      <div><label className="block text-label-md text-on-surface-variant mb-1">Payment Method</label><select name="payment_method" defaultValue={showEdit.payment_method || 'MPESA'} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option>MPESA</option><option>BANK</option><option>CASH</option></select></div>
      <button type="submit" className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">Update Farmer</button>
    </form>
  )

  return (
    <div>
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Farmers</h2>
          <p className="text-on-surface-variant font-body-md">{stats ? `${stats.total} total · ${stats.active} active` : ''}</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { exportCsv('/api/farmers/?export=csv') }} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">download</span>Export
          </button>
          <button onClick={() => { window.open('/api/farmers/import_template/', '_blank') }} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">description</span>Template
          </button>
          <button onClick={() => setShowImport(true)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">upload_file</span>Import CSV
          </button>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">add</span>Add Farmer
          </button>
        </div>
      </header>

      <div className="mb-4 flex items-center gap-4 flex-wrap">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input name="search" defaultValue={search} placeholder="Search farmers..." className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-64"/>
          <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Search</button>
        </form>

      </div>

      {loading ? <TableSkeleton rows={10} cols={7} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={data?.results || []}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            sortField={sortField}
            sortOrder={sortOrder}
            onSort={handleSort}
            onRowClick={(row) => setDetailFarmer(row)}
            emptyMessage="No farmers found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailFarmer} onClose={() => setDetailFarmer(null)} title="Farmer Details" width="max-w-xl">
        {detailFarmer && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['member_number','first_name','last_name','phone_number','email','county','payment_method','is_active'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace('_',' ')}</p><p className="text-body-md text-on-surface font-medium">{String(detailFarmer[f] ?? '-')}</p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>

      <SlideOutPanel open={showCreate} onClose={() => setShowCreate(false)} title="New Farmer" width="max-w-md">
        {createForm}
      </SlideOutPanel>

      <SlideOutPanel open={!!showEdit} onClose={() => setShowEdit(null)} title="Edit Farmer" width="max-w-md">
        {editForm}
      </SlideOutPanel>

      <ConfirmModal open={!!showDelete} title="Delete Farmer" message={`Delete ${showDelete?.first_name} ${showDelete?.last_name}?`} confirmLabel="Delete" destructive onConfirm={handleDelete} onCancel={() => setShowDelete(null)} />

      <SlideOutPanel open={showImport} onClose={() => { setShowImport(false); setImportPreview(null); setImportFile(null) }} title="Import Farmers CSV" width="max-w-xl">
        <div className="space-y-4">
          <p className="text-body-md text-on-surface-variant">Upload a CSV file with columns: first_name, last_name, phone_number, id_number, county</p>
          {!importPreview ? (
            <input type="file" accept=".csv" onChange={handleImportSelect} className="block w-full text-body-md" />
          ) : (
            <div>
              <div className="flex gap-4 mb-4">
                <span className="text-success text-body-md font-bold">{importPreview.valid} valid</span>
                {importPreview.invalid > 0 && <span className="text-error text-body-md font-bold">{importPreview.invalid} invalid</span>}
              </div>
              <div className="max-h-64 overflow-y-auto border border-outline-variant rounded-lg">
                <table className="w-full text-body-md">
                  <thead><tr className="bg-surface-container border-b border-outline-variant">{importPreview.headers.map(h => <th key={h} className="px-3 py-2 text-left text-label-md">{h}</th>)}</tr></thead>
                  <tbody>
                    {importPreview.rows.map((row) => (
                      <tr key={row.index} className={`border-b border-outline-variant/50 ${!row.valid ? 'bg-error-container/30' : ''}`}>
                        {importPreview.headers.map(h => <td key={h} className="px-3 py-2">{row[h]}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-3 mt-4">
                <button onClick={() => { setImportPreview(null); setImportFile(null) }} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
                <button onClick={handleImportConfirm} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold" disabled={importPreview.valid === 0}>Import {importPreview.valid} Farmers</button>
              </div>
            </div>
          )}
        </div>
      </SlideOutPanel>
    </div>
  )
}

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch, exportCsv } from '../api/client'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import KpiCard from '../components/common/KpiCard'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'
import { KpiSkeleton, TableSkeleton } from '../components/common/Skeleton'
import { useLocation, useSearchParams } from 'react-router-dom'

const KENYA_COUNTIES = [
  'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo Marakwet',
  'Embu', 'Garissa', 'Homa Bay', 'Isiolo', 'Kajiado',
  'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga',
  'Kisii', 'Kisumu', 'Kitui', 'Kwale', 'Laikipia',
  'Lamu', 'Machakos', 'Makueni', 'Mandera', 'Marsabit',
  'Meru', 'Migori', 'Mombasa', "Murang'a", 'Nairobi',
  'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua',
  'Nyeri', 'Samburu', 'Siaya', 'Taita Taveta', 'Tana River',
  'Tharaka Nithi', 'Trans Nzoia', 'Turkana', 'Uasin Gishu',
  'Vihiga', 'Wajir', 'West Pokot',
]

const produceTypeOptions = [
  { value: 'DAIRY', label: 'Dairy' },
  { value: 'COFFEE', label: 'Coffee' },
  { value: 'HONEY', label: 'Honey' },
]

const paymentModelOptions = [
  { value: 'FIXED_PRICE', label: 'Fixed Price' },
  { value: 'REVENUE_SHARE', label: 'Revenue Share' },
]

const statusOptions = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
]

export default function Cooperatives() {
  const { showToast } = useToast()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [sortField, setSortField] = useState('name')
  const [sortOrder, setSortOrder] = useState('asc')
  const [selectedIds, setSelectedIds] = useState([])
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelItem, setPanelItem] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [createOpen, setCreateOpen] = useState(location.state?.openModal === true)
  const [form, setForm] = useState({ name: '', prefix: '', email: '', phone_number: '', physical_address: '', registration_number: '', county: 'Nairobi', produce_type: 'DAIRY', payment_model: 'FIXED_PRICE', levy_percentage: '', monthly_fee: '', sub_county: '', ward: '' })
  const [formLoading, setFormLoading] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editItem, setEditItem] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', prefix: '', email: '', phone_number: '', physical_address: '', registration_number: '', county: 'Nairobi', produce_type: 'DAIRY', payment_model: 'FIXED_PRICE', levy_percentage: '', monthly_fee: '', sub_county: '', ward: '' })
  const [editLoading, setEditLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', page)
    params.set('page_size', pageSize)
    if (search) params.set('search', search)
    if (filters.status === 'active') params.set('is_active', 'true')
    else if (filters.status === 'inactive') params.set('is_active', 'false')
    if (sortField) params.set('ordering', sortOrder === 'desc' ? `-${sortField}` : sortField)
    return params.toString()
  }, [page, pageSize, search, filters.status, sortField, sortOrder])

  const { data, loading, error, refetch } = useApi(`/api/admin/cooperatives/?${query}`)
  const { data: kpiData } = useApi('/api/admin/cooperatives/?page=1&page_size=1')

  const kpis = useMemo(() => ({
    total: kpiData?.count || 0,
  }), [kpiData])

  const items = data?.results || []

  useEffect(() => {
    if (selectedId && items.length > 0) {
      const found = items.find(i => String(i.id) === String(selectedId))
      if (found && !panelOpen) {
        setPanelItem(found)
        setPanelOpen(true)
      }
    }
  }, [selectedId, items])

  const handleSort = useCallback((field) => {
    if (sortField === field) setSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortOrder('asc') }
  }, [sortField])

  const execAction = async (url, opts = {}) => {
    setActionLoading(true)
    try {
      const res = await apiFetch(url, { method: 'POST', ...opts })
      if (!res.ok) throw new Error(await res.text())
      const msg = url.includes('activate') ? 'activated' : url.includes('deactivate') ? 'deactivated' : url.includes('delete') ? 'deleted' : url.includes('restore') ? 'restored' : 'updated'
      showToast({ type: 'success', message: `Cooperative ${msg}.` })
      refetch()
      const result = await res.json().catch(() => ({}))
      if (panelItem && typeof result === 'object') {
        const { detail, message, error, status, ...updates } = result
        const safeUpdates = Object.fromEntries(
          Object.entries(updates).filter(([, v]) => v !== null && typeof v !== 'object')
        )
        if (Object.keys(safeUpdates).length > 0) {
          setPanelItem(prev => ({ ...prev, ...safeUpdates }))
        }
      }
      setModalConfig({ open: false })
    } catch (e) {
      showToast({ type: 'error', message: `Action failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleActivate = (item) => setModalConfig({ open: true, title: 'Activate Cooperative', message: `Activate ${item.name}?`, destructive: false, onConfirm: () => execAction(`/api/admin/cooperatives/${item.id}/activate/`) })
  const handleDeactivate = (item) => setModalConfig({ open: true, title: 'Deactivate Cooperative', message: `Deactivate ${item.name}?`, destructive: true, onConfirm: () => execAction(`/api/admin/cooperatives/${item.id}/deactivate/`) })
  const handleDelete = (item) => setModalConfig({ open: true, title: 'Delete Cooperative', message: `Soft-delete ${item.name}?`, destructive: true, onConfirm: () => execAction(`/api/admin/cooperatives/${item.id}/delete/`, { body: JSON.stringify({ confirm: true }), headers: { 'Content-Type': 'application/json' } }) })

  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return
    try {
      const res = await apiFetch('/api/admin/cooperatives/bulk-action/', { method: 'POST', body: JSON.stringify({ action, ids: selectedIds }) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Bulk ${action} for ${selectedIds.length} cooperatives.` })
      setSelectedIds([])
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Bulk action failed: ${e.message}` })
    }
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    if (!editItem) return
    setEditLoading(true)
    try {
      const res = await apiFetch(`/api/admin/cooperatives/${editItem.id}/`, { method: 'PATCH', body: JSON.stringify(editForm) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Cooperative ${editForm.name} updated.` })
      setEditOpen(false)
      setEditItem(null)
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Update failed: ${e.message}` })
    } finally {
      setEditLoading(false)
    }
  }

  const openEdit = (item) => {
    setEditItem(item)
    setEditForm({ name: item.name || '', prefix: item.prefix || '', email: item.email || '', phone_number: item.phone_number || '', physical_address: item.physical_address || '', registration_number: item.registration_number || '', county: item.county || 'Nairobi', produce_type: item.produce_type || 'DAIRY', payment_model: item.payment_model || 'FIXED_PRICE', levy_percentage: item.levy_percentage || '', monthly_fee: item.monthly_fee || '', sub_county: item.sub_county || '', ward: item.ward || '' })
    setEditOpen(true)
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setFormLoading(true)
    try {
      const res = await apiFetch('/api/admin/cooperatives/', { method: 'POST', body: JSON.stringify(form) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Cooperative ${form.name} created.` })
      setCreateOpen(false)
      setForm({ name: '', prefix: '', email: '', phone_number: '', physical_address: '', registration_number: '', county: 'Nairobi', produce_type: 'DAIRY', payment_model: 'FIXED_PRICE', levy_percentage: '', monthly_fee: '', sub_county: '', ward: '' })
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Creation failed: ${e.message}` })
    } finally {
      setFormLoading(false)
    }
  }

  const columns = useMemo(() => [
    { key: 'name', label: 'Name', sortable: true, render: (_, r) => <span className="font-medium text-body-md">{r.name}</span> },
    { key: 'code', label: 'Code', render: (_, r) => <span className="text-label-md text-on-surface-variant">{r.code || '-'}</span> },
    { key: 'email', label: 'Email', render: (_, r) => <span className="text-label-md text-on-surface-variant">{r.email || '-'}</span> },
    { key: 'phone_number', label: 'Phone', render: (_, r) => <span className="text-label-md text-on-surface-variant">{r.phone_number || '-'}</span> },
    { key: 'is_active', label: 'Status', render: (_, r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} /> },
  ], [])

  if (error) return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load cooperatives: {error}</div>

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">Cooperatives</h2>
          <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">add</span>
            New Cooperative
          </button>
        </div>
        <p className="text-on-surface-variant font-body-md">Manage farmer cooperatives and their members.</p>
      </header>

      {loading && !kpiData ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"><KpiSkeleton count={1} /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KpiCard label="Total Cooperatives" value={kpis.total} icon="groups" />
        </div>
      )}

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search by name, code, email..."
        filters={[
          { key: 'status', label: 'Status', options: statusOptions },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.status === 'active') p.set('is_active', 'true'); else if (filters.status === 'inactive') p.set('is_active', 'false'); p.set('export', 'csv'); exportCsv(`/api/admin/cooperatives/?${p}`) }}
      />

      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 px-4 py-2 bg-primary-container/50 border border-primary-container rounded-lg">
          <span className="text-label-md font-medium text-on-primary-container">{selectedIds.length} selected</span>
          <button onClick={() => handleBulkAction('activate')} className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90">Activate</button>
          <button onClick={() => handleBulkAction('deactivate')} className="px-3 py-1 text-label-md font-bold bg-error text-on-error rounded-lg hover:bg-error/90">Deactivate</button>
          <button onClick={() => setSelectedIds([])} className="text-label-md text-on-surface-variant hover:text-on-surface ml-auto">Clear</button>
        </div>
      )}

      {loading ? <TableSkeleton /> : (
        <DataTable
          columns={columns}
          data={data?.results || []}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          sortField={sortField}
          sortOrder={sortOrder}
          onSort={handleSort}
          emptyMessage="No cooperatives found."
          rowActions={(item) => (
            <div className="flex items-center gap-1">
              <button onClick={() => { setPanelItem(item); setPanelOpen(true) }} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant" aria-label="View cooperative details"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">visibility</span></button>
              <button onClick={() => openEdit(item)} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Edit cooperative"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span></button>
              {item.is_active ? (
                <button onClick={() => handleDeactivate(item)} className="p-1.5 rounded-lg hover:bg-error-container text-error" aria-label="Deactivate cooperative"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">block</span></button>
              ) : (
                <button onClick={() => handleActivate(item)} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Activate cooperative"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">check_circle</span></button>
              )}
              <button onClick={() => handleDelete(item)} className="p-1.5 rounded-lg hover:bg-error-container text-error" aria-label="Delete cooperative"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span></button>
            </div>
          )}
        />
      )}

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelItem(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Cooperative Details">
        {panelItem && (
          <div className="space-y-4">
            <div>
              <h4 className="font-headline-sm text-headline-sm text-on-surface">{panelItem.name}</h4>
              <StatusBadge status={panelItem.is_active ? 'active' : 'inactive'} label={panelItem.is_active ? 'Active' : 'Inactive'} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Code</p><p className="font-body-md text-on-surface">{panelItem.code || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Email</p><p className="font-body-md text-on-surface">{panelItem.email || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Phone</p><p className="font-body-md text-on-surface">{panelItem.phone_number || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Reg Number</p><p className="font-body-md text-on-surface">{panelItem.registration_number || '-'}</p></div>
              <div className="col-span-2 p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Address</p><p className="font-body-md text-on-surface">{panelItem.address || '-'}</p></div>
            </div>
            <div className="pt-2 grid grid-cols-2 gap-2">
              <button onClick={() => { setPanelOpen(false); panelItem.is_active ? handleDeactivate(panelItem) : handleActivate(panelItem) }} className={`px-4 py-2 rounded-lg text-label-md font-bold ${panelItem.is_active ? 'border border-error text-error hover:bg-error-container' : 'bg-primary text-on-primary hover:bg-primary/90'}`}>
                {panelItem.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button onClick={() => { setPanelOpen(false); handleDelete(panelItem) }} className="px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container">Delete</button>
            </div>
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal open={modalConfig.open} title={modalConfig.title} message={modalConfig.message} onConfirm={modalConfig.onConfirm} onCancel={() => setModalConfig({ open: false })} loading={actionLoading} destructive={modalConfig.destructive} />

      {editOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30" onClick={() => { setEditOpen(false); setEditItem(null) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-lg w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="edit-cooperative-title">
            <h3 id="edit-cooperative-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Edit Cooperative</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Update cooperative details.</p>
            <form onSubmit={handleEdit} className="space-y-3">
              <div><label htmlFor="coop-edit-name" className="block text-label-md font-bold text-on-surface-variant mb-1">Name *</label><input id="coop-edit-name" required value={editForm.name} onChange={(e) => setEditForm(f => ({ ...f, name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-edit-prefix" className="block text-label-md font-bold text-on-surface-variant mb-1">Prefix</label><input id="coop-edit-prefix" value={editForm.prefix} onChange={(e) => setEditForm(f => ({ ...f, prefix: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="e.g. KCC" /></div>
                <div><label htmlFor="coop-edit-reg" className="block text-label-md font-bold text-on-surface-variant mb-1">Reg Number *</label><input id="coop-edit-reg" required value={editForm.registration_number} onChange={(e) => setEditForm(f => ({ ...f, registration_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-edit-county" className="block text-label-md font-bold text-on-surface-variant mb-1">County *</label><select id="coop-edit-county" required value={editForm.county} onChange={(e) => setEditForm(f => ({ ...f, county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">{KENYA_COUNTIES.map(c => <option key={c} value={c}>{c}</option>)}</select></div>
                <div><label htmlFor="coop-edit-subcounty" className="block text-label-md font-bold text-on-surface-variant mb-1">Sub-County</label><input id="coop-edit-subcounty" value={editForm.sub_county} onChange={(e) => setEditForm(f => ({ ...f, sub_county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-edit-ward" className="block text-label-md font-bold text-on-surface-variant mb-1">Ward</label><input id="coop-edit-ward" value={editForm.ward} onChange={(e) => setEditForm(f => ({ ...f, ward: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="coop-edit-produce" className="block text-label-md font-bold text-on-surface-variant mb-1">Produce Type *</label><select id="coop-edit-produce" required value={editForm.produce_type} onChange={(e) => setEditForm(f => ({ ...f, produce_type: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">{produceTypeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-edit-payment" className="block text-label-md font-bold text-on-surface-variant mb-1">Payment Model *</label><select id="coop-edit-payment" required value={editForm.payment_model} onChange={(e) => setEditForm(f => ({ ...f, payment_model: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">{paymentModelOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></div>
                <div><label htmlFor="coop-edit-levy" className="block text-label-md font-bold text-on-surface-variant mb-1">Levy % *</label><input id="coop-edit-levy" required type="number" step="0.01" min="0" max="100" value={editForm.levy_percentage} onChange={(e) => setEditForm(f => ({ ...f, levy_percentage: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-edit-fee" className="block text-label-md font-bold text-on-surface-variant mb-1">Monthly Fee *</label><input id="coop-edit-fee" required type="number" step="0.01" min="0" value={editForm.monthly_fee} onChange={(e) => setEditForm(f => ({ ...f, monthly_fee: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="coop-edit-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label><input id="coop-edit-email" type="email" value={editForm.email} onChange={(e) => setEditForm(f => ({ ...f, email: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div><label htmlFor="coop-edit-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label><input id="coop-edit-phone" type="tel" value={editForm.phone_number} onChange={(e) => setEditForm(f => ({ ...f, phone_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="coop-edit-address" className="block text-label-md font-bold text-on-surface-variant mb-1">Physical Address</label><textarea id="coop-edit-address" rows={2} value={editForm.physical_address} onChange={(e) => setEditForm(f => ({ ...f, physical_address: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setEditOpen(false); setEditItem(null) }} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={editLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50">{editLoading ? 'Saving...' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30" onClick={() => setCreateOpen(false)} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-lg w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="create-cooperative-title">
            <h3 id="create-cooperative-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Create Cooperative</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Register a new farmer cooperative.</p>
            <form onSubmit={handleCreate} className="space-y-3">
              <div><label htmlFor="coop-create-name" className="block text-label-md font-bold text-on-surface-variant mb-1">Name *</label><input id="coop-create-name" required value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-create-prefix" className="block text-label-md font-bold text-on-surface-variant mb-1">Prefix</label><input id="coop-create-prefix" value={form.prefix} onChange={(e) => setForm(f => ({ ...f, prefix: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="e.g. KCC" /></div>
                <div><label htmlFor="coop-create-reg" className="block text-label-md font-bold text-on-surface-variant mb-1">Reg Number *</label><input id="coop-create-reg" required value={form.registration_number} onChange={(e) => setForm(f => ({ ...f, registration_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-create-county" className="block text-label-md font-bold text-on-surface-variant mb-1">County *</label><select id="coop-create-county" required value={form.county} onChange={(e) => setForm(f => ({ ...f, county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">{KENYA_COUNTIES.map(c => <option key={c} value={c}>{c}</option>)}</select></div>
                <div><label htmlFor="coop-create-subcounty" className="block text-label-md font-bold text-on-surface-variant mb-1">Sub-County</label><input id="coop-create-subcounty" value={form.sub_county} onChange={(e) => setForm(f => ({ ...f, sub_county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-create-ward" className="block text-label-md font-bold text-on-surface-variant mb-1">Ward</label><input id="coop-create-ward" value={form.ward} onChange={(e) => setForm(f => ({ ...f, ward: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="coop-create-produce" className="block text-label-md font-bold text-on-surface-variant mb-1">Produce Type *</label><select id="coop-create-produce" required value={form.produce_type} onChange={(e) => setForm(f => ({ ...f, produce_type: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">{produceTypeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-create-payment" className="block text-label-md font-bold text-on-surface-variant mb-1">Payment Model *</label><select id="coop-create-payment" required value={form.payment_model} onChange={(e) => setForm(f => ({ ...f, payment_model: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">{paymentModelOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></div>
                <div><label htmlFor="coop-create-levy" className="block text-label-md font-bold text-on-surface-variant mb-1">Levy % *</label><input id="coop-create-levy" required type="number" step="0.01" min="0" max="100" value={form.levy_percentage} onChange={(e) => setForm(f => ({ ...f, levy_percentage: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="coop-create-fee" className="block text-label-md font-bold text-on-surface-variant mb-1">Monthly Fee *</label><input id="coop-create-fee" required type="number" step="0.01" min="0" value={form.monthly_fee} onChange={(e) => setForm(f => ({ ...f, monthly_fee: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="coop-create-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label><input id="coop-create-email" type="email" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div><label htmlFor="coop-create-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label><input id="coop-create-phone" type="tel" value={form.phone_number} onChange={(e) => setForm(f => ({ ...f, phone_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="coop-create-address" className="block text-label-md font-bold text-on-surface-variant mb-1">Physical Address</label><textarea id="coop-create-address" rows={2} value={form.physical_address} onChange={(e) => setForm(f => ({ ...f, physical_address: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setCreateOpen(false)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={formLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50">{formLoading ? 'Creating...' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

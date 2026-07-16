import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
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
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

const statusOptions = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'defaulted', label: 'Defaulted' },
  { value: 'completed', label: 'Completed' },
]

const statusBadgeMap = {
  pending: 'computing',
  approved: 'active',
  active: 'active',
  rejected: 'error',
  defaulted: 'locked',
  completed: 'completed',
}

import { useLocation, useSearchParams } from 'react-router-dom'

export default function Loans() {
  const { showToast } = useToast()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [sortField, setSortField] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selectedIds, setSelectedIds] = useState([])
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelItem, setPanelItem] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [createOpen, setCreateOpen] = useState(location.state?.openModal === true)
  const [editOpen, setEditOpen] = useState(false)
  const [editLoan, setEditLoan] = useState(null)
  const [farmerSearch, setFarmerSearch] = useState('')
  const [farmerOptions, setFarmerOptions] = useState([])
  const [farmerSearchOpen, setFarmerSearchOpen] = useState(false)
  const [selectedFarmerName, setSelectedFarmerName] = useState('')
  const [selectedFarmerId, setSelectedFarmerId] = useState('')
  const farmerRef = useRef(null)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    const handler = (e) => {
      if (farmerRef.current && !farmerRef.current.contains(e.target)) setFarmerSearchOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!farmerSearch || farmerSearch.length < 2) { setFarmerOptions([]); return }
    const t = setTimeout(async () => {
      try {
        const res = await apiFetch(`/api/admin/farmers/?search=${encodeURIComponent(farmerSearch)}&page_size=10`)
        if (!res.ok) return
        const d = await res.json()
        setFarmerOptions(d?.results || [])
      } catch {}
    }, 300)
    return () => clearTimeout(t)
  }, [farmerSearch])

  const selectFarmer = (f) => {
    setSelectedFarmerId(f.id)
    setSelectedFarmerName(`${f.first_name} ${f.last_name}`)
    setFarmerSearch('')
    setFarmerOptions([])
    setFarmerSearchOpen(false)
  }

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', page)
    params.set('page_size', pageSize)
    if (search) params.set('search', search)
    if (filters.status) params.set('status', filters.status)
    if (sortField) params.set('ordering', sortOrder === 'desc' ? `-${sortField}` : sortField)
    return params.toString()
  }, [page, pageSize, search, filters, sortField, sortOrder])

  const { data, loading, error, refetch } = useApi(`/api/admin/loans/?${query}`)
  const { data: kpiData } = useApi('/api/admin/loans/?page=1&page_size=1')

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

  const execAction = async (url) => {
    setActionLoading(true)
    try {
      const res = await apiFetch(url, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Loan updated.' })
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

  const { formAction: editFormAction } = useFormAction(async (prev, formData) => {
    if (!editLoan) return {}
    const data = formDataToObject(formData)
    try {
      const body = { ...data, amount_principal: parseFloat(data.amount_principal), interest_rate: parseFloat(data.interest_rate), number_of_installments: parseInt(data.number_of_installments) }
      const res = await apiFetch(`/api/admin/loans/${editLoan.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Loan updated.' })
      setEditOpen(false)
      setEditLoan(null)
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Update failed: ${e.message}` })
    }
    return {}
  }, {})

  const openEditLoan = (item) => {
    setEditLoan(item)
    setEditOpen(true)
  }

  const handleDisburse = (item) => {
    setModalConfig({
      open: true,
      title: 'Disburse Loan',
      message: `Disburse loan for ${item.farmer_name || item.id}?`,
      destructive: false,
      onConfirm: () => execAction(`/api/admin/loans/${item.id}/disburse/`),
    })
  }

  const { formAction: createFormAction } = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    try {
      const body = { ...data, farmer: selectedFarmerId, amount_principal: parseFloat(data.amount_principal), interest_rate: parseFloat(data.interest_rate), number_of_installments: parseInt(data.number_of_installments) }
      const res = await apiFetch('/api/admin/loans/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Loan created.' })
      setCreateOpen(false)
      setSelectedFarmerName('')
      setSelectedFarmerId('')
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Creation failed: ${e.message}` })
    }
    return {}
  }, {})

  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return
    const ids = [...selectedIds]
    try {
      await Promise.all(ids.map(id => apiFetch(`/api/admin/loans/${id}/${action}/`, { method: 'POST' })))
      showToast({ type: 'success', message: `${ids.length} loans ${action}ed.` })
      setSelectedIds([])
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Bulk action failed: ${e.message}` })
    }
  }

  const handleStatusAction = (item, newStatus) => {
    const labels = { approved: 'Approve', rejected: 'Reject', defaulted: 'Mark Defaulted', completed: 'Mark Completed' }
    setModalConfig({
      open: true,
      title: `${labels[newStatus]} Loan`,
      message: `${labels[newStatus]} loan for ${item.farmer_name || item.id}?`,
      destructive: newStatus === 'rejected' || newStatus === 'defaulted',
      onConfirm: () => execAction(`/api/admin/loans/${item.id}/${newStatus}/`),
    })
  }

  const columns = useMemo(() => [
    { key: 'id', label: 'ID', sortable: true, render: (_, r) => <span className="font-data-mono text-label-md text-on-surface-variant">{r.id?.slice(0, 8)}...</span> },
    { key: 'farmer_name', label: 'Farmer', sortable: true, render: (_, r) => <span className="font-medium text-body-md">{r.farmer_name || r.farmer?.name || '-'}</span> },
    { key: 'amount', label: 'Amount', sortable: true, render: (_, r) => <span className="font-data-mono text-body-md">KES {r.amount?.toLocaleString() || '-'}</span> },
    { key: 'interest_rate', label: 'Rate', render: (_, r) => <span className="text-label-md">{r.interest_rate ? `${r.interest_rate}%` : '-'}</span> },
    { key: 'status', label: 'Status', sortable: true, render: (_, r) => <StatusBadge status={statusBadgeMap[r.status] || 'computing'} label={r.status ? r.status.charAt(0).toUpperCase() + r.status.slice(1) : '-'} /> },
    { key: 'created_at', label: 'Date', sortable: true, render: (_, r) => r.created_at ? new Date(r.created_at).toLocaleDateString() : '-' },
  ], [])

  if (error) return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load loans: {error}</div>

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">Loans</h2>
          <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">add</span>
            New Loan
          </button>
        </div>
        <p className="text-on-surface-variant font-body-md">Manage farmer loan applications and disbursements.</p>
      </header>

      {loading && !kpiData ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"><KpiSkeleton count={1} /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KpiCard label="Total Loans" value={kpis.total} icon="account_balance" />
        </div>
      )}

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search farmer, ID..."
        filters={[
          { key: 'status', label: 'Status', options: statusOptions },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.status) p.set('status', filters.status); p.set('export', 'csv'); exportCsv(`/api/admin/loans/?${p}`) }}
      />

      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 px-4 py-2 bg-primary-container/50 border border-primary-container rounded-lg">
          <span className="text-label-md font-medium text-on-primary-container">{selectedIds.length} selected</span>
          <button onClick={() => handleBulkAction('approve')} className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90">Approve</button>
          <button onClick={() => handleBulkAction('reject')} className="px-3 py-1 text-label-md font-bold bg-error text-on-error rounded-lg hover:bg-error/90">Reject</button>
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
          emptyMessage="No loans found."
          rowActions={(item) => (
            <div className="flex items-center gap-1">
              <button onClick={() => { setPanelItem(item); setPanelOpen(true) }} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant" aria-label="View loan details"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">visibility</span></button>
              {item.status === 'pending' && (
                <>
                  <button onClick={() => openEditLoan(item)} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Edit loan"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span></button>
                  <button onClick={() => handleStatusAction(item, 'approved')} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Approve loan"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">check_circle</span></button>
                  <button onClick={() => handleStatusAction(item, 'rejected')} className="p-1.5 rounded-lg hover:bg-error-container text-error" aria-label="Reject loan"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">cancel</span></button>
                </>
              )}
              {item.status === 'approved' && (
                <>
                  <button onClick={() => handleDisburse(item)} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Disburse loan"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">payments</span></button>
                  <button onClick={() => handleStatusAction(item, 'defaulted')} className="p-1.5 rounded-lg hover:bg-error-container text-error" aria-label="Mark as defaulted"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">warning</span></button>
                  <button onClick={() => handleStatusAction(item, 'completed')} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Mark as completed"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">task_alt</span></button>
                </>
              )}
            </div>
          )}
        />
      )}

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelItem(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Loan Details">
        {panelItem && (
          <div className="space-y-4">
            <h4 className="font-headline-sm text-headline-sm text-on-surface">Loan Details</h4>
            <StatusBadge status={statusBadgeMap[panelItem.status] || 'computing'} label={panelItem.status ? panelItem.status.charAt(0).toUpperCase() + panelItem.status.slice(1) : '-'} />
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Farmer</p><p className="font-body-md text-on-surface">{panelItem.farmer_name || panelItem.farmer?.name || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Amount</p><p className="font-body-md text-on-surface font-data-mono">KES {panelItem.amount?.toLocaleString() || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Interest Rate</p><p className="font-body-md text-on-surface">{panelItem.interest_rate ? `${panelItem.interest_rate}%` : '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Duration</p><p className="font-body-md text-on-surface">{panelItem.duration_months ? `${panelItem.duration_months} months` : '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Created</p><p className="font-body-md text-on-surface">{panelItem.created_at ? new Date(panelItem.created_at).toLocaleDateString() : '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Due Date</p><p className="font-body-md text-on-surface">{panelItem.due_date ? new Date(panelItem.due_date).toLocaleDateString() : '-'}</p></div>
            </div>
            {panelItem.notes && (
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Notes</p><p className="font-body-md text-on-surface">{panelItem.notes}</p></div>
            )}
            <div className="pt-2 flex flex-wrap gap-2">
              {panelItem.status === 'pending' && (
                <>
                  <button onClick={() => { setPanelOpen(false); handleStatusAction(panelItem, 'approved') }} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90">Approve</button>
                  <button onClick={() => { setPanelOpen(false); handleStatusAction(panelItem, 'rejected') }} className="px-4 py-2 border border-error text-error rounded-lg text-label-md font-bold hover:bg-error-container">Reject</button>
                </>
              )}
              {panelItem.status === 'approved' && (
                <>
                  <button onClick={() => { setPanelOpen(false); handleStatusAction(panelItem, 'completed') }} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90">Mark Completed</button>
                  <button onClick={() => { setPanelOpen(false); handleStatusAction(panelItem, 'defaulted') }} className="px-4 py-2 border border-error text-error rounded-lg text-label-md font-bold hover:bg-error-container">Mark Defaulted</button>
                </>
              )}
            </div>
          </div>
        )}
      </SlideOutPanel>

      {createOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30 cursor-pointer" onClick={() => setCreateOpen(false)} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-md w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="create-loan-title">
            <h3 id="create-loan-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Create Loan</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Issue a new loan to a farmer.</p>
            <form action={createFormAction} className="space-y-3">
              <div ref={farmerRef} className="relative">
                <label htmlFor="loan-create-farmer" className="block text-label-md font-bold text-on-surface-variant mb-1">Farmer *</label>
                {selectedFarmerName ? (
                  <div className="flex items-center gap-2 w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">
                    <span className="flex-1">{selectedFarmerName}</span>
                    <button type="button" onClick={() => { setSelectedFarmerId(''); setSelectedFarmerName('') }} className="text-on-surface-variant hover:text-on-surface" aria-label="Clear farmer selection"><span className="material-symbols-outlined text-[16px]" aria-hidden="true">close</span></button>
                  </div>
                ) : (
                  <input id="loan-create-farmer" value={farmerSearch} onChange={(e) => { setFarmerSearch(e.target.value); setFarmerSearchOpen(true) }} onFocus={() => setFarmerSearchOpen(true)} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="Search farmer by name, phone, ID..." />
                )}
                {farmerSearchOpen && farmerOptions.length > 0 && (
                  <div className="absolute z-50 mt-1 w-full bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg max-h-48 overflow-y-auto" role="listbox">
                    {farmerOptions.map(f => (
                      <button key={f.id} type="button" role="option" aria-selected="false" onClick={() => selectFarmer(f)} className="flex items-center gap-3 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors text-left">
                        <div className="w-7 h-7 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-[10px]">{f.first_name?.[0]}{f.last_name?.[0]}</div>
                        <div><p className="font-medium">{f.first_name} {f.last_name}</p><p className="text-[11px] text-on-surface-variant">{f.phone_number || f.email || f.id_number}</p></div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <input type="hidden" name="farmer" value={selectedFarmerId} />
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="loan-create-amount" className="block text-label-md font-bold text-on-surface-variant mb-1">Amount (KES) *</label><input id="loan-create-amount" type="number" min="0" step="0.01" required name="amount_principal" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="loan-create-rate" className="block text-label-md font-bold text-on-surface-variant mb-1">Interest Rate (%) *</label><input id="loan-create-rate" type="number" min="0" step="0.1" required name="interest_rate" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div><label htmlFor="loan-create-installments" className="block text-label-md font-bold text-on-surface-variant mb-1">Installments *</label><input id="loan-create-installments" type="number" min="1" required name="number_of_installments" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="loan-create-purpose" className="block text-label-md font-bold text-on-surface-variant mb-1">Purpose</label><input id="loan-create-purpose" name="purpose" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="loan-create-notes" className="block text-label-md font-bold text-on-surface-variant mb-1">Notes</label><textarea id="loan-create-notes" rows={2} name="notes" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setCreateOpen(false)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <SubmitButton className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90">Create</SubmitButton>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmModal open={modalConfig.open} title={modalConfig.title} message={modalConfig.message} onConfirm={modalConfig.onConfirm} onCancel={() => setModalConfig({ open: false })} loading={actionLoading} destructive={modalConfig.destructive} />

      {editOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30 cursor-pointer" onClick={() => { setEditOpen(false); setEditLoan(null) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-md w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="edit-loan-title">
            <h3 id="edit-loan-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Edit Loan</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Update loan details.</p>
            <form key={editLoan?.id} action={editFormAction} className="space-y-3">
              <div><label htmlFor="loan-edit-farmer" className="block text-label-md font-bold text-on-surface-variant mb-1">Farmer</label><input id="loan-edit-farmer" value={editLoan?.farmer_name || editLoan?.farmer?.name || ''} disabled className="w-full bg-surface-container/50 border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface opacity-60" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="loan-edit-amount" className="block text-label-md font-bold text-on-surface-variant mb-1">Amount (KES)</label><input id="loan-edit-amount" type="number" min="0" step="0.01" required name="amount_principal" defaultValue={editLoan?.amount_principal || editLoan?.amount || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="loan-edit-rate" className="block text-label-md font-bold text-on-surface-variant mb-1">Interest Rate (%)</label><input id="loan-edit-rate" type="number" min="0" step="0.1" required name="interest_rate" defaultValue={editLoan?.interest_rate || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div><label htmlFor="loan-edit-installments" className="block text-label-md font-bold text-on-surface-variant mb-1">Installments</label><input id="loan-edit-installments" type="number" min="1" required name="number_of_installments" defaultValue={editLoan?.number_of_installments || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="loan-edit-purpose" className="block text-label-md font-bold text-on-surface-variant mb-1">Purpose</label><input id="loan-edit-purpose" name="purpose" defaultValue={editLoan?.purpose || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="loan-edit-notes" className="block text-label-md font-bold text-on-surface-variant mb-1">Notes</label><textarea id="loan-edit-notes" rows={2} name="notes" defaultValue={editLoan?.notes || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setEditOpen(false); setEditLoan(null) }} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <SubmitButton className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90">Save</SubmitButton>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

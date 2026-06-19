import { useState, useMemo, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import KpiCard from '../components/common/KpiCard'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'
import { KpiSkeleton, TableSkeleton } from '../components/common/Skeleton'

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
  rejected: 'error',
  defaulted: 'locked',
  completed: 'completed',
}

export default function Loans() {
  const { showToast } = useToast()
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
  const [createOpen, setCreateOpen] = useState(false)
  const [loanForm, setLoanForm] = useState({ farmer: '', amount_principal: '', interest_rate: '', number_of_installments: '', purpose: '', notes: '' })
  const [formLoading, setFormLoading] = useState(false)

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

  const handleSort = useCallback((field) => {
    if (sortField === field) setSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortOrder('asc') }
  }, [sortField])

  const execAction = async (url) => {
    try {
      const res = await apiFetch(url, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Loan updated.' })
      setModalConfig({ open: false })
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Action failed: ${e.message}` })
    }
  }

  const handleCreateLoan = async (e) => {
    e.preventDefault()
    setFormLoading(true)
    try {
      const body = { ...loanForm, amount_principal: parseFloat(loanForm.amount_principal), interest_rate: parseFloat(loanForm.interest_rate), number_of_installments: parseInt(loanForm.number_of_installments) }
      const res = await apiFetch('/api/admin/loans/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Loan created.' })
      setCreateOpen(false)
      setLoanForm({ farmer: '', amount_principal: '', interest_rate: '', number_of_installments: '', purpose: '', notes: '' })
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Creation failed: ${e.message}` })
    } finally {
      setFormLoading(false)
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
    { key: 'id', label: 'ID', sortable: true, render: (r) => <span className="font-data-mono text-label-md text-on-surface-variant">{r.id?.slice(0, 8)}...</span> },
    { key: 'farmer_name', label: 'Farmer', sortable: true, render: (r) => <span className="font-medium text-body-md">{r.farmer_name || r.farmer?.name || '-'}</span> },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="font-data-mono text-body-md">KES {r.amount?.toLocaleString() || '-'}</span> },
    { key: 'interest_rate', label: 'Rate', render: (r) => <span className="text-label-md">{r.interest_rate ? `${r.interest_rate}%` : '-'}</span> },
    { key: 'status', label: 'Status', sortable: true, render: (r) => <StatusBadge status={statusBadgeMap[r.status] || 'computing'} label={r.status ? r.status.charAt(0).toUpperCase() + r.status.slice(1) : '-'} /> },
    { key: 'created_at', label: 'Date', sortable: true, render: (r) => r.created_at ? new Date(r.created_at).toLocaleDateString() : '-' },
  ], [])

  if (error) return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load loans: {error}</div>

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">Loans</h2>
          <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
            <span className="material-symbols-outlined text-[16px]">add</span>
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
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.status) p.set('status', filters.status); p.set('export', 'csv'); window.open(`/api/admin/loans/?${p}`, '_blank') }}
      />

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
              <button onClick={() => { setPanelItem(item); setPanelOpen(true) }} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant" aria-label="View"><span className="material-symbols-outlined text-[18px]">visibility</span></button>
              {item.status === 'pending' && (
                <>
                  <button onClick={() => handleStatusAction(item, 'approved')} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Approve"><span className="material-symbols-outlined text-[18px]">check_circle</span></button>
                  <button onClick={() => handleStatusAction(item, 'rejected')} className="p-1.5 rounded-lg hover:bg-error-container text-error" aria-label="Reject"><span className="material-symbols-outlined text-[18px]">cancel</span></button>
                </>
              )}
              {item.status === 'approved' && (
                <>
                  <button onClick={() => handleStatusAction(item, 'defaulted')} className="p-1.5 rounded-lg hover:bg-error-container text-error" aria-label="Mark Defaulted"><span className="material-symbols-outlined text-[18px]">warning</span></button>
                  <button onClick={() => handleStatusAction(item, 'completed')} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Mark Completed"><span className="material-symbols-outlined text-[18px]">task_alt</span></button>
                </>
              )}
            </div>
          )}
        />
      )}

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelItem(null) }} title="Loan Details">
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
        <div className="fixed inset-0 z-[65] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => setCreateOpen(false)} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-md w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">Create Loan</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Issue a new loan to a farmer.</p>
            <form onSubmit={handleCreateLoan} className="space-y-3">
              <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Farmer ID *</label><input required value={loanForm.farmer} onChange={(e) => setLoanForm(f => ({ ...f, farmer: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="UUID" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Amount (KES) *</label><input type="number" min="0" step="0.01" required value={loanForm.amount_principal} onChange={(e) => setLoanForm(f => ({ ...f, amount_principal: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Interest Rate (%) *</label><input type="number" min="0" step="0.1" required value={loanForm.interest_rate} onChange={(e) => setLoanForm(f => ({ ...f, interest_rate: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Installments *</label><input type="number" min="1" required value={loanForm.number_of_installments} onChange={(e) => setLoanForm(f => ({ ...f, number_of_installments: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Purpose</label><input value={loanForm.purpose} onChange={(e) => setLoanForm(f => ({ ...f, purpose: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Notes</label><textarea rows={2} value={loanForm.notes} onChange={(e) => setLoanForm(f => ({ ...f, notes: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setCreateOpen(false)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={formLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50">{formLoading ? 'Creating...' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmModal open={modalConfig.open} title={modalConfig.title} message={modalConfig.message} onConfirm={modalConfig.onConfirm} onCancel={() => setModalConfig({ open: false })} destructive={modalConfig.destructive} />
    </div>
  )
}

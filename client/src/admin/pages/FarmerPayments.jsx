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

export default function FarmerPayments() {
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

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', page)
    params.set('page_size', pageSize)
    if (search) params.set('search', search)
    if (filters.status) params.set('status', filters.status)
    if (filters.cycle) params.set('cycle', filters.cycle)
    if (sortField) params.set('ordering', sortOrder === 'desc' ? `-${sortField}` : sortField)
    return params.toString()
  }, [page, pageSize, search, filters, sortField, sortOrder])

  const { data, loading, error, refetch } = useApi(`/api/admin/farmer-payments/?${query}`)
  const { data: kpiData } = useApi('/api/admin/farmer-payments/?page=1&page_size=1')
  const { data: cyclesData } = useApi('/api/admin/payment-cycles/?page_size=50&ordering=-created_at')

  const cycles = cyclesData?.results || (Array.isArray(cyclesData) ? cyclesData : [])

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
      showToast({ type: 'success', message: 'Payment updated.' })
      setModalConfig({ open: false })
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Action failed: ${e.message}` })
    }
  }

  const handleHold = (item) => setModalConfig({ open: true, title: 'Hold Payment', message: `Hold payment for ${item.farmer_name || item.id}?`, destructive: false, onConfirm: () => execAction(`/api/admin/farmer-payments/${item.id}/hold/`) })
  const handleUnhold = (item) => setModalConfig({ open: true, title: 'Release Payment', message: `Release hold on payment for ${item.farmer_name || item.id}?`, destructive: false, onConfirm: () => execAction(`/api/admin/farmer-payments/${item.id}/unhold/`) })

  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return
    const ids = [...selectedIds]
    try {
      await Promise.all(ids.map(id => apiFetch(`/api/admin/farmer-payments/${id}/${action}/`, { method: 'POST' })))
      showToast({ type: 'success', message: `${ids.length} payments ${action}ed.` })
      setSelectedIds([])
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Bulk action failed: ${e.message}` })
    }
  }

  const columns = useMemo(() => [
    { key: 'id', label: 'ID', render: (r) => <span className="font-data-mono text-label-md text-on-surface-variant">{r.id?.slice(0, 8)}...</span> },
    { key: 'farmer_name', label: 'Farmer', sortable: true, render: (r) => <span className="font-medium text-body-md">{r.farmer_name || r.farmer?.name || '-'}</span> },
    { key: 'cycle', label: 'Cycle', render: (r) => <span className="text-label-md text-on-surface-variant">{r.cycle_name || r.cycle?.name || '-'}</span> },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="font-data-mono text-body-md">KES {r.amount?.toLocaleString() || '-'}</span> },
    { key: 'status', label: 'Status', sortable: true, render: (r) => <StatusBadge status={r.status === 'held' ? 'locked' : r.status === 'paid' ? 'completed' : 'active'} label={r.status ? r.status.charAt(0).toUpperCase() + r.status.slice(1) : '-'} /> },
    { key: 'created_at', label: 'Date', sortable: true, render: (r) => r.created_at ? new Date(r.created_at).toLocaleDateString() : '-' },
  ], [])

  if (error) return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load payments: {error}</div>

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">Farmer Payments</h2>
        </div>
        <p className="text-on-surface-variant font-body-md">Track payments to farmers across payment cycles.</p>
      </header>

      {loading && !kpiData ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"><KpiSkeleton count={1} /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KpiCard label="Total Payments" value={kpis.total} icon="payments" />
        </div>
      )}

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search farmer, cycle..."
        filters={[
          { key: 'status', label: 'Status', options: [{ value: 'pending', label: 'Pending' }, { value: 'paid', label: 'Paid' }, { value: 'held', label: 'Held' }] },
          { key: 'cycle', label: 'Cycle', options: cycles.map(c => ({ value: c.id, label: c.name || c.id?.slice(0, 8) })) },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.status) p.set('payment_status', filters.status); if (filters.cycle) p.set('cycle', filters.cycle); p.set('export', 'csv'); window.open(`/api/admin/farmer-payments/?${p}`, '_blank') }}
      />

      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 px-4 py-2 bg-primary-container/50 border border-primary-container rounded-lg">
          <span className="text-label-md font-medium text-on-primary-container">{selectedIds.length} selected</span>
          <button onClick={() => handleBulkAction('hold')} className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90">Hold</button>
          <button onClick={() => handleBulkAction('unhold')} className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90">Release</button>
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
          emptyMessage="No payments found."
          rowActions={(item) => (
            <div className="flex items-center gap-1">
              <button onClick={() => { setPanelItem(item); setPanelOpen(true) }} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant" aria-label="View"><span className="material-symbols-outlined text-[18px]">visibility</span></button>
              {item.status === 'held' ? (
                <button onClick={() => handleUnhold(item)} className="p-1.5 rounded-lg hover:bg-primary-container text-primary" aria-label="Release"><span className="material-symbols-outlined text-[18px]">lock_open</span></button>
              ) : (
                <button onClick={() => handleHold(item)} className="p-1.5 rounded-lg hover:bg-warning-container text-warning" aria-label="Hold"><span className="material-symbols-outlined text-[18px]">lock</span></button>
              )}
            </div>
          )}
        />
      )}

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelItem(null) }} title="Payment Details">
        {panelItem && (
          <div className="space-y-4">
            <h4 className="font-headline-sm text-headline-sm text-on-surface">Farmer Payment</h4>
            <StatusBadge status={panelItem.status === 'held' ? 'locked' : panelItem.status === 'paid' ? 'completed' : 'active'} label={panelItem.status ? panelItem.status.charAt(0).toUpperCase() + panelItem.status.slice(1) : '-'} />
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Farmer</p><p className="font-body-md text-on-surface">{panelItem.farmer_name || panelItem.farmer?.name || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Amount</p><p className="font-body-md text-on-surface font-data-mono">KES {panelItem.amount?.toLocaleString() || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Cycle</p><p className="font-body-md text-on-surface">{panelItem.cycle_name || panelItem.cycle?.name || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Status</p><p className="font-body-md text-on-surface">{panelItem.status || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Created</p><p className="font-body-md text-on-surface">{panelItem.created_at ? new Date(panelItem.created_at).toLocaleDateString() : '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Paid On</p><p className="font-body-md text-on-surface">{panelItem.paid_at ? new Date(panelItem.paid_at).toLocaleDateString() : '-'}</p></div>
            </div>
            <div className="pt-2">
              {panelItem.status === 'held' ? (
                <button onClick={() => { setPanelOpen(false); handleUnhold(panelItem) }} className="w-full px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90">Release Payment</button>
              ) : (
                <button onClick={() => { setPanelOpen(false); handleHold(panelItem) }} className="w-full px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container">Hold Payment</button>
              )}
            </div>
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal open={modalConfig.open} title={modalConfig.title} message={modalConfig.message} onConfirm={modalConfig.onConfirm} onCancel={() => setModalConfig({ open: false })} destructive={modalConfig.destructive} />
    </div>
  )
}

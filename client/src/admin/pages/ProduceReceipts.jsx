import { useState, useMemo, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'

const statusOptions = [
  { value: 'PENDING', label: 'Pending' },
  { value: 'GRADED', label: 'Graded' },
  { value: 'ACCEPTED', label: 'Accepted' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'PAID', label: 'Paid' },
]

const statusBadgeMap = {
  PENDING: 'pending',
  GRADED: 'graded',
  ACCEPTED: 'accepted',
  REJECTED: 'rejected',
  PAID: 'paid',
}

const productTypeOptions = [
  { value: 'COFFEE', label: 'Coffee' },
  { value: 'MAIZE', label: 'Maize' },
  { value: 'BEANS', label: 'Beans' },
  { value: 'MILK', label: 'Milk' },
]

const shiftOptions = [
  { value: 'MORNING', label: 'Morning' },
  { value: 'AFTERNOON', label: 'Afternoon' },
  { value: 'EVENING', label: 'Evening' },
]

export default function ProduceReceipts() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [sortField, setSortField] = useState('date_delivered')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selectedIds, setSelectedIds] = useState([])
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelDelivery, setPanelDelivery] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [actionLoading, setActionLoading] = useState(false)
  const [statusDelivery, setStatusDelivery] = useState(null)
  const [statusTarget, setStatusTarget] = useState('')

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', page)
    params.set('page_size', pageSize)
    if (search) params.set('search', search)
    if (filters.status) params.set('status', filters.status)
    if (filters.product_type) params.set('product_type', filters.product_type)
    if (filters.shift) params.set('shift', filters.shift)
    if (sortField) params.set('ordering', sortOrder === 'desc' ? `-${sortField}` : sortField)
    return params.toString()
  }, [page, pageSize, search, filters, sortField, sortOrder])

  const { data, loading, error, refetch } = useApi(`/api/admin/deliveries/?${query}`)

  const handleSort = useCallback((field) => {
    if (sortField === field) setSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortOrder('asc') }
  }, [sortField])

  const handleView = (delivery) => {
    setPanelDelivery(delivery)
    setPanelOpen(true)
  }

  const openForceStatus = (delivery) => {
    setStatusDelivery(delivery)
    setStatusTarget('')
  }

  const confirmForceStatus = async () => {
    if (!statusDelivery || !statusTarget) return
    setActionLoading(true)
    setModalConfig({ open: false })
    try {
      const res = await apiFetch(`/api/admin/deliveries/${statusDelivery.id}/force-status/`, {
        method: 'POST',
        body: JSON.stringify({ status: statusTarget }),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Delivery ${statusDelivery.batch_id} status changed to ${statusTarget}.` })
      refetch()
      setStatusDelivery(null)
      setStatusTarget('')
    } catch (e) {
      showToast({ type: 'error', message: `Force status failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const openConfirmForceStatus = () => {
    if (!statusTarget) return
    setModalConfig({
      open: true,
      title: 'Confirm Status Change',
      message: `Change delivery ${statusDelivery.batch_id} status to ${statusTarget}? This is an admin override.`,
      onConfirm: confirmForceStatus,
      destructive: statusTarget === 'REJECTED',
    })
  }

  const statusCounts = useMemo(() => {
    if (!data?.results) return { total: 0 }
    const counts = {}
    data.results.forEach(d => { counts[d.status] = (counts[d.status] || 0) + 1 })
    return { total: data.results.length, ...counts }
  }, [data])

  const columns = useMemo(() => [
    { key: 'batch_id', label: 'Batch ID', sortable: true, render: (r) => <span className="font-data-mono text-primary">{r.batch_id}</span> },
    { key: 'farmer_name', label: 'Farmer', sortable: true, render: (r) => <span className="font-medium">{r.farmer_name}</span> },
    { key: 'product_type', label: 'Product', sortable: true, render: (r) => <span className="capitalize">{r.product_type?.toLowerCase()}</span> },
    { key: 'quantity_kg', label: 'Qty (kg)', sortable: true, render: (r) => <span className="font-data-mono">{r.quantity_kg?.toLocaleString()}</span> },
    { key: 'grade', label: 'Grade', render: (r) => <span className="font-medium">{r.grade || '-'}</span> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={statusBadgeMap[r.status] || 'draft'} label={r.status} /> },
    { key: 'shift', label: 'Shift', sortable: true, render: (r) => <span className="capitalize text-on-surface-variant">{(r.shift || '').toLowerCase()}</span> },
    { key: 'date_delivered', label: 'Date', sortable: true, render: (r) => r.date_delivered ? new Date(r.date_delivered).toLocaleDateString() : '-' },
  ], [])

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load deliveries: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Produce Receipts</h2>
        <p className="text-on-surface-variant font-body-md">Track and manage all produce deliveries across cooperatives.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KpiCard icon="inventory_2" label="Total Deliveries" value={data?.count || 0} />
        <KpiCard icon="grading" label="Pending Grading" value={statusCounts.PENDING || 0} />
        <KpiCard icon="check_circle" label="Accepted" value={statusCounts.ACCEPTED || 0} />
        <KpiCard icon="cancel" label="Rejected" value={statusCounts.REJECTED || 0} highlighted={statusCounts.REJECTED > 0} />
      </div>

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search batch ID, farmer name, phone..."
        filters={[
          { key: 'status', label: 'Status', options: statusOptions },
          { key: 'product_type', label: 'Product', options: productTypeOptions },
          { key: 'shift', label: 'Shift', options: shiftOptions },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.status) p.set('status', filters.status); if (filters.product_type) p.set('product_type', filters.product_type); if (filters.shift) p.set('shift', filters.shift); p.set('export', 'csv'); window.open(`/api/admin/deliveries/?${p}`, '_blank') }}
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        sortField={sortField}
        sortOrder={sortOrder}
        onSort={handleSort}
        loading={loading}
        emptyMessage="No deliveries found."
        rowActions={(delivery) => (
          <div className="flex gap-0.5">
            <button onClick={() => handleView(delivery)} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined text-[18px]">visibility</span>
            </button>
            <button onClick={() => openForceStatus(delivery)} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors" title="Force Status">
              <span className="material-symbols-outlined text-[18px]">swap_horiz</span>
            </button>
          </div>
        )}
      />

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      {/* Force Status Dropdown Modal */}
      {statusDelivery && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => { setStatusDelivery(null); setStatusTarget('') }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-1">Force Status Change</h3>
            <p className="text-label-md text-on-surface-variant mb-4">
              Delivery: <span className="font-data-mono">{statusDelivery.batch_id}</span>
            </p>
            <select
              value={statusTarget}
              onChange={(e) => setStatusTarget(e.target.value)}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface mb-4"
            >
              <option value="">Select new status...</option>
              {statusOptions.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setStatusDelivery(null); setStatusTarget('') }}
                className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={openConfirmForceStatus}
                disabled={!statusTarget}
                className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelDelivery(null) }} title="Delivery Details">
        {panelDelivery && (
          <div className="space-y-4">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-2 rounded-lg bg-primary/5 text-primary">
                <span className="material-symbols-outlined text-[24px]">receipt_long</span>
              </div>
              <div>
                <h4 className="font-headline-sm text-headline-sm text-on-surface">{panelDelivery.batch_id}</h4>
                <StatusBadge status={statusBadgeMap[panelDelivery.status] || 'draft'} label={panelDelivery.status} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Farmer</p>
                <p className="font-body-md text-on-surface">{panelDelivery.farmer_name}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Grader</p>
                <p className="font-body-md text-on-surface">{panelDelivery.grader_name || 'Unassigned'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Product</p>
                <p className="font-body-md text-on-surface capitalize">{panelDelivery.product_type?.toLowerCase()}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Quantity</p>
                <p className="font-data-mono text-headline-sm text-on-surface">{panelDelivery.quantity_kg?.toLocaleString()} kg</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Grade</p>
                <p className="font-body-md text-on-surface">{panelDelivery.grade || 'Not graded'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Shift</p>
                <p className="font-body-md text-on-surface capitalize">{(panelDelivery.shift || '').toLowerCase()}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Date Delivered</p>
                <p className="font-body-md text-on-surface">{panelDelivery.date_delivered ? new Date(panelDelivery.date_delivered).toLocaleDateString() : '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Rejection Reason</p>
                <p className="font-body-md text-on-surface">{panelDelivery.rejection_reason || '-'}</p>
              </div>
            </div>
            {panelDelivery.quality_metrics && (
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant mb-2">Quality Metrics</p>
                <p className="font-body-md text-on-surface">{JSON.stringify(panelDelivery.quality_metrics)}</p>
              </div>
            )}
            <div className="pt-2">
              <button onClick={() => { setPanelOpen(false); openForceStatus(panelDelivery) }} className="w-full px-4 py-2 border border-primary text-primary rounded-lg text-label-md font-bold hover:bg-primary/5 transition-colors">
                Force Status Change
              </button>
            </div>
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal
        open={modalConfig.open}
        title={modalConfig.title}
        message={modalConfig.message}
        onConfirm={modalConfig.onConfirm}
        onCancel={() => setModalConfig({ open: false })}
        loading={actionLoading}
        destructive={modalConfig.destructive}
      />
    </div>
  )
}

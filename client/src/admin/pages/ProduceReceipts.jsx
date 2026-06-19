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

  const handleForceStatus = (delivery) => {
    setModalConfig({
      open: true,
      title: 'Force Status Change',
      message: `Change status of delivery ${delivery.batch_id}? This is an admin override.`,
      onConfirm: async () => {
        setActionLoading(true)
        setModalConfig({ open: false })
        try {
          const res = await apiFetch(`/api/admin/deliveries/${delivery.id}/force-status/`, {
            method: 'POST',
            body: JSON.stringify({ status: prompt('Enter new status (PENDING/GRADED/ACCEPTED/REJECTED/PAID):') }),
          })
          refetch()
        } catch (e) {
          console.error('Force status failed', e)
        } finally {
          setActionLoading(false)
        }
      },
      destructive: false,
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
            <button onClick={() => handleForceStatus(delivery)} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors" title="Force Status">
              <span className="material-symbols-outlined text-[18px]">swap_horiz</span>
            </button>
          </div>
        )}
      />

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

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
              <button onClick={() => handleForceStatus(panelDelivery)} className="w-full px-4 py-2 border border-primary text-primary rounded-lg text-label-md font-bold hover:bg-primary/5 transition-colors">
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

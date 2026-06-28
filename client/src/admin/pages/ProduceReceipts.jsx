import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch, exportCsv } from '../api/client'
import KpiCard from '../components/common/KpiCard'
import { KpiSkeleton } from '../components/common/Skeleton'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'
import { useLocation } from 'react-router-dom'

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

const createProductTypeOptions = [
  { value: 'MILK', label: 'Milk' },
  { value: 'COFFEE_CHERRIES', label: 'Coffee Cherries' },
  { value: 'HONEY', label: 'Honey' },
  { value: 'OTHER', label: 'Other' },
]

const createShiftOptions = [
  { value: 'AM', label: 'Morning' },
  { value: 'PM', label: 'Evening' },
]

const productTypeOptions = [
  { value: 'COFFEE', label: 'Coffee' },
  { value: 'MAIZE', label: 'Maize' },
  { value: 'BEANS', label: 'Beans' },
  { value: 'MILK', label: 'Milk' },
]

const gradeLetterOptions = [
  { value: 'A', label: 'A' },
  { value: 'B', label: 'B' },
  { value: 'C', label: 'C' },
  { value: 'PREMIUM', label: 'Premium' },
  { value: 'STANDARD', label: 'Standard' },
]

const shiftOptions = [
  { value: 'MORNING', label: 'Morning' },
  { value: 'AFTERNOON', label: 'Afternoon' },
  { value: 'EVENING', label: 'Evening' },
]

export default function ProduceReceipts() {
  const { showToast } = useToast()
  const location = useLocation()
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
  const [createOpen, setCreateOpen] = useState(location.state?.openModal === true)
  const [createForm, setCreateForm] = useState({ farmer: '', product_type: 'MILK', quantity_kg: '', volume_litres: '', shift: 'AM', date_delivered: '' })
  const [formLoading, setFormLoading] = useState(false)
  const [gradeDelivery, setGradeDelivery] = useState(null)
  const [gradeForm, setGradeForm] = useState({ grade_letter: 'A', price_per_unit: '', rejection_reason: '', override_reason: '' })
  const [gradeLoading, setGradeLoading] = useState(false)
  const [farmerSearch, setFarmerSearch] = useState('')
  const [farmerOptions, setFarmerOptions] = useState([])
  const [farmerSearchOpen, setFarmerSearchOpen] = useState(false)
  const [selectedFarmerName, setSelectedFarmerName] = useState('')
  const farmerRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (farmerRef.current && !farmerRef.current.contains(e.target)) setFarmerSearchOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!farmerSearch || farmerSearch.length < 2) { setFarmerOptions([]); return }
    const timer = setTimeout(async () => {
      try {
        const res = await apiFetch(`/api/admin/farmers/?search=${encodeURIComponent(farmerSearch)}&page_size=10`)
        const data = await res.json()
        setFarmerOptions(data?.results || [])
      } catch { setFarmerOptions([]) }
    }, 300)
    return () => clearTimeout(timer)
  }, [farmerSearch])

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

  const handleCreate = async (e) => {
    e.preventDefault()
    setFormLoading(true)
    try {
      const body = {
        farmer: createForm.farmer,
        product_type: createForm.product_type,
        quantity_kg: createForm.quantity_kg ? parseFloat(createForm.quantity_kg) : null,
        volume_litres: createForm.volume_litres ? parseFloat(createForm.volume_litres) : null,
        shift: createForm.shift,
        date_delivered: createForm.date_delivered || undefined,
      }
      const res = await apiFetch('/api/admin/deliveries/', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || Object.values(err).flat().join(', ') || 'Create failed')
      }
      showToast({ type: 'success', message: 'Delivery created successfully.' })
      setCreateOpen(false)
      setCreateForm({ farmer: '', product_type: 'MILK', quantity_kg: '', volume_litres: '', shift: 'AM', date_delivered: '' })
      setSelectedFarmerName('')
      setFarmerSearch('')
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: e.message })
    } finally {
      setFormLoading(false)
    }
  }

  const openForceStatus = (delivery) => {
    setStatusDelivery(delivery)
    setStatusTarget('')
  }

  const confirmForceStatus = async (delivery, target) => {
    setActionLoading(true)
    try {
      const res = await apiFetch(`/api/admin/deliveries/${delivery.id}/force-status/`, {
        method: 'POST',
        body: JSON.stringify({ status: target }),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Delivery ${delivery.batch_id} status changed to ${target}.` })
      refetch()
      const result = await res.json().catch(() => ({}))
      if (panelDelivery && typeof result === 'object') {
        const { detail, message, error, status, ...updates } = result
        const safeUpdates = Object.fromEntries(
          Object.entries(updates).filter(([, v]) => v !== null && typeof v !== 'object')
        )
        if (Object.keys(safeUpdates).length > 0) {
          setPanelDelivery(prev => ({ ...prev, ...safeUpdates }))
        }
      }
      setModalConfig({ open: false })
    } catch (e) {
      showToast({ type: 'error', message: `Force status failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const openConfirmForceStatus = () => {
    if (!statusTarget) return
    const delivery = statusDelivery
    const target = statusTarget
    setStatusDelivery(null)
    setStatusTarget('')
    setModalConfig({
      open: true,
      title: 'Confirm Status Change',
      message: `Change delivery ${delivery.batch_id} status to ${target}? This is an admin override.`,
      onConfirm: () => confirmForceStatus(delivery, target),
      destructive: target === 'REJECTED',
    })
  }

  const openAssignGrade = (delivery) => {
    setGradeDelivery(delivery)
    setGradeForm({
      grade_letter: delivery.grade || 'A',
      price_per_unit: '',
      rejection_reason: '',
      override_reason: '',
    })
  }

  const handleAssignGrade = async (e) => {
    e.preventDefault()
    if (!gradeDelivery) return
    setGradeLoading(true)
    try {
      const body = {}
      if (gradeForm.rejection_reason) {
        body.rejection_reason = gradeForm.rejection_reason
      } else {
        body.grade_letter = gradeForm.grade_letter
        body.price_per_unit = gradeForm.price_per_unit ? parseFloat(gradeForm.price_per_unit) : null
      }
      if (gradeForm.override_reason) body.override_reason = gradeForm.override_reason

      const res = await apiFetch(`/api/admin/deliveries/${gradeDelivery.id}/assign-grade/`, {
        method: 'POST',
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || Object.values(err).flat().join(', ') || 'Assign grade failed')
      }
      showToast({ type: 'success', message: `Grade assigned to ${gradeDelivery.batch_id}.` })
      setGradeDelivery(null)
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: e.message })
    } finally {
      setGradeLoading(false)
    }
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
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Produce Receipts</h2>
          <p className="text-on-surface-variant font-body-md">Track and manage all produce deliveries across cooperatives.</p>
        </div>
        <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-label-md font-bold hover:bg-primary/90 transition-colors">
          <span className="material-symbols-outlined text-[18px]">add</span>
          New Delivery
        </button>
      </header>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6"><KpiSkeleton count={4} /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <KpiCard icon="inventory_2" label="Total Deliveries" value={data?.count || 0} />
          <KpiCard icon="grading" label="Pending Grading" value={statusCounts.PENDING || 0} />
          <KpiCard icon="check_circle" label="Accepted" value={statusCounts.ACCEPTED || 0} />
          <KpiCard icon="cancel" label="Rejected" value={statusCounts.REJECTED || 0} highlighted={statusCounts.REJECTED > 0} />
        </div>
      )}

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
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.status) p.set('status', filters.status); if (filters.product_type) p.set('product_type', filters.product_type); if (filters.shift) p.set('shift', filters.shift); p.set('export', 'csv'); exportCsv(`/api/admin/deliveries/?${p}`) }}
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
            <button onClick={() => { setPanelOpen(false); setPanelDelivery(null); openForceStatus(delivery) }} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors" title="Force Status">
              <span className="material-symbols-outlined text-[18px]">swap_horiz</span>
            </button>
            <button onClick={() => openAssignGrade(delivery)} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors" title="Assign Grade">
              <span className="material-symbols-outlined text-[18px]">rate_review</span>
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

      {/* Assign Grade Modal */}
      {gradeDelivery && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => { if (!gradeLoading) setGradeDelivery(null) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-md w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">Assign Grade</h3>
              <button onClick={() => setGradeDelivery(null)} className="p-1 rounded-lg hover:bg-surface-container text-on-surface-variant" disabled={gradeLoading}>
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <p className="text-label-md text-on-surface-variant mb-4">
              Delivery: <span className="font-data-mono">{gradeDelivery.batch_id}</span>
            </p>
            <form onSubmit={handleAssignGrade} className="space-y-4">
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <button
                    type="button"
                    onClick={() => setGradeForm(f => ({ ...f, grade_letter: f.grade_letter || 'A', rejection_reason: '' }))}
                    className={`px-3 py-1.5 rounded-lg text-label-md font-bold transition-colors ${!gradeForm.rejection_reason ? 'bg-primary text-white' : 'bg-surface-container text-on-surface-variant'}`}
                  >
                    Grade
                  </button>
                  <button
                    type="button"
                    onClick={() => setGradeForm(f => ({ ...f, rejection_reason: ' ', grade_letter: '' }))}
                    className={`px-3 py-1.5 rounded-lg text-label-md font-bold transition-colors ${gradeForm.rejection_reason ? 'bg-error text-white' : 'bg-surface-container text-on-surface-variant'}`}
                  >
                    Reject
                  </button>
                </div>
              </div>
              {!gradeForm.rejection_reason ? (
                <>
                  <div>
                    <label className="block text-label-md font-bold text-on-surface mb-1.5">Grade Letter</label>
                    <select
                      value={gradeForm.grade_letter}
                      onChange={(e) => setGradeForm(f => ({ ...f, grade_letter: e.target.value }))}
                      className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                      disabled={gradeLoading}
                    >
                      {gradeLetterOptions.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-label-md font-bold text-on-surface mb-1.5">Price per Unit</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={gradeForm.price_per_unit}
                      onChange={(e) => setGradeForm(f => ({ ...f, price_per_unit: e.target.value }))}
                      placeholder="0.00"
                      className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
                      disabled={gradeLoading}
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="block text-label-md font-bold text-on-surface mb-1.5">Rejection Reason</label>
                  <textarea
                    value={gradeForm.rejection_reason === ' ' ? '' : gradeForm.rejection_reason}
                    onChange={(e) => setGradeForm(f => ({ ...f, rejection_reason: e.target.value }))}
                    placeholder="Reason for rejection..."
                    rows={3}
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant resize-none"
                    disabled={gradeLoading}
                  />
                </div>
              )}
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Override Reason</label>
                <textarea
                  value={gradeForm.override_reason}
                  onChange={(e) => setGradeForm(f => ({ ...f, override_reason: e.target.value }))}
                  placeholder="Why is this being overridden?"
                  rows={2}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant resize-none"
                  disabled={gradeLoading}
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setGradeDelivery(null)}
                  className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-higher transition-colors"
                  disabled={gradeLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={gradeLoading || (!gradeForm.grade_letter && !gradeForm.rejection_reason.trim())}
                  className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {gradeLoading && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                  {gradeLoading ? 'Assigning...' : 'Assign Grade'}
                </button>
              </div>
            </form>
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

      {/* Create Delivery Modal */}
      {createOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => { if (!formLoading) { setCreateOpen(false); setSelectedFarmerName(''); setFarmerSearch('') } }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-lg w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">New Delivery</h3>
              <button onClick={() => { setCreateOpen(false); setSelectedFarmerName(''); setFarmerSearch('') }} className="p-1 rounded-lg hover:bg-surface-container text-on-surface-variant" disabled={formLoading}>
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div ref={farmerRef} className="relative">
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Farmer *</label>
                <div className="relative">
                  <input
                    type="text"
                    value={selectedFarmerName || farmerSearch}
                    onChange={(e) => { setFarmerSearch(e.target.value); setSelectedFarmerName(''); setCreateForm(f => ({ ...f, farmer: '' })); setFarmerSearchOpen(true) }}
                    onFocus={() => { if (farmerSearch.length >= 2) setFarmerSearchOpen(true) }}
                    placeholder="Search farmer by name or phone..."
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 pr-10 text-body-md text-on-surface placeholder:text-on-surface-variant"
                    disabled={formLoading}
                    autoComplete="off"
                  />
                  {farmerSearchOpen && farmerOptions.length > 0 && (
                    <div className="absolute z-10 mt-1 w-full bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg max-h-48 overflow-y-auto">
                      {farmerOptions.map(f => (
                        <button
                          key={f.id}
                          type="button"
                          onClick={() => { setSelectedFarmerName(`${f.first_name} ${f.last_name} (${f.phone_number || f.id.slice(0, 8)})`); setCreateForm(ff => ({ ...ff, farmer: f.id })); setFarmerSearchOpen(false); setFarmerSearch('') }}
                          className="w-full text-left px-3 py-2 text-body-md text-on-surface hover:bg-surface-container transition-colors"
                        >
                          {f.first_name} {f.last_name}
                          <span className="text-on-surface-variant text-label-sm ml-2">{f.phone}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {farmerSearchOpen && farmerSearch.length >= 2 && farmerOptions.length === 0 && (
                    <div className="absolute z-10 mt-1 w-full bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg p-3 text-center text-on-surface-variant text-body-md">
                      No farmers found.
                    </div>
                  )}
                </div>
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface mb-1.5">Product Type *</label>
                <select
                  value={createForm.product_type}
                  onChange={(e) => setCreateForm(f => ({ ...f, product_type: e.target.value }))}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  disabled={formLoading}
                >
                  {createProductTypeOptions.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-label-md font-bold text-on-surface mb-1.5">Quantity (kg)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={createForm.quantity_kg}
                    onChange={(e) => setCreateForm(f => ({ ...f, quantity_kg: e.target.value }))}
                    placeholder="0.00"
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
                    disabled={formLoading}
                  />
                </div>
                <div>
                  <label className="block text-label-md font-bold text-on-surface mb-1.5">Volume (L)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={createForm.volume_litres}
                    onChange={(e) => setCreateForm(f => ({ ...f, volume_litres: e.target.value }))}
                    placeholder="0.00"
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
                    disabled={formLoading}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-label-md font-bold text-on-surface mb-1.5">Shift *</label>
                  <select
                    value={createForm.shift}
                    onChange={(e) => setCreateForm(f => ({ ...f, shift: e.target.value }))}
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                    disabled={formLoading}
                  >
                    {createShiftOptions.map(o => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-label-md font-bold text-on-surface mb-1.5">Date Delivered</label>
                  <input
                    type="date"
                    value={createForm.date_delivered}
                    onChange={(e) => setCreateForm(f => ({ ...f, date_delivered: e.target.value }))}
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                    disabled={formLoading}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setCreateOpen(false); setSelectedFarmerName(''); setFarmerSearch('') }}
                  className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-higher transition-colors"
                  disabled={formLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading || !createForm.farmer}
                  className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {formLoading && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                  {formLoading ? 'Creating...' : 'Create Delivery'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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

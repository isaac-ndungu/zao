import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

export default function GradingQueue() {
  const [tab, setTab] = useState('recent')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [selectedIds, setSelectedIds] = useState([])
  const [detailItem, setDetailItem] = useState(null)
  const [showOverride, setShowOverride] = useState(null)
  const [overrideData, setOverrideData] = useState({ grade_letter: '', price_per_unit: '', override_reason: '' })
  const [showResolve, setShowResolve] = useState(null)
  const [resolveData, setResolveData] = useState({ status: 'RESOLVED', resolution_notes: '' })
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')

  const tabs = [
    { key: 'recent', label: 'Recent Grades' },
    { key: 'awaiting', label: 'Awaiting Grade' },
    { key: 'disputes', label: 'Disputes' },
  ]

  const gradesParams = new URLSearchParams({ page, page_size: pageSize })
  const { data: grades, loading: gradesLoading, error: gradesError, refetch: refetchGrades } = useApi(tab === 'recent' ? `/api/grades/?${gradesParams}` : null)

  const awaitingParams = new URLSearchParams({ page, page_size: pageSize, status: 'PENDING' })
  const { data: awaitingDeliveries, loading: awaitingLoading, error: awaitingError } = useApi(tab === 'awaiting' ? `/api/deliveries/?${awaitingParams}` : null)

  const disputesParams = new URLSearchParams({ page, page_size: pageSize })
  const { data: disputes, loading: disputesLoading, error: disputesError, refetch: refetchDisputes } = useApi(tab === 'disputes' ? `/api/disputes/?${disputesParams}` : null)

  const activeItems = tab === 'recent' ? (grades?.results || [])
    : tab === 'awaiting' ? (awaitingDeliveries?.results || [])
    : (disputes?.results || [])

  useEffect(() => {
    if (selectedId && activeItems.length > 0) {
      const found = activeItems.find(i => String(i.id) === String(selectedId))
      if (found && !detailItem) {
        setDetailItem(found)
      }
    }
  }, [selectedId, activeItems, tab])

  const handleOverride = async () => {
    if (!showOverride) return
    try {
      const res = await apiFetch(`/api/grades/${showOverride.id}/override/`, { method: 'POST', body: JSON.stringify(overrideData) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Override failed') }
      showToast({ type: 'success', message: 'Grade overridden.' })
      setShowOverride(null); setOverrideData({ grade_letter: '', override_reason: '' })
      refetchGrades()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleResolve = async () => {
    if (!showResolve) return
    try {
      const res = await apiFetch(`/api/disputes/${showResolve.id}/resolve/`, { method: 'POST', body: JSON.stringify(resolveData) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Resolve failed') }
      showToast({ type: 'success', message: 'Dispute resolved.' })
      setShowResolve(null); setResolveData({ status: 'RESOLVED', resolution_notes: '' })
      refetchDisputes()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const gradeColumns = [
    { key: 'id', label: 'ID', render: (v, row) => row.id?.slice(0, 8) || '' },
    { key: 'grade_letter', label: 'Grade', render: (v, row) => <StatusBadge status={row.grade_letter?.toLowerCase()} label={row.grade_letter} /> },
    { key: 'price_per_unit', label: 'Price/Unit', render: (v, row) => row.price_per_unit ? `KES ${row.price_per_unit}` : '-' },
    { key: 'is_overridden', label: 'Overridden', render: (v, row) => row.is_overridden ? 'Yes' : 'No' },
    { key: 'created_at', label: 'Date', render: (v, row) => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (v, row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button onClick={(e) => { e.stopPropagation(); setShowOverride(row); setOverrideData({ grade_letter: row.grade_letter, override_reason: '' }) }} className="text-primary hover:text-primary/80" aria-label="Override grade"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit_note</span></button>
        </div>
      ),
    },
  ]

  const awaitingColumns = [
    { key: 'batch_id', label: 'Batch ID' },
    { key: 'farmer_name', label: 'Farmer' },
    { key: 'product_type', label: 'Product' },
    { key: 'quantity_kg', label: 'Qty (kg)', render: (v, row) => row.quantity_kg || row.volume_litres || '-' },
    { key: 'date_delivered', label: 'Delivered', render: (v, row) => row.date_delivered ? new Date(row.date_delivered).toLocaleDateString() : '-' },
    { key: 'shift', label: 'Shift' },
  ]

  const disputeColumns = [
    { key: 'id', label: 'ID', render: (v, row) => row.id?.slice(0, 8) || '' },
    { key: 'status', label: 'Status', render: (v, row) => <StatusBadge status={row.status?.toLowerCase()} label={row.status} /> },
    { key: 'reason', label: 'Reason' },
    { key: 'created_at', label: 'Date', render: (v, row) => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (v, row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          {row.status === 'PENDING' ? (
            <button onClick={(e) => { e.stopPropagation(); setShowResolve(row); setResolveData({ status: 'RESOLVED', resolution_notes: '' }) }} className="text-primary hover:text-primary/80" aria-label="Resolve dispute"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">check_circle</span></button>
          ) : (
            <button onClick={(e) => { e.stopPropagation(); setShowResolve(row); setResolveData({ status: 'RESOLVED', resolution_notes: '' }) }} className="text-primary hover:text-primary/80" aria-label="View dispute"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">visibility</span></button>
          )}
        </div>
      ),
    },
  ]

  const currentData = tab === 'recent' ? grades : tab === 'awaiting' ? awaitingDeliveries : disputes
  const currentLoading = tab === 'recent' ? gradesLoading : tab === 'awaiting' ? awaitingLoading : disputesLoading
  const currentError = tab === 'recent' ? gradesError : tab === 'awaiting' ? awaitingError : disputesError
  const currentRefetch = tab === 'recent' ? refetchGrades : tab === 'awaiting' ? undefined : refetchDisputes
  const currentColumns = tab === 'recent' ? gradeColumns : tab === 'awaiting' ? awaitingColumns : disputeColumns

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h2 className="text-3xl font-bold text-on-surface mb-1">Grading Queue</h2>
        <p className="text-sm text-on-surface-variant">Monitor grades, pending deliveries, and disputes</p>
      </header>

      <div className="flex gap-1 mb-6 bg-surface-container rounded-lg p-1 w-fit">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setPage(1) }}
            className={`px-4 py-2 rounded-md text-label-md font-bold transition-colors ${tab === t.key ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {currentLoading ? <TableSkeleton rows={8} cols={6} /> : currentError ? (
        <ErrorState message={currentError} action={{ label: 'Retry', onClick: currentRefetch }} />
      ) : (
        <>
          <DataTable
            columns={currentColumns}
            data={currentData?.results || []}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            onRowClick={(row) => setDetailItem(row)}
            emptyMessage={tab === 'recent' ? 'No grades yet.' : tab === 'awaiting' ? 'No pending deliveries.' : 'No disputes.'}
          />
          <Pagination page={page} pageSize={pageSize} total={currentData?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailItem} onClose={() => { setDetailItem(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Details" width="max-w-lg">
        {detailItem && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(detailItem).filter(([k]) => !['id', 'delivery'].includes(k)).map(([k, v]) => (
                <div key={k}><p className="text-label-md text-on-surface-variant capitalize">{k.replace('_', ' ')}</p><p className="text-body-md text-on-surface font-medium">{v !== null && v !== undefined ? String(v) : '-'}</p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>

      <SlideOutPanel open={!!showOverride} onClose={() => setShowOverride(null)} title="Override Grade" width="max-w-md">
        <div className="space-y-4">
          <div><label htmlFor="override-grade_letter" className="block text-label-md text-on-surface-variant mb-1">Grade Letter</label><select id="override-grade_letter" value={overrideData.grade_letter} onChange={(e) => setOverrideData(p => ({ ...p, grade_letter: e.target.value }))} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option value="A">A</option><option value="B">B</option><option value="C">C</option><option value="PREMIUM">Premium</option><option value="STANDARD">Standard</option></select></div>
          <div><label htmlFor="override-price_per_unit" className="block text-label-md text-on-surface-variant mb-1">Price per Unit</label><input id="override-price_per_unit" type="number" step="0.01" min="0" value={overrideData.price_per_unit} onChange={(e) => setOverrideData(p => ({ ...p, price_per_unit: e.target.value }))} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
          <div><label htmlFor="override-override_reason" className="block text-label-md text-on-surface-variant mb-1">Reason</label><textarea id="override-override_reason" value={overrideData.override_reason} onChange={(e) => setOverrideData(p => ({ ...p, override_reason: e.target.value }))} rows={3} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
          <button onClick={handleOverride} className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">Override Grade</button>
        </div>
      </SlideOutPanel>

      <SlideOutPanel open={!!showResolve} onClose={() => setShowResolve(null)} title="Resolve Dispute" width="max-w-md">
        <div className="space-y-4">
          <div><label htmlFor="resolve-status" className="block text-label-md text-on-surface-variant mb-1">Status</label><select id="resolve-status" value={resolveData.status} onChange={(e) => setResolveData(p => ({ ...p, status: e.target.value }))} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option value="RESOLVED">Resolved</option><option value="REJECTED">Rejected</option></select></div>
          <div><label htmlFor="resolve-resolution_notes" className="block text-label-md text-on-surface-variant mb-1">Notes</label><textarea id="resolve-resolution_notes" value={resolveData.resolution_notes} onChange={(e) => setResolveData(p => ({ ...p, resolution_notes: e.target.value }))} rows={3} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
          <button onClick={handleResolve} className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">Submit Resolution</button>
        </div>
      </SlideOutPanel>
    </div>
  )
}
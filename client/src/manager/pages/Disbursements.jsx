import { useState } from 'react'
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

export default function Disbursements() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortField, setSortField] = useState('-created_at')
  const [detailDisbursement, setDetailDisbursement] = useState(null)
  const [showReject, setShowReject] = useState(null)
  const [showApprove, setShowApprove] = useState(null)
  const { showToast } = useToast()

  const params = new URLSearchParams({ page, page_size: pageSize, ordering: sortField })
  if (statusFilter) params.set('status', statusFilter)

  const { data, loading, error, refetch } = useApi(`/api/disbursements/?${params}`)

  const handleSort = (key) => setSortField(prev => prev === key ? `-${key}` : key)

  const handleApprove = async () => {
    if (!showApprove) return
    try {
      const res = await apiFetch(`/api/disbursements/${showApprove.id}/approve/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Approval failed') }
      showToast({ type: 'success', message: 'Disbursement approved.' })
      setShowApprove(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleReject = async () => {
    if (!showReject) return
    try {
      const res = await apiFetch(`/api/disbursements/${showReject.id}/`, { method: 'PATCH', body: JSON.stringify({ status: 'REJECTED' }) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to reject') }
      showToast({ type: 'success', message: 'Disbursement rejected.' })
      setShowReject(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const items = data?.results || []
  const total = data?.count || 0

  const columns = [
    { key: 'batch_ref', label: 'Batch Ref', sortable: true, render: (v) => v || '-' },
    { key: 'cycle_name', label: 'Cycle', sortable: true, render: (v) => v || '-' },
    { key: 'total_amount', label: 'Total', sortable: true, render: (v) => v ? `KES ${Number(v).toLocaleString()}` : '-' },
    { key: 'farmer_count', label: 'Farmers', sortable: true, render: (v) => v ?? '-' },
    { key: 'status', label: 'Status', sortable: true, render: (v) => <StatusBadge status={v?.toLowerCase()} label={v} /> },
    { key: 'created_at', label: 'Created', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (_, row) => (
        <div className="flex gap-2">
          {row.status === 'PENDING' && (
            <>
              <button onClick={(e) => { e.stopPropagation(); setShowApprove(row) }} className="text-success text-label-md hover:underline">Approve</button>
              <button onClick={(e) => { e.stopPropagation(); setShowReject(row) }} className="text-error text-label-md hover:underline">Reject</button>
            </>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Disbursements</h2>
          <p className="text-sm text-on-surface-variant">{total} total</p>
        </div>
      </header>

      <div className="mb-4 flex items-center gap-4 flex-wrap">
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="PROCESSING">Processing</option>
          <option value="COMPLETED">Completed</option>
          <option value="REJECTED">Rejected</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {loading ? <TableSkeleton rows={10} cols={7} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={items}
            sortField={sortField.replace('-', '')}
            sortOrder={sortField.startsWith('-') ? 'desc' : 'asc'}
            onSort={handleSort}
            onRowClick={(row) => setDetailDisbursement(row)}
            emptyMessage="No disbursements found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailDisbursement} onClose={() => setDetailDisbursement(null)} title="Disbursement Details" width="max-w-xl">
        {detailDisbursement && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['batch_ref', 'cycle_name', 'total_amount', 'farmer_count', 'status', 'created_at', 'updated_at'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">{f.includes('amount') ? `KES ${Number(detailDisbursement[f] || 0).toLocaleString()}` : String(detailDisbursement[f] ?? '-')}</p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal
        open={!!showApprove}
        title="Approve Disbursement"
        message={`Approve disbursement batch "${showApprove?.batch_ref || showApprove?.id}"? This will queue it for processing.`}
        confirmLabel="Approve"
        onConfirm={handleApprove}
        onCancel={() => setShowApprove(null)}
      />

      <ConfirmModal
        open={!!showReject}
        title="Reject Disbursement"
        message={`Reject disbursement batch "${showReject?.batch_ref || showReject?.id}"?`}
        confirmLabel="Reject"
        destructive
        onConfirm={handleReject}
        onCancel={() => setShowReject(null)}
      />
    </div>
  )
}
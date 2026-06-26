import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import KpiCard from '../../admin/components/common/KpiCard'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

export default function Cycles() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [sortField, setSortField] = useState('-created_at')
  const [detailCycle, setDetailCycle] = useState(null)
  const [showLock, setShowLock] = useState(null)
  const { showToast } = useToast()

  const sortParam = sortField.startsWith('-') ? sortField : sortField
  const params = new URLSearchParams({ page, page_size: pageSize, ordering: sortParam })
  const { data, loading, error, refetch } = useApi(`/api/payment-engine/?${params}`)

  const handleSort = (key) => setSortField(prev => prev === key ? `-${key}` : key)

  const handleLock = async () => {
    if (!showLock) return
    try {
      const res = await apiFetch(`/api/payment-engine/${showLock.id}/lock/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to lock') }
      showToast({ type: 'success', message: 'Cycle locked.' })
      setShowLock(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const cycles = data?.results || []
  const totalCount = data?.count || 0
  const pendingCount = cycles.filter(c => c.status === 'PENDING').length
  const lockedCount = cycles.filter(c => c.status === 'LOCKED').length
  const completedCount = cycles.filter(c => c.status === 'COMPLETED').length

  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'status', label: 'Status', sortable: true, render: (v) => <StatusBadge status={v?.toLowerCase()} label={v} /> },
    { key: 'start_date', label: 'Start', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    { key: 'end_date', label: 'End', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    { key: 'total_amount', label: 'Total', sortable: true, render: (v) => v ? `KES ${Number(v).toLocaleString()}` : '-' },
    { key: 'farmer_count', label: 'Farmers', sortable: true, render: (v) => v ?? '-' },
    { key: 'created_at', label: 'Created', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (_, row) => (
        <div className="flex gap-2">
          {row.status === 'PENDING' && (
            <button onClick={(e) => { e.stopPropagation(); setShowLock(row) }} className="text-warning text-label-md hover:underline">Lock</button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Payment Cycles</h2>
          <p className="text-on-surface-variant font-body-md">{totalCount} total</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KpiCard icon="payments" label="Total Cycles" value={String(totalCount)} />
        <KpiCard icon="pending" label="Pending" value={String(pendingCount)} />
        <KpiCard icon="lock" label="Locked" value={String(lockedCount)} />
        <KpiCard icon="check_circle" label="Completed" value={String(completedCount)} />
      </div>

      {loading ? <TableSkeleton rows={10} cols={8} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={cycles}
            sortField={sortField.replace('-', '')}
            sortOrder={sortField.startsWith('-') ? 'desc' : 'asc'}
            onSort={handleSort}
            onRowClick={(row) => setDetailCycle(row)}
            emptyMessage="No payment cycles found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailCycle} onClose={() => setDetailCycle(null)} title="Cycle Details" width="max-w-xl">
        {detailCycle && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['name', 'status', 'start_date', 'end_date', 'total_amount', 'farmer_count', 'total_volume', 'total_deductions', 'net_payout', 'created_at', 'updated_at'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">{f.includes('amount') || f.includes('payout') || f.includes('deductions') ? `KES ${Number(detailCycle[f] || 0).toLocaleString()}` : String(detailCycle[f] ?? '-')}</p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal
        open={!!showLock}
        title="Lock Payment Cycle"
        message={`Lock cycle "${showLock?.name}"? This will finalize the cycle for processing.`}
        confirmLabel="Lock Cycle"
        onConfirm={handleLock}
        onCancel={() => setShowLock(null)}
      />
    </div>
  )
}

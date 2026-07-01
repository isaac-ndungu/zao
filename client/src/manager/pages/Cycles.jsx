import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')

  const sortParam = sortField.startsWith('-') ? sortField : sortField
  const params = new URLSearchParams({ page, page_size: pageSize, ordering: sortParam })
  const { data, loading, error, refetch } = useApi(`/api/payment-engine/?${params}`)

  const cycles = data?.results || []

  useEffect(() => {
    if (selectedId && cycles.length > 0) {
      const found = cycles.find(i => String(i.id) === String(selectedId))
      if (found && !detailCycle) {
        setDetailCycle(found)
      }
    }
  }, [selectedId, cycles])

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

  const totalCount = data?.count || 0
  const pendingCount = cycles.filter(c => c.status === 'PENDING').length
  const lockedCount = cycles.filter(c => c.status === 'LOCKED').length
  const completedCount = cycles.filter(c => c.status === 'COMPLETED').length

  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'status', label: 'Status', sortable: true, render: (row) => <StatusBadge status={row.status?.toLowerCase()} label={row.status} /> },
    { key: 'start_date', label: 'Start', sortable: true, render: (row) => row.start_date ? new Date(row.start_date).toLocaleDateString() : '-' },
    { key: 'end_date', label: 'End', sortable: true, render: (row) => row.end_date ? new Date(row.end_date).toLocaleDateString() : '-' },
    { key: 'total_amount', label: 'Total', sortable: true, render: (row) => row.total_amount ? `KES ${Number(row.total_amount).toLocaleString()}` : '-' },
    { key: 'farmer_count', label: 'Farmers', sortable: true, render: (row) => row.farmer_count ?? '-' },
    { key: 'created_at', label: 'Created', sortable: true, render: (row) => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          {row.status === 'PENDING' && (
            <button onClick={(e) => { e.stopPropagation(); setShowLock(row) }} className="text-warning hover:text-warning/80" title="Lock Cycle"><span className="material-symbols-outlined text-[18px]">lock</span></button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Payment Cycles</h2>
          <p className="text-sm text-on-surface-variant">{totalCount} total</p>
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

      <SlideOutPanel open={!!detailCycle} onClose={() => { setDetailCycle(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Cycle Details" width="max-w-xl">
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
import { useContext, useMemo, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'
import { KpiSkeleton, TableSkeleton } from '../components/common/Skeleton'

const tabOptions = [
  { key: 'cycles', label: 'Payment Cycles' },
  { key: 'batches', label: 'Disbursement Batches' },
  { key: 'overview', label: 'Overview' },
]

const cycleStatusBadge = {
  DRAFT: 'draft',
  COMPUTING: 'computing',
  COMPUTED: 'computed',
  LOCKED: 'locked',
  DISBURSING: 'processing',
  DISBURSED: 'disbursed',
}

const batchStatusBadge = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  PARTIALLY_COMPLETED: 'computing',
  FAILED: 'failed',
}

export default function Financials() {
  const { showToast } = useToast()
  const { period } = useContext(AdminFilterContext)
  const [tab, setTab] = useState('overview')
  const [cyclePage, setCyclePage] = useState(1)
  const [cyclePageSize, setCyclePageSize] = useState(10)
  const [batchPage, setBatchPage] = useState(1)
  const [batchPageSize, setBatchPageSize] = useState(10)
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [actionLoading, setActionLoading] = useState(false)

  const { data: finData, loading, error } = useApi(`/api/admin/analytics/financial/?period=${period}`)
  const { data: cyclesData, loading: cyclesLoading, refetch: refetchCycles } = useApi(`/api/admin/payment-cycles/?page=${cyclePage}&page_size=${cyclePageSize}`)
  const { data: batchesData, loading: batchesLoading, refetch: refetchBatches } = useApi(`/api/admin/disbursement-batches/?page=${batchPage}&page_size=${batchPageSize}`)

  const fin = finData?.data

  const execAction = async (url, body = {}) => {
    setActionLoading(true)
    setModalConfig({ open: false })
    try {
      const res = await apiFetch(url, { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Action completed successfully.' })
      refetchCycles()
      refetchBatches()
    } catch (e) {
      showToast({ type: 'error', message: `Action failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleCycleAction = (cycle, action) => {
    const label = action.charAt(0).toUpperCase() + action.slice(1)
    setModalConfig({
      open: true,
      title: `${label} Cycle`,
      message: `${label} cycle "${cycle.name}"?`,
      onConfirm: () => execAction(`/api/admin/payment-cycles/${cycle.id}/${action}/`),
      destructive: false,
    })
  }

  const handleBatchAction = (batch, action) => {
    const label = action.charAt(0).toUpperCase() + action.slice(1)
    setModalConfig({
      open: true,
      title: `${label} Batch`,
      message: `${label} disbursement batch?`,
      onConfirm: () => execAction(`/api/admin/disbursement-batches/${batch.id}/${action}/`),
      destructive: action === 'reject',
    })
  }

  const cycleColumns = useMemo(() => [
    { key: 'name', label: 'Name', sortable: true, render: (r) => <span className="font-medium">{r.name}</span> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={cycleStatusBadge[r.status] || 'draft'} label={r.status} /> },
    { key: 'start_date', label: 'Start', render: (r) => r.start_date ? new Date(r.start_date).toLocaleDateString() : '-' },
    { key: 'end_date', label: 'End', render: (r) => r.end_date ? new Date(r.end_date).toLocaleDateString() : '-' },
    { key: 'total_levy', label: 'Levy', render: (r) => <span className="font-data-mono">KES {r.total_levy?.toLocaleString() || '0'}</span> },
    { key: 'total_cooperative_fee', label: 'Coop Fee', render: (r) => <span className="font-data-mono">KES {r.total_cooperative_fee?.toLocaleString() || '0'}</span> },
  ], [])

  const batchColumns = useMemo(() => [
    { key: 'id', label: 'Batch ID', render: (r) => <span className="font-data-mono text-primary">{r.id?.slice(0, 8)}...</span> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={batchStatusBadge[r.status] || 'draft'} label={r.status} /> },
    { key: 'total_amount', label: 'Amount', render: (r) => <span className="font-data-mono">KES {r.total_amount?.toLocaleString() || '0'}</span> },
    { key: 'total_transactions', label: 'Transactions', render: (r) => r.total_transactions || 0 },
    { key: 'successful_count', label: 'Success', render: (r) => <span className="text-primary font-data-mono">{r.successful_count || 0}</span> },
    { key: 'failed_count', label: 'Failed', render: (r) => <span className="text-error font-data-mono">{r.failed_count || 0}</span> },
  ], [])

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load financial data: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Financials</h2>
        <p className="text-on-surface-variant font-body-md">Payment cycles, disbursement batches, and financial overview.</p>
      </header>

      <div className="flex gap-1 bg-surface-container rounded-lg p-0.5 mb-6 inline-flex">
        {tabOptions.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded-lg text-label-md font-bold transition-colors ${tab === t.key ? 'bg-surface-container-lowest shadow-sm text-on-surface' : 'text-on-surface-variant hover:text-on-surface'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          {loading ? (
            <KpiSkeleton count={4} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <KpiCard icon="payments" label="Total Revenue" value={fin?.total_revenue ? `KES ${fin.total_revenue.toLocaleString()}` : '-'} />
              <KpiCard icon="account_balance" label="Gross Payout" value={fin?.total_gross_payout ? `KES ${fin.total_gross_payout.toLocaleString()}` : '-'} />
              <KpiCard icon="account_balance_wallet" label="Net Payout" value={fin?.total_net_payout ? `KES ${fin.total_net_payout.toLocaleString()}` : '-'} />
              <KpiCard icon="receipt" label="Withholding Tax" value={fin?.total_withholding_tax ? `KES ${fin.total_withholding_tax.toLocaleString()}` : 'KES 0'} />
            </div>
          )}

          {fin?.deductions_breakdown && Object.keys(fin.deductions_breakdown).length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mb-6">
              <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Deductions Breakdown</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(fin.deductions_breakdown).map(([key, val]) => (
                  <div key={key} className="p-3 bg-surface-container rounded-lg">
                    <p className="text-[10px] uppercase font-bold text-on-surface-variant">{key.replace(/_/g, ' ')}</p>
                    <p className="font-data-mono text-headline-sm text-on-surface">KES {Number(val).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {fin?.payout_monthly_series && fin.payout_monthly_series.length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
              <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Monthly Payout Trend</h4>
              <div className="space-y-2">
                {fin.payout_monthly_series.slice(-12).map((m) => {
                  const maxVal = Math.max(...fin.payout_monthly_series.map(x => x.amount))
                  return (
                    <div key={m.month} className="flex items-center gap-4">
                      <span className="text-label-md font-medium text-on-surface-variant w-24">{m.month}</span>
                      <div className="flex-1 h-6 bg-surface-container rounded-lg overflow-hidden">
                        <div className="h-full bg-primary transition-all" style={{ width: `${(m.amount / maxVal) * 100}%` }} />
                      </div>
                      <span className="font-data-mono text-label-md text-on-surface-variant w-28 text-right">
                        KES {m.amount?.toLocaleString()}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {!fin && !loading && (
            <div className="text-center py-12 text-on-surface-variant">
              <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">payments</span>
              <p>No financial data available for the selected period.</p>
            </div>
          )}
        </>
      )}

      {tab === 'cycles' && (
        <>
          {cyclesLoading ? <TableSkeleton /> : (
            <>
              <DataTable
                columns={cycleColumns}
                data={cyclesData?.results || []}
                loading={false}
                emptyMessage="No payment cycles found."
                rowActions={(cycle) => {
                  const canLock = cycle.status === 'COMPUTED'
                  const canUnlock = cycle.status === 'LOCKED'
                  return (
                    <div className="flex gap-1">
                      {canLock && <button onClick={() => handleCycleAction(cycle, 'lock')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-primary transition-colors" title="Lock"><span className="material-symbols-outlined text-[18px]">lock</span></button>}
                      {canUnlock && <button onClick={() => handleCycleAction(cycle, 'unlock')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors" title="Unlock"><span className="material-symbols-outlined text-[18px]">lock_open</span></button>}
                      <button className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors"><span className="material-symbols-outlined text-[18px]">more_vert</span></button>
                    </div>
                  )
                }}
              />
              <div className="mt-2">
                <Pagination page={cyclePage} pageSize={cyclePageSize} total={cyclesData?.count || 0} onPageChange={setCyclePage} onPageSizeChange={setCyclePageSize} />
              </div>
            </>
          )}
        </>
      )}

      {tab === 'batches' && (
        <>
          {batchesLoading ? <TableSkeleton /> : (
            <>
              <DataTable
                columns={batchColumns}
                data={batchesData?.results || []}
                loading={false}
                emptyMessage="No disbursement batches found."
                rowActions={(batch) => {
                  const canApprove = batch.status === 'PENDING'
                  return (
                    <div className="flex gap-1">
                      {canApprove && <button onClick={() => handleBatchAction(batch, 'approve')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-primary transition-colors" title="Approve"><span className="material-symbols-outlined text-[18px]">check_circle</span></button>}
                      {canApprove && <button onClick={() => handleBatchAction(batch, 'reject')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-error transition-colors" title="Reject"><span className="material-symbols-outlined text-[18px]">cancel</span></button>}
                    </div>
                  )
                }}
              />
              <div className="mt-2">
                <Pagination page={batchPage} pageSize={batchPageSize} total={batchesData?.count || 0} onPageChange={setBatchPage} onPageSizeChange={setBatchPageSize} />
              </div>
            </>
          )}
        </>
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

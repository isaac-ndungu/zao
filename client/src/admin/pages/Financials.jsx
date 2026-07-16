import { useContext, useMemo, useState, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch, exportCsv } from '../api/client'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import ConfirmModal from '../components/common/ConfirmModal'
import SlideOutPanel from '../components/common/SlideOutPanel'
import FilterBar from '../components/common/FilterBar'
import { useToast } from '../contexts/ToastContext'
import { KpiSkeleton, TableSkeleton } from '../components/common/Skeleton'
import LineChartCard from '../components/charts/LineChartCard'
import PieChartCard from '../components/charts/PieChartCard'
import BarChartCard from '../components/charts/BarChartCard'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

const tabOptions = [
  { key: 'cycles', label: 'Payment Cycles' },
  { key: 'batches', label: 'Disbursement Batches' },
  { key: 'overview', label: 'Overview' },
  { key: 'efficiency', label: 'Payment Efficiency' },
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

import { useLocation } from 'react-router-dom'

export default function Financials() {
  const { showToast } = useToast()
  const { period } = useContext(AdminFilterContext)
  const location = useLocation()
  const [tab, setTab] = useState(location.state?.openModal === true ? 'cycles' : 'overview')
  const [cyclePage, setCyclePage] = useState(1)
  const [cyclePageSize, setCyclePageSize] = useState(10)
  const [batchPage, setBatchPage] = useState(1)
  const [batchPageSize, setBatchPageSize] = useState(10)
  const [cycleSortField, setCycleSortField] = useState('name')
  const [cycleSortOrder, setCycleSortOrder] = useState('asc')
  const [batchSortField, setBatchSortField] = useState('id')
  const [batchSortOrder, setBatchSortOrder] = useState('desc')
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [actionLoading, setActionLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(location.state?.openModal === true)
  const [detailPanel, setDetailPanel] = useState({ open: false, item: null, type: '' })
  const { data: effData, loading: effLoading } = useApi(`/api/admin/analytics/payment-efficiency/?period=${period}`)

  const { data: finData, loading, error } = useApi(`/api/admin/analytics/financial/?period=${period}`)
  const cycleQuery = useMemo(() => {
    const p = new URLSearchParams({ page: cyclePage, page_size: cyclePageSize })
    if (cycleSortField) p.set('ordering', cycleSortOrder === 'desc' ? `-${cycleSortField}` : cycleSortField)
    return p.toString()
  }, [cyclePage, cyclePageSize, cycleSortField, cycleSortOrder])
  const batchQuery = useMemo(() => {
    const p = new URLSearchParams({ page: batchPage, page_size: batchPageSize })
    if (batchSortField) p.set('ordering', batchSortOrder === 'desc' ? `-${batchSortField}` : batchSortField)
    return p.toString()
  }, [batchPage, batchPageSize, batchSortField, batchSortOrder])
  const { data: cyclesData, loading: cyclesLoading, refetch: refetchCycles } = useApi(`/api/admin/payment-cycles/?${cycleQuery}`)
  const { data: batchesData, loading: batchesLoading, refetch: refetchBatches } = useApi(`/api/admin/disbursement-batches/?${batchQuery}`)

  const fin = finData?.data

  const deductionsPie = useMemo(() => {
    if (!fin?.deductions_breakdown) return []
    return Object.entries(fin.deductions_breakdown).map(([key, val]) => ({
      name: key.replace(/_/g, ' '),
      value: Number(val),
    }))
  }, [fin])

  const payoutLineData = useMemo(() => {
    if (!fin?.payout_monthly_series) return []
    return Object.entries(fin.payout_monthly_series)
      .slice(-12)
      .map(([month, vals]) => ({
        month,
        gross: vals.gross,
        net: vals.net,
      }))
  }, [fin])

  const efficiencyCycleData = useMemo(() => {
    if (!effData?.data?.cycles) return []
    return effData.data.cycles.map(c => ({
      name: c.cycle_name,
      computation: c.computation_days,
      approval: c.approval_days,
      disbursement: c.disbursement_days,
    }))
  }, [effData])

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

  const handleRunComputation = async (cycle) => {
    setActionLoading(true)
    try {
      const res = await apiFetch(`/api/admin/payment-cycles/${cycle.id}/run/`, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Computation started for "${cycle.name}". Check back shortly.` })
      refetchCycles()
    } catch (e) {
      showToast({ type: 'error', message: `Computation failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleCycleSort = useCallback((field) => {
    if (cycleSortField === field) setCycleSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setCycleSortField(field); setCycleSortOrder('asc') }
  }, [cycleSortField])
  const handleBatchSort = useCallback((field) => {
    if (batchSortField === field) setBatchSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setBatchSortField(field); setBatchSortOrder('asc') }
  }, [batchSortField])

  const { formAction: createCycleAction } = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    try {
      const res = await apiFetch('/api/admin/payment-cycles/', { method: 'POST', body: JSON.stringify(data) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Cycle "${data.name}" created.` })
      setCreateOpen(false)
      refetchCycles()
    } catch (e) {
      showToast({ type: 'error', message: `Creation failed: ${e.message}` })
    }
    return {}
  }, {})

  const cycleColumns = useMemo(() => [
    { key: 'name', label: 'Name', sortable: true, render: (_, r) => <span className="font-medium">{r.name}</span> },
    { key: 'status', label: 'Status', render: (_, r) => <StatusBadge status={cycleStatusBadge[r.status] || 'draft'} label={r.status} /> },
    { key: 'start_date', label: 'Start', render: (_, r) => r.start_date ? new Date(r.start_date).toLocaleDateString() : '-' },
    { key: 'end_date', label: 'End', render: (_, r) => r.end_date ? new Date(r.end_date).toLocaleDateString() : '-' },
    { key: 'total_levy', label: 'Levy', render: (_, r) => <span className="font-data-mono">KES {r.total_levy?.toLocaleString() || '0'}</span> },
    { key: 'total_cooperative_fee', label: 'Coop Fee', render: (_, r) => <span className="font-data-mono">KES {r.total_cooperative_fee?.toLocaleString() || '0'}</span> },
  ], [])

  const batchColumns = useMemo(() => [
    { key: 'id', label: 'Batch ID', render: (_, r) => <span className="font-data-mono text-primary">{r.id?.slice(0, 8)}...</span> },
    { key: 'status', label: 'Status', render: (_, r) => <StatusBadge status={batchStatusBadge[r.status] || 'draft'} label={r.status} /> },
    { key: 'total_amount', label: 'Amount', render: (_, r) => <span className="font-data-mono">KES {r.total_amount?.toLocaleString() || '0'}</span> },
    { key: 'total_transactions', label: 'Transactions', render: (_, r) => r.total_transactions || 0 },
    { key: 'successful_count', label: 'Success', render: (_, r) => <span className="text-primary font-data-mono">{r.successful_count || 0}</span> },
    { key: 'failed_count', label: 'Failed', render: (_, r) => <span className="text-error font-data-mono">{r.failed_count || 0}</span> },
  ], [])

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load financial data: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">Financials</h2>
          {tab === 'cycles' && (
            <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
              <span className="material-symbols-outlined text-[16px]" aria-hidden="true">add</span>
              New Cycle
            </button>
          )}
        </div>
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

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {deductionsPie.length > 0 && (
              <PieChartCard
                title="Deductions Breakdown"
                data={deductionsPie}
                dataKey="value"
                nameKey="name"
                height={300}
                showPercent
                emptyMessage="No deductions data available."
              />
            )}
            {payoutLineData.length > 0 && (
              <LineChartCard
                title="Monthly Payout Trend"
                data={payoutLineData}
                xKey="month"
                lines={[
                  { key: 'gross', name: 'Gross Payout', color: '#2563eb' },
                  { key: 'net', name: 'Net Payout', color: '#059669' },
                ]}
                yFormatter={(v) => `KES ${(v / 1000).toFixed(0)}k`}
                height={300}
                emptyMessage="No payout data available."
              />
            )}
          </div>

          {!fin && !loading && deductionsPie.length === 0 && payoutLineData.length === 0 && (
            <div className="text-center py-12 text-on-surface-variant">
              <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant" aria-hidden="true">payments</span>
              <p>No financial data available for the selected period.</p>
            </div>
          )}
        </>
      )}

      {tab === 'cycles' && (
        <>
          <FilterBar
            search={''}
            onSearchChange={() => {}}
            placeholder=""
            filters={[]}
            filterValues={{}}
            onFilterChange={() => {}}
            onClear={() => {}}
            onExport={() => { const p = new URLSearchParams(); p.set('export', 'csv'); exportCsv(`/api/admin/payment-cycles/?${p}`) }}
          />
          {cyclesLoading ? <TableSkeleton /> : (
            <>
              <DataTable
                columns={cycleColumns}
                data={cyclesData?.results || []}
                sortField={cycleSortField}
                sortOrder={cycleSortOrder}
                onSort={handleCycleSort}
                loading={false}
                emptyMessage="No payment cycles found."
                onRowClick={(cycle) => setDetailPanel({ open: true, item: cycle, type: 'cycle' })}
                rowActions={(cycle) => {
                  const canRun = cycle.status === 'DRAFT'
                  const canLock = cycle.status === 'COMPUTED'
                  const canUnlock = cycle.status === 'LOCKED'
                  return (
                    <div className="flex gap-1">
                      {canRun && <button onClick={() => handleRunComputation(cycle)} disabled={actionLoading} className="p-1.5 rounded-lg hover:bg-primary-container text-primary transition-colors" aria-label="Run computation"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">play_arrow</span></button>}
                      {canLock && <button onClick={() => handleCycleAction(cycle, 'lock')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-primary transition-colors" aria-label="Lock cycle"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">lock</span></button>}
                      {canUnlock && <button onClick={() => handleCycleAction(cycle, 'unlock')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors" aria-label="Unlock cycle"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">lock_open</span></button>}
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
          <FilterBar
            search={''}
            onSearchChange={() => {}}
            placeholder=""
            filters={[]}
            filterValues={{}}
            onFilterChange={() => {}}
            onClear={() => {}}
            onExport={() => { const p = new URLSearchParams(); p.set('export', 'csv'); exportCsv(`/api/admin/disbursement-batches/?${p}`) }}
          />
          {batchesLoading ? <TableSkeleton /> : (
            <>
              <DataTable
                columns={batchColumns}
                data={batchesData?.results || []}
                sortField={batchSortField}
                sortOrder={batchSortOrder}
                onSort={handleBatchSort}
                loading={false}
                emptyMessage="No disbursement batches found."
                onRowClick={(batch) => setDetailPanel({ open: true, item: batch, type: 'batch' })}
                rowActions={(batch) => {
                  const canApprove = batch.status === 'PENDING'
                  return (
                    <div className="flex gap-1">
                      {canApprove && <button onClick={() => handleBatchAction(batch, 'approve')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-primary transition-colors" aria-label="Approve batch"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">check_circle</span></button>}
                      {canApprove && <button onClick={() => handleBatchAction(batch, 'reject')} className="p-1.5 rounded-lg hover:bg-surface-container-high text-error transition-colors" aria-label="Reject batch"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">cancel</span></button>}
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

      {tab === 'efficiency' && (
        <>
          {effLoading ? <KpiSkeleton count={3} /> : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <KpiCard icon="speed" label="Avg Total Days" value={effData?.data?.averages?.avg_total_days !== undefined ? `${effData.data.averages.avg_total_days.toFixed(1)} days` : '-'} />
                <KpiCard icon="sort" label="Median Days" value={effData?.data?.averages?.median_total_days !== undefined ? `${effData.data.averages.median_total_days} days` : '-'} />
                <KpiCard icon="replay" label="Cycle Count" value={effData?.data?.averages?.cycle_count || 0} />
              </div>

              {efficiencyCycleData.length > 0 && (
                <BarChartCard
                  title="Cycle Timeline"
                  data={efficiencyCycleData}
                  categoryKey="name"
                  dataKeys={['computation', 'approval', 'disbursement']}
                  stacked
                  height={400}
                  emptyMessage="No cycle timeline data available."
                />
              )}

              {effData?.data?.cycles?.length > 0 && (
                <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mt-6">
                  <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Cycle Details</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-outline-variant bg-surface-container">
                          <th scope="col" className="px-3 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase">Cycle</th>
                          <th scope="col" className="px-3 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase">Status</th>
                          <th scope="col" className="px-3 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase">Comp.</th>
                          <th scope="col" className="px-3 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase">Approval</th>
                          <th scope="col" className="px-3 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase">Disburse</th>
                          <th scope="col" className="px-3 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {effData.data.cycles.map((c, i) => (
                          <tr key={i} className={`border-b border-outline-variant/50 ${i % 2 === 0 ? 'bg-surface-container-lowest' : 'bg-surface-container'}`}>
                            <td className="px-3 py-2 text-body-md text-on-surface font-medium">{c.cycle_name}</td>
                            <td className="px-3 py-2"><StatusBadge status={c.status?.toLowerCase() === 'completed' ? 'completed' : c.status?.toLowerCase() === 'locked' ? 'locked' : 'draft'} label={c.status} /></td>
                            <td className="px-3 py-2 text-right font-data-mono text-on-surface">{c.computation_days}d</td>
                            <td className="px-3 py-2 text-right font-data-mono text-on-surface">{c.approval_days}d</td>
                            <td className="px-3 py-2 text-right font-data-mono text-on-surface">{c.disbursement_days}d</td>
                            <td className="px-3 py-2 text-right font-data-mono text-primary font-bold">{c.total_days}d</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {(!effData?.data?.cycles || effData.data.cycles.length === 0) && (
                <div className="text-center py-12 text-on-surface-variant">
                  <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant" aria-hidden="true">timer</span>
                  <p>No payment efficiency data for the selected period.</p>
                </div>
              )}
            </>
          )}
        </>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30 cursor-pointer" onClick={() => setCreateOpen(false)} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="create-cycle-title">
            <h3 id="create-cycle-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Create Payment Cycle</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Define a new payment cycle for farmer payouts.</p>
            <form action={createCycleAction} className="space-y-3">
              <div><label htmlFor="cycle-create-name" className="block text-label-md font-bold text-on-surface-variant mb-1">Name *</label><input id="cycle-create-name" required name="name" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="e.g. June 2026 Payout" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="cycle-create-start" className="block text-label-md font-bold text-on-surface-variant mb-1">Start Date *</label><input id="cycle-create-start" type="date" required name="start_date" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="cycle-create-end" className="block text-label-md font-bold text-on-surface-variant mb-1">End Date *</label><input id="cycle-create-end" type="date" required name="end_date" className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setCreateOpen(false)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <SubmitButton className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90">Create</SubmitButton>
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

      <SlideOutPanel open={detailPanel.open} onClose={() => setDetailPanel({ open: false, item: null, type: '' })} title={detailPanel.type === 'cycle' ? 'Payment Cycle Details' : 'Disbursement Batch Details'}>
        {detailPanel.item && detailPanel.type === 'cycle' && (
          <div className="space-y-4">
            <div>
              <h4 className="font-headline-sm text-headline-sm text-on-surface">{detailPanel.item.name}</h4>
              <StatusBadge status={cycleStatusBadge[detailPanel.item.status] || 'draft'} label={detailPanel.item.status} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Start Date</p><p className="font-body-md text-on-surface">{detailPanel.item.start_date ? new Date(detailPanel.item.start_date).toLocaleDateString() : '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">End Date</p><p className="font-body-md text-on-surface">{detailPanel.item.end_date ? new Date(detailPanel.item.end_date).toLocaleDateString() : '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Levy</p><p className="font-body-md text-on-surface font-data-mono">KES {detailPanel.item.total_levy?.toLocaleString() || '0'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Coop Fee</p><p className="font-body-md text-on-surface font-data-mono">KES {detailPanel.item.total_cooperative_fee?.toLocaleString() || '0'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Gross Payout</p><p className="font-body-md text-on-surface font-data-mono">KES {detailPanel.item.total_gross_payout?.toLocaleString() || '0'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Net Payout</p><p className="font-body-md text-on-surface font-data-mono">KES {detailPanel.item.total_net_payout?.toLocaleString() || '0'}</p></div>
            </div>
          </div>
        )}
        {detailPanel.item && detailPanel.type === 'batch' && (
          <div className="space-y-4">
            <div>
              <h4 className="font-headline-sm text-headline-sm text-on-surface">Batch {detailPanel.item.id?.slice(0, 8)}</h4>
              <StatusBadge status={batchStatusBadge[detailPanel.item.status] || 'draft'} label={detailPanel.item.status} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Total Amount</p><p className="font-body-md text-on-surface font-data-mono">KES {detailPanel.item.total_amount?.toLocaleString() || '0'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Transactions</p><p className="font-body-md text-on-surface">{detailPanel.item.total_transactions || 0}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Successful</p><p className="font-body-md text-on-surface text-primary font-data-mono">{detailPanel.item.successful_count || 0}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Failed</p><p className="font-body-md text-on-surface text-error font-data-mono">{detailPanel.item.failed_count || 0}</p></div>
            </div>
          </div>
        )}
      </SlideOutPanel>
    </div>
  )
}

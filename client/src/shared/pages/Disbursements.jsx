import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch, exportCsv } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../components/ErrorState'

const DARAJA_ERROR_CODES = {
  '0': 'Success',
  '1': 'Insufficient balance',
  '2': 'Invalid phone number',
  '3': 'Invalid amount',
  '17': 'Queue timeout',
  '20': 'Duplicate transaction',
  '26': 'System error',
  '1032': 'Transaction cancelled by user',
  '1037': 'Timeout',
  '2001': 'Invalid initiator',
}

function darajaError(rec) {
  if (!rec.result_code || rec.result_code === '0') return null
  return DARAJA_ERROR_CODES[rec.result_code] || rec.result_desc || `Error ${rec.result_code}`
}

function formatKes(n) {
  return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0'
}

function statusColor(status) {
  const map = {
    PENDING: 'warning',
    APPROVED: 'info',
    PROCESSING: 'info',
    COMPLETED: 'success',
    PARTIALLY_COMPLETED: 'warning',
    FAILED: 'error',
    REJECTED: 'error',
  }
  return map[status] || 'default'
}

export default function Disbursements() {
  const { isManager } = useAuth()
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortField, setSortField] = useState('-created_at')
  const [detailDisbursement, setDetailDisbursement] = useState(null)
  const [detailTxnPage, setDetailTxnPage] = useState(1)
  const [detailTxnStatus, setDetailTxnStatus] = useState('')
  const [detailTxnMethod, setDetailTxnMethod] = useState('')

  const [showApprove, setShowApprove] = useState(null)
  const [showReject, setShowReject] = useState(null)
  const [showLive, setShowLive] = useState(null)
  const [showRetry, setShowRetry] = useState(null)
  const [showDelete, setShowDelete] = useState(null)

  const [showInitiate, setShowInitiate] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [initCycleId, setInitCycleId] = useState('')
  const [initSaving, setInitSaving] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)

  const [showConfirmManual, setShowConfirmManual] = useState(null)
  const [confirmTxns, setConfirmTxns] = useState([])
  const [confirmTxnIds, setConfirmTxnIds] = useState([])
  const [confirmNotes, setConfirmNotes] = useState('')
  const [confirmSaving, setConfirmSaving] = useState(false)
  const [confirmLoading, setConfirmLoading] = useState(false)

  const [showCsvFormat, setShowCsvFormat] = useState(null)
  const [csvSaving, setCsvSaving] = useState(false)

  const [actionLoading, setActionLoading] = useState(null)
  const [openDropdownId, setOpenDropdownId] = useState(null)
  const dropdownRef = useRef(null)

  useEffect(() => {
    if (!openDropdownId) return
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpenDropdownId(null)
      }
    }
    const escapeHandler = (e) => { if (e.key === 'Escape') setOpenDropdownId(null) }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', escapeHandler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', escapeHandler)
    }
  }, [openDropdownId])

  const [pollingId, setPollingId] = useState(null)

  const qp = new URLSearchParams({ page, page_size: pageSize, ordering: sortField })
  if (statusFilter) qp.set('status', statusFilter)

  const { data, loading, error, refetch } = useApi(`/api/disbursements/?${qp}`)
  const { data: cyclesData } = useApi('/api/payment-engine/?page=1&page_size=100')

  const items = data?.results || []
  const total = data?.count || 0

  useEffect(() => {
    if (selectedId && items.length > 0) {
      const found = items.find(i => String(i.id) === String(selectedId))
      if (found && !detailDisbursement) {
        setDetailDisbursement(found)
      }
    }
  }, [selectedId, items])

  const cycles = (cyclesData?.results || []).filter(
    (c) => c.status === 'LOCKED' || c.status === 'ACTIVE' || c.status === 'COMPLETED',
  )

  useEffect(() => {
    if (!pollingId) return
    const interval = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/disbursements/${pollingId}/`)
        if (res.ok) {
          const batch = await res.json()
          if (batch.status !== 'PROCESSING') {
            setPollingId(null)
            refetch()
          }
        }
      } catch { }
    }, 5000)
    return () => clearInterval(interval)
  }, [pollingId, refetch])

  useEffect(() => {
    if (!showConfirmManual) { setConfirmTxns([]); return }
    setConfirmLoading(true)
    ;(async () => {
      try {
        const res = await apiFetch(`/api/disbursements/${showConfirmManual.id}/transactions/?page=1&page_size=100`)
        if (res.ok) {
          const result = await res.json()
          setConfirmTxns(result.results || [])
        }
      } catch { }
      finally { setConfirmLoading(false) }
    })()
  }, [showConfirmManual])

  const handleSort = (key) => setSortField(prev => (prev === key ? `-${key}` : key))

  const doAction = async (id, action, onSuccess) => {
    setActionLoading(`${id}-${action}`)
    try {
      const res = await apiFetch(`/api/disbursements/${id}/${action}/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || `Failed to ${action}`) }
      const result = await res.json()
      showToast({ type: 'success', message: `Batch ${action.replace(/_/g, ' ')}d.` })
      if (onSuccess) onSuccess(result)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setActionLoading(null) }
  }

  const doDelete = async (id) => {
    setActionLoading(`${id}-delete`)
    try {
      const res = await apiFetch(`/api/disbursements/${id}/`, { method: 'DELETE' })
      if (res.status === 204) {
        showToast({ type: 'success', message: 'Batch deleted.' })
      } else if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Delete failed' }))
        throw new Error(err.detail || 'Delete failed')
      }
      setShowDelete(null)
      setDetailDisbursement(null)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setActionLoading(null) }
  }

  const handleApprove = () => doAction(showApprove.id, 'approve', () => setShowApprove(null))
  const handleReject = () => doAction(showReject.id, 'reject', () => setShowReject(null))
  const handleLive = () => {
    doAction(showLive.id, 'live', (r) => {
      setShowLive(null)
      if (r.task_id) setPollingId(showLive.id)
    })
  }
  const handleRetry = () => doAction(showRetry.id, 'retry_failed', () => setShowRetry(null))

  const handleCsvDownload = async (format) => {
    if (!showCsvFormat) return
    setCsvSaving(true)
    try {
      await exportCsv(`/api/disbursements/${showCsvFormat.id}/csv/?bank=${format}`)
      showToast({ type: 'success', message: 'CSV downloaded.' })
      setShowCsvFormat(null)
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setCsvSaving(false) }
  }

  const handleInitiate = async (e) => {
    e.preventDefault()
    setInitSaving(true)
    try {
      const res = await apiFetch('/api/disbursements/initiate/', {
        method: 'POST',
        body: JSON.stringify({ payment_cycle: initCycleId }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Initiation failed') }
      showToast({ type: 'success', message: 'Disbursement batch created.' })
      setShowInitiate(false)
      setInitCycleId('')
      setShowPreview(false)
      setPreviewData(null)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setInitSaving(false) }
  }

  const handlePreview = async () => {
    if (!initCycleId) return
    setPreviewLoading(true)
    try {
      const res = await apiFetch('/api/disbursements/preview/', {
        method: 'POST',
        body: JSON.stringify({ payment_cycle: initCycleId }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Preview failed') }
      const result = await res.json()
      setPreviewData(result)
      setShowPreview(true)
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setPreviewLoading(false) }
  }

  const handleConfirmManual = async () => {
    if (!showConfirmManual || !confirmTxnIds.length) return
    setConfirmSaving(true)
    try {
      const res = await apiFetch(`/api/disbursements/${showConfirmManual.id}/confirm_manual/`, {
        method: 'POST',
        body: JSON.stringify({
          transaction_ids: confirmTxnIds,
          notes: confirmNotes || undefined,
        }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Confirmation failed') }
      const result = await res.json()
      showToast({ type: 'success', message: `${result.confirmed} transaction(s) confirmed manually.${result.skipped ? ` ${result.skipped} skipped.` : ''}` })
      setShowConfirmManual(null)
      setConfirmTxnIds([])
      setConfirmNotes('')
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setConfirmSaving(false) }
  }

  const handleRowClick = (row) => {
    setDetailDisbursement(row)
    setDetailTxnPage(1)
    setDetailTxnStatus('')
    setDetailTxnMethod('')
  }

  const txnQp = detailDisbursement
    ? new URLSearchParams({ page: detailTxnPage, page_size: '20' })
    : null
  if (txnQp) {
    if (detailTxnStatus) txnQp.set('status', detailTxnStatus)
    if (detailTxnMethod) txnQp.set('payment_method', detailTxnMethod)
  }

  const { data: txnData, loading: txnLoading } = useApi(
    detailDisbursement ? `/api/disbursements/${detailDisbursement.id}/transactions/?${txnQp}` : null,
  )

  const txns = txnData?.results || []
  const txnTotal = txnData?.count || 0

  const confirmAvailableTxns = confirmTxns.filter(
    t => ['PENDING', 'FAILED'].includes(t.status) && ['BANK', 'CASH'].includes(t.payment_method),
  )

  const columns = [
    {
      key: 'id', label: 'Batch Ref', sortable: false,
      render: (row) => <span className="font-mono text-sm">{row.id?.slice(0, 8) || '-'}</span>,
    },
    {
      key: 'payment_cycle_name', label: 'Cycle', sortable: false,
      render: (row) => row.payment_cycle_name || '-',
    },
    {
      key: 'total_amount', label: 'Total', sortable: true,
      render: (row) => formatKes(row.total_amount),
    },
    {
      key: 'transaction_count', label: 'Farmers', sortable: false,
      render: (row) => row.transaction_count ?? '-',
    },
    {
      key: 'status', label: 'Status', sortable: true,
      render: (row) => <StatusBadge status={statusColor(row.status)} label={row.status} />,
    },
    {
      key: 'created_at', label: 'Created', sortable: true,
      render: (row) => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-',
    },
  ]

  const rowActions = (row) => {
    const isOpen = openDropdownId === row.id
    const showApproveReject = row.status === 'PENDING' && isManager
    const showSend = row.status === 'APPROVED'
    const showRetry = row.status === 'FAILED'
    const showDelete = ['PENDING', 'FAILED', 'REJECTED'].includes(row.status)
    if (!showApproveReject && !showSend && !showRetry && !showDelete) return null

    return (
      <div className="relative" ref={isOpen ? dropdownRef : undefined}>
        <button
          onClick={(e) => { e.stopPropagation(); setOpenDropdownId(isOpen ? null : row.id) }}
          className={`p-1 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors ${isOpen ? 'opacity-100' : ''}`}
          aria-label="Actions"
          title="Batch actions"
        >
          <span className="material-symbols-outlined text-lg" aria-hidden="true">more_vert</span>
        </button>
        {isOpen && (
          <div className="absolute right-0 top-full mt-1 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-lg z-50 min-w-[160px] py-1 overflow-hidden" onClick={(e) => e.stopPropagation()}>
            {showApproveReject && (
              <>
                <button onClick={() => { setShowApprove(row); setOpenDropdownId(null) }} className="w-full text-left px-4 py-2 text-label-md text-success hover:bg-surface-container-high transition-colors">Approve</button>
                <button onClick={() => { setShowReject(row); setOpenDropdownId(null) }} className="w-full text-left px-4 py-2 text-label-md text-error hover:bg-surface-container-high transition-colors">Reject</button>
              </>
            )}
            {showSend && (
              <button onClick={() => { setShowLive(row); setOpenDropdownId(null) }} className="w-full text-left px-4 py-2 text-label-md text-primary hover:bg-surface-container-high transition-colors">Send to M-Pesa</button>
            )}
            {showRetry && (
              <button onClick={() => { setShowRetry(row); setOpenDropdownId(null) }} className="w-full text-left px-4 py-2 text-label-md text-warning hover:bg-surface-container-high transition-colors">Retry Failed</button>
            )}
            {showDelete && (
              <>
                {showApproveReject && <div className="border-t border-outline-variant my-1" />}
                <button onClick={() => { setShowDelete(row); setOpenDropdownId(null) }} className="w-full text-left px-4 py-2 text-label-md text-error hover:bg-surface-container-high transition-colors">Delete Batch</button>
              </>
            )}
          </div>
        )}
      </div>
    )
  }

  const detailActions = (row) => (
    <div className="space-y-3 pt-4 border-t border-outline-variant">
      {row.status === 'PENDING' && isManager && (
        <div className="flex gap-2">
          <button onClick={() => { setShowApprove(row); setDetailDisbursement(null) }} className="flex-1 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Approve</button>
          <button onClick={() => { setShowReject(row); setDetailDisbursement(null) }} className="flex-1 py-2 border border-error text-error rounded-lg text-label-md font-bold">Reject</button>
        </div>
      )}
      {row.status === 'APPROVED' && (
        <button onClick={() => { setShowLive(row); setDetailDisbursement(null) }} disabled={actionLoading === `${row.id}-live`} className="w-full py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">
          {actionLoading === `${row.id}-live` ? 'Sending...' : 'Send to M-Pesa'}
        </button>
      )}
      {row.status === 'FAILED' && (
        <button onClick={() => { setShowRetry(row); setDetailDisbursement(null) }} disabled={actionLoading === `${row.id}-retry_failed`} className="w-full py-2 bg-warning-container text-on-warning-container rounded-lg text-label-md font-bold disabled:opacity-50">
          {actionLoading === `${row.id}-retry_failed` ? 'Retrying...' : 'Retry Failed'}
        </button>
      )}
      {(row.status === 'PROCESSING' || row.status === 'COMPLETED' || row.status === 'PARTIALLY_COMPLETED') && (
        <button onClick={() => { setDetailDisbursement(null); setShowCsvFormat(row) }} className="w-full py-2 border border-outline-variant rounded-lg text-label-md font-bold">Download CSV</button>
      )}
      <button onClick={() => { setDetailDisbursement(null); setShowConfirmManual(row) }} disabled={confirmLoading} className="w-full py-2 bg-success-container text-on-success-container rounded-lg text-label-md font-bold disabled:opacity-50">
        Confirm Manual Payment
      </button>
      {['PENDING', 'FAILED', 'REJECTED'].includes(row.status) && (
        <button onClick={() => { setShowDelete(row); setDetailDisbursement(null) }} className="w-full py-2 border border-error text-error rounded-lg text-label-md font-bold">Delete Batch</button>
      )}
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Disbursements</h2>
          <p className="text-sm text-on-surface-variant">{total} total{pollingId && ' • Polling active'}</p>
        </div>
        <button onClick={() => setShowInitiate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
          + Initiate from Cycle
        </button>
      </header>

      <div className="mb-4 flex items-center gap-4 flex-wrap">
        <label htmlFor="disbursement-status-filter" className="sr-only">Filter by status</label>
        <select id="disbursement-status-filter" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="PROCESSING">Processing</option>
          <option value="COMPLETED">Completed</option>
          <option value="PARTIALLY_COMPLETED">Partially Completed</option>
          <option value="FAILED">Failed</option>
          <option value="REJECTED">Rejected</option>
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
            rowActions={rowActions}
            onRowClick={handleRowClick}
            emptyMessage="No disbursements found."
          />
          <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailDisbursement} onClose={() => { setDetailDisbursement(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Disbursement Details" width="max-w-2xl">
        {detailDisbursement && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              {[
                { key: 'id', label: 'Batch Ref' },
                { key: 'payment_cycle_name', label: 'Cycle' },
                { key: 'total_amount', label: 'Total', fmt: (v) => formatKes(v) },
                { key: 'transaction_count', label: 'Farmers' },
                { key: 'status', label: 'Status' },
                { key: 'created_at', label: 'Created', fmt: (v) => v ? new Date(v).toLocaleDateString() : '-' },
                { key: 'approved_by_name', label: 'Approved By' },
                { key: 'approved_at', label: 'Approved At', fmt: (v) => v ? new Date(v).toLocaleString() : '-' },
              ].map(({ key, label, fmt }) => (
                <div key={key}>
                  <p className="text-label-md text-on-surface-variant capitalize">{label}</p>
                  <p className="text-body-md text-on-surface font-medium">
                    {key === 'status'
                      ? <StatusBadge status={statusColor(detailDisbursement[key])} label={detailDisbursement[key]} />
                      : fmt ? fmt(detailDisbursement[key]) : String(detailDisbursement[key] ?? '-')}
                  </p>
                </div>
              ))}
            </div>

            <div className="border-t border-outline-variant pt-4">
              <h4 className="text-label-lg text-on-surface font-bold mb-3">Transactions</h4>
              <div className="flex gap-2 mb-3">
                <label htmlFor="txn-status-filter" className="sr-only">Filter by transaction status</label>
                <select id="txn-status-filter" value={detailTxnStatus} onChange={(e) => { setDetailTxnStatus(e.target.value); setDetailTxnPage(1) }} className="px-2 py-1 border border-outline-variant rounded text-body-sm bg-surface-container">
                  <option value="">All Statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="SUCCESS">Success</option>
                  <option value="FAILED">Failed</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
                <label htmlFor="txn-method-filter" className="sr-only">Filter by payment method</label>
                <select id="txn-method-filter" value={detailTxnMethod} onChange={(e) => { setDetailTxnMethod(e.target.value); setDetailTxnPage(1) }} className="px-2 py-1 border border-outline-variant rounded text-body-sm bg-surface-container">
                  <option value="">All Methods</option>
                  <option value="M_PESA">M-Pesa</option>
                  <option value="BANK">Bank</option>
                  <option value="CASH">Cash</option>
                </select>
              </div>
              {txnLoading ? <TableSkeleton rows={5} cols={4} /> : txns.length === 0 ? (
                <p className="text-body-sm text-on-surface-variant">No transactions found.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-body-sm">
                    <thead>
                      <tr className="border-b border-outline-variant text-label-md text-on-surface-variant">
                        <th scope="col" className="py-2 pr-2">Farmer</th>
                        <th scope="col" className="py-2 pr-2">Amount</th>
                        <th scope="col" className="py-2 pr-2">Method</th>
                        <th scope="col" className="py-2 pr-2">Status</th>
                        <th scope="col" className="py-2 pr-2">Ref</th>
                        <th scope="col" className="py-2">Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {txns.map((t) => (
                        <tr key={t.id} className="border-b border-outline-variant/50">
                          <td className="py-2 pr-2">{t.farmer_name || `#${t.farmer_id?.slice(0, 8) || t.farmer}`}</td>
                          <td className="py-2 pr-2">{formatKes(t.amount)}</td>
                          <td className="py-2 pr-2">{t.payment_method?.replace(/_/g, ' ') || '-'}</td>
                          <td className="py-2 pr-2"><StatusBadge status={statusColor(t.status)} label={t.status} /></td>
                          <td className="py-2 pr-2 font-mono text-xs">{t.transaction_ref || '-'}</td>
                          <td className="py-2 text-error text-xs max-w-[200px] truncate" title={darajaError(t) || ''}>
                            {darajaError(t) || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {txnTotal > 20 && (
                    <div className="flex justify-center gap-2 mt-3">
                      <button disabled={detailTxnPage <= 1} onClick={() => setDetailTxnPage(p => p - 1)} className="px-2 py-1 border border-outline-variant rounded text-body-sm disabled:opacity-50">Prev</button>
                      <span className="text-body-sm text-on-surface-variant self-center">{detailTxnPage} / {Math.ceil(txnTotal / 20)}</span>
                      <button disabled={detailTxnPage >= Math.ceil(txnTotal / 20)} onClick={() => setDetailTxnPage(p => p + 1)} className="px-2 py-1 border border-outline-variant rounded text-body-sm disabled:opacity-50">Next</button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {detailActions(detailDisbursement)}
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal open={!!showApprove} title="Approve Disbursement" message={`Approve batch "${showApprove?.payment_cycle_name || showApprove?.id?.slice(0, 8)}"? Once approved, it can be sent to M-Pesa.`} confirmLabel="Approve" onConfirm={handleApprove} loading={actionLoading === `${showApprove?.id}-approve`} onCancel={() => setShowApprove(null)} />

      <ConfirmModal open={!!showReject} title="Reject Disbursement" message={`Reject batch "${showReject?.payment_cycle_name || showReject?.id?.slice(0, 8)}"?`} confirmLabel="Reject" destructive onConfirm={handleReject} loading={actionLoading === `${showReject?.id}-reject`} onCancel={() => setShowReject(null)} />

      <ConfirmModal open={!!showLive} title="Send to M-Pesa" message={`Queue batch "${showLive?.payment_cycle_name || showLive?.id?.slice(0, 8)}" for live M-Pesa disbursement?`} confirmLabel="Send" onConfirm={handleLive} loading={actionLoading === `${showLive?.id}-live`} onCancel={() => setShowLive(null)} />

      <ConfirmModal open={!!showRetry} title="Retry Failed" message={`Retry all FAILED transactions in batch "${showRetry?.payment_cycle_name || showRetry?.id?.slice(0, 8)}"?`} confirmLabel="Retry" onConfirm={handleRetry} loading={actionLoading === `${showRetry?.id}-retry_failed`} onCancel={() => setShowRetry(null)} />

      <ConfirmModal open={!!showDelete} title="Delete Batch" message={`Permanently delete batch "${showDelete?.payment_cycle_name || showDelete?.id?.slice(0, 8)}"? This cannot be undone.`} confirmLabel="Delete" destructive onConfirm={() => doDelete(showDelete.id)} loading={actionLoading === `${showDelete?.id}-delete`} onCancel={() => setShowDelete(null)} />

      {showCsvFormat && (
        <div className="fixed inset-0 bg-black/40 z-[60] flex items-center justify-center" onClick={() => setShowCsvFormat(null)}>
          <div className="bg-surface rounded-xl p-6 max-w-sm w-[90vw] relative" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-headline-sm text-headline-sm mb-4">Download CSV</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Select bank format for CSV export.</p>
            <div className="space-y-2">
              {[
                { value: 'generic', label: 'Generic Format' },
                { value: 'equity', label: 'Equity Bank Format' },
                { value: 'kcb', label: 'KCB Bank Format' },
              ].map((opt) => (
                <button key={opt.value} onClick={() => handleCsvDownload(opt.value)} disabled={csvSaving} className="w-full py-2 px-4 border border-outline-variant rounded-lg text-label-md font-bold text-left hover:bg-surface-container-high disabled:opacity-50">
                  {opt.label}
                </button>
              ))}
            </div>
            <button onClick={() => setShowCsvFormat(null)} className="w-full mt-3 py-2 text-label-md font-bold text-on-surface-variant">Cancel</button>
          </div>
        </div>
      )}

      {showConfirmManual && (
        <div className="fixed inset-0 bg-black/40 z-[60] flex items-center justify-center" onClick={() => { setShowConfirmManual(null); setConfirmTxnIds([]); setConfirmNotes('') }}>
          <div className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] max-h-[80vh] overflow-y-auto relative" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-headline-sm text-headline-sm mb-4">Confirm Manual Payment</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Select BANK/CASH transactions to mark as paid.</p>

            {confirmLoading ? <TableSkeleton rows={5} cols={3} /> : confirmAvailableTxns.length === 0 ? (
              <p className="text-body-md text-on-surface-variant">No pending/retriable BANK/CASH transactions available.</p>
            ) : (
              <>
                <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
                  {confirmAvailableTxns.map((t) => (
                    <label key={t.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container-high cursor-pointer">
                      <input type="checkbox" checked={confirmTxnIds.includes(t.id)} onChange={(e) => setConfirmTxnIds(prev => e.target.checked ? [...prev, t.id] : prev.filter(id => id !== t.id))} className="accent-primary" />
                      <div className="flex-1">
                        <p className="text-body-md font-medium">{t.farmer_name || `#${t.farmer_id?.slice(0, 8)}`}</p>
                        <p className="text-body-sm text-on-surface-variant">{formatKes(t.amount)} — {t.payment_method?.replace(/_/g, ' ')}</p>
                      </div>
                    </label>
                  ))}
                </div>

                <textarea value={confirmNotes} onChange={(e) => setConfirmNotes(e.target.value)} placeholder="Optional notes..." className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container mb-4" rows={2} />

                <div className="flex gap-3">
                  <button onClick={handleConfirmManual} disabled={!confirmTxnIds.length || confirmSaving} className="flex-1 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">
                    {confirmSaving ? 'Confirming...' : `Confirm (${confirmTxnIds.length})`}
                  </button>
                  <button onClick={() => { setShowConfirmManual(null); setConfirmTxnIds([]); setConfirmNotes('') }} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showInitiate && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => { setShowInitiate(false); setShowPreview(false); setPreviewData(null) }}>
          <div className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] relative" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-headline-sm text-headline-sm mb-4">Initiate Disbursements from Cycle</h3>
            <form onSubmit={handleInitiate} className="space-y-4">
              <div>
                <label htmlFor="payment-cycle" className="block text-label-md text-on-surface-variant mb-1">Payment Cycle</label>
                <select id="payment-cycle" value={initCycleId} onChange={(e) => setInitCycleId(e.target.value)} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
                  <option value="">Select cycle...</option>
                  {cycles.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.status})</option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3">
                <button type="button" onClick={handlePreview} disabled={!initCycleId || previewLoading} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold disabled:opacity-50">
                  {previewLoading ? 'Loading...' : 'Preview'}
                </button>
                <button type="submit" disabled={initSaving || !initCycleId} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">
                  {initSaving ? 'Initiating...' : 'Initiate'}
                </button>
                <button type="button" onClick={() => { setShowInitiate(false); setShowPreview(false); setPreviewData(null) }} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showPreview && previewData && (
        <div className="fixed inset-0 bg-black/40 z-[70] flex items-center justify-center" onClick={() => setShowPreview(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-md w-[90vw] relative" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-headline-sm text-headline-sm mb-4">Pre-flight Summary</h3>
            <div className="space-y-3 mb-6">
              <div className="flex justify-between"><span className="text-on-surface-variant">Cycle</span><span className="font-medium">{previewData.cycle_name}</span></div>
              <div className="flex justify-between"><span className="text-on-surface-variant">Total Farmers in Cycle</span><span className="font-medium">{previewData.total_farmers_in_cycle}</span></div>
              <div className="flex justify-between"><span className="text-on-surface-variant">Eligible Farmers</span><span className="font-medium">{previewData.total_eligible}</span></div>
              <div className="flex justify-between"><span className="text-on-surface-variant">Skipped</span><span className="font-medium">{previewData.total_skipped} ({formatKes(previewData.skipped_carry_forward_amount)} carried forward)</span></div>
              <div className="border-t border-outline-variant pt-3">
                <div className="flex justify-between font-bold"><span>Total Amount</span><span>{formatKes(previewData.total_amount)}</span></div>
              </div>
              <div className="border-t border-outline-variant pt-3">
                <p className="text-label-md text-on-surface-variant mb-2">Breakdown by Method</p>
                {Object.entries(previewData.breakdown || {}).map(([method, amount]) => (
                  amount > 0 && (
                    <div key={method} className="flex justify-between text-body-sm">
                      <span>{method.replace(/_/g, ' ')}</span>
                      <span>{formatKes(amount)}</span>
                    </div>
                  )
                ))}
              </div>
            </div>
            <button onClick={() => setShowPreview(false)} className="w-full py-2 border border-outline-variant rounded-lg text-label-md font-bold">Close</button>
          </div>
        </div>
      )}
    </div>
  )
}

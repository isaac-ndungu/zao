import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import DataTable from '../../admin/components/common/DataTable'
import ErrorState from '../../shared/components/ErrorState'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

const statusColors = {
  PENDING: 'badge-warning', APPROVED: 'badge-info', SENDING: 'badge-warning',
  SENT: 'badge-success', FAILED: 'badge-error', REJECTED: 'badge-error',
  CONFIRMED: 'badge-primary',
}

export default function AccountantDisbursements() {
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [showInitiate, setShowInitiate] = useState(false)
  const [initForm, setInitForm] = useState({ cycle: '' })
  const [saving, setSaving] = useState(false)
  const [actionLoading, setActionLoading] = useState(null)

  const qp = new URLSearchParams({ page, page_size: '20' })
  if (statusFilter) qp.set('status', statusFilter)

  const { data, loading, error, refetch } = useApi(`/api/disbursements/?${qp}`)
  const { data: cycles } = useApi('/api/cycles/?page=1&page_size=100')

  const disbursements = data?.results || data || []
  const totalCount = data?.count || disbursements.length

  const selected = selectedId
    ? disbursements.find((d) => String(d.id) === selectedId)
    : null

  const handleInitiate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch(`/api/cycles/${initForm.cycle}/initiate-disbursements/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to initiate disbursements') }
      showToast({ type: 'success', message: 'Disbursements initiated from cycle.' })
      setShowInitiate(false)
      setInitForm({ cycle: '' })
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  const handleAction = async (id, action) => {
    setActionLoading(`${id}-${action}`)
    try {
      const res = await apiFetch(`/api/disbursements/${id}/${action}/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || `Failed to ${action}`) }
      showToast({ type: 'success', message: `Disbursement ${action.replace('_', ' ')}d.` })
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setActionLoading(null) }
  }

  const handleExport = async () => {
    try {
      const res = await apiFetch('/api/disbursements/export/')
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Export failed') }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'disbursements_export.csv'
      a.click()
      URL.revokeObjectURL(url)
      showToast({ type: 'success', message: 'Disbursements exported.' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const statuses = ['', 'PENDING', 'APPROVED', 'SENT', 'FAILED', 'REJECTED', 'CONFIRMED']

  const columns = [
    { header: 'ID', accessor: 'id' },
    { header: 'Farmer', accessor: (d) => d.farmer_name || d.farmer?.full_name || `#${d.farmer}` },
    { header: 'Amount', accessor: (d) => formatKes(d.amount) },
    { header: 'Status', accessor: (d) => <span className={`badge ${statusColors[d.status] || 'badge-default'}`}>{d.status}</span> },
    { header: 'Method', accessor: (d) => d.payment_method || '-' },
    { header: 'Date', accessor: (d) => d.created_at ? new Date(d.created_at).toLocaleDateString() : '-' },
  ]

  return (
    <div>
      <header className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Disbursements</h2>
          <p className="text-on-surface-variant font-body-md">{totalCount} disbursements</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleExport} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold hover:bg-surface-container-high transition-colors">Export CSV</button>
          <button onClick={() => setShowInitiate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">+ Initiate from Cycle</button>
        </div>
      </header>

      <div className="flex items-center gap-3 mb-4">
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          {statuses.map((s) => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
        </select>
        <p className="text-body-md text-on-surface-variant ml-auto">
          {disbursements.filter((d) => d.status === 'SENT').length} sent / {disbursements.filter((d) => d.status === 'FAILED').length} failed
        </p>
      </div>

      {loading ? <TableSkeleton rows={10} cols={6} /> : error ? <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} /> : (
        <DataTable
          columns={columns}
          data={disbursements}
          onRowClick={(d) => setSearchParams({ ...Object.fromEntries(searchParams.entries()), selected: String(d.id) })}
          page={page}
          totalPages={Math.ceil(totalCount / 20)}
          onPageChange={setPage}
        />
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setSearchParams({ ...Object.fromEntries(searchParams.entries()), selected: undefined })}>
          <div className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] max-h-[90vh] overflow-y-auto relative" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface">Disbursement #{selected.id}</h3>
                <p className="text-body-md text-on-surface-variant">{selected.farmer_name || selected.farmer?.full_name || `Farmer #${selected.farmer}`}</p>
              </div>
              <button onClick={() => setSearchParams({ ...Object.fromEntries(searchParams.entries()), selected: undefined })} aria-label="Close panel" className="text-on-surface-variant hover:text-on-surface"><span className="material-symbols-outlined">close</span></button>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div><p className="text-label-md text-on-surface-variant">Amount</p><p className="text-body-md font-bold">{formatKes(selected.amount)}</p></div>
              <div><p className="text-label-md text-on-surface-variant">Status</p><span className={`badge ${statusColors[selected.status] || 'badge-default'}`}>{selected.status}</span></div>
              <div><p className="text-label-md text-on-surface-variant">Method</p><p className="text-body-md">{selected.payment_method || '-'}</p></div>
              <div><p className="text-label-md text-on-surface-variant">Reference</p><p className="text-body-md">{selected.transaction_ref || '-'}</p></div>
              <div><p className="text-label-md text-on-surface-variant">Phone</p><p className="text-body-md">{selected.phone_number || '-'}</p></div>
              <div><p className="text-label-md text-on-surface-variant">Created</p><p className="text-body-md">{selected.created_at ? new Date(selected.created_at).toLocaleString() : '-'}</p></div>
            </div>

            {selected.error_message && (
              <div className="bg-error-container text-on-error-container rounded-xl p-4 mb-6">
                <p className="text-label-md font-bold">Error</p>
                <p className="text-body-md">{selected.error_message}</p>
              </div>
            )}

            {selected.notes && (
              <div className="mb-6"><p className="text-label-md text-on-surface-variant mb-1">Notes</p><p className="text-body-md">{selected.notes}</p></div>
            )}

            <div className="pt-4 border-t border-outline-variant space-y-3">
              {selected.status === 'APPROVED' && (
                <button onClick={() => handleAction(selected.id, 'live_send')} disabled={actionLoading === `${selected.id}-live_send`} className="w-full py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">
                  {actionLoading === `${selected.id}-live_send` ? '...' : 'Live Send'}
                </button>
              )}
              {selected.status === 'FAILED' && (
                <button onClick={() => handleAction(selected.id, 'live_send')} disabled={actionLoading === `${selected.id}-live_send`} className="w-full py-2 bg-warning-container text-on-warning-container rounded-lg text-label-md font-bold disabled:opacity-50">
                  {actionLoading === `${selected.id}-live_send` ? '...' : 'Retry'}
                </button>
              )}
              {selected.status === 'SENT' && (
                <button onClick={() => handleAction(selected.id, 'confirm_manual')} disabled={actionLoading === `${selected.id}-confirm_manual`} className="w-full py-2 bg-success-container text-on-success-container rounded-lg text-label-md font-bold disabled:opacity-50">
                  {actionLoading === `${selected.id}-confirm_manual` ? '...' : 'Confirm Manual'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {showInitiate && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setShowInitiate(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] relative" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-headline-sm text-headline-sm mb-4">Initiate Disbursements from Cycle</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Select an active cycle to generate disbursements for all farmers.</p>
            <form onSubmit={handleInitiate} className="space-y-4">
              <div><label className="block text-label-md text-on-surface-variant mb-1">Cycle</label>
                <select value={initForm.cycle} onChange={(e) => setInitForm(p => ({ ...p, cycle: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
                  <option value="">Select cycle...</option>
                  {cycles?.results?.filter((c) => c.status === 'ACTIVE' || c.status === 'LOCKED' || c.status === 'COMPLETED')?.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.status}) — {formatKes(c.net_payout)}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <button type="submit" disabled={saving} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">{saving ? '...' : 'Initiate'}</button>
                <button type="button" onClick={() => setShowInitiate(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

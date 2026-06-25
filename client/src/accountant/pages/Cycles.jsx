import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import DataTable from '../../admin/components/common/DataTable'

const statusColors = {
  DRAFT: 'badge-default', ACTIVE: 'badge-info', LOCKED: 'badge-warning',
  PROCESSING: 'badge-warning', COMPLETED: 'badge-success', CANCELLED: 'badge-error',
}

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

function CycleDetailPanel({ cycle, onClose, onAction }) {
  const { showToast } = useToast()
  const [running, setRunning] = useState(false)
  const [runProgress, setRunProgress] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  async function handleRunCycle() {
    runCycle.current = handleRunCycle
    setRunning(true)
    setRunProgress({ status: 'starting', message: 'Starting cycle...' })
    try {
      const res = await apiFetch(`/api/cycles/${cycle.id}/run/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to run cycle') }
      const result = await res.json()
      setRunProgress({ status: 'processing', message: 'Processing disbursements...', taskId: result.task_id || result.id })
      pollRef.current = setInterval(async () => {
        try {
          const pr = await apiFetch(`/api/cycles/${cycle.id}/run-status/`)
          if (pr.ok) {
            const status = await pr.json()
            if (status.status === 'COMPLETED') {
              clearInterval(pollRef.current)
              setRunProgress({ status: 'completed', message: 'Cycle completed successfully!' })
              setRunning(false)
              onAction()
            } else if (status.status === 'FAILED') {
              clearInterval(pollRef.current)
              setRunProgress({ status: 'failed', message: status.error || 'Cycle run failed' })
              setRunning(false)
            } else {
              setRunProgress({ status: 'processing', message: status.message || `Processing... (${status.processed || 0}/${status.total || '?'})` })
            }
          }
        } catch (e) { /* ignore poll errors */ }
      }, 3000)
    } catch (err) {
      setRunProgress({ status: 'failed', message: err.message })
      setRunning(false)
    }
  }

  const handleHoldRelease = async (action) => {
    try {
      const res = await apiFetch(`/api/cycles/${cycle.id}/${action}/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || `Failed to ${action}`) }
      showToast({ type: 'success', message: `Payments ${action === 'hold' ? 'held' : 'released'}.` })
      onAction()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleLockUnlock = async (action) => {
    try {
      const res = await apiFetch(`/api/cycles/${cycle.id}/${action}/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || `Failed to ${action}`) }
      showToast({ type: 'success', message: `Cycle ${action === 'lock' ? 'locked' : 'unlocked'}.` })
      onAction()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-headline-sm text-headline-sm text-on-surface">{cycle.name}</h3>
          <p className="text-body-md text-on-surface-variant">Cycle #{cycle.id}</p>
        </div>
        <button onClick={onClose} className="text-on-surface-variant hover:text-on-surface"><span className="material-symbols-outlined">close</span></button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div><p className="text-label-md text-on-surface-variant">Status</p><span className={`badge ${statusColors[cycle.status] || 'badge-default'}`}>{cycle.status}</span></div>
        <div><p className="text-label-md text-on-surface-variant">Total Gross</p><p className="text-body-md font-bold">{formatKes(cycle.total_gross)}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Total Deductions</p><p className="text-body-md">{formatKes(cycle.total_deductions)}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Net Payout</p><p className="text-body-md font-bold">{formatKes(cycle.net_payout)}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Farmers</p><p className="text-body-md">{cycle.farmer_count || '-'}</p></div>
        <div><p className="text-label-md text-on-surface-variant">WHT</p><p className="text-body-md">{formatKes(cycle.withholding_tax)}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Period Start</p><p className="text-body-md">{cycle.period_start ? new Date(cycle.period_start).toLocaleDateString() : '-'}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Period End</p><p className="text-body-md">{cycle.period_end ? new Date(cycle.period_end).toLocaleDateString() : '-'}</p></div>
      </div>

      {cycle.notes && (
        <div><p className="text-label-md text-on-surface-variant mb-1">Notes</p><p className="text-body-md">{cycle.notes}</p></div>
      )}

      <div className="pt-4 border-t border-outline-variant space-y-3">
        {running && runProgress ? (
          <div className="bg-surface-container rounded-xl p-4 space-y-2">
            <div className="flex items-center gap-2">
              <span className={`material-symbols-outlined ${runProgress.status === 'completed' ? 'text-success' : runProgress.status === 'failed' ? 'text-error' : 'text-warning animate-spin'}`}>
                {runProgress.status === 'completed' ? 'check_circle' : runProgress.status === 'failed' ? 'error' : 'sync'}
              </span>
              <span className="text-body-md">{runProgress.message}</span>
            </div>
          </div>
        ) : (
          <>
            {cycle.status === 'DRAFT' && (
              <button onClick={handleRunCycle} className="w-full py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
                Run Cycle
              </button>
            )}
            {cycle.status === 'ACTIVE' && (
              <button onClick={() => handleHoldRelease('hold')} className="w-full py-2 bg-warning-container text-on-warning-container rounded-lg text-label-md font-bold hover:bg-warning-container/80 transition-colors">
                Hold All Payments
              </button>
            )}
            {cycle.status === 'HOLD' && (
              <button onClick={() => handleHoldRelease('release')} className="w-full py-2 bg-success-container text-on-success-container rounded-lg text-label-md font-bold hover:bg-success-container/80 transition-colors">
                Release Payments
              </button>
            )}
            {(cycle.status === 'DRAFT' || cycle.status === 'ACTIVE') && (
              <button onClick={() => handleLockUnlock('lock')} disabled={cycle.status !== 'ACTIVE'} className="w-full py-2 bg-error-container text-on-error-container rounded-lg text-label-md font-bold disabled:opacity-50 transition-colors">
                Lock Cycle
              </button>
            )}
            {cycle.status === 'LOCKED' && (
              <button onClick={() => handleLockUnlock('unlock')} className="w-full py-2 bg-success-container text-on-success-container rounded-lg text-label-md font-bold hover:bg-success-container/80 transition-colors">
                Unlock Cycle
              </button>
            )}
            {cycle.status === 'DRAFT' && (
              <button onClick={() => handleLockUnlock('lock')} className="w-full py-2 border border-error text-error rounded-lg text-label-md font-bold">
                Lock Cycle
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function AccountantCycles() {
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({ name: '', period_start: '', period_end: '', notes: '', status: 'DRAFT' })
  const [saving, setSaving] = useState(false)

  const qp = new URLSearchParams({ page, page_size: '20' })
  const { data, loading, error, refetch } = useApi(`/api/cycles/?${qp}`)

  const cycles = data?.results || data || []
  const totalCount = data?.count || cycles.length

  const selectedCycle = selectedId
    ? cycles.find((c) => String(c.id) === selectedId) || data?.results?.find((c) => String(c.id) === selectedId)
    : null

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch('/api/cycles/', {
        method: 'POST',
        body: JSON.stringify(formData),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create cycle') }
      showToast({ type: 'success', message: 'Payment cycle created.' })
      setShowForm(false)
      setFormData({ name: '', period_start: '', period_end: '', notes: '', status: 'DRAFT' })
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  const handleExport = async () => {
    try {
      const res = await apiFetch('/api/cycles/export/')
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Export failed') }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'cycles_export.csv'
      a.click()
      URL.revokeObjectURL(url)
      showToast({ type: 'success', message: 'Cycles exported.' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const columns = [
    { header: 'ID', accessor: 'id', sortable: true },
    { header: 'Name', accessor: 'name', sortable: true },
    { header: 'Status', accessor: (c) => <span className={`badge ${statusColors[c.status] || 'badge-default'}`}>{c.status}</span> },
    { header: 'Gross', accessor: (c) => formatKes(c.total_gross) },
    { header: 'Net', accessor: (c) => formatKes(c.net_payout) },
    { header: 'Farmers', accessor: 'farmer_count' },
    { header: 'Period', accessor: (c) => c.period_start ? `${new Date(c.period_start).toLocaleDateString()} - ${new Date(c.period_end).toLocaleDateString()}` : '-' },
  ]

  return (
    <div>
      <header className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Payment Cycles</h2>
          <p className="text-on-surface-variant font-body-md">{totalCount} cycles</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleExport} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold hover:bg-surface-container-high transition-colors">Export CSV</button>
          <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">+ New Cycle</button>
        </div>
      </header>

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-1 min-w-0">
          {loading ? <TableSkeleton rows={10} cols={7} /> : error ? <p className="text-error">Failed to load cycles.</p> : (
            <DataTable
              columns={columns}
              data={cycles}
              onRowClick={(c) => setSearchParams({ selected: String(c.id) })}
              page={page}
              totalPages={Math.ceil(totalCount / 20)}
              onPageChange={setPage}
            />
          )}
        </div>

        {selectedCycle && (
          <div className="w-full lg:w-[400px] shrink-0">
            <CycleDetailPanel cycle={selectedCycle} onClose={() => setSearchParams({})} onAction={refetch} />
          </div>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setShowForm(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] max-h-[90vh] overflow-y-auto relative" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-headline-sm text-headline-sm mb-4">Create Payment Cycle</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div><label className="block text-label-md text-on-surface-variant mb-1">Name</label>
                <input value={formData.name} onChange={(e) => setFormData(p => ({ ...p, name: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" placeholder="e.g. June 2026 Payout" />
              </div>
              <div><label className="block text-label-md text-on-surface-variant mb-1">Period Start</label>
                <input type="date" value={formData.period_start} onChange={(e) => setFormData(p => ({ ...p, period_start: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
              </div>
              <div><label className="block text-label-md text-on-surface-variant mb-1">Period End</label>
                <input type="date" value={formData.period_end} onChange={(e) => setFormData(p => ({ ...p, period_end: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
              </div>
              <div><label className="block text-label-md text-on-surface-variant mb-1">Notes</label>
                <textarea value={formData.notes} onChange={(e) => setFormData(p => ({ ...p, notes: e.target.value }))} rows={3} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
              </div>
              <div className="flex gap-3">
                <button type="submit" disabled={saving} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">{saving ? '...' : 'Create'}</button>
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

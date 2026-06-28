import { useState, useEffect, useRef } from 'react'
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

export default function Loans() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortField, setSortField] = useState('-created_at')
  const [detailLoan, setDetailLoan] = useState(null)
  const [showApprove, setShowApprove] = useState(null)
  const [showDefault, setShowDefault] = useState(null)
  const [showAddGuarantor, setShowAddGuarantor] = useState(null)
  const [guarantorSearch, setGuarantorSearch] = useState('')
  const [guarantorResults, setGuarantorResults] = useState([])
  const [selectedGuarantor, setSelectedGuarantor] = useState(null)
  const [guarantorSearchOpen, setGuarantorSearchOpen] = useState(false)
  const guarantorRef = useRef(null)
  const { showToast } = useToast()

  const params = new URLSearchParams({ page, page_size: pageSize, ordering: sortField })
  if (statusFilter) params.set('status', statusFilter)

  const { data, loading, error, refetch } = useApi(`/api/loans/?${params}`)

  useEffect(() => {
    if (!guarantorSearch || guarantorSearch.length < 2) { setGuarantorResults([]); return }
    const timer = setTimeout(async () => {
      try {
        const res = await apiFetch(`/api/farmers/?search=${encodeURIComponent(guarantorSearch)}&page_size=10`)
        if (res.ok) { const d = await res.json(); setGuarantorResults(d.results || []); setGuarantorSearchOpen(true) }
      } catch { /* ignore */ }
    }, 300)
    return () => clearTimeout(timer)
  }, [guarantorSearch])

  useEffect(() => {
    const handler = (e) => { if (guarantorRef.current && !guarantorRef.current.contains(e.target)) setGuarantorSearchOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSort = (key) => setSortField(prev => prev === key ? `-${key}` : key)

  const handleApprove = async () => {
    if (!showApprove) return
    if (!showApprove.guarantors?.length) {
      showToast({ type: 'warning', message: 'Add at least one guarantor before approving.' })
      return
    }
    try {
      const res = await apiFetch(`/api/loans/${showApprove.id}/approve/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Approval failed') }
      showToast({ type: 'success', message: 'Loan approved.' })
      setShowApprove(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleDefault = async () => {
    if (!showDefault) return
    try {
      const res = await apiFetch(`/api/loans/${showDefault.id}/mark_defaulted/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to mark defaulted') }
      showToast({ type: 'success', message: 'Loan marked as defaulted.' })
      setShowDefault(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleAddGuarantor = async () => {
    if (!showAddGuarantor || !selectedGuarantor) return
    try {
      const res = await apiFetch(`/api/loans/${showAddGuarantor.id}/add_guarantor/`, { method: 'POST', body: JSON.stringify({ guarantor_id: selectedGuarantor.id }) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to add guarantor') }
      showToast({ type: 'success', message: 'Guarantor added.' })
      setShowAddGuarantor(null); setGuarantorSearch(''); setSelectedGuarantor(null); setGuarantorResults([]); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const items = data?.results || []
  const total = data?.count || 0

  const columns = [
    { key: 'farmer_name', label: 'Farmer', sortable: true, render: (v) => v || '-' },
    { key: 'amount', label: 'Amount', sortable: true, render: (v) => v ? `KES ${Number(v).toLocaleString()}` : '-' },
    { key: 'balance', label: 'Balance', sortable: true, render: (v) => v !== undefined && v !== null ? `KES ${Number(v).toLocaleString()}` : '-' },
    { key: 'interest_rate', label: 'Interest', sortable: true, render: (v) => v ? `${v}%` : '-' },
    { key: 'status', label: 'Status', sortable: true, render: (v) => <StatusBadge status={v?.toLowerCase()} label={v} /> },
    { key: 'guarantors', label: 'Guarantors', render: (v) => Array.isArray(v) ? v.length : 0 },
    { key: 'created_at', label: 'Created', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (_, row) => (
        <div className="flex gap-2">
          {row.status === 'PENDING' && (
            <>
              <button onClick={(e) => { e.stopPropagation(); setShowAddGuarantor(row) }} className="text-primary text-label-md hover:underline">+ Guarantor</button>
              <button onClick={(e) => { e.stopPropagation(); setShowApprove(row) }} className="text-success text-label-md hover:underline">Approve</button>
            </>
          )}
          {row.status === 'ACTIVE' && (
            <button onClick={(e) => { e.stopPropagation(); setShowDefault(row) }} className="text-error text-label-md hover:underline">Default</button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Loans</h2>
          <p className="text-sm text-on-surface-variant">{total} total</p>
        </div>
      </header>

      <div className="mb-4 flex items-center gap-4 flex-wrap">
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="ACTIVE">Active</option>
          <option value="COMPLETED">Completed</option>
          <option value="DEFAULTED">Defaulted</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {loading ? <TableSkeleton rows={10} cols={8} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={items}
            sortField={sortField.replace('-', '')}
            sortOrder={sortField.startsWith('-') ? 'desc' : 'asc'}
            onSort={handleSort}
            onRowClick={(row) => setDetailLoan(row)}
            emptyMessage="No loans found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailLoan} onClose={() => setDetailLoan(null)} title="Loan Details" width="max-w-xl">
        {detailLoan && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['farmer_name', 'amount', 'balance', 'interest_rate', 'status', 'guarantors', 'created_at', 'updated_at'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">
                  {f === 'guarantors' ? (Array.isArray(detailLoan[f]) ? detailLoan[f].length : detailLoan[f] ?? '-')
                    : f.includes('amount') || f === 'balance' ? `KES ${Number(detailLoan[f] || 0).toLocaleString()}`
                    : String(detailLoan[f] ?? '-')}
                </p></div>
              ))}
            </div>
            {Array.isArray(detailLoan.guarantors) && detailLoan.guarantors.length > 0 && (
              <div>
                <p className="text-label-md text-on-surface-variant mb-2">Guarantors</p>
                <div className="space-y-2">
                  {detailLoan.guarantors.map((g, i) => (
                    <div key={i} className="flex items-center gap-3 px-3 py-2 bg-surface-container rounded-lg">
                      <span className="material-symbols-outlined text-on-surface-variant text-[18px]">person</span>
                      <span className="text-body-md text-on-surface">{g.farmer_name || g.phone_number || g.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </SlideOutPanel>

      <SlideOutPanel open={!!showAddGuarantor} onClose={() => { setShowAddGuarantor(null); setGuarantorSearch(''); setSelectedGuarantor(null); setGuarantorResults([]) }} title="Add Guarantor" width="max-w-md">
        <div className="space-y-4" ref={guarantorRef}>
          <p className="text-body-md text-on-surface-variant">Search for a farmer to add as guarantor.</p>
          <div className="relative">
            <label className="block text-label-md text-on-surface-variant mb-1">Search Farmer</label>
            <input value={guarantorSearch} onChange={(e) => { setGuarantorSearch(e.target.value); setSelectedGuarantor(null) }} placeholder="Name or phone..." className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
            {selectedGuarantor && <p className="text-sm text-on-surface-variant mt-1">Selected: {selectedGuarantor.first_name} {selectedGuarantor.last_name} ({selectedGuarantor.phone_number})</p>}
            {guarantorSearchOpen && guarantorResults.length > 0 && (
              <div className="absolute z-10 mt-1 w-full border border-outline-variant rounded-lg bg-surface shadow-lg max-h-40 overflow-y-auto">
                {guarantorResults.map(f => (
                  <button key={f.id} type="button" onClick={() => { setSelectedGuarantor(f); setGuarantorSearch(`${f.first_name} ${f.last_name}`); setGuarantorSearchOpen(false) }} className="w-full text-left px-3 py-2 hover:bg-surface-container text-body-md">{f.first_name} {f.last_name} — {f.phone_number}</button>
                ))}
              </div>
            )}
          </div>
          <button onClick={handleAddGuarantor} disabled={!selectedGuarantor} className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold disabled:opacity-50">Add Guarantor</button>
        </div>
      </SlideOutPanel>

      <ConfirmModal
        open={!!showApprove}
        title="Approve Loan"
        message={`Approve loan for KES ${Number(showApprove?.amount || 0).toLocaleString()}?${!showApprove?.guarantors?.length ? ' Warning: No guarantors added yet.' : ''}`}
        confirmLabel="Approve"
        onConfirm={handleApprove}
        onCancel={() => setShowApprove(null)}
      />

      <ConfirmModal
        open={!!showDefault}
        title="Mark as Defaulted"
        message={`Mark loan for ${showDefault?.farmer_name || 'this farmer'} as defaulted? This will affect their credit score.`}
        confirmLabel="Mark Defaulted"
        destructive
        onConfirm={handleDefault}
        onCancel={() => setShowDefault(null)}
      />
    </div>
  )
}
import { useState, useCallback, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import ErrorState from '../../shared/components/ErrorState'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

const statusColors = {
  PENDING: 'badge-warning', APPROVED: 'badge-info', DISBURSED: 'badge-success',
  COMPLETED: 'badge-primary', DEFAULTED: 'badge-error', WRITTEN_OFF: 'badge-error',
}

function LoanDetailPanel({ loan, onClose, onAction }) {
  const { showToast } = useToast()
  const [addingGuarantor, setAddingGuarantor] = useState(false)
  const [guarantorSearch, setGuarantorSearch] = useState('')
  const [guarantorResults, setGuarantorResults] = useState([])
  const [selectedGuarantor, setSelectedGuarantor] = useState(null)
  const [guarantorSearchOpen, setGuarantorSearchOpen] = useState(false)
  const guarantorRef = useRef(null)
  const [actionLoading, setActionLoading] = useState(null)

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

  const handleAction = async (action) => {
    setActionLoading(action)
    try {
      const res = await apiFetch(`/api/loans/${loan.id}/${action}/`, { method: 'POST' })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || `Failed to ${action}`) }
      onAction()
      showToast({ type: 'success', message: `Loan ${action.replace('_', ' ')}d.` })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setActionLoading(null) }
  }

  const handleAddGuarantor = async (e) => {
    e.preventDefault()
    if (!selectedGuarantor) return
    setActionLoading('guarantor')
    try {
      const res = await apiFetch(`/api/loans/${loan.id}/add_guarantor/`, {
        method: 'POST',
        body: JSON.stringify({ guarantor_id: selectedGuarantor.id }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to add guarantor') }
      showToast({ type: 'success', message: 'Guarantor added.' })
      setAddingGuarantor(false)
      setGuarantorSearch('')
      setSelectedGuarantor(null)
      setGuarantorResults([])
      onAction()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setActionLoading(null) }
  }

  const canDisburse = loan.status === 'APPROVED' && (loan.guarantors?.length || 0) >= 1

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-headline-sm text-headline-sm text-on-surface">Loan #{loan.id}</h3>
          <p className="text-body-md text-on-surface-variant">{loan.farmer_name || loan.farmer?.full_name || `Farmer #${loan.farmer}`}</p>
        </div>
        <button onClick={onClose} aria-label="Close panel" className="text-on-surface-variant hover:text-on-surface"><span className="material-symbols-outlined" aria-hidden="true">close</span></button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div><p className="text-label-md text-on-surface-variant">Amount</p><p className="text-body-md font-bold">{formatKes(loan.amount)}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Balance</p><p className="text-body-md font-bold">{formatKes(loan.balance)}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Status</p><span className={`badge ${statusColors[loan.status] || 'badge-default'}`}>{loan.status}</span></div>
        <div><p className="text-label-md text-on-surface-variant">Interest Rate</p><p className="text-body-md">{loan.interest_rate ? `${loan.interest_rate}%` : '-'}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Created</p><p className="text-body-md">{loan.created_at ? new Date(loan.created_at).toLocaleDateString() : '-'}</p></div>
        <div><p className="text-label-md text-on-surface-variant">Due Date</p><p className="text-body-md">{loan.due_date ? new Date(loan.due_date).toLocaleDateString() : '-'}</p></div>
      </div>

      <div>
        <p className="text-label-md text-on-surface-variant mb-2">Purpose</p>
        <p className="text-body-md">{loan.purpose || '-'}</p>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <p className="text-label-md text-on-surface-variant font-bold">Guarantors ({loan.guarantors?.length || 0})</p>
          <button
            onClick={() => setAddingGuarantor(true)}
            disabled={actionLoading === 'guarantor'}
            className="text-primary hover:text-primary/80 disabled:opacity-50"
            aria-label="Add a guarantor to this loan"
            title="Add Guarantor"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">person_add</span>
          </button>
        </div>
        {loan.guarantors?.length > 0 ? (
          <div className="space-y-2">
            {loan.guarantors.map((g, i) => (
              <div key={i} className="flex justify-between bg-surface-container rounded-lg px-4 py-2">
                <span className="text-body-md">{g.full_name || g.name || `Guarantor #${i + 1}`}</span>
                <span className="text-body-md text-on-surface-variant">{g.phone_number}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-body-md text-on-surface-variant italic">No guarantors yet</p>
        )}
      </div>

      {addingGuarantor && (
        <form onSubmit={handleAddGuarantor} className="bg-surface-container rounded-xl p-4 space-y-3" ref={guarantorRef}>
          <div>
            <label htmlFor="guarantor-search" className="block text-label-md text-on-surface-variant mb-1">Search for Guarantor</label>
            <div
              role="combobox"
              aria-expanded={guarantorSearchOpen && guarantorResults.length > 0}
              aria-haspopup="listbox"
              aria-owns="guarantor-listbox"
            >
              <input
                id="guarantor-search"
                type="text"
                value={guarantorSearch}
                onChange={(e) => { setGuarantorSearch(e.target.value); setSelectedGuarantor(null) }}
                placeholder="Search farmer by name or phone..."
                required={!selectedGuarantor}
                className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface"
                aria-autocomplete="list"
                aria-controls="guarantor-listbox"
                aria-activedescendant={selectedGuarantor ? `guarantor-option-${selectedGuarantor.id}` : undefined}
              />
            </div>
            {selectedGuarantor && (
              <p className="text-sm text-on-surface-variant mt-1" role="status">
                Selected: {selectedGuarantor.first_name} {selectedGuarantor.last_name} ({selectedGuarantor.phone_number})
              </p>
            )}
            {guarantorSearchOpen && guarantorResults.length > 0 && (
              <ul
                role="listbox"
                id="guarantor-listbox"
                aria-label="Guarantor search results"
                className="absolute z-10 mt-1 w-full border border-outline-variant rounded-lg bg-surface shadow-lg max-h-40 overflow-y-auto"
              >
                {guarantorResults.map(f => (
                  <li
                    key={f.id}
                    id={`guarantor-option-${f.id}`}
                    role="option"
                    aria-selected={selectedGuarantor?.id === f.id}
                    onClick={() => { setSelectedGuarantor(f); setGuarantorSearch(`${f.first_name} ${f.last_name}`); setGuarantorSearchOpen(false) }}
                    className="w-full text-left px-3 py-2 hover:bg-surface-container text-body-md cursor-pointer"
                  >
                    {f.first_name} {f.last_name} — {f.phone_number}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={!selectedGuarantor || actionLoading === 'guarantor'}
              className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50"
              aria-label={actionLoading === 'guarantor' ? 'Adding guarantor...' : 'Add selected guarantor to this loan'}
            >
              {actionLoading === 'guarantor' ? 'Adding...' : 'Add'}
            </button>
            <button
              type="button"
              onClick={() => { setAddingGuarantor(false); setGuarantorSearch(''); setSelectedGuarantor(null); setGuarantorResults([]) }}
              className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold"
              aria-label="Cancel and close guarantor search"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="pt-4 border-t border-outline-variant space-y-3">
        {loan.status === 'APPROVED' && (
          <button
            onClick={() => handleAction('disburse')}
            disabled={!canDisburse || actionLoading}
            className={`w-full py-2 rounded-lg text-label-md font-bold transition-colors inline-flex items-center justify-center gap-2 ${canDisburse ? 'bg-success-container text-on-success-container hover:bg-success-container/80' : 'bg-surface-container text-on-surface-variant cursor-not-allowed'}`}
            aria-label={actionLoading === 'disburse' ? 'Disbursing loan...' : canDisburse ? 'Disburse this loan' : 'Add a guarantor before disbursing'}
          >
            {actionLoading === 'disburse' ? '...' : <><span className="material-symbols-outlined text-[18px]" aria-hidden="true">payments</span> {canDisburse ? 'Disburse Loan' : 'Add Guarantor First'}</>}
          </button>
        )}
        {loan.status === 'DISBURSED' && (
          <button
            onClick={() => handleAction('mark_completed')}
            disabled={actionLoading}
            className="w-full py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50 inline-flex items-center justify-center gap-2"
            aria-label={actionLoading === 'mark_completed' ? 'Marking loan as completed...' : 'Mark this loan as completed'}
          >
            {actionLoading === 'mark_completed' ? '...' : <><span className="material-symbols-outlined text-[18px]" aria-hidden="true">check_circle</span> Mark Completed</>}
          </button>
        )}
        {(loan.status === 'APPROVED' || loan.status === 'DISBURSED') && (
          <button
            onClick={() => handleAction('mark_defaulted')}
            disabled={actionLoading}
            className="w-full py-2 bg-error-container text-on-error-container rounded-lg text-label-md font-bold disabled:opacity-50 inline-flex items-center justify-center gap-2"
            aria-label={actionLoading === 'mark_defaulted' ? 'Marking loan as defaulted...' : 'Mark this loan as defaulted'}
          >
            {actionLoading === 'mark_defaulted' ? '...' : <><span className="material-symbols-outlined text-[18px]" aria-hidden="true">block</span> Mark Defaulted</>}
          </button>
        )}
      </div>
    </div>
  )
}

export default function AccountantLoans() {
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') || ''
  const selectedId = searchParams.get('selected')
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({ farmer: '', amount_principal: '', interest_rate: '10', number_of_installments: '1', notes: '' })
  const [saving, setSaving] = useState(false)

  const queryParams = new URLSearchParams({ page, page_size: pageSize })
  if (search) queryParams.set('search', search)
  if (statusFilter) queryParams.set('status', statusFilter)

  const { data, loading, error, refetch } = useApi(`/api/loans/?${queryParams}`)
  const { data: farmers } = useApi('/api/farmers/?page=1&page_size=100')

  const loans = data?.results || data || []
  const totalCount = data?.count || loans.length

  const selectedLoan = selectedId ? loans.find((l) => String(l.id) === selectedId) || data?.results?.find((l) => String(l.id) === selectedId) : null

  const handleSearch = useCallback((e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const q = fd.get('search')
    setSearchParams(q ? { search: q } : {})
    setPage(1)
  }, [setSearchParams])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch('/api/loans/', { method: 'POST', body: JSON.stringify(formData) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create loan') }
      showToast({ type: 'success', message: 'Loan created.' })
      setShowForm(false)
      setFormData({ farmer: '', amount_principal: '', interest_rate: '10', number_of_installments: '1', notes: '' })
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  const statuses = ['', 'PENDING', 'APPROVED', 'DISBURSED', 'COMPLETED', 'DEFAULTED', 'WRITTEN_OFF']

  const columns = [
    { key: 'id', label: 'ID', render: (v, row) => row.id },
    { key: 'farmer', label: 'Farmer', render: (v, l) => l.farmer_name || l.farmer?.full_name || `#${l.farmer}` },
    { key: 'amount', label: 'Amount', render: (v, l) => formatKes(l.amount) },
    { key: 'balance', label: 'Balance', render: (v, l) => formatKes(l.balance) },
    { key: 'status', label: 'Status', render: (v, l) => <span className={`badge ${statusColors[l.status] || 'badge-default'}`}>{l.status}</span> },
    { key: 'due_date', label: 'Due', render: (v, l) => l.due_date ? new Date(l.due_date).toLocaleDateString() : '-' },
    { key: 'created_at', label: 'Created', render: (v, l) => l.created_at ? new Date(l.created_at).toLocaleDateString() : '-' },
  ]

  return (
    <div>
      <header className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Loans</h2>
          <p className="text-on-surface-variant font-body-md">{totalCount} loans</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors"
          aria-label="Create a new loan"
        >
          + New Loan
        </button>
      </header>

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-1 min-w-0">
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <form onSubmit={handleSearch} className="flex-1 flex gap-2">
              <label htmlFor="loan-search" className="sr-only">Search loans by farmer name</label>
              <input
                id="loan-search"
                name="search"
                defaultValue={search}
                placeholder="Search farmers..."
                className="flex-1 px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
              />
              <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold" aria-label="Submit search">Search</button>
            </form>
            <label htmlFor="loan-status-filter" className="sr-only">Filter loans by status</label>
            <select
              id="loan-status-filter"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
            >
              {statuses.map((s) => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
            </select>
          </div>

          {loading ? <TableSkeleton rows={10} cols={7} /> : error ? <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} /> : (
            <>
              <DataTable
                columns={columns}
                data={loans}
                onRowClick={(l) => setSearchParams({ ...Object.fromEntries(searchParams.entries()), selected: String(l.id) })}
              />
              <Pagination page={page} pageSize={pageSize} total={totalCount} onPageChange={setPage} onPageSizeChange={setPageSize} />
            </>
          )}
        </div>

        {selectedLoan && (
          <div className="w-full lg:w-[400px] shrink-0">
            <LoanDetailPanel
              loan={selectedLoan}
              onClose={() => setSearchParams({ ...Object.fromEntries(searchParams.entries()), selected: undefined })}
              onAction={refetch}
            />
          </div>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setShowForm(false)} role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-loan-title"
            className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] max-h-[90vh] overflow-y-auto relative"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="create-loan-title" className="font-headline-sm text-headline-sm mb-4">Create Loan</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label htmlFor="loan-farmer" className="block text-label-md text-on-surface-variant mb-1">Farmer</label>
                <select
                  id="loan-farmer"
                  value={formData.farmer}
                  onChange={(e) => setFormData(p => ({ ...p, farmer: e.target.value }))}
                  required
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
                >
                  <option value="">Select farmer...</option>
                  {farmers?.results?.map((f) => <option key={f.id} value={f.id}>{f.full_name} ({f.phone_number})</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="loan-amount" className="block text-label-md text-on-surface-variant mb-1">Amount Principal (KES)</label>
                <input
                  id="loan-amount"
                  type="number" min="1"
                  value={formData.amount_principal}
                  onChange={(e) => setFormData(p => ({ ...p, amount_principal: e.target.value }))}
                  required
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
                />
              </div>
              <div>
                <label htmlFor="loan-interest" className="block text-label-md text-on-surface-variant mb-1">Interest Rate (%)</label>
                <input
                  id="loan-interest"
                  type="number" step="0.1" min="0"
                  value={formData.interest_rate}
                  onChange={(e) => setFormData(p => ({ ...p, interest_rate: e.target.value }))}
                  required
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
                />
              </div>
              <div>
                <label htmlFor="loan-installments" className="block text-label-md text-on-surface-variant mb-1">Number of Installments</label>
                <input
                  id="loan-installments"
                  type="number" min="1"
                  value={formData.number_of_installments}
                  onChange={(e) => setFormData(p => ({ ...p, number_of_installments: e.target.value }))}
                  required
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
                />
              </div>
              <div>
                <label htmlFor="loan-notes" className="block text-label-md text-on-surface-variant mb-1">Notes</label>
                <textarea
                  id="loan-notes"
                  value={formData.notes}
                  onChange={(e) => setFormData(p => ({ ...p, notes: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50"
                  aria-label={saving ? 'Creating loan...' : 'Create this loan'}
                >
                  {saving ? '...' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold"
                  aria-label="Cancel and close"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

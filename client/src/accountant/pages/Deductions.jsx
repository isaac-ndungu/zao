import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import ErrorState from '../../shared/components/ErrorState'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

const deductionTypeColors = { LOAN: 'badge-info', ADVANCE: 'badge-warning', FARM_INPUT: 'badge-success', PENALTY: 'badge-error', OTHER: 'badge-default' }

export default function AccountantDeductions() {
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'deductions'
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [typeFilter, setTypeFilter] = useState('')
  const [showCreditForm, setShowCreditForm] = useState(false)

  const qp = new URLSearchParams({ page, page_size: pageSize })
  if (typeFilter) qp.set('type', typeFilter)

  const { data: dedData, loading: dedLoading, error: dedError, refetch: dedRefetch } = useApi(tab === 'deductions' ? `/api/deductions/?${qp}` : null)
  const { data: creditsData, loading: creditsLoading, error: creditsError, refetch: creditsRefetch } = useApi(tab === 'credits' ? `/api/deductions/farm-input-credits/?${qp}` : null)
  const { data: farmers } = useApi('/api/farmers/?page=1&page_size=100')
  const { data: stats } = useApi(tab === 'deductions' ? '/api/analytics/financial/' : null)

  const deductions = dedData?.results || dedData || []
  const credits = creditsData?.results || creditsData || []
  const totalCount = tab === 'deductions' ? (dedData?.count || deductions.length) : (creditsData?.count || credits.length)

  const financial = stats?.data || stats || {}
  const deductionStats = financial.deductions_breakdown || {}

  const handleCreateCredit = async (prev, formData) => {
    const data = formDataToObject(formData)
    try {
      const res = await apiFetch('/api/deductions/farm-input-credits/', { method: 'POST', body: JSON.stringify(data) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create credit') }
      showToast({ type: 'success', message: 'Farm input credit created.' })
      creditsRefetch()
      setShowCreditForm(false)
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const { formAction: createCreditAction } = useFormAction(handleCreateCredit, {})

  const dedColumns = [
    { key: 'id', label: 'ID', render: (v, row) => row.id },
    { key: 'farmer', label: 'Farmer', render: (v, d) => d.farmer_name || d.farmer?.full_name || `#${d.farmer}` },
    { key: 'deduction_type', label: 'Type', render: (v, d) => <span className={`badge ${deductionTypeColors[d.deduction_type] || 'badge-default'}`}>{d.deduction_type}</span> },
    { key: 'amount', label: 'Amount', render: (v, d) => formatKes(d.amount) },
    { key: 'description', label: 'Description', render: (v, d) => d.description || '-' },
    { key: 'created_at', label: 'Date', render: (v, d) => d.created_at ? new Date(d.created_at).toLocaleDateString() : '-' },
  ]

  const creditColumns = [
    { key: 'id', label: 'ID', render: (v, row) => row.id },
    { key: 'farmer', label: 'Farmer', render: (v, c) => c.farmer_name || c.farmer?.full_name || `#${c.farmer}` },
    { key: 'amount', label: 'Amount', render: (v, c) => formatKes(c.amount) },
    { key: 'description', label: 'Description', render: (v, c) => c.description || '-' },
    { key: 'created_at', label: 'Date', render: (v, c) => c.created_at ? new Date(c.created_at).toLocaleDateString() : '-' },
  ]

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Deductions & Credits</h2>
        <p className="text-on-surface-variant font-body-md">
          {tab === 'deductions'
            ? `${totalCount} deductions recorded`
            : `${totalCount} farm input credits`}
        </p>
      </header>

      <div className="flex gap-2 mb-6 border-b border-outline-variant pb-2">
        <button onClick={() => { setSearchParams({ tab: 'deductions' }); setPage(1) }} className={`px-4 py-2 text-label-md font-bold transition-colors ${tab === 'deductions' ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-on-surface'}`}>Deductions</button>
        <button onClick={() => { setSearchParams({ tab: 'credits' }); setPage(1) }} className={`px-4 py-2 text-label-md font-bold transition-colors ${tab === 'credits' ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-on-surface'}`}>Farm Input Credits</button>
      </div>

      {tab === 'deductions' && (
        <>
          {Object.keys(deductionStats).length > 0 && (
            <div className="flex flex-wrap gap-3 mb-6">
              {Object.entries(deductionStats).map(([k, v]) => (
                <div key={k} className="bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 text-center min-w-[120px]">
                  <p className="font-label-md text-on-surface-variant">{k.replace(/_/g, ' ')}</p>
                  <p className="font-headline-sm text-headline-sm text-on-surface">{formatKes(v)}</p>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-3 mb-4">
            <label htmlFor="deduction-type-filter" className="sr-only">Filter by type</label>
            <select id="deduction-type-filter" value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
              <option value="">All Types</option>
              {Object.keys(deductionTypeColors).map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
            </select>
          </div>

          {dedLoading ? <TableSkeleton rows={10} cols={6} /> : dedError ? <ErrorState message={dedError} action={{ label: 'Retry', onClick: dedRefetch }} /> : (
            <>
              <DataTable columns={dedColumns} data={deductions} />
              <Pagination page={page} pageSize={pageSize} total={totalCount} onPageChange={setPage} onPageSizeChange={setPageSize} />
            </>
          )}
        </>
      )}

      {tab === 'credits' && (
        <>
          <div className="mb-4">
            <button onClick={() => setShowCreditForm(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">+ New Farm Input Credit</button>
          </div>

          {creditsLoading ? <TableSkeleton rows={10} cols={5} /> : creditsError ? <ErrorState message={creditsError} action={{ label: 'Retry', onClick: creditsRefetch }} /> : (
            <>
              <DataTable columns={creditColumns} data={credits} />
              <Pagination page={page} pageSize={pageSize} total={totalCount} onPageChange={setPage} onPageSizeChange={setPageSize} />
            </>
          )}

          {showCreditForm && (
            <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center cursor-pointer" onClick={() => setShowCreditForm(false)}>
              <div className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] relative" onClick={(e) => e.stopPropagation()}>
                <h3 className="font-headline-sm text-headline-sm mb-4">New Farm Input Credit</h3>
                <form action={createCreditAction} className="space-y-4">
                  <div><label htmlFor="credit-farmer" className="block text-label-md text-on-surface-variant mb-1">Farmer</label>
                    <select id="credit-farmer" name="farmer" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
                      <option value="">Select farmer...</option>
                      {farmers?.results?.map((f) => <option key={f.id} value={f.id}>{f.full_name} ({f.phone_number})</option>)}
                    </select>
                  </div>
                  <div><label htmlFor="credit-amount" className="block text-label-md text-on-surface-variant mb-1">Amount (KES)</label>
                    <input id="credit-amount" name="amount" type="number" min="1" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
                  </div>
                  <div><label htmlFor="credit-description" className="block text-label-md text-on-surface-variant mb-1">Description</label>
                    <textarea id="credit-description" name="item_description" rows={3} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" placeholder="e.g. Fertilizer, Seeds..." />
                  </div>
                  <div className="flex gap-3">
                    <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Create</SubmitButton>
                    <button type="button" onClick={() => setShowCreditForm(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

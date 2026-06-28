import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import DataTable from '../../admin/components/common/DataTable'
import ErrorState from '../../shared/components/ErrorState'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

const deductionTypeColors = { LOAN: 'badge-info', ADVANCE: 'badge-warning', FARM_INPUT: 'badge-success', PENALTY: 'badge-error', OTHER: 'badge-default' }

export default function AccountantDeductions() {
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'deductions'
  const [page, setPage] = useState(1)
  const [typeFilter, setTypeFilter] = useState('')
  const [showCreditForm, setShowCreditForm] = useState(false)
  const [creditForm, setCreditForm] = useState({ farmer: '', item_description: '', amount: '' })
  const [saving, setSaving] = useState(false)

  const qp = new URLSearchParams({ page, page_size: '20' })
  if (typeFilter) qp.set('type', typeFilter)

  const { data: dedData, loading: dedLoading, error: dedError, refetch: dedRefetch } = useApi(tab === 'deductions' ? `/api/deductions/?${qp}` : null)
  const { data: creditsData, loading: creditsLoading, error: creditsError, refetch: creditsRefetch } = useApi(tab === 'credits' ? `/api/deductions/farm-input-credits/?${qp}` : null)
  const { data: farmers } = useApi('/api/farmers/?page=1&page_size=100')
  const { data: stats } = useApi('/api/analytics/financial/')

  const deductions = dedData?.results || dedData || []
  const credits = creditsData?.results || creditsData || []
  const totalCount = tab === 'deductions' ? (dedData?.count || deductions.length) : (creditsData?.count || credits.length)

  const financial = stats?.data || stats || {}
  const deductionStats = financial.deductions_breakdown || {}

  const handleCreateCredit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch('/api/deductions/farm-input-credits/', { method: 'POST', body: JSON.stringify(creditForm) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create credit') }
      showToast({ type: 'success', message: 'Farm input credit created.' })
      setShowCreditForm(false)
      setCreditForm({ farmer: '', item_description: '', amount: '' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  const dedColumns = [
    { header: 'ID', accessor: 'id' },
    { header: 'Farmer', accessor: (d) => d.farmer_name || d.farmer?.full_name || `#${d.farmer}` },
    { header: 'Type', accessor: (d) => <span className={`badge ${deductionTypeColors[d.deduction_type] || 'badge-default'}`}>{d.deduction_type}</span> },
    { header: 'Amount', accessor: (d) => formatKes(d.amount) },
    { header: 'Description', accessor: (d) => d.description || '-' },
    { header: 'Date', accessor: (d) => d.created_at ? new Date(d.created_at).toLocaleDateString() : '-' },
  ]

  const creditColumns = [
    { header: 'ID', accessor: 'id' },
    { header: 'Farmer', accessor: (c) => c.farmer_name || c.farmer?.full_name || `#${c.farmer}` },
    { header: 'Amount', accessor: (c) => formatKes(c.amount) },
    { header: 'Description', accessor: (c) => c.description || '-' },
    { header: 'Date', accessor: (c) => c.created_at ? new Date(c.created_at).toLocaleDateString() : '-' },
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
            <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
              <option value="">All Types</option>
              {Object.keys(deductionTypeColors).map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
            </select>
          </div>

          {dedLoading ? <TableSkeleton rows={10} cols={6} /> : dedError ? <ErrorState message={dedError} action={{ label: 'Retry', onClick: dedRefetch }} /> : (
            <DataTable columns={dedColumns} data={deductions} page={page} totalPages={Math.ceil(totalCount / 20)} onPageChange={setPage} />
          )}
        </>
      )}

      {tab === 'credits' && (
        <>
          <div className="mb-4">
            <button onClick={() => setShowCreditForm(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">+ New Farm Input Credit</button>
          </div>

          {creditsLoading ? <TableSkeleton rows={10} cols={5} /> : creditsError ? <ErrorState message={creditsError} action={{ label: 'Retry', onClick: creditsRefetch }} /> : (
            <DataTable columns={creditColumns} data={credits} page={page} totalPages={Math.ceil(totalCount / 20)} onPageChange={setPage} />
          )}

          {showCreditForm && (
            <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setShowCreditForm(false)}>
              <div className="bg-surface rounded-xl p-6 max-w-lg w-[90vw] relative" onClick={(e) => e.stopPropagation()}>
                <h3 className="font-headline-sm text-headline-sm mb-4">New Farm Input Credit</h3>
                <form onSubmit={handleCreateCredit} className="space-y-4">
                  <div><label className="block text-label-md text-on-surface-variant mb-1">Farmer</label>
                    <select value={creditForm.farmer} onChange={(e) => setCreditForm(p => ({ ...p, farmer: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
                      <option value="">Select farmer...</option>
                      {farmers?.results?.map((f) => <option key={f.id} value={f.id}>{f.full_name} ({f.phone_number})</option>)}
                    </select>
                  </div>
                  <div><label className="block text-label-md text-on-surface-variant mb-1">Amount (KES)</label>
                    <input type="number" min="1" value={creditForm.amount} onChange={(e) => setCreditForm(p => ({ ...p, amount: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
                  </div>
                  <div><label className="block text-label-md text-on-surface-variant mb-1">Description</label>
                    <textarea value={creditForm.item_description} onChange={(e) => setCreditForm(p => ({ ...p, item_description: e.target.value }))} rows={3} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" placeholder="e.g. Fertilizer, Seeds..." />
                  </div>
                  <div className="flex gap-3">
                    <button type="submit" disabled={saving} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">{saving ? '...' : 'Create'}</button>
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

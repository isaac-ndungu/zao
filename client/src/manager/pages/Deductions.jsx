import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ErrorState from '../../shared/components/ErrorState'

export default function Deductions() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [typeFilter, setTypeFilter] = useState('')
  const [detailItem, setDetailItem] = useState(null)

  const params = new URLSearchParams({ page, page_size: pageSize })
  if (typeFilter) params.set('type', typeFilter)

  const { data, loading, error, refetch } = useApi(`/api/deductions/?${params}`)

  const items = data?.results || []
  const total = data?.count || 0

  const columns = [
    { key: 'farmer_name', label: 'Farmer', sortable: true, render: (row) => row.farmer_name || '-' },
    { key: 'deduction_type', label: 'Type', sortable: true },
    { key: 'amount', label: 'Amount', sortable: true, render: (row) => row.amount ? `KES ${Number(row.amount).toLocaleString()}` : '-' },
    { key: 'cycle_name', label: 'Cycle', sortable: true, render: (row) => row.cycle_name || '-' },
    { key: 'status', label: 'Status', sortable: true, render: (row) => <StatusBadge status={row.status?.toLowerCase()} label={row.status} /> },
    { key: 'loan_id', label: 'Related Loan', render: (row) => row.loan_id ? (
      <button onClick={(e) => { e.stopPropagation(); navigate(`/manager/loans`) }} className="text-primary text-label-md hover:underline underline">
        {typeof row.loan_id === 'string' ? row.loan_id.slice(0, 8) : row.loan_id}
      </button>
    ) : '-' },
    { key: 'created_at', label: 'Date', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
  ]

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h2 className="text-3xl font-bold text-on-surface mb-1">Deductions</h2>
        <p className="text-sm text-on-surface-variant">{total} total</p>
      </header>

      <div className="mb-4">
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Types</option>
          <option value="LOAN_REPAYMENT">Loan Repayment</option>
          <option value="FARM_INPUT">Farm Input</option>
          <option value="FEES">Fees</option>
          <option value="OTHER">Other</option>
        </select>
      </div>

      {loading ? <TableSkeleton rows={10} cols={7} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={items}
            onRowClick={(row) => setDetailItem(row)}
            emptyMessage="No deductions found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailItem} onClose={() => setDetailItem(null)} title="Deduction Details" width="max-w-xl">
        {detailItem && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['farmer_name', 'deduction_type', 'amount', 'cycle_name', 'status', 'loan_id', 'description', 'created_at'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">
                  {f === 'loan_id' && detailItem[f]
                    ? <button onClick={() => navigate('/manager/loans')} className="text-primary hover:underline">{detailItem[f]}</button>
                    : f === 'amount' ? `KES ${Number(detailItem[f] || 0).toLocaleString()}`
                    : String(detailItem[f] ?? '-')}
                </p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>
    </div>
  )
}
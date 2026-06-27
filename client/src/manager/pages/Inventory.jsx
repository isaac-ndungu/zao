import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import KpiCard from '../../admin/components/common/KpiCard'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ErrorState from '../../shared/components/ErrorState'

export default function Inventory() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [productFilter, setProductFilter] = useState('')
  const [detailItem, setDetailItem] = useState(null)
  const [showAlerts, setShowAlerts] = useState(false)

  const params = new URLSearchParams({ page, page_size: pageSize })
  if (productFilter) params.set('product_type', productFilter)

  const { data, loading, error, refetch } = useApi(`/api/inventory/?${params}`)
  const { data: summary, loading: summaryLoading } = useApi('/api/inventory/summary/')
  const { data: alerts } = useApi('/api/inventory/alerts/')

  const items = data?.results || []
  const total = data?.count || 0
  const alertList = alerts?.results || alerts || []

  const columns = [
    { key: 'batch_id', label: 'Batch ID', sortable: true },
    { key: 'product_type', label: 'Product', sortable: true },
    { key: 'grade', label: 'Grade', sortable: true, render: (v) => v || '-' },
    { key: 'unit', label: 'Unit', render: (v) => v || '-' },
    { key: 'quantity_in', label: 'Qty In', sortable: true, render: (v) => v ?? '-' },
    { key: 'quantity_out', label: 'Qty Out', sortable: true, render: (v) => v ?? '-' },
    { key: 'running_balance', label: 'Balance', sortable: true, render: (v) => v !== undefined && v !== null ? v : '-' },
    { key: 'is_sold', label: 'Status', render: (v) => <StatusBadge status={v ? 'sold' : 'available'} label={v ? 'Sold' : 'Available'} /> },
    { key: 'created_at', label: 'Created', sortable: true, render: (v) => v ? new Date(v).toLocaleDateString() : '-' },
  ]

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Inventory</h2>
          <p className="text-sm text-on-surface-variant">{total} batches</p>
        </div>
        <button onClick={() => setShowAlerts(!showAlerts)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">warning</span>
          Alerts {alertList.length > 0 && <span className="ml-1 bg-error text-on-error text-[10px] font-bold px-1.5 py-0.5 rounded-full">{alertList.length}</span>}
        </button>
      </header>

      {!summaryLoading && summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <KpiCard icon="inventory_2" label="Total Batches" value={String(summary.total_batches || total)} />
          <KpiCard icon="warehouse" label="Available" value={String(summary.available_batches || items.filter(i => !i.is_sold).length)} />
          <KpiCard icon="check_circle" label="Sold Out" value={String(summary.sold_batches || items.filter(i => i.is_sold).length)} />
          <KpiCard icon="trending_up" label="Total Qty In" value={summary.total_quantity_in ? `${Number(summary.total_quantity_in).toLocaleString()} kg` : '-'} />
        </div>
      )}

      {showAlerts && alertList.length > 0 && (
        <div className="mb-6 bg-warning-container border border-warning rounded-xl p-4">
          <h3 className="font-headline-sm text-headline-sm text-on-warning-container mb-3">Inventory Alerts</h3>
          <div className="space-y-2">
            {alertList.map((alert, i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-2 bg-surface-container-lowest rounded-lg">
                <span className="material-symbols-outlined text-warning">info</span>
                <span className="text-body-md text-on-surface">{alert.message || alert}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4">
        <select value={productFilter} onChange={(e) => { setProductFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Products</option>
          <option value="MILK">Milk</option>
          <option value="COFFEE_CHERRIES">Coffee Cherries</option>
          <option value="HONEY">Honey</option>
          <option value="OTHER">Other</option>
        </select>
      </div>

      {loading ? <TableSkeleton rows={10} cols={9} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={items}
            onRowClick={(row) => setDetailItem(row)}
            emptyMessage="No inventory found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailItem} onClose={() => setDetailItem(null)} title="Batch Details" width="max-w-xl">
        {detailItem && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['batch_id', 'product_type', 'grade', 'unit', 'quantity_in', 'quantity_out', 'running_balance', 'is_sold', 'created_at'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">
                  {f === 'is_sold' ? (detailItem[f] ? 'Sold' : 'Available') : String(detailItem[f] ?? '-')}
                </p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>
    </div>
  )
}
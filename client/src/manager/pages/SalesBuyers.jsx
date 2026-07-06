import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
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

export default function SalesBuyers() {
  const [tab, setTab] = useState('sales')

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h2 className="text-3xl font-bold text-on-surface mb-1">Sales & Buyers</h2>
        <p className="text-sm text-on-surface-variant">Manage sales and buyer records</p>
      </header>

      <div className="flex gap-1 mb-6 bg-surface-container rounded-lg p-1 w-fit">
        {['sales', 'buyers'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-label-md font-bold transition-colors capitalize ${tab === t ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'sales' ? <SalesSection /> : <BuyersSection />}
    </div>
  )
}

function SalesSection() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortField, setSortField] = useState('-sale_date')
  const [detailSale, setDetailSale] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showDelete, setShowDelete] = useState(null)
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')

  const params = new URLSearchParams({ page, page_size: pageSize, ordering: sortField })
  if (statusFilter) params.set('status', statusFilter)

  const { data, loading, error, refetch } = useApi(`/api/sales/?${params}`)

  const items = data?.results || []

  useEffect(() => {
    if (selectedId && items.length > 0) {
      const found = items.find(i => String(i.id) === String(selectedId))
      if (found && !detailSale) {
        setDetailSale(found)
      }
    }
  }, [selectedId, items])

  const handleSort = (key) => setSortField(prev => prev === key ? `-${key}` : key)

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/sales/${showDelete.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Sale deleted.' })
      setShowDelete(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const columns = [
    { key: 'invoice_number', label: 'Invoice', sortable: true, render: (row) => row.invoice_number || '-' },
    { key: 'buyer_name', label: 'Buyer', sortable: true },
    { key: 'product_type', label: 'Product', sortable: true },
    { key: 'quantity', label: 'Qty', sortable: true, render: (row) => row.quantity ?? '-' },
    { key: 'unit', label: 'Unit', render: (row) => row.unit || '-' },
    { key: 'price_per_unit', label: 'Price/Unit', sortable: true, render: (row) => row.price_per_unit ? `KES ${row.price_per_unit}` : '-' },
    { key: 'total_amount', label: 'Total', sortable: true, render: (row) => row.total_amount ? `KES ${Number(row.total_amount).toLocaleString()}` : '-' },
    { key: 'status', label: 'Status', sortable: true, render: (row) => <StatusBadge status={row.status?.toLowerCase()} label={row.status} /> },
    { key: 'sale_date', label: 'Date', sortable: true, render: (row) => row.sale_date ? new Date(row.sale_date).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error hover:text-error/80" aria-label={`Delete sale ${row.invoice_number || ''}`}><span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span></button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="mb-4 flex items-center justify-between flex-wrap gap-4">
        <div className="flex gap-2">
          <label htmlFor="sales-status-filter" className="sr-only">Filter by status</label>
          <select id="sales-status-filter" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">add</span>Record Sale
        </button>
      </div>

      {loading ? <TableSkeleton rows={10} cols={10} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={data?.results || []}
            sortField={sortField.replace('-', '')}
            sortOrder={sortField.startsWith('-') ? 'desc' : 'asc'}
            onSort={handleSort}
            onRowClick={(row) => setDetailSale(row)}
            emptyMessage="No sales found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailSale} onClose={() => { setDetailSale(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Sale Details" width="max-w-xl">
        {detailSale && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['buyer_name', 'invoice_number', 'product_type', 'grade_letter', 'quantity', 'unit', 'price_per_unit', 'total_amount', 'status', 'sale_date', 'notes'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">
                  {f === 'total_amount' || f === 'price_per_unit' ? `KES ${Number(detailSale[f] || 0).toLocaleString()}`
                    : String(detailSale[f] ?? '-')}
                </p></div>
              ))}
            </div>
            {detailSale.batch_ids?.length > 0 && (
              <div>
                <p className="text-label-md text-on-surface-variant mb-2">Batches</p>
                <div className="space-y-1">
                  {detailSale.batch_ids.map((b, i) => (
                    <div key={i} className="px-3 py-2 bg-surface-container rounded-lg text-body-md text-on-surface">{b}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </SlideOutPanel>

      {showCreate && <CreateSaleForm onClose={() => setShowCreate(false)} onSuccess={refetch} />}

      <ConfirmModal open={!!showDelete} title="Delete Sale" message={`Delete sale ${showDelete?.invoice_number || ''}?`} confirmLabel="Delete" destructive onConfirm={handleDelete} onCancel={() => setShowDelete(null)} />
    </div>
  )
}

function CreateSaleForm({ onClose, onSuccess }) {
  const [buyerSearch, setBuyerSearch] = useState('')
  const [buyerResults, setBuyerResults] = useState([])
  const [selectedBuyer, setSelectedBuyer] = useState(null)
  const [stockId, setStockId] = useState('')
  const [quantity, setQuantity] = useState(0)
  const [pricePerUnit, setPricePerUnit] = useState(0)
  const [saleDate, setSaleDate] = useState(new Date().toISOString().split('T')[0])
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [notes, setNotes] = useState('')
  const [creating, setCreating] = useState(false)
  const [validationError, setValidationError] = useState('')
  const { showToast } = useToast()

  const { data: stockData } = useApi('/api/stock/')
  const stockItems = stockData?.results || []
  const selectedStock = stockItems.find(s => s.id === stockId) || null

  const searchBuyer = useCallback(async (q) => {
    setBuyerSearch(q)
    if (q.length < 2) { setBuyerResults([]); return }
    try {
      const res = await apiFetch(`/api/buyers/?search=${encodeURIComponent(q)}`)
      if (res.ok) {
        const d = await res.json()
        setBuyerResults(d.results || [])
      }
    } catch { showToast({ type: 'error', message: 'Failed to search buyers.' }) }
  }, [])

  const totalAmount = Number(quantity || 0) * Number(pricePerUnit || 0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setValidationError('')

    if (!selectedBuyer) { setValidationError('Select a buyer.'); return }
    if (!stockId) { setValidationError('Select a product / grade (stock).'); return }
    if (Number(quantity) <= 0) { setValidationError('Quantity must be greater than 0.'); return }
    if (Number(pricePerUnit) <= 0) { setValidationError('Price per unit must be greater than 0.'); return }
    if (selectedStock && Number(quantity) > Number(selectedStock.quantity_available)) {
      setValidationError(`Insufficient stock: ${selectedStock.quantity_available} ${selectedStock.unit} available, ${quantity} ${selectedStock.unit} requested.`)
      return
    }

    setCreating(true)
    try {
      const body = {
        buyer: selectedBuyer.id,
        stock: stockId,
        quantity: Number(quantity),
        price_per_unit: Number(pricePerUnit),
        sale_date: saleDate,
        invoice_number: invoiceNumber,
        notes,
      }
      const res = await apiFetch('/api/sales/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create sale') }
      showToast({ type: 'success', message: 'Sale recorded. The server allocated FIFO across cycle-pools.' })
      onSuccess(); onClose()
    } catch (err) { setValidationError(err.message) }
    finally { setCreating(false) }
  }

  return (
    <SlideOutPanel open onClose={onClose} title="Record Sale" width="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="create-buyer" className="block text-label-md text-on-surface-variant mb-1">Buyer</label>
          {!selectedBuyer ? (
            <>
              <input id="create-buyer" value={buyerSearch} onChange={(e) => searchBuyer(e.target.value)} placeholder="Search buyers..." className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
              {buyerResults.length > 0 && (
                <div className="mt-1 border border-outline-variant rounded-lg overflow-hidden max-h-40 overflow-y-auto">
                  {buyerResults.map(b => (
                    <button key={b.id} type="button" onClick={() => { setSelectedBuyer(b); setBuyerResults([]); setBuyerSearch(b.name) }} className="w-full text-left px-3 py-2 hover:bg-surface-container text-body-md">{b.name} — {b.phone_number || ''}</button>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-between px-3 py-2 bg-surface-container rounded-lg">
              <span className="text-body-md text-on-surface">{selectedBuyer.name}</span>
              <button type="button" onClick={() => { setSelectedBuyer(null); setBuyerSearch('') }} className="text-error text-label-md">Change</button>
            </div>
          )}
        </div>

        <div>
          <label htmlFor="create-stock" className="block text-label-md text-on-surface-variant mb-1">Product / Grade (Stock)</label>
          <select id="create-stock" value={stockId} onChange={(e) => setStockId(e.target.value)} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
            <option value="">Select stock...</option>
            {stockItems.map(s => (
              <option key={s.id} value={s.id}>
                {s.product_type} {s.grade ? `(${s.grade})` : ''} — avail: {s.quantity_available} {s.unit}
              </option>
            ))}
          </select>
          {selectedStock && (
            <p className="text-label-md text-on-surface-variant mt-1">Available: <span className="font-bold text-on-surface">{selectedStock.quantity_available} {selectedStock.unit}</span> — server will allocate FIFO across cycle-pools.</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="create-quantity" className="block text-label-md text-on-surface-variant mb-1">Quantity ({selectedStock?.unit || 'unit'})</label>
            <input id="create-quantity" type="number" step="0.001" min="0" value={quantity || ''} onChange={(e) => setQuantity(e.target.value)} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-price_per_unit" className="block text-label-md text-on-surface-variant mb-1">Price per Unit (KES)</label>
            <input id="create-price_per_unit" type="number" step="0.01" min="0" value={pricePerUnit} onChange={(e) => setPricePerUnit(e.target.value)} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
        </div>

        <div>
          <span className="block text-label-md text-on-surface-variant mb-1">Total Amount</span>
          <div className="px-3 py-2 bg-surface-container-low rounded-lg text-body-md font-bold text-primary">KES {totalAmount.toLocaleString()}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="create-sale_date" className="block text-label-md text-on-surface-variant mb-1">Sale Date</label>
            <input id="create-sale_date" type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-invoice_number" className="block text-label-md text-on-surface-variant mb-1">Invoice #</label>
            <input id="create-invoice_number" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
        </div>

        <div>
          <label htmlFor="create-notes" className="block text-label-md text-on-surface-variant mb-1">Notes</label>
          <textarea id="create-notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
        </div>

        {validationError && (
          <div className="px-3 py-2 bg-error-container text-on-error-container rounded-lg text-body-md">{validationError}</div>
        )}

        <button type="submit" disabled={creating} className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold disabled:opacity-50">
          {creating ? 'Recording...' : 'Record Sale'}
        </button>
      </form>
    </SlideOutPanel>
  )
}

function BuyersSection() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState('name')
  const [sortOrder, setSortOrder] = useState('asc')
  const [detailBuyer, setDetailBuyer] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(null)
  const [showDelete, setShowDelete] = useState(null)
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')

  const sortParam = sortOrder === 'desc' ? `-${sortField}` : sortField
  const queryParams = new URLSearchParams({ page, page_size: pageSize, ordering: sortParam })
  if (search) queryParams.set('search', search)

  const { data, loading, error, refetch } = useApi(`/api/buyers/?${queryParams}`)

  const items = data?.results || []

  useEffect(() => {
    if (selectedId && items.length > 0) {
      const found = items.find(i => String(i.id) === String(selectedId))
      if (found && !detailBuyer) {
        setDetailBuyer(found)
      }
    }
  }, [selectedId, items])

  const handleSort = (key) => {
    if (sortField === key) setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    else { setSortField(key); setSortOrder('asc') }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const body = Object.fromEntries(fd.entries())
    try {
      const res = await apiFetch('/api/buyers/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to create') }
      showToast({ type: 'success', message: 'Buyer created.' })
      setShowCreate(false); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const body = Object.fromEntries(fd.entries())
    try {
      const res = await apiFetch(`/api/buyers/${showEdit.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to update') }
      showToast({ type: 'success', message: 'Buyer updated.' })
      setShowEdit(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/buyers/${showDelete.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Buyer deleted.' })
      setShowDelete(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'contact_person', label: 'Contact', sortable: true, render: (row) => row.contact_person || '-' },
    { key: 'phone_number', label: 'Phone', sortable: true, render: (row) => row.phone_number || '-' },
    { key: 'email', label: 'Email', render: (row) => row.email || '-' },
    { key: 'is_active', label: 'Active', render: (row) => <StatusBadge status={row.is_active} label={row.is_active ? 'Yes' : 'No'} /> },
    { key: 'created_at', label: 'Created', sortable: true, render: (row) => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button onClick={(e) => { e.stopPropagation(); setShowEdit(row) }} className="text-primary hover:text-primary/80" aria-label={`Edit ${row.name}`}><span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span></button>
          <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error hover:text-error/80" aria-label={`Delete ${row.name}`}><span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span></button>
        </div>
      ),
    },
  ]

  const buyerFormFields = [
    { key: 'name', label: 'Name', required: true },
    { key: 'contact_person', label: 'Contact Person' },
    { key: 'phone_number', label: 'Phone' },
    { key: 'email', label: 'Email' },
    { key: 'kra_pin', label: 'KRA PIN' },
    { key: 'physical_address', label: 'Physical Address', textarea: true },
  ]

  const buyerForm = (defaults = {}, onSubmit, submitLabel) => (
    <form onSubmit={onSubmit} className="space-y-4">
      {buyerFormFields.map(({ key, label, required, textarea }) => (
        <div key={key}>
          <label htmlFor={`create-${key}`} className="block text-label-md text-on-surface-variant mb-1 capitalize">{label}</label>
          {textarea ? (
            <textarea id={`create-${key}`} name={key} defaultValue={defaults[key] || ''} rows={2} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          ) : (
            <input id={`create-${key}`} name={key} defaultValue={defaults[key] || ''} required={required} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          )}
        </div>
      ))}
      <button type="submit" className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">{submitLabel}</button>
    </form>
  )

  return (
    <div>
      <div className="mb-4 flex items-center justify-between flex-wrap gap-4">
        <form onSubmit={(e) => { e.preventDefault(); setSearch(new FormData(e.target).get('search') || ''); setPage(1) }} className="flex gap-2">
          <label htmlFor="buyers-search" className="sr-only">Search buyers</label>
          <input id="buyers-search" name="search" defaultValue={search} placeholder="Search buyers..." className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-64"/>
          <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Search</button>
        </form>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">add</span>Add Buyer
        </button>
      </div>

      {loading ? <TableSkeleton rows={10} cols={7} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={data?.results || []}
            sortField={sortField}
            sortOrder={sortOrder}
            onSort={handleSort}
            onRowClick={(row) => setDetailBuyer(row)}
            emptyMessage="No buyers found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailBuyer} onClose={() => { setDetailBuyer(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Buyer Details" width="max-w-xl">
        {detailBuyer && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['name', 'contact_person', 'phone_number', 'email', 'kra_pin', 'physical_address', 'is_active', 'created_at'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace(/_/g, ' ')}</p><p className="text-body-md text-on-surface font-medium">{String(detailBuyer[f] ?? '-')}</p></div>
              ))}
            </div>
          </div>
        )}
      </SlideOutPanel>

      <SlideOutPanel open={showCreate} onClose={() => setShowCreate(false)} title="New Buyer" width="max-w-md">
        {buyerForm({}, handleCreate, 'Create Buyer')}
      </SlideOutPanel>

      <SlideOutPanel open={!!showEdit} onClose={() => setShowEdit(null)} title="Edit Buyer" width="max-w-md">
        {showEdit && buyerForm(showEdit, handleEdit, 'Update Buyer')}
      </SlideOutPanel>

      <ConfirmModal open={!!showDelete} title="Delete Buyer" message={`Delete buyer "${showDelete?.name}"?`} confirmLabel="Delete" destructive onConfirm={handleDelete} onCancel={() => setShowDelete(null)} />
    </div>
  )
}
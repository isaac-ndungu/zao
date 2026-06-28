import { useState, useCallback } from 'react'
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

  const params = new URLSearchParams({ page, page_size: pageSize, ordering: sortField })
  if (statusFilter) params.set('status', statusFilter)

  const { data, loading, error, refetch } = useApi(`/api/sales/?${params}`)

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
        <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error text-label-md hover:underline">Delete</button>
      ),
    },
  ]

  return (
    <div>
      <div className="mb-4 flex items-center justify-between flex-wrap gap-4">
        <div className="flex gap-2">
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
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

      <SlideOutPanel open={!!detailSale} onClose={() => setDetailSale(null)} title="Sale Details" width="max-w-xl">
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
  const [lineItems, setLineItems] = useState([{ inventory_id: '', quantity: 0 }])
  const [pricePerUnit, setPricePerUnit] = useState(0)
  const [saleDate, setSaleDate] = useState(new Date().toISOString().split('T')[0])
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [notes, setNotes] = useState('')
  const [creating, setCreating] = useState(false)
  const [validationError, setValidationError] = useState('')
  const { showToast } = useToast()

  const { data: inventoryData } = useApi('/api/inventory/')
  const inventoryBatches = inventoryData?.results || []

  const searchBuyer = useCallback(async (q) => {
    setBuyerSearch(q)
    if (q.length < 2) { setBuyerResults([]); return }
    try {
      const res = await apiFetch(`/api/buyers/?search=${encodeURIComponent(q)}`)
      if (res.ok) {
        const d = await res.json()
        setBuyerResults(d.results || [])
      }
    } catch { /* ignore */ }
  }, [])

  const totalQty = lineItems.reduce((s, li) => s + (Number(li.quantity) || 0), 0)
  const totalAmount = totalQty * Number(pricePerUnit || 0)

  const addLineItem = () => {
    setValidationError('')
    setLineItems(prev => [...prev, { inventory_id: '', quantity: 0 }])
  }

  const removeLineItem = (index) => {
    setValidationError('')
    setLineItems(prev => prev.filter((_, i) => i !== index))
  }

  const updateLineItem = (index, field, value) => {
    setValidationError('')
    setLineItems(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item))
  }

  const selectedBatchIds = lineItems.map(li => li.inventory_id).filter(Boolean)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setValidationError('')

    if (!selectedBuyer) { setValidationError('Select a buyer.'); return }
    const validLineItems = lineItems.filter(li => li.inventory_id && Number(li.quantity) > 0)
    if (validLineItems.length === 0) { setValidationError('Add at least one batch line item with quantity.'); return }

    const ids = validLineItems.map(li => li.inventory_id)
    if (new Set(ids).size !== ids.length) { setValidationError('Duplicate batch selected.'); return }

    const selectedBatches = validLineItems.map(li => inventoryBatches.find(b => b.id === li.inventory_id)).filter(Boolean)
    if (selectedBatches.length > 1) {
      const types = new Set(selectedBatches.map(b => b.product_type))
      const grades = new Set(selectedBatches.map(b => b.grade))
      if (types.size > 1 || grades.size > 1) {
        setValidationError('All batches must have the same product type and grade.')
        return
      }
    }

    for (const li of validLineItems) {
      const batch = inventoryBatches.find(b => b.id === li.inventory_id)
      if (batch && Number(li.quantity) > Number(batch.running_balance || batch.quantity_in - batch.quantity_out)) {
        setValidationError(`Quantity for batch ${batch.batch_id} exceeds available balance (${batch.running_balance || batch.quantity_in - batch.quantity_out}).`)
        return
      }
    }

    setCreating(true)
    try {
      const body = {
        buyer: selectedBuyer.id,
        line_items: validLineItems.map(li => ({ inventory: li.inventory_id, quantity: Number(li.quantity) })),
        quantity: totalQty,
        price_per_unit: Number(pricePerUnit),
        sale_date: saleDate,
        invoice_number: invoiceNumber,
        notes,
      }
      const res = await apiFetch('/api/sales/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create sale') }
      showToast({ type: 'success', message: 'Sale recorded.' })
      onSuccess(); onClose()
    } catch (err) { setValidationError(err.message) }
    finally { setCreating(false) }
  }

  return (
    <SlideOutPanel open onClose={onClose} title="Record Sale" width="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-label-md text-on-surface-variant mb-1">Buyer</label>
          {!selectedBuyer ? (
            <>
              <input value={buyerSearch} onChange={(e) => searchBuyer(e.target.value)} placeholder="Search buyers..." className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
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
          <div className="flex items-center justify-between mb-2">
            <label className="text-label-md text-on-surface-variant">Batch Line Items</label>
            <button type="button" onClick={addLineItem} className="text-primary text-label-md font-bold flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px]">add</span>Add Batch
            </button>
          </div>
          <div className="space-y-3">
            {lineItems.map((item, index) => (
              <div key={index} className="flex gap-2 items-start">
                <div className="flex-1">
                  <select
                    value={item.inventory_id}
                    onChange={(e) => updateLineItem(index, 'inventory_id', e.target.value)}
                    className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
                  >
                    <option value="">Select batch...</option>
                    {inventoryBatches
                      .filter(b => !selectedBatchIds.includes(b.id) || b.id === item.inventory_id)
                      .map(b => (
                        <option key={b.id} value={b.id}>
                          {b.batch_id} — {b.product_type} ({b.grade}) — avail: {b.running_balance || Number(b.quantity_in - b.quantity_out)}
                        </option>
                      ))}
                  </select>
                </div>
                <div className="w-28">
                  <input
                    type="number"
                    step="0.001"
                    min="0"
                    value={item.quantity || ''}
                    onChange={(e) => updateLineItem(index, 'quantity', e.target.value)}
                    placeholder="Qty"
                    className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
                  />
                </div>
                {lineItems.length > 1 && (
                  <button type="button" onClick={() => removeLineItem(index)} className="text-error mt-2">
                    <span className="material-symbols-outlined text-[18px]">remove_circle</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Total Quantity</label>
            <input value={totalQty} disabled className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container-low text-on-surface-variant" />
          </div>
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Price per Unit (KES)</label>
            <input type="number" step="0.01" min="0" value={pricePerUnit} onChange={(e) => setPricePerUnit(e.target.value)} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
        </div>

        <div>
          <label className="block text-label-md text-on-surface-variant mb-1">Total Amount</label>
          <div className="px-3 py-2 bg-surface-container-low rounded-lg text-body-md font-bold text-primary">KES {totalAmount.toLocaleString()}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Sale Date</label>
            <input type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Invoice #</label>
            <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
        </div>

        <div>
          <label className="block text-label-md text-on-surface-variant mb-1">Notes</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
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

  const sortParam = sortOrder === 'desc' ? `-${sortField}` : sortField
  const queryParams = new URLSearchParams({ page, page_size: pageSize, ordering: sortParam })
  if (search) queryParams.set('search', search)

  const { data, loading, error, refetch } = useApi(`/api/buyers/?${queryParams}`)

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
        <div className="flex gap-2">
          <button onClick={(e) => { e.stopPropagation(); setShowEdit(row) }} className="text-primary text-label-md hover:underline">Edit</button>
          <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error text-label-md hover:underline">Delete</button>
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
          <label className="block text-label-md text-on-surface-variant mb-1 capitalize">{label}</label>
          {textarea ? (
            <textarea name={key} defaultValue={defaults[key] || ''} rows={2} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          ) : (
            <input name={key} defaultValue={defaults[key] || ''} required={required} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
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
          <input name="search" defaultValue={search} placeholder="Search buyers..." className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-64"/>
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

      <SlideOutPanel open={!!detailBuyer} onClose={() => setDetailBuyer(null)} title="Buyer Details" width="max-w-xl">
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
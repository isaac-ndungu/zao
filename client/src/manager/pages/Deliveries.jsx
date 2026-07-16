import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton, KpiSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import KpiCard from '../../admin/components/common/KpiCard'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'
import MapView from '../../shared/components/MapView'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

export default function Deliveries() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [productFilter, setProductFilter] = useState('')
  const [sortField, setSortField] = useState('-date_delivered')
  const [selectedIds, setSelectedIds] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(null)
  const [showDelete, setShowDelete] = useState(null)
  const [showMap, setShowMap] = useState(false)
  const [detailDelivery, setDetailDelivery] = useState(null)
  const [farmerSearch, setFarmerSearch] = useState('')
  const [farmerResults, setFarmerResults] = useState([])
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')
  const [pickedFarmer, setPickedFarmer] = useState(null)
  const [pickedFarmerLocation, setPickedFarmerLocation] = useState(null)
  const [pickedRouteStops, setPickedRouteStops] = useState([])
  const [pickedRouteStop, setPickedRouteStop] = useState('')
  const [createLat, setCreateLat] = useState('')
  const [createLng, setCreateLng] = useState('')

  const params = new URLSearchParams({ page, page_size: pageSize, ordering: sortField })
  if (statusFilter) params.set('status', statusFilter)
  if (productFilter) params.set('product_type', productFilter)

  const { data, loading, error, refetch } = useApi(`/api/deliveries/?${params}`)
  const { data: summary } = useApi('/api/deliveries/summary/')
  const { data: mapData } = useApi(showMap ? '/api/deliveries/map/' : null)

  const items = data?.results || []

  useEffect(() => {
    if (selectedId && items.length > 0) {
      const found = items.find(i => String(i.id) === String(selectedId))
      if (found && !detailDelivery) {
        setDetailDelivery(found)
      }
    }
  }, [selectedId, items])

  const handleSort = (key) => setSortField((prev) => (prev === key ? `-${key}` : key))

  const searchFarmer = useCallback(async (q) => {
    setFarmerSearch(q)
    if (q.length < 2) { setFarmerResults([]); return }
    try {
      const isNumeric = /^[\d\+]+$/.test(q)
      const param = isNumeric ? `phone=${encodeURIComponent(q)}` : `name=${encodeURIComponent(q)}`
      const res = await apiFetch(`/api/farmers/lookup/?${param}`)
      if (res.ok) {
        const d = await res.json()
        setFarmerResults(d.results || [d])
      }
    } catch {}
  }, [])

  const pickFarmer = useCallback(async (farmerId) => {
    setPickedFarmer(farmerId)
    setPickedRouteStop('')
    setPickedFarmerLocation(null)
    setPickedRouteStops([])
    try {
      const res = await apiFetch(`/api/farmers/${farmerId}/location/`)
      if (res.ok) {
        const d = await res.json()
        setPickedFarmerLocation({ latitude: d.latitude, longitude: d.longitude })
        setPickedRouteStops(d.route_stops || [])
        if (d.latitude != null) setCreateLat(String(d.latitude))
        if (d.longitude != null) setCreateLng(String(d.longitude))
      }
    } catch {}
  }, [])

  const handleRouteStopChange = (stopId) => {
    setPickedRouteStop(stopId)
    if (stopId) {
      const s = pickedRouteStops.find((x) => String(x.id) === String(stopId))
    }
  }

  const [, createAction] = useFormAction(async (_prev, formData) => {
    const body = formDataToObject(formData)
    if (body.farmer_id) body.farmer = body.farmer_id
    const res = await apiFetch('/api/deliveries/', { method: 'POST', body: JSON.stringify(body) })
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to create') }
    showToast({ type: 'success', message: 'Delivery recorded.' })
    setShowCreate(false); refetch()
  }, {})

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/deliveries/${showDelete.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Delivery deleted.' })
      setShowDelete(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const openEdit = (delivery) => {
    setShowEdit(delivery)
  }

  const [, editAction] = useFormAction(async (_prev, formData) => {
    const body = formDataToObject(formData)
    if (!body.quantity_kg) delete body.quantity_kg
    if (!body.volume_litres) delete body.volume_litres
    if (!body.latitude) delete body.latitude
    if (!body.longitude) delete body.longitude
    const res = await apiFetch(`/api/deliveries/${showEdit.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
    if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to update') }
    showToast({ type: 'success', message: 'Delivery updated.' })
    setShowEdit(null); refetch()
  }, {})

  const withLocationCount = mapData?.filter((m) => m.latitude && m.longitude)?.length || 0
  const totalMapItems = mapData?.length || 0

  const columns = [
    { key: 'batch_id', label: 'Batch ID', sortable: true },
    { key: 'farmer_name', label: 'Farmer', sortable: true },
    { key: 'product_type', label: 'Product', sortable: true },
    { key: 'quantity_kg', label: 'Qty (kg)', sortable: true, render: (v, row) => row.quantity_kg || row.volume_litres || '-' },
    { key: 'shift', label: 'Shift', sortable: true },
    { key: 'status', label: 'Status', sortable: true, render: (v, row) => <StatusBadge status={row.status?.toLowerCase()} label={row.status} /> },
    { key: 'date_delivered', label: 'Date', sortable: true, render: (v, row) => row.date_delivered ? new Date(row.date_delivered).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (v, row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button onClick={(e) => { e.stopPropagation(); openEdit(row) }} className="text-on-surface-variant hover:text-primary" aria-label="Edit delivery"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span></button>
          <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error hover:text-error/80" aria-label="Delete delivery"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span></button>
        </div>
      ),
    },
  ]

  const totalDeliveries = summary?.total || 0

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Deliveries</h2>
          <p className="text-sm text-on-surface-variant">{totalDeliveries} total</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowMap(!showMap)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">map</span>Map View
          </button>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">add</span>Add Delivery
          </button>
        </div>
      </header>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <KpiCard icon="local_shipping" label="Total" value={String(summary.total || 0)} />
          <KpiCard icon="pending" label="Pending" value={String(summary.pending_grading || 0)} />
          <KpiCard icon="grading" label="Graded" value={String(summary.by_status?.find(s => s.status === 'GRADED')?.count || 0)} />
          <KpiCard icon="check_circle" label="Accepted" value={String(summary.by_status?.find(s => s.status === 'ACCEPTED')?.count || 0)} />
        </div>
      )}

      <div className="mb-4 flex items-center gap-4 flex-wrap">
        <label htmlFor="status-filter" className="sr-only">Filter by status</label>
        <select id="status-filter" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="GRADED">Graded</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="REJECTED">Rejected</option>
          <option value="PAID">Paid</option>
        </select>
        <label htmlFor="product-filter" className="sr-only">Filter by product</label>
        <select id="product-filter" value={productFilter} onChange={(e) => { setProductFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Products</option>
          <option value="MILK">Milk</option>
          <option value="COFFEE_CHERRIES">Coffee Cherries</option>
          <option value="HONEY">Honey</option>
          <option value="OTHER">Other</option>
        </select>
      </div>

      {showMap && (
        <div className="mb-6 bg-surface-container rounded-2xl border border-outline-variant/40 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Delivery Map</h3>
            <span className="text-label-md text-on-surface-variant">
              Showing {withLocationCount} of {totalMapItems} deliveries {totalMapItems > 0 && withLocationCount < totalMapItems ? `(${totalMapItems - withLocationCount} have no location data)` : ''}
            </span>
          </div>
          {withLocationCount > 0 ? (
            <MapView deliveries={mapData || []} height="320px" />
          ) : (
            <div className="bg-surface-container-high rounded-lg h-80 flex items-center justify-center text-on-surface-variant">
              <div className="text-center">
                <span className="material-symbols-outlined text-[48px]" aria-hidden="true">map</span>
                <p className="text-body-md mt-2">No deliveries with location data</p>
                <p className="text-label-md text-on-surface-variant mt-1">Add coordinates to deliveries to see them on the map</p>
              </div>
            </div>
          )}
        </div>
      )}

      {loading ? <TableSkeleton rows={10} cols={8} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={data?.results || []}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            sortField={sortField.replace('-', '')}
            sortOrder={sortField.startsWith('-') ? 'desc' : 'asc'}
            onSort={handleSort}
            onRowClick={(row) => setDetailDelivery(row)}
            emptyMessage="No deliveries found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailDelivery} onClose={() => { setDetailDelivery(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="Delivery Details" width="max-w-xl">
        {detailDelivery && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {['batch_id','farmer_name','product_type','quantity_kg','volume_litres','shift','status','grade','date_delivered'].map(f => (
                <div key={f}><p className="text-label-md text-on-surface-variant capitalize">{f.replace('_',' ')}</p><p className="text-body-md text-on-surface font-medium">{String(detailDelivery[f] ?? '-')}</p></div>
              ))}
            </div>
            {(detailDelivery.route_name || detailDelivery.route_stop) && (
              <div className="pt-2 border-t border-outline-variant">
                <h3 className="text-label-lg font-bold mb-2">Route</h3>
                <p className="text-body-md">
                  {detailDelivery.route_name ? (
                    <>Route: <span className="font-medium">{detailDelivery.route_name}</span></>
                  ) : null}
                  {detailDelivery.route_stop ? (
                    <> · Stop: <span className="font-medium">#{detailDelivery.route_stop}</span></>
                  ) : null}
                </p>
              </div>
            )}
          </div>
        )}
      </SlideOutPanel>

      <SlideOutPanel open={showCreate} onClose={() => { setShowCreate(false); setPickedFarmer(null); setPickedFarmerLocation(null); setPickedRouteStops([]); setPickedRouteStop(''); setCreateLat(''); setCreateLng('') }} title="Record Delivery" width="max-w-md">
        <form action={createAction} className="space-y-4">
          <div>
            <label htmlFor="create-farmer-search" className="block text-label-md text-on-surface-variant mb-1">Farmer</label>
            <input id="create-farmer-search" value={farmerSearch} onChange={(e) => searchFarmer(e.target.value)} placeholder="Search by name or phone..." className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/>
            {farmerResults.length > 0 && (
              <div className="mt-1 border border-outline-variant rounded-lg overflow-hidden" role="listbox">
                {farmerResults.map(f => (
                  <button
                    type="button"
                    key={f.id}
                    onClick={() => { pickFarmer(f.id); setFarmerResults([]); setFarmerSearch(`${f.first_name} ${f.last_name}`) }}
                    className={`w-full flex items-center gap-2 px-3 py-2 hover:bg-surface-container cursor-pointer text-left ${pickedFarmer === f.id ? 'bg-primary-container' : ''}`}
                  >
                    <span className="material-symbols-outlined text-primary text-[18px]">check_circle</span>
                    <span className="text-body-md">{f.first_name} {f.last_name} — {f.phone_number}</span>
                  </button>
                ))}
              </div>
            )}
            <input type="hidden" name="farmer_id" value={pickedFarmer || ''} />
          </div>
          {pickedFarmer && pickedRouteStops.length > 0 && (
            <div>
              <label htmlFor="create-route-stop" className="block text-label-md text-on-surface-variant mb-1">Pickup stop (optional)</label>
              <select
                id="create-route-stop"
                name="route_stop"
                value={pickedRouteStop}
                onChange={(e) => handleRouteStopChange(e.target.value)}
                className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
              >
                <option value="">— None —</option>
                {pickedRouteStops.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.route_name} — Stop {s.stop_order}
                  </option>
                ))}
              </select>
              <p className="text-label-sm text-on-surface-variant mt-1">
                Selecting a stop fills the delivery coordinates from the stop location.
              </p>
            </div>
          )}
          <div><label htmlFor="create-product-type" className="block text-label-md text-on-surface-variant mb-1">Product Type</label><select id="create-product-type" name="product_type" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option value="MILK">Milk</option><option value="COFFEE_CHERRIES">Coffee Cherries</option><option value="HONEY">Honey</option><option value="OTHER">Other</option></select></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label htmlFor="create-quantity-kg" className="block text-label-md text-on-surface-variant mb-1">Quantity (kg)</label><input id="create-quantity-kg" name="quantity_kg" type="number" step="0.01" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
            <div><label htmlFor="create-volume-litres" className="block text-label-md text-on-surface-variant mb-1">Volume (L)</label><input id="create-volume-litres" name="volume_litres" type="number" step="0.01" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label htmlFor="create-shift" className="block text-label-md text-on-surface-variant mb-1">Shift</label><select id="create-shift" name="shift" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option value="AM">AM</option><option value="PM">PM</option></select></div>
            <div><label htmlFor="create-date-delivered" className="block text-label-md text-on-surface-variant mb-1">Date Delivered</label><input id="create-date-delivered" name="date_delivered" type="date" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="create-latitude" className="block text-label-md text-on-surface-variant mb-1">Latitude</label>
              <input id="create-latitude" name="latitude" type="number" step="any" value={createLat} onChange={(e) => setCreateLat(e.target.value)} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
              {pickedFarmerLocation?.latitude == null && pickedFarmer && (
                <p className="text-label-sm text-on-surface-variant mt-1">Farmer has no saved pickup location.</p>
              )}
            </div>
            <div>
              <label htmlFor="create-longitude" className="block text-label-md text-on-surface-variant mb-1">Longitude</label>
              <input id="create-longitude" name="longitude" type="number" step="any" value={createLng} onChange={(e) => setCreateLng(e.target.value)} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
            </div>
          </div>
          <SubmitButton className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold disabled:opacity-50">Record Delivery</SubmitButton>
        </form>
      </SlideOutPanel>

      <SlideOutPanel open={!!showEdit} onClose={() => setShowEdit(null)} title="Edit Delivery" width="max-w-md">
        {showEdit && (
          <form action={editAction} className="space-y-4">
            <div>
              <p className="text-label-md text-on-surface-variant">Batch ID</p>
              <p className="text-body-md text-on-surface font-medium">{showEdit.batch_id}</p>
            </div>
            <div>
              <p className="text-label-md text-on-surface-variant">Farmer</p>
              <p className="text-body-md text-on-surface font-medium">{showEdit.farmer_name}</p>
            </div>
            <div><label htmlFor="edit-product-type" className="block text-label-md text-on-surface-variant mb-1">Product Type</label><select id="edit-product-type" name="product_type" defaultValue={showEdit.product_type || 'MILK'} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option value="MILK">Milk</option><option value="COFFEE_CHERRIES">Coffee Cherries</option><option value="HONEY">Honey</option><option value="OTHER">Other</option></select></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label htmlFor="edit-quantity-kg" className="block text-label-md text-on-surface-variant mb-1">Quantity (kg)</label><input id="edit-quantity-kg" name="quantity_kg" type="number" step="0.01" defaultValue={showEdit.quantity_kg || ''} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
              <div><label htmlFor="edit-volume-litres" className="block text-label-md text-on-surface-variant mb-1">Volume (L)</label><input id="edit-volume-litres" name="volume_litres" type="number" step="0.01" defaultValue={showEdit.volume_litres || ''} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label htmlFor="edit-shift" className="block text-label-md text-on-surface-variant mb-1">Shift</label><select id="edit-shift" name="shift" defaultValue={showEdit.shift || 'AM'} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"><option value="AM">AM</option><option value="PM">PM</option></select></div>
              <div><label htmlFor="edit-date-delivered" className="block text-label-md text-on-surface-variant mb-1">Date Delivered</label><input id="edit-date-delivered" name="date_delivered" type="date" defaultValue={showEdit.date_delivered ? showEdit.date_delivered.slice(0, 10) : new Date().toISOString().slice(0, 10)} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label htmlFor="edit-latitude" className="block text-label-md text-on-surface-variant mb-1">Latitude</label><input id="edit-latitude" name="latitude" type="number" step="any" defaultValue={showEdit.latitude || ''} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
              <div><label htmlFor="edit-longitude" className="block text-label-md text-on-surface-variant mb-1">Longitude</label><input id="edit-longitude" name="longitude" type="number" step="any" defaultValue={showEdit.longitude || ''} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
            </div>
            <SubmitButton className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">
              Save Changes
            </SubmitButton>
          </form>
        )}
      </SlideOutPanel>

      <ConfirmModal open={!!showDelete} title="Delete Delivery" message={`Delete delivery ${showDelete?.batch_id || ''}?`} confirmLabel="Delete" destructive onConfirm={handleDelete} onCancel={() => setShowDelete(null)} />
    </div>
  )
}

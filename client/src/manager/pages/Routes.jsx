import { useState, useEffect, useMemo, useCallback, lazy, Suspense } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

const RouteMapView = lazy(() => import('../../shared/components/RouteMapView'))

const DAYS = ['', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function mapStopsFromApi(stops) {
  return (stops || []).map((s) => ({
    id: s.id,
    order: s.order,
    lat: s.lat,
    lng: s.lng,
    estimated_minutes: s.estimated_minutes,
    farmers: s.farmers || [],
  }))
}

export default function Routes() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [detailRoute, setDetailRoute] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showDelete, setShowDelete] = useState(null)
  const [stops, setStops] = useState([])
  const [savingStops, setSavingStops] = useState(false)
  const { showToast } = useToast()

  const queryParams = new URLSearchParams({ page, page_size: pageSize, ordering: 'name' })
  if (search) queryParams.set('search', search)

  const { data, loading, error, refetch } = useApi(`/api/routes/?${queryParams}`)

  const items = data?.results || []
  const total = data?.count || 0

  const { data: mapData, refetch: refetchMap } = useApi(
    detailRoute ? `/api/routes/${detailRoute.id}/map/` : null,
  )

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    if (!mapData) {
      setStops([])
      return
    }
    setStops(mapStopsFromApi(mapData.stops))
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [mapData])

  const { data: farmersData } = useApi('/api/farmers/?page_size=200')
  const assignedFarmerIds = useMemo(() => {
    const s = new Set()
    stops.forEach((st) => (st.farmers || []).forEach((f) => s.add(f.id)))
    return s
  }, [stops])
  const unassignedFarmers = useMemo(() => {
    const all = farmersData?.results || []
    return all.filter(
      (f) => !assignedFarmerIds.has(f.id) && f.latitude != null && f.longitude != null,
    )
  }, [farmersData, assignedFarmerIds])

  const [, searchAction] = useFormAction(async (_prev, formData) => {
    setSearch(formData.get('search') || '')
    setPage(1)
  }, {})

  const [, createAction] = useFormAction(async (_prev, formData) => {
    const body = formDataToObject(formData)
    if (!body.name) return
    const res = await apiFetch('/api/routes/', {
      method: 'POST',
      body: JSON.stringify({ name: body.name, description: body.description, day_of_week: body.day_of_week || null }),
    })
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to create') }
    const created = await res.json()
    showToast({ type: 'success', message: 'Route created.' })
    setShowCreate(false)
    refetch()
    setDetailRoute({ id: created.id, name: created.name })
  }, {})

  const handleDelete = async () => {
    try {
      const res = await apiFetch(`/api/routes/${showDelete.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast({ type: 'success', message: 'Route deleted.' })
      setShowDelete(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleStopsChange = (newStops) => {
    const renumbered = newStops
      .sort((a, b) => a.order - b.order)
      .map((s, i) => ({ ...s, order: i + 1 }))
    setStops(renumbered)
  }

  const handleSaveStops = async () => {
    if (!detailRoute) return
    setSavingStops(true)
    try {
      const payload = {
        stops: stops.map((s) => ({
          stop_order: s.order,
          latitude: String(s.lat),
          longitude: String(s.lng),
          estimated_minutes: s.estimated_minutes || null,
          farmer_ids: (s.farmers || []).map((f) => f.id),
        })),
      }
      const res = await apiFetch(`/api/routes/${detailRoute.id}/assign-stops/`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to save stops')
      }
      showToast({ type: 'success', message: 'Stops saved.' })
      refetch()
      refetchMap()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSavingStops(false) }
  }

  const handleAssignFarmer = useCallback(async (farmerId, stopId) => {
    if (!detailRoute) return
    try {
      const res = await apiFetch(`/api/routes/${detailRoute.id}/assign-farmer/`, {
        method: 'POST',
        body: JSON.stringify({ farmer_id: farmerId, stop_id: stopId }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to assign') }
      refetchMap()
      showToast({ type: 'success', message: 'Farmer assigned to stop.' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }, [detailRoute, refetchMap, showToast])

  const handleUnassignFarmer = useCallback(async (farmerId) => {
    if (!detailRoute) return
    try {
      const res = await apiFetch(`/api/routes/${detailRoute.id}/unassign-farmer/`, {
        method: 'POST',
        body: JSON.stringify({ farmer_id: farmerId }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to unassign') }
      refetchMap()
      showToast({ type: 'success', message: 'Farmer removed.' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }, [detailRoute, refetchMap, showToast])

  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'day_of_week', label: 'Day', render: (v) => DAYS.indexOf(v) >= 0 ? v.charAt(0) + v.slice(1).toLowerCase() : '-' },
    { key: 'farmer_count', label: 'Farmers', render: (v) => v ?? 0 },
    { key: 'stop_count', label: 'Stops', render: (v) => v ?? 0 },
    { key: 'is_active', label: 'Active', render: (v) => v ? '✓' : '—' },
    {
      key: 'actions', label: '', render: (_, row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button onClick={(e) => { e.stopPropagation(); setShowDelete(row) }} className="text-error hover:text-error/80" aria-label={`Delete ${row.name}`}><span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span></button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Routes</h2>
          <p className="text-on-surface-variant font-body-md">{total} total</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">add</span>Add Route
        </button>
      </header>

      <div className="mb-4">
        <form action={searchAction} className="flex gap-2">
          <label htmlFor="routes-search" className="sr-only">Search routes</label>
          <input id="routes-search" name="search" defaultValue={search} placeholder="Search routes..." className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-64" />
          <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Search</SubmitButton>
        </form>
      </div>

      {loading ? <TableSkeleton rows={10} cols={6} /> : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={items}
            onRowClick={(row) => setDetailRoute(row)}
            emptyMessage="No routes found."
          />
          <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
        </>
      )}

      <SlideOutPanel open={!!detailRoute} onClose={() => { setDetailRoute(null); setStops([]) }} title={`Route · ${detailRoute?.name || ''}`} width="max-w-3xl">
        {detailRoute && (
          <div className="space-y-4">
            <Suspense fallback={<div className="h-[420px] flex items-center justify-center bg-surface-container rounded-lg"><span className="text-on-surface-variant">Loading map…</span></div>}>
              <RouteMapView
                route={mapData || { path: { coordinates: stops.map((s) => [s.lng, s.lat]) } }}
                stops={stops}
                onStopsChange={handleStopsChange}
                onSelectFarmer={(f) => handleUnassignFarmer(f.id)}
                height="420px"
              />
            </Suspense>
            <div className="flex items-center justify-between">
              <h3 className="text-label-lg font-bold">Stops ({stops.length})</h3>
              <button
                onClick={handleSaveStops}
                disabled={savingStops}
                className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {savingStops && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                Save stops
              </button>
            </div>
            <ul className="divide-y divide-outline-variant border border-outline-variant rounded-lg">
              {stops.length === 0 && (
                <li className="p-3 text-body-sm text-on-surface-variant">Click the map to add the first stop.</li>
              )}
              {stops.map((s) => (
                <li key={s.id} className="p-3 flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="text-label-md font-bold">Stop {s.order}</p>
                    <p className="text-body-sm text-on-surface-variant">{s.lat.toFixed(5)}, {s.lng.toFixed(5)}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <label htmlFor={`eta-${s.id}`} className="text-label-sm text-on-surface-variant">ETA (min)</label>
                      <input
                        id={`eta-${s.id}`}
                        type="number"
                        min="1"
                        value={s.estimated_minutes || ''}
                        onChange={(e) => {
                          const v = e.target.value ? Number(e.target.value) : null
                          setStops((prev) => prev.map((x) => x.id === s.id ? { ...x, estimated_minutes: v } : x))
                        }}
                        className="w-20 px-2 py-1 border border-outline-variant rounded text-body-sm bg-surface-container"
                      />
                    </div>
                    {(s.farmers || []).length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {s.farmers.map((f) => (
                          <li key={f.id} className="flex items-center justify-between bg-surface-container-lowest rounded px-2 py-1">
                            <span className="text-body-sm">{f.name} <span className="text-on-surface-variant text-label-sm">{f.member_number}</span></span>
                            <button
                              type="button"
                              onClick={() => handleUnassignFarmer(f.id)}
                              className="text-error text-label-sm"
                              aria-label={`Remove ${f.name}`}
                            >remove</button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <select
                    value=""
                    onChange={(e) => {
                      if (e.target.value) {
                        handleAssignFarmer(e.target.value, s.id)
                        e.target.value = ''
                      }
                    }}
                    className="px-2 py-1 border border-outline-variant rounded text-body-sm bg-surface-container"
                    aria-label={`Add farmer to stop ${s.order}`}
                  >
                    <option value="">+ farmer</option>
                    {unassignedFarmers.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.first_name} {f.last_name} ({f.member_number || '—'})
                      </option>
                    ))}
                  </select>
                </li>
              ))}
            </ul>
          </div>
        )}
      </SlideOutPanel>

      <SlideOutPanel open={showCreate} onClose={() => setShowCreate(false)} title="New Route" width="max-w-md">
        <form action={createAction} className="space-y-4">
          <div>
            <label htmlFor="create-name" className="block text-label-md text-on-surface-variant mb-1">Name *</label>
            <input id="create-name" name="name" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-description" className="block text-label-md text-on-surface-variant mb-1">Description</label>
            <textarea id="create-description" name="description" rows={3} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-day" className="block text-label-md text-on-surface-variant mb-1">Day of week</label>
            <select id="create-day" name="day_of_week" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
              <option value="">— Any —</option>
              {DAYS.filter(Boolean).map((d) => <option key={d} value={d.toUpperCase()}>{d}</option>)}
            </select>
          </div>
          <SubmitButton className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">Create Route</SubmitButton>
        </form>
      </SlideOutPanel>

      <ConfirmModal
        open={!!showDelete}
        title="Delete Route"
        message={`Delete route "${showDelete?.name}"?`}
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setShowDelete(null)}
      />
    </div>
  )
}

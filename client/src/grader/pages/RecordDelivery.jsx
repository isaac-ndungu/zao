import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { useOnlineStatus } from '../../shared/hooks/useOnlineStatus'
import { useFormAction, formDataToObject } from '../../shared/hooks/useFormAction'
import {
  saveDelivery,
  cacheFarmers,
  getCachedFarmers,
  searchCachedFarmers,
  cacheFarmerLocation,
  getCachedFarmerLocation,
} from '../services/offlineQueue'
import MapView from '../../shared/components/MapView'

const productTypes = [
  { value: 'MILK', label: 'Milk' },
  { value: 'COFFEE_CHERRIES', label: 'Coffee Cherries' },
  { value: 'HONEY', label: 'Honey' },
  { value: 'OTHER', label: 'Other' },
]

export default function RecordDelivery() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const isOnline = useOnlineStatus()
  const [farmerSearch, setFarmerSearch] = useState('')
  const [farmerOptions, setFarmerOptions] = useState([])
  const [selectedFarmer, setSelectedFarmer] = useState(null)
  const [cachedFarmersList, setCachedFarmersList] = useState(null)
  const [justSelected, setJustSelected] = useState(false)
  const [routeStops, setRouteStops] = useState([])
  const [pickedStop, setPickedStop] = useState('')
  const [geoBusy, setGeoBusy] = useState(false)
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')

  useEffect(() => {
    getCachedFarmers().then(cached => {
      if (cached) setCachedFarmersList(cached)
    })
    if (isOnline) {
      apiFetch('/api/farmers/?page_size=500').then(r => {
        if (!r.ok) return null
        return r.json()
      }).then(data => {
        if (data?.results) {
          setCachedFarmersList(data.results)
          cacheFarmers(data.results)
        }
      })
    }
  }, [isOnline])

  const { formAction, isPending } = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    if (!data.farmer) {
      showToast({ type: 'error', message: 'Select a farmer.' })
      return {}
    }
    const body = { ...data, farmer_id: data.farmer, farmer_name: farmerSearch }
    delete body.farmer
    if (!body.quantity_kg) delete body.quantity_kg
    if (!body.volume_litres) delete body.volume_litres
    if (!body.latitude) delete body.latitude
    if (!body.longitude) delete body.longitude
    if (!body.route_stop) delete body.route_stop
    if (isOnline) {
      const res = await apiFetch('/api/deliveries/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create delivery') }
      showToast({ type: 'success', message: 'Delivery recorded.' })
    } else {
      await saveDelivery(body)
      showToast({ type: 'success', message: 'Delivery saved offline. Will sync when online.' })
    }
    navigate('/grader/grade')
    return {}
  }, {})

  const searchFarmer = async (q) => {
    if (justSelected) { setJustSelected(false); return }
    setFarmerSearch(q)
    setSelectedFarmer(null)
    setLatitude('')
    setLongitude('')
    setRouteStops([])
    setPickedStop('')
    if (q.length < 2) { setFarmerOptions([]); return }
    if (!isOnline) {
      if (cachedFarmersList) {
        setFarmerOptions(searchCachedFarmers(cachedFarmersList, q))
      } else {
        setFarmerOptions([])
      }
      return
    }
    try {
      const isNumeric = /^[\d\+]+$/.test(q)
      const param = isNumeric ? `phone=${encodeURIComponent(q)}` : `name=${encodeURIComponent(q)}`
      const res = await apiFetch(`/api/farmers/lookup/?${param}`)
      if (res.ok) {
        const data = await res.json()
        setFarmerOptions(data.results || [])
      }
    } catch {}
  }

  const selectFarmer = async (farmer) => {
    setSelectedFarmer(farmer)
    setLatitude('')
    setLongitude('')
    setFarmerSearch(`${farmer.first_name} ${farmer.last_name} (${farmer.phone_number || farmer.id.slice(0, 8)})`)
    setFarmerOptions([])
    setJustSelected(true)
    setPickedStop('')
    setRouteStops([])

    if (isOnline) {
      try {
        const res = await apiFetch(`/api/farmers/${farmer.id}/location/`)
        if (res.ok) {
          const data = await res.json()
          if (data.latitude != null && data.longitude != null) {
            setLatitude(String(data.latitude))
            setLongitude(String(data.longitude))
          }
          setRouteStops(data.route_stops || [])
          cacheFarmerLocation(farmer.id, {
            latitude: data.latitude,
            longitude: data.longitude,
            route_stops: data.route_stops || [],
          })
        }
      } catch {}
    } else {
      const cached = await getCachedFarmerLocation(farmer.id).catch(() => null)
      if (cached) {
        if (cached.latitude != null && cached.longitude != null) {
          setLatitude(String(cached.latitude))
          setLongitude(String(cached.longitude))
        }
        setRouteStops(cached.route_stops || [])
      }
    }
  }

  const useMyLocation = () => {
    if (!('geolocation' in navigator)) {
      showToast({ type: 'error', message: 'Geolocation not available.' })
      return
    }
    setGeoBusy(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6))
        setLongitude(pos.coords.longitude.toFixed(6))
        setGeoBusy(false)
      },
      (err) => {
        setGeoBusy(false)
        showToast({ type: 'error', message: err.message || 'Could not get your location.' })
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  }

  const pickup = (latitude && longitude)
    ? { lat: Number(latitude), lng: Number(longitude) }
    : null

  return (
    <div className="max-w-lg mx-auto">
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Record Delivery</h2>
        <p className="text-on-surface-variant font-body-md">Log a new delivery from a farmer</p>
      </header>

      <form action={formAction} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 space-y-4">
        <div className="relative">
          <label htmlFor="record-farmer" className="block text-label-md font-bold text-on-surface mb-1.5">Farmer *</label>
          <input
            id="record-farmer"
            type="text"
            value={farmerSearch}
            onChange={(e) => searchFarmer(e.target.value)}
            placeholder="Search by name or phone..."
            className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
            disabled={isPending}
            autoComplete="off"
          />
          {!isOnline && !cachedFarmersList && (
            <p className="text-label-sm text-on-surface-variant mt-1 px-1">Loading offline farmer data...</p>
          )}
          {farmerOptions.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg max-h-48 overflow-y-auto">
              {farmerOptions.map(f => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => selectFarmer(f)}
                  className="w-full text-left px-3 py-2 text-body-md text-on-surface hover:bg-surface-container transition-colors"
                >
                  {f.first_name} {f.last_name}
                  <span className="text-on-surface-variant text-label-sm ml-2">{f.phone_number}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {selectedFarmer && routeStops.length > 0 && (
          <div>
            <label htmlFor="record-route-stop" className="block text-label-md font-bold text-on-surface mb-1.5">Pickup stop</label>
            <select
              id="record-route-stop"
              value={pickedStop}
              onChange={(e) => setPickedStop(e.target.value)}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              disabled={isPending}
            >
              <option value="">— None —</option>
              {routeStops.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.route_name} — Stop {s.stop_order}
                </option>
              ))}
            </select>
            <p className="text-label-sm text-on-surface-variant mt-1">
              Coordinates below are pre-filled from the farmer's saved pickup location.
            </p>
          </div>
        )}

        {pickup && (
          <div>
            <p className="block text-label-md font-bold text-on-surface mb-1.5">Pickup location</p>
            <MapView deliveries={[]} pickupLocation={pickup} pickupLabel={selectedFarmer ? `${selectedFarmer.first_name}'s pickup` : 'Pickup'} height="180px" />
          </div>
        )}

        <div>
          <label htmlFor="record-product-type" className="block text-label-md font-bold text-on-surface mb-1.5">Product Type *</label>
          <select
            id="record-product-type"
            name="product_type"
            defaultValue="MILK"
            className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
            disabled={isPending}
          >
            {productTypes.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="record-quantity" className="block text-label-md font-bold text-on-surface mb-1.5">Quantity (kg)</label>
            <input
              id="record-quantity"
              name="quantity_kg"
              type="number" step="0.01" min="0"
              placeholder="0.00"
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
              disabled={isPending}
            />
          </div>
          <div>
            <label htmlFor="record-volume" className="block text-label-md font-bold text-on-surface mb-1.5">Volume (L)</label>
            <input
              id="record-volume"
              name="volume_litres"
              type="number" step="0.01" min="0"
              placeholder="0.00"
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
              disabled={isPending}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="record-shift" className="block text-label-md font-bold text-on-surface mb-1.5">Shift *</label>
            <select
              id="record-shift"
              name="shift"
              defaultValue="AM"
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              disabled={isPending}
            >
              <option value="AM">AM</option>
              <option value="PM">PM</option>
            </select>
          </div>
          <div>
            <label htmlFor="record-date" className="block text-label-md font-bold text-on-surface mb-1.5">Date Delivered</label>
            <input
              id="record-date"
              name="date_delivered"
              type="date"
              defaultValue={new Date().toISOString().slice(0, 10)}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              disabled={isPending}
            />
          </div>
        </div>

        <input type="hidden" name="farmer" value={selectedFarmer?.id || ''} />
        <input type="hidden" name="latitude" value={latitude} />
        <input type="hidden" name="longitude" value={longitude} />
        <input type="hidden" name="route_stop" value={pickedStop} />

        <div className="flex justify-end">
          <button
            type="button"
            onClick={useMyLocation}
            disabled={geoBusy}
            className="text-label-sm text-primary font-bold disabled:opacity-50"
          >
            {geoBusy ? 'Locating…' : 'Use my current location'}
          </button>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button type="button" onClick={() => navigate(-1)} className="px-6 py-2.5 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors" disabled={isPending}>
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending || !selectedFarmer}
            className="flex-1 px-6 py-2.5 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isPending && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            {isPending ? 'Recording...' : 'Record Delivery'}
          </button>
        </div>
      </form>
    </div>
  )
}

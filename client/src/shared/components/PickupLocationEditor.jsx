import { useEffect, useRef, useState } from 'react'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { apiFetch } from '../../admin/api/client'

const baseIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})
L.Marker.prototype.options.icon = baseIcon

const pickupIcon = L.divIcon({
  className: 'pickup-pin',
  html: '<div style="background:#2563eb;width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 0 0 1px #2563eb"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
})

/**
 * Inline map picker for a farmer's pickup location.
 * Click the map (or use the "Use my location" button) to set lat/lng.
 *
 * Props:
 *  - farmerId: the farmer whose location to set
 *  - initial: { latitude, longitude } (may be null)
 *  - height: CSS height
 *  - onSaved(location): callback after a successful PATCH
 */
export default function PickupLocationEditor({ farmerId, initial = null, height = '280px', onSaved }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markerRef = useRef(null)
  const [lat, setLat] = useState(initial?.latitude ?? '')
  const [lng, setLng] = useState(initial?.longitude ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  // Stash the initial values so the effect dependency array stays empty.
  const initialRef = useRef(initial)
  // Keep the ref in sync with prop changes via effect (avoids writing during render).
  useEffect(() => {
    initialRef.current = initial
  }, [initial])

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return
    const init = initialRef.current
    const map = L.map(mapRef.current).setView(
      init?.latitude != null ? [init.latitude, init.longitude] : [0, 20],
      init?.latitude != null ? 14 : 2,
    )
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)
    if (init?.latitude != null && init?.longitude != null) {
      markerRef.current = L.marker([init.latitude, init.longitude], {
        icon: pickupIcon,
        draggable: true,
      }).addTo(map)
      markerRef.current.on('dragend', () => {
        const ll = markerRef.current.getLatLng()
        setLat(ll.lat)
        setLng(ll.lng)
      })
    }
    if (initial?.latitude != null && initial?.longitude != null) {
      markerRef.current = L.marker([initial.latitude, initial.longitude], {
        icon: pickupIcon,
        draggable: true,
      }).addTo(map)
      markerRef.current.on('dragend', () => {
        const ll = markerRef.current.getLatLng()
        setLat(ll.lat)
        setLng(ll.lng)
      })
    }
    map.on('click', (e) => {
      const { lat: la, lng: ln } = e.latlng
      setLat(la)
      setLng(ln)
      if (markerRef.current) {
        markerRef.current.setLatLng(e.latlng)
      } else {
        markerRef.current = L.marker(e.latlng, { icon: pickupIcon, draggable: true }).addTo(map)
        markerRef.current.on('dragend', () => {
          const ll = markerRef.current.getLatLng()
          setLat(ll.lat)
          setLng(ll.lng)
        })
      }
    })
    mapInstanceRef.current = map
    return () => {
      map.remove()
      mapInstanceRef.current = null
      markerRef.current = null
    }
  }, [farmerId])

  const useMyLocation = () => {
    if (!('geolocation' in navigator)) {
      setError('Geolocation not available in this browser.')
      return
    }
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const la = pos.coords.latitude
        const ln = pos.coords.longitude
        setLat(la); setLng(ln)
        if (mapInstanceRef.current) {
          mapInstanceRef.current.setView([la, ln], 16)
        }
        if (markerRef.current) {
          markerRef.current.setLatLng([la, ln])
        } else if (mapInstanceRef.current) {
          markerRef.current = L.marker([la, ln], { icon: pickupIcon, draggable: true })
            .addTo(mapInstanceRef.current)
          markerRef.current.on('dragend', () => {
            const ll = markerRef.current.getLatLng()
            setLat(ll.lat); setLng(ll.lng)
          })
        }
      },
      (err) => setError(err.message || 'Could not get your location.'),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  }

  const save = async () => {
    if (lat === '' || lng === '') {
      setError('Pick a location first.')
      return
    }
    setSaving(true); setError(null); setSaved(false)
    try {
      const res = await apiFetch(`/api/farmers/${farmerId}/location/`, {
        method: 'PATCH',
        body: JSON.stringify({ latitude: Number(lat).toFixed(6), longitude: Number(lng).toFixed(6) }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(typeof err === 'string' ? err : JSON.stringify(err))
      }
      setSaved(true)
      onSaved?.({ latitude: Number(lat), longitude: Number(lng) })
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg overflow-hidden" style={{ height }} role="application" aria-label="Pickup location picker">
        <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="pickup-lat" className="block text-label-sm text-on-surface-variant mb-1">Latitude</label>
          <input
            id="pickup-lat"
            type="number"
            step="any"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          />
        </div>
        <div>
          <label htmlFor="pickup-lng" className="block text-label-sm text-on-surface-variant mb-1">Longitude</label>
          <input
            id="pickup-lng"
            type="number"
            step="any"
            value={lng}
            onChange={(e) => setLng(e.target.value)}
            className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          />
        </div>
      </div>
      {error && <p className="text-label-sm text-error" role="alert">{error}</p>}
      {saved && <p className="text-label-sm text-success" role="status">Pickup location saved.</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={useMyLocation}
          className="px-3 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high"
        >
          Use my location
        </button>
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="flex-1 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save pickup location'}
        </button>
      </div>
    </div>
  )
}

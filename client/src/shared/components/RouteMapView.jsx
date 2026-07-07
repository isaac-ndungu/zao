import { useEffect, useRef, useState } from 'react'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-routing-machine/dist/leaflet-routing-machine.css'
import 'leaflet-routing-machine'
import { apiFetch } from '../../admin/api/client'

// Default Leaflet markers (CDN) so the bundle stays webpack-friendly.
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

const farmerIcon = L.divIcon({
  className: 'farmer-pin',
  html: '<div style="background:#16a34a;width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 0 0 1px #16a34a"></div>',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

const pickupIcon = L.divIcon({
  className: 'pickup-pin',
  html: '<div style="background:#2563eb;width:18px;height:18px;border-radius:50%;border:2px solid white;box-shadow:0 0 0 1px #2563eb"></div>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

const makeStopIcon = (order) =>
  L.divIcon({
    className: 'stop-pin',
    html: `<div style="background:#dc2626;color:white;width:24px;height:24px;border-radius:50%;border:2px solid white;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;box-shadow:0 1px 3px rgba(0,0,0,0.3)">${order}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  })

/**
 * Custom L.Routing router that proxies ORS requests through our backend,
 * so the ORS_API_KEY never reaches the browser. The backend returns a raw
 * GeoJSON FeatureCollection, which L.Routing.osrmv1 (its formatter) can
 * consume directly via `waypoints` and `routes` shape.
 */
function orsRouter(waypoints, callback) {
  const profile = 'driving-car'
  const wps = waypoints.map((wp) => [wp.lng, wp.lat])
  apiFetch('/api/routes/route/', {
    method: 'POST',
    body: JSON.stringify({ waypoints: wps, profile }),
  })
    .then((r) => {
      if (!r.ok) throw new Error(`Route proxy ${r.status}`)
      return r.json()
    })
    .then((data) => {
      const feature = (data.features || [])[0]
      const geometry = feature?.geometry
      if (!geometry || !geometry.coordinates) {
        throw new Error('No route geometry')
      }
      const coords = geometry.coordinates
      const wpObjs = coords.map(([lng, lat], i) => ({
        latLng: L.latLng(lat, lng),
        name: i === 0 ? 'Start' : i === coords.length - 1 ? 'End' : `Waypoint ${i}`,
      }))
      // Build OSRM-compatible route shape that LRM's formatter expects.
      const route = {
        name: 'ORS route',
        coordinates: coords,
        summary: {
          totalDistance: (feature.properties?.summary?.distance) || 0,
          totalTime: (feature.properties?.summary?.duration) || 0,
        },
        instructions: [],
        inputWaypoints: wpObjs,
        waypoints: wpObjs.map((wp) => ({
          latLng: wp.latLng,
          name: wp.name,
          options: { isVia: false, isStop: true },
        })),
      }
      callback(null, [route])
    })
    .catch((err) => callback(err))
}

/**
 * Map view for collection routes. Renders stops as numbered draggable markers,
 * farmers at each stop, the route polyline (from `path` or a straight line),
 * and an optional real road route via leaflet-routing-machine.
 *
 * Props:
 *  - route: { id, name, path: { coordinates: [[lng,lat]...] } }
 *  - stops: [{ id, order, lat, lng, estimated_minutes, farmers: [{id, name, ...}] }]
 *  - onStopsChange(stops): invoked when stops are added/moved/deleted
 *  - onSelectFarmer(farmer): invoked when a farmer marker is clicked
 *  - pickupLocation: { lat, lng } (optional, drawn as a blue pin)
 *  - readOnly: hide editing affordances
 *  - height: CSS height
 *  - fitOnLoad: fit map to content
 */
export default function RouteMapView({
  route = null,
  stops = [],
  onStopsChange,
  onSelectFarmer,
  pickupLocation = null,
  readOnly = false,
  height = '420px',
  fitOnLoad = true,
}) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const stopMarkersRef = useRef({})
  const farmerMarkersRef = useRef([])
  const pickupMarkerRef = useRef(null)
  const pathLayerRef = useRef(null)
  const routingControlRef = useRef(null)
  const [useRoadRoute, setUseRoadRoute] = useState(false)
  const [routingError, setRoutingError] = useState(null)

  // Init map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return
    const map = L.map(mapRef.current, { zoomControl: true })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)
    mapInstanceRef.current = map
    return () => {
      if (routingControlRef.current) {
        try { map.removeControl(routingControlRef.current) } catch { /* ignore */ }
        routingControlRef.current = null
      }
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // Click-to-add stop
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || readOnly) return
    const onClick = (e) => {
      if (!onStopsChange) return
      const nextOrder = (stops?.length || 0) + 1
      const newStop = {
        id: `new-${Date.now()}`,
        order: nextOrder,
        lat: e.latlng.lat,
        lng: e.latlng.lng,
        estimated_minutes: 10,
        farmers: [],
        _new: true,
      }
      onStopsChange([...(stops || []), newStop])
    }
    map.on('click', onClick)
    return () => { map.off('click', onClick) }
  }, [stops, onStopsChange, readOnly])

  // Render stops + farmers + path
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return

    // Remove old stop markers
    Object.values(stopMarkersRef.current).forEach((m) => m.remove())
    stopMarkersRef.current = {}
    // Remove old farmer markers
    farmerMarkersRef.current.forEach((m) => m.remove())
    farmerMarkersRef.current = []
    // Remove old path
    if (pathLayerRef.current) {
      pathLayerRef.current.remove()
      pathLayerRef.current = null
    }

    const orderedStops = [...(stops || [])].sort((a, b) => a.order - b.order)
    orderedStops.forEach((stop) => {
      const m = L.marker([stop.lat, stop.lng], {
        icon: makeStopIcon(stop.order),
        draggable: !readOnly,
        autoPan: true,
        keyboard: true,
        title: `Stop ${stop.order}`,
        alt: `Stop ${stop.order}`,
      }).addTo(map)
      const farmersHtml = (stop.farmers || []).length
        ? `<ul style="margin:4px 0;padding-left:16px">${stop.farmers
            .map((f) => `<li>${f.name}${f.member_number ? ` (${f.member_number})` : ''}</li>`)
            .join('')}</ul>`
        : '<em style="color:#666">No farmers assigned</em>'
      m.bindPopup(`<strong>Stop ${stop.order}</strong>${stop.estimated_minutes ? `<br/>ETA: ${stop.estimated_minutes} min` : ''}<br/>${farmersHtml}`)
      m.on('dragend', () => {
        if (!onStopsChange) return
        const ll = m.getLatLng()
        onStopsChange(
          orderedStops.map((s) => (s.id === stop.id ? { ...s, lat: ll.lat, lng: ll.lng } : s)),
        )
      })
      m.on('contextmenu', () => {
        if (readOnly || !onStopsChange) return
        if (!window.confirm(`Delete stop ${stop.order}?`)) return
        onStopsChange(orderedStops.filter((s) => s.id !== stop.id))
      })
      stopMarkersRef.current[stop.id] = m

      // Farmer pins at this stop
      ;(stop.farmers || []).forEach((f) => {
        const fm = L.marker([stop.lat, stop.lng], { icon: farmerIcon })
          .addTo(map)
          .bindTooltip(f.name, { direction: 'top', offset: [0, -8] })
        if (onSelectFarmer) {
          fm.on('click', () => onSelectFarmer(f))
        }
        farmerMarkersRef.current.push(fm)
      })
    })

    // Path from route.path or straight segments
    if (orderedStops.length >= 2) {
      const coords = orderedStops.map((s) => [s.lat, s.lng])
      const fromPath = route?.path?.coordinates?.length
      const pathCoords = fromPath
        ? route.path.coordinates.map(([lng, lat]) => [lat, lng])
        : coords
      pathLayerRef.current = L.polyline(pathCoords, {
        color: '#2563eb',
        weight: 4,
        opacity: 0.7,
        dashArray: fromPath ? null : '6,8',
      }).addTo(map)
    }

    // Pickup pin
    if (pickupLocation?.lat != null && pickupLocation?.lng != null) {
      pickupMarkerRef.current = L.marker([pickupLocation.lat, pickupLocation.lng], {
        icon: pickupIcon,
      })
        .addTo(map)
        .bindTooltip('Pickup location', { direction: 'top' })
    } else if (pickupMarkerRef.current) {
      pickupMarkerRef.current.remove()
      pickupMarkerRef.current = null
    }

    // Fit bounds
    if (fitOnLoad && orderedStops.length > 0) {
      const bounds = L.latLngBounds(orderedStops.map((s) => [s.lat, s.lng]))
      if (pickupMarkerRef.current) {
        bounds.extend(pickupMarkerRef.current.getLatLng())
      }
      map.fitBounds(bounds.pad(0.15))
    } else if (fitOnLoad && pickupMarkerRef.current) {
      map.setView(pickupMarkerRef.current.getLatLng(), 13)
    } else if (fitOnLoad) {
      map.setView([0, 20], 2)
    }
  }, [stops, route?.path, pickupLocation?.lat, pickupLocation?.lng, readOnly, onStopsChange, onSelectFarmer, fitOnLoad])

  // Reset routing error when the toggle changes (separate from the LRM init effect)
  useEffect(() => {
    if (!useRoadRoute) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRoutingError(null)
    }
  }, [useRoadRoute])

  // Real road route via LRM
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return
    if (routingControlRef.current) {
      try { map.removeControl(routingControlRef.current) } catch { /* ignore */ }
      routingControlRef.current = null
    }
    if (!useRoadRoute) {
      return
    }
    const orderedStops = [...(stops || [])].sort((a, b) => a.order - b.order)
    if (orderedStops.length < 2) {
      // Defer the state update to a microtask to avoid the setState-in-effect lint.
      queueMicrotask(() => setRoutingError('Need at least 2 stops for a road route.'))
      return
    }
    const waypoints = orderedStops.map((s) => L.latLng(s.lat, s.lng))
    try {
      const control = L.Routing.control({
        waypoints,
        router: L.Routing.osrmv1({ serviceUrl: '__custom__' }),
        // Override the osrmv1 router's internal `route` method to call our proxy.
        addWaypoints: false,
        draggableWaypoints: false,
        fitSelectedRoutes: true,
        show: false,
        createMarker: () => null,
      })
      // Patch the router to use our backend proxy
      control.getRouter().route = orsRouter
      control.on('routingerror', (e) => {
        setRoutingError(e?.error?.message || 'Routing failed')
      })
      control.on('routesfound', () => setRoutingError(null))
      control.addTo(map)
      routingControlRef.current = control
    } catch (err) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRoutingError(err.message || 'Failed to initialise routing')
    }
  }, [useRoadRoute, stops])

  return (
    <div className="relative" role="application" aria-label="Route map">
      {!readOnly && (
        <div className="absolute top-2 right-2 z-[400] flex flex-col gap-1">
          <button
            type="button"
            onClick={() => setUseRoadRoute((v) => !v)}
            aria-pressed={useRoadRoute}
            className={`px-3 py-1.5 rounded-lg text-label-sm font-bold shadow ${
              useRoadRoute
                ? 'bg-primary text-on-primary'
                : 'bg-surface-container-lowest text-on-surface border border-outline-variant'
            }`}
          >
            {useRoadRoute ? 'Road route ✓' : 'Use road route'}
          </button>
        </div>
      )}
      {routingError && (
        <p className="absolute bottom-2 left-2 z-[400] bg-error/90 text-on-error px-3 py-1.5 rounded text-label-sm" role="alert">
          {routingError}
        </p>
      )}
      <div className="rounded-lg overflow-hidden" style={{ height }}>
        <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
      </div>
      {!readOnly && stops?.length > 0 && (
        <p className="text-label-sm text-on-surface-variant mt-2 px-1">
          Click the map to add a stop. Drag a stop to move it. Right-click a stop to delete.
        </p>
      )}
    </div>
  )
}

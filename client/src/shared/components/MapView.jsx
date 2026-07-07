import { useEffect, useRef } from 'react'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

L.Marker.prototype.options.icon = defaultIcon

export default function MapView({
  deliveries = [],
  height = '320px',
  center = null,
  zoom = 13,
  pickupLocation = null,
  pickupLabel = 'Pickup location',
}) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const pickupMarkerRef = useRef(null)

  useEffect(() => {
    if (!mapRef.current) return

    const deliveriesWithLocation = deliveries.filter(d => d.latitude && d.longitude)

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove()
      mapInstanceRef.current = null
    }

    const map = L.map(mapRef.current)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)

    const pickupIcon = L.divIcon({
      className: 'pickup-pin',
      html: '<div style="background:#2563eb;width:18px;height:18px;border-radius:50%;border:2px solid white;box-shadow:0 0 0 1px #2563eb"></div>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    })

    deliveriesWithLocation.forEach(delivery => {
      const popupContent = `
        <div style="min-width: 150px;">
          <strong>${delivery.farmer_name || 'Unknown Farmer'}</strong><br/>
          ${delivery.batch_id ? `Batch: ${delivery.batch_id}<br/>` : ''}
          ${delivery.product_type ? `${delivery.product_type}<br/>` : ''}
          ${delivery.quantity_kg ? `Qty: ${delivery.quantity_kg} kg` : ''}
        </div>
      `
      L.marker([parseFloat(delivery.latitude), parseFloat(delivery.longitude)])
        .addTo(map)
        .bindPopup(popupContent)
    })

    if (pickupLocation?.lat != null && pickupLocation?.lng != null) {
      pickupMarkerRef.current = L.marker([parseFloat(pickupLocation.lat), parseFloat(pickupLocation.lng)], {
        icon: pickupIcon,
      })
        .addTo(map)
        .bindTooltip(pickupLabel, { direction: 'top' })
    }

    const points = []
    if (deliveriesWithLocation.length > 0) {
      deliveriesWithLocation.forEach(d => points.push([parseFloat(d.latitude), parseFloat(d.longitude)]))
    }
    if (pickupMarkerRef.current) {
      points.push(pickupMarkerRef.current.getLatLng())
    }

    if (points.length > 0) {
      const group = L.featureGroup(points.map(p => L.marker(p)))
      map.fitBounds(group.getBounds().pad(0.1))
    } else if (center) {
      map.setView(center, zoom)
    } else {
      map.setView([0, 20], 2)
    }

    mapInstanceRef.current = map

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [deliveries, center, zoom, pickupLocation?.lat, pickupLocation?.lng, pickupLabel])

  return (
    <div className="rounded-lg overflow-hidden" style={{ height }} role="img" aria-label="Map showing delivery locations">
      <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}

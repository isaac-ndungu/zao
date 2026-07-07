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

export default function MapView({ deliveries = [], height = '320px', center = null, zoom = 13 }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)

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

    if (deliveriesWithLocation.length > 0) {
      const group = L.featureGroup(deliveriesWithLocation.map(d =>
        L.marker([parseFloat(d.latitude), parseFloat(d.longitude)])
      ))
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
  }, [deliveries, center, zoom])

  return (
    <div className="rounded-lg overflow-hidden" style={{ height }} role="img" aria-label="Map showing delivery locations">
      <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}

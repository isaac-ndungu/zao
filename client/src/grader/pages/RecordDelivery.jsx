import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { useOnlineStatus } from '../../shared/hooks/useOnlineStatus'
import { saveDelivery, cacheFarmers, getCachedFarmers, searchCachedFarmers } from '../services/offlineQueue'

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
  const [submitting, setSubmitting] = useState(false)
  const [farmerSearch, setFarmerSearch] = useState('')
  const [farmerOptions, setFarmerOptions] = useState([])
  const [selectedFarmer, setSelectedFarmer] = useState(null)
  const [cachedFarmersList, setCachedFarmersList] = useState(null)
  const [justSelected, setJustSelected] = useState(false)

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

  const [form, setForm] = useState({
    farmer: '',
    product_type: 'MILK',
    quantity_kg: '',
    volume_litres: '',
    shift: 'AM',
    date_delivered: new Date().toISOString().slice(0, 10),
    latitude: '',
    longitude: '',
  })

  const searchFarmer = async (q) => {
    if (justSelected) { setJustSelected(false); return }
    setFarmerSearch(q)
    setSelectedFarmer(null)
    setForm(f => ({ ...f, farmer: '' }))
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

  const selectFarmer = (farmer) => {
    setSelectedFarmer(farmer)
    setForm(f => ({ ...f, farmer: farmer.id }))
    setFarmerSearch(`${farmer.first_name} ${farmer.last_name} (${farmer.phone_number || farmer.id.slice(0, 8)})`)
    setFarmerOptions([])
    setJustSelected(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.farmer) {
      showToast({ type: 'error', message: 'Select a farmer.' })
      return
    }
    setSubmitting(true)
    try {
      const body = { ...form, farmer_id: form.farmer, farmer_name: farmerSearch }
      if (!body.quantity_kg) delete body.quantity_kg
      if (!body.volume_litres) delete body.volume_litres
      if (!body.latitude) delete body.latitude
      if (!body.longitude) delete body.longitude
      if (isOnline) {
        const res = await apiFetch('/api/deliveries/', { method: 'POST', body: JSON.stringify(body) })
        if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to create delivery') }
        showToast({ type: 'success', message: 'Delivery recorded.' })
        navigate('/grader/grade')
      } else {
        await saveDelivery(body)
        showToast({ type: 'success', message: 'Delivery saved offline. Will sync when online.' })
        navigate('/grader/grade')
      }
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSubmitting(false) }
  }

  return (
    <div className="max-w-lg mx-auto">
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Record Delivery</h2>
        <p className="text-on-surface-variant font-body-md">Log a new delivery from a farmer</p>
      </header>

      <form onSubmit={handleSubmit} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 space-y-4">
        <div className="relative">
          <label htmlFor="record-farmer" className="block text-label-md font-bold text-on-surface mb-1.5">Farmer *</label>
          <input
            id="record-farmer"
            type="text"
            value={farmerSearch}
            onChange={(e) => searchFarmer(e.target.value)}
            placeholder="Search by name or phone..."
            className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
            disabled={submitting}
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

        <div>
          <label htmlFor="record-product-type" className="block text-label-md font-bold text-on-surface mb-1.5">Product Type *</label>
          <select
            id="record-product-type"
            value={form.product_type}
            onChange={(e) => setForm(f => ({ ...f, product_type: e.target.value }))}
            className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
            disabled={submitting}
          >
            {productTypes.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="record-quantity" className="block text-label-md font-bold text-on-surface mb-1.5">Quantity (kg)</label>
            <input
              id="record-quantity"
              type="number" step="0.01" min="0"
              value={form.quantity_kg}
              onChange={(e) => setForm(f => ({ ...f, quantity_kg: e.target.value }))}
              placeholder="0.00"
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
              disabled={submitting}
            />
          </div>
          <div>
            <label htmlFor="record-volume" className="block text-label-md font-bold text-on-surface mb-1.5">Volume (L)</label>
            <input
              id="record-volume"
              type="number" step="0.01" min="0"
              value={form.volume_litres}
              onChange={(e) => setForm(f => ({ ...f, volume_litres: e.target.value }))}
              placeholder="0.00"
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
              disabled={submitting}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="record-shift" className="block text-label-md font-bold text-on-surface mb-1.5">Shift *</label>
            <select
              id="record-shift"
              value={form.shift}
              onChange={(e) => setForm(f => ({ ...f, shift: e.target.value }))}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              disabled={submitting}
            >
              <option value="AM">AM</option>
              <option value="PM">PM</option>
            </select>
          </div>
          <div>
            <label htmlFor="record-date" className="block text-label-md font-bold text-on-surface mb-1.5">Date Delivered</label>
            <input
              id="record-date"
              type="date"
              value={form.date_delivered}
              onChange={(e) => setForm(f => ({ ...f, date_delivered: e.target.value }))}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              disabled={submitting}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="record-latitude" className="block text-label-md font-bold text-on-surface mb-1.5">Latitude</label>
            <input
              id="record-latitude"
              type="number" step="any"
              value={form.latitude}
              onChange={(e) => setForm(f => ({ ...f, latitude: e.target.value }))}
              placeholder="Optional"
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
              disabled={submitting}
            />
          </div>
          <div>
            <label htmlFor="record-longitude" className="block text-label-md font-bold text-on-surface mb-1.5">Longitude</label>
            <input
              id="record-longitude"
              type="number" step="any"
              value={form.longitude}
              onChange={(e) => setForm(f => ({ ...f, longitude: e.target.value }))}
              placeholder="Optional"
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant"
              disabled={submitting}
            />
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button type="button" onClick={() => navigate(-1)} className="px-6 py-2.5 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors" disabled={submitting}>
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !form.farmer}
            className="flex-1 px-6 py-2.5 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {submitting && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            {submitting ? 'Recording...' : 'Record Delivery'}
          </button>
        </div>
      </form>
    </div>
  )
}

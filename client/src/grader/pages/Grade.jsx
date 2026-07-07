import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useOnlineStatus } from '../../shared/hooks/useOnlineStatus'
import { useToast } from '../../admin/contexts/ToastContext'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import ErrorState from '../../shared/components/ErrorState'
import { saveGrade, cachePendingDeliveries, getCachedPendingDeliveries } from '../services/offlineQueue'

const gradeOptions = ['PREMIUM', 'STANDARD', 'A', 'B', 'C']

export default function Grade() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const preSelectedDelivery = searchParams.get('delivery') || searchParams.get('selected')

  const [selectedDelivery, setSelectedDelivery] = useState(null)
  const [page, setPage] = useState(1)
  const [queueSearch, setQueueSearch] = useState('')
  const [cachedDeliveries, setCachedDeliveries] = useState([])
  const [showCached, setShowCached] = useState(false)

  const { data: pricesData } = useApi('/api/grades/prices/')
  const searchParam = queueSearch ? `&search=${encodeURIComponent(queueSearch)}` : ''
  const { data: pendingData, loading, error, refetch } = useApi(`/api/deliveries/?status=PENDING&page=${page}&page_size=10&ordering=-date_delivered${searchParam}`)

  // Cache successful delivery fetches for offline use
  useEffect(() => {
    if (pendingData?.results) {
      cachePendingDeliveries(pendingData.results)
    }
  }, [pendingData])

  // On error (offline), try loading cached deliveries
  useEffect(() => {
    if (error) {
      getCachedPendingDeliveries().then(cached => {
        if (cached) {
          setCachedDeliveries(cached)
          setShowCached(true)
        }
      })
    } else {
      setShowCached(false)
      setCachedDeliveries([])
    }
  }, [error])

  const prices = pricesData?.results || pricesData || []
  const priceMap = {}
  prices.forEach(p => { priceMap[p.grade_letter] = p.price_per_unit })

  const pendingDeliveries = showCached ? cachedDeliveries : (pendingData?.results || [])

  const autoSelected = preSelectedDelivery && pendingDeliveries.length > 0
    ? pendingDeliveries.find(d => d.id === preSelectedDelivery)
    : null
  if (autoSelected && !selectedDelivery) setSelectedDelivery(autoSelected)

  const handleSelectDelivery = (delivery) => {
    setSelectedDelivery(delivery)
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Grade Delivery</h2>
        <p className="text-on-surface-variant font-body-md">
          {selectedDelivery
            ? `Grading: ${selectedDelivery.batch_id} — ${selectedDelivery.farmer_name}`
            : 'Select a delivery from the queue to grade'}
        </p>
      </header>

      {!selectedDelivery ? (
        <>
          <div className="mb-4 flex items-center gap-4">
            <form onSubmit={(e) => { e.preventDefault(); setQueueSearch(new FormData(e.target).get('search') || ''); setPage(1) }} className="flex gap-2">
              <input
                name="search"
                defaultValue={queueSearch}
                placeholder="Search batch ID or farmer..."
                className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-72"
                aria-label="Search deliveries by batch ID or farmer name"
              />
              <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold" aria-label="Submit search">Search</button>
            </form>
            <button onClick={() => { setSelectedDelivery(null); refetch() }} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold flex items-center gap-2" aria-label="Refresh delivery queue">
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">refresh</span>Refresh
            </button>
            {showCached && (
              <span className="text-label-md text-warning" role="status">Showing cached data (offline)</span>
            )}
          </div>

          {loading ? <TableSkeleton rows={8} cols={5} /> : error && !showCached ? <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} /> : (
            <>
              <DataTable
                columns={[
                  { key: 'batch_id', label: 'Batch ID' },
                  { key: 'farmer_name', label: 'Farmer' },
                  { key: 'product_type', label: 'Product' },
                  { key: 'quantity_kg', label: 'Qty', render: (v, r) => v ? `${v} kg` : r.volume_litres ? `${r.volume_litres} L` : '-' },
                  { key: 'date_delivered', label: 'Time', render: (v, _r) => v ? new Date(v).toLocaleString() : '-' },
                ]}
                data={pendingDeliveries}
                onRowClick={(row) => handleSelectDelivery(row)}
                emptyMessage="No pending deliveries."
              />
              <Pagination page={page} pageSize={10} total={pendingData?.count || 0} onPageChange={setPage} onPageSizeChange={() => {}} />
            </>
          )}
        </>
      ) : (
        <GradeForm
          delivery={selectedDelivery}
          priceMap={priceMap}
          onBack={() => setSelectedDelivery(null)}
          onComplete={() => { setSelectedDelivery(null); navigate('/grader/my-grades') }}
        />
      )}
    </div>
  )
}

function GradeForm({ delivery, priceMap, onBack, onComplete }) {
  const isOnline = useOnlineStatus()
  const { showToast } = useToast()

  const [grade, setGrade] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [qualityMetrics, setQualityMetrics] = useState('{}')
  const [photos, setPhotos] = useState([])
  const [photoPreviews, setPhotoPreviews] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [jsonError, setJsonError] = useState('')

  useEffect(() => {
    return () => photoPreviews.forEach(url => URL.revokeObjectURL(url))
  }, [photoPreviews])

  const handlePhotoAdd = (e) => {
    const files = Array.from(e.target.files || [])
    const remaining = 5 - photos.length
    const toAdd = files.slice(0, remaining)
    setPhotos(prev => [...prev, ...toAdd])
    setPhotoPreviews(prev => [...prev, ...toAdd.map(f => URL.createObjectURL(f))])
  }

  const handlePhotoRemove = (index) => {
    URL.revokeObjectURL(photoPreviews[index])
    setPhotos(prev => prev.filter((_, i) => i !== index))
    setPhotoPreviews(prev => prev.filter((_, i) => i !== index))
  }

  const handleJsonChange = (val) => {
    setQualityMetrics(val)
    if (!val) { setJsonError(''); return }
    try {
      JSON.parse(val)
      setJsonError('')
    } catch {
      setJsonError('Invalid JSON')
    }
  }

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      showToast({ type: 'error', message: 'Provide a reason for rejection.' })
      return
    }
    setSubmitting(true)
    try {
      if (!isOnline) {
        await saveGrade({
          delivery_id: delivery.id,
          delivery_batch_id: delivery.batch_id,
          farmer_name: delivery.farmer_name,
          rejection_reason: rejectReason.trim(),
          quality_metrics: qualityMetrics !== '{}' ? qualityMetrics : null,
        })
        showToast({ type: 'success', message: 'Rejection saved offline. Will sync when online.' })
        onComplete()
        return
      }
      const body = {
        delivery: delivery.id,
        rejection_reason: rejectReason.trim(),
      }
      const res = await apiFetch('/api/grades/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Rejection failed') }
      showToast({ type: 'success', message: 'Delivery rejected.' })
      onComplete()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSubmitting(false) }
  }

  const uploadPhotos = async (gradeId) => {
    if (photos.length === 0) return
    for (const photo of photos) {
      try {
        const fd = new FormData()
        fd.append('image', photo)
        await apiFetch(`/api/grades/${gradeId}/images/`, { method: 'POST', headers: {}, body: fd })
      } catch {
        showToast({ type: 'warning', message: `Photo upload failed — grade was saved.` })
      }
    }
  }

  const handleGrade = async () => {
    if (!grade) {
      showToast({ type: 'error', message: 'Select a grade.' })
      return
    }

    setSubmitting(true)
    try {
      if (!isOnline) {
        await saveGrade({
          delivery_id: delivery.id,
          delivery_batch_id: delivery.batch_id,
          farmer_name: delivery.farmer_name,
          grade_letter: grade,
          price_per_unit: priceMap[grade] || null,
          quality_metrics: qualityMetrics !== '{}' ? qualityMetrics : null,
        })
        showToast({ type: 'success', message: `Grade ${grade} saved offline. Will sync when online.` })
        onComplete()
        return
      }

      const body = {
        delivery: delivery.id,
        grade_letter: grade,
        price_per_unit: priceMap[grade] || null,
      }
      if (qualityMetrics !== '{}') {
        try { body.quality_metrics = JSON.parse(qualityMetrics) } catch {}
      }
      const res = await apiFetch('/api/grades/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Grading failed') }
      const gradeResult = await res.json()
      const gradeId = gradeResult.id

      await uploadPhotos(gradeId)

      showToast({ type: 'success', message: `Graded as ${grade}.` })
      onComplete()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSubmitting(false) }
  }

  return (
    <div>
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Delivery Details</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><p className="text-label-md text-on-surface-variant">Batch ID</p><p className="text-body-md text-on-surface font-medium">{delivery.batch_id}</p></div>
          <div><p className="text-label-md text-on-surface-variant">Farmer</p><p className="text-body-md text-on-surface font-medium">{delivery.farmer_name}</p></div>
          <div><p className="text-label-md text-on-surface-variant">Product</p><p className="text-body-md text-on-surface font-medium">{delivery.product_type || '-'}</p></div>
          <div><p className="text-label-md text-on-surface-variant">Quantity</p><p className="text-body-md text-on-surface font-medium">{delivery.quantity_kg ? `${delivery.quantity_kg} kg` : delivery.volume_litres ? `${delivery.volume_litres} L` : '-'}</p></div>
          <div><p className="text-label-md text-on-surface-variant">Shift</p><p className="text-body-md text-on-surface font-medium">{delivery.shift || '-'}</p></div>
          <div><p className="text-label-md text-on-surface-variant">Delivered</p><p className="text-body-md text-on-surface font-medium">{delivery.date_delivered ? new Date(delivery.date_delivered).toLocaleString() : '-'}</p></div>
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Quality Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label htmlFor="temperature" className="block text-label-md text-on-surface-variant mb-1">Temperature (°C)</label>
            <input
              id="temperature"
              type="number" step="0.1"
              onChange={(e) => {
                try {
                  const current = JSON.parse(qualityMetrics || '{}')
                  current.temperature = e.target.value ? Number(e.target.value) : undefined
                  setQualityMetrics(JSON.stringify(current))
                  setJsonError('')
                } catch {}
              }}
              className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
            />
          </div>
          <div>
            <label htmlFor="fat-content" className="block text-label-md text-on-surface-variant mb-1">Fat Content (%)</label>
            <input
              id="fat-content"
              type="number" step="0.01"
              onChange={(e) => {
                try {
                  const current = JSON.parse(qualityMetrics || '{}')
                  current.fat_content = e.target.value ? Number(e.target.value) : undefined
                  setQualityMetrics(JSON.stringify(current))
                  setJsonError('')
                } catch {}
              }}
              className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
            />
          </div>
        </div>
        <div>
          <label htmlFor="additional-metrics" className="block text-label-md text-on-surface-variant mb-1">Additional Metrics (JSON)</label>
          <textarea
            id="additional-metrics"
            value={qualityMetrics}
            onChange={(e) => handleJsonChange(e.target.value)}
            rows={3}
            placeholder='{"acidity": 0.15, "density": 1.032}'
            className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container font-mono"
          />
          {jsonError && <p role="alert" className="text-error text-label-md mt-1">{jsonError}</p>}
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h3 id="grade-selection-label" className="font-headline-sm text-headline-sm text-on-surface mb-4">Grade Selection</h3>
        <div
          role="radiogroup"
          aria-labelledby="grade-selection-label"
          className="flex flex-wrap gap-3 mb-4"
        >
          {gradeOptions.map(g => (
            <button
              key={g}
              type="button"
              role="radio"
              aria-checked={grade === g}
              aria-label={g === 'REJECT' ? 'Reject this delivery' : `Grade ${g}`}
              onClick={() => { setGrade(g); setRejectReason('') }}
              className={`px-6 py-3 rounded-lg text-label-md font-bold transition-colors ${
                grade === g
                  ? 'bg-primary text-on-primary ring-2 ring-primary'
                  : 'bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high'
              } ${rejectReason ? 'opacity-40 pointer-events-none' : ''}`}
            >
              <div>{g}</div>
              {priceMap[g] && <div className="text-[10px] opacity-80">KES {priceMap[g]}</div>}
            </button>
          ))}
        </div>

        {grade && priceMap[grade] && (
          <div className="px-4 py-3 bg-primary-container text-on-primary-container rounded-lg text-body-md font-medium" role="status">
            Price: KES {priceMap[grade]}/unit
          </div>
        )}
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Rejection</h3>
        <p className="text-body-md text-on-surface-variant mb-3">Use this section to reject the delivery instead of grading it.</p>
        <textarea
          id="rejection-reason"
          value={rejectReason}
          onChange={(e) => { setRejectReason(e.target.value); if (e.target.value) setGrade('') }}
          rows={3}
          placeholder="Enter rejection reason..."
          className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          aria-describedby="rejection-help"
        />
        <p id="rejection-help" className="text-label-md text-on-surface-variant mt-1">Providing a rejection reason will prevent grade selection.</p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Photos ({photos.length}/5)</h3>
        <div className="flex flex-wrap gap-3 mb-3">
          {photoPreviews.map((url, i) => (
            <div key={i} className="relative w-20 h-20 rounded-lg overflow-hidden border border-outline-variant">
              <img src={url} alt={`Photo ${i + 1} of delivery`} className="w-full h-full object-cover" />
              <button
                type="button"
                onClick={() => handlePhotoRemove(i)}
                aria-label={`Remove photo ${i + 1}`}
                className="absolute top-0 right-0 bg-error text-on-error rounded-bl-lg p-0.5"
              >
                <span className="material-symbols-outlined text-[14px]" aria-hidden="true">close</span>
              </button>
            </div>
          ))}
          {photos.length < 5 && (
            <label htmlFor="photo-upload" className="w-20 h-20 rounded-lg border-2 border-dashed border-outline-variant flex items-center justify-center cursor-pointer hover:bg-surface-container transition-colors">
              <span className="material-symbols-outlined text-on-surface-variant" aria-hidden="true">add</span>
              <input id="photo-upload" type="file" accept="image/*" capture="environment" onChange={handlePhotoAdd} className="hidden" aria-label="Add photo to delivery" />
            </label>
          )}
        </div>
        <p className="text-label-md text-on-surface-variant" role="status">
          {isOnline
            ? 'Upload photos of the delivery for quality verification.'
            : 'Photos cannot be taken offline. Grade now and add photos later.'}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="px-6 py-2.5 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors"
          aria-label="Back to grading queue"
        >
          Back to Queue
        </button>
        <div className="flex-1" />
        {rejectReason.trim() && !grade && (
          <button
            onClick={handleReject}
            disabled={submitting}
            className="px-6 py-2.5 bg-error text-on-error rounded-lg text-label-md font-bold hover:bg-error/90 transition-colors disabled:opacity-50"
            aria-label={submitting ? 'Saving rejection...' : 'Reject this delivery'}
          >
            {submitting ? <><span aria-hidden="true" className="inline-block animate-spin h-5 w-5 border-2 border-error/30 border-t-error rounded-full mr-2" /> Saving...</> : isOnline ? 'Reject Delivery' : 'Save Rejection Offline'}
          </button>
        )}
        {grade && !rejectReason.trim() && (
          <button
            onClick={handleGrade}
            disabled={submitting}
            className="px-6 py-2.5 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors disabled:opacity-50"
            aria-label={submitting ? 'Saving grade...' : `Submit grade ${grade} for this delivery`}
          >
            {submitting ? <><span aria-hidden="true" className="inline-block animate-spin h-5 w-5 border-2 border-primary/30 border-t-primary rounded-full mr-2" /> Saving...</> : isOnline ? `Submit Grade ${grade}` : `Save Grade ${grade} Offline`}
          </button>
        )}
      </div>
    </div>
  )
}

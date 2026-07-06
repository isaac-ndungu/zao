import { apiFetch } from '../../admin/api/client'
import * as offlineQueue from './offlineQueue'

const MAX_RETRIES = 3
const RETRYABLE_ERRORS = ['Server error', 'Network error', 'ECONNREFUSED', 'ETIMEDOUT']

function chunk(arr, size) {
  const result = []
  for (let i = 0; i < arr.length; i += size) result.push(arr.slice(i, i + size))
  return result
}

function isRetryable(error) {
  if (!error) return true
  return RETRYABLE_ERRORS.some(e => String(error).includes(e))
}

class SyncManager {
  constructor() {
    this._interval = null
  }

  async syncAll() {
    if (!navigator.onLine) return { synced: 0, failed: 0 }
    let synced = 0
    let failed = 0

    const pendingDeliveries = await offlineQueue.getPendingDeliveries()
    const toRetry = pendingDeliveries.filter(d => d.retry_count > 0 && d.retry_count < MAX_RETRIES && isRetryable(d.last_error))
    const toProcess = pendingDeliveries.filter(d => !d.retry_count || d.retry_count < MAX_RETRIES)

    if (toProcess.length > 0) {
      const batches = chunk(toProcess, 50)
      for (const batch of batches) {
        const payload = {
          deliveries: batch.map(d => ({
            local_id: d.local_id,
            farmer: d.farmer_id,
            product_type: d.product_type,
            quantity_kg: d.quantity_kg,
            volume_litres: d.volume_litres,
            shift: d.shift,
            quality_metrics: d.quality_metrics,
            latitude: d.latitude,
            longitude: d.longitude,
            status: 'PENDING',
          })),
        }
        try {
          const res = await apiFetch('/api/deliveries/sync/', { method: 'POST', body: JSON.stringify(payload) })
          if (res.ok) {
            const data = await res.json()
            if (data.synced) {
              for (const s of data.synced) { await offlineQueue.markSynced(s.local_id) }
              synced += data.synced.length
            }
          } else if (res.status === 409) {
            const errData = await res.json()
            if (errData.conflicts) {
              for (const c of errData.conflicts) { await offlineQueue.markSynced(c.local_id) }
              synced += errData.conflicts.length
            }
          } else {
            const errData = await res.json().catch(() => ({}))
            const errorMsg = Object.values(errData).flat().join(', ') || 'Server error'
            for (const d of batch) {
              if (d.retry_count >= MAX_RETRIES - 1) {
                await offlineQueue.markFailed(d.local_id, errorMsg)
                failed++
              }
            }
          }
        } catch (e) {
          for (const d of batch) {
            if (d.retry_count >= MAX_RETRIES - 1) {
              await offlineQueue.markFailed(d.local_id, e.message)
              failed++
            }
          }
        }
      }
      await offlineQueue.deleteSynced()
    }

    if (toRetry.length > 0) {
      const batches = chunk(toRetry, 50)
      for (const batch of batches) {
        const payload = {
          deliveries: batch.map(d => ({
            local_id: d.local_id,
            farmer: d.farmer_id,
            product_type: d.product_type,
            quantity_kg: d.quantity_kg,
            volume_litres: d.volume_litres,
            shift: d.shift,
            quality_metrics: d.quality_metrics,
            latitude: d.latitude,
            longitude: d.longitude,
            status: 'PENDING',
          })),
        }
        try {
          const res = await apiFetch('/api/deliveries/sync/', { method: 'POST', body: JSON.stringify(payload) })
          if (res.ok) {
            const data = await res.json()
            if (data.synced) {
              for (const s of data.synced) { await offlineQueue.markSynced(s.local_id) }
              synced += data.synced.length
            }
          }
        } catch {}
      }
    }

    const pendingGrades = await offlineQueue.getPendingGrades()
    for (const grade of pendingGrades) {
      if (grade.retry_count >= MAX_RETRIES && isRetryable(grade.last_error)) {
        continue
      }
      try {
        const body = {}
        body.delivery = grade.delivery_id
        if (grade.grade_letter) {
          body.grade_letter = grade.grade_letter
          if (grade.price_per_unit) body.price_per_unit = grade.price_per_unit
        }
        if (grade.rejection_reason) body.rejection_reason = grade.rejection_reason
        if (grade.quality_metrics) {
          try { body.quality_metrics = JSON.parse(grade.quality_metrics) } catch { body.quality_metrics = grade.quality_metrics }
        }
        const res = await apiFetch('/api/grades/', { method: 'POST', body: JSON.stringify(body) })
        if (res.ok) {
          const result = await res.json()
          await offlineQueue.markGradeSynced(grade.local_id, result.id)
          synced++
        } else if (res.status === 400) {
          await offlineQueue.markGradeSynced(grade.local_id, null)
          synced++
        } else {
          await offlineQueue.markGradeFailed(grade.local_id, 'Server error')
        }
      } catch (e) {
        await offlineQueue.markGradeFailed(grade.local_id, e.message)
      }
    }

    return { synced, failed }
  }

  startAutoSync(intervalMs = 30000) {
    this.stopAutoSync()
    this._interval = setInterval(() => {
      if (navigator.onLine) this.syncAll()
    }, intervalMs)
  }

  stopAutoSync() {
    if (this._interval) {
      clearInterval(this._interval)
      this._interval = null
    }
  }
}

const syncManager = new SyncManager()
export default syncManager

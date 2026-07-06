const DB_NAME = 'zao-grader-offline'
const DB_VERSION = 2
const DELIVERY_STORE = 'pending-deliveries'
const GRADE_STORE = 'pending-grades'
const CACHE_STORE = 'cached-pending-deliveries'

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains(DELIVERY_STORE)) {
        db.createObjectStore(DELIVERY_STORE, { keyPath: 'local_id' })
      }
      if (!db.objectStoreNames.contains(GRADE_STORE)) {
        db.createObjectStore(GRADE_STORE, { keyPath: 'local_id' })
      }
      if (!db.objectStoreNames.contains(CACHE_STORE)) {
        db.createObjectStore(CACHE_STORE, { keyPath: 'key' })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function saveDelivery(item) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DELIVERY_STORE, 'readwrite')
    const store = tx.objectStore(DELIVERY_STORE)
    const data = {
      local_id: item.local_id || crypto.randomUUID(),
      farmer_id: item.farmer_id,
      farmer_name: item.farmer_name || '',
      product_type: item.product_type,
      quantity_kg: item.quantity_kg || null,
      volume_litres: item.volume_litres || null,
      shift: item.shift || 'AM',
      quality_metrics: item.quality_metrics || null,
      latitude: item.latitude || null,
      longitude: item.longitude || null,
      created_at: item.created_at || new Date().toISOString(),
      sync_status: item.sync_status || 'pending',
      retry_count: item.retry_count || 0,
      last_error: item.last_error || null,
    }
    store.put(data)
    tx.oncomplete = () => resolve(data)
    tx.onerror = () => reject(tx.error)
  })
}

export async function getPendingDeliveries() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DELIVERY_STORE, 'readonly')
    const store = tx.objectStore(DELIVERY_STORE)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      resolve(all.filter(d => d.sync_status !== 'synced'))
    }
    request.onerror = () => reject(request.error)
  })
}

export async function markSynced(localId) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DELIVERY_STORE, 'readwrite')
    const store = tx.objectStore(DELIVERY_STORE)
    const request = store.get(localId)
    request.onsuccess = () => {
      const data = request.result
      if (data) {
        data.sync_status = 'synced'
        data.retry_count = 0
        data.last_error = null
        store.put(data)
      }
    }
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function markFailed(localId, error) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DELIVERY_STORE, 'readwrite')
    const store = tx.objectStore(DELIVERY_STORE)
    const request = store.get(localId)
    request.onsuccess = () => {
      const data = request.result
      if (data) {
        data.sync_status = 'failed'
        data.retry_count = (data.retry_count || 0) + 1
        data.last_error = error
        store.put(data)
      }
    }
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function deleteSynced() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DELIVERY_STORE, 'readwrite')
    const store = tx.objectStore(DELIVERY_STORE)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
      all.forEach(item => {
        if (item.sync_status === 'synced' && new Date(item.created_at).getTime() < sevenDaysAgo) {
          store.delete(item.local_id)
        }
      })
    }
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getCount() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DELIVERY_STORE, 'readonly')
    const store = tx.objectStore(DELIVERY_STORE)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      resolve(all.filter(d => d.sync_status !== 'synced').length)
    }
    request.onerror = () => reject(request.error)
  })
}

export async function getFailedDeliveries() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DELIVERY_STORE, 'readonly')
    const store = tx.objectStore(DELIVERY_STORE)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      resolve(all.filter(d => d.sync_status === 'failed'))
    }
    request.onerror = () => reject(request.error)
  })
}

export async function getFailedGrades() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(GRADE_STORE, 'readonly')
    const store = tx.objectStore(GRADE_STORE)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      resolve(all.filter(g => g.sync_status === 'failed'))
    }
    request.onerror = () => reject(request.error)
  })
}


export async function saveGrade(item) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(GRADE_STORE, 'readwrite')
    const store = tx.objectStore(GRADE_STORE)
    const data = {
      local_id: item.local_id || crypto.randomUUID(),
      delivery_id: item.delivery_id,
      delivery_batch_id: item.delivery_batch_id || '',
      farmer_name: item.farmer_name || '',
      grade_letter: item.grade_letter || null,
      rejection_reason: item.rejection_reason || null,
      price_per_unit: item.price_per_unit || null,
      quality_metrics: item.quality_metrics || null,
      created_at: item.created_at || new Date().toISOString(),
      sync_status: 'pending',
      retry_count: 0,
      last_error: null,
    }
    store.put(data)
    tx.oncomplete = () => resolve(data)
    tx.onerror = () => reject(tx.error)
  })
}

export async function getPendingGrades() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(GRADE_STORE, 'readonly')
    const store = tx.objectStore(GRADE_STORE)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      resolve(all.filter(g => g.sync_status !== 'synced'))
    }
    request.onerror = () => reject(request.error)
  })
}

export async function markGradeSynced(localId, serverId) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(GRADE_STORE, 'readwrite')
    const store = tx.objectStore(GRADE_STORE)
    const request = store.get(localId)
    request.onsuccess = () => {
      const data = request.result
      if (data) {
        data.sync_status = 'synced'
        data.server_id = serverId
        data.retry_count = 0
        data.last_error = null
        store.put(data)
      }
    }
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function markGradeFailed(localId, error) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(GRADE_STORE, 'readwrite')
    const store = tx.objectStore(GRADE_STORE)
    const request = store.get(localId)
    request.onsuccess = () => {
      const data = request.result
      if (data) {
        data.sync_status = 'failed'
        data.retry_count = (data.retry_count || 0) + 1
        data.last_error = error
        store.put(data)
      }
    }
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getGradeCount() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(GRADE_STORE, 'readonly')
    const store = tx.objectStore(GRADE_STORE)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      resolve(all.filter(g => g.sync_status !== 'synced').length)
    }
    request.onerror = () => reject(request.error)
  })
}


export async function cachePendingDeliveries(deliveries) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CACHE_STORE, 'readwrite')
    const store = tx.objectStore(CACHE_STORE)
    store.put({ key: 'pending', data: deliveries, cached_at: new Date().toISOString() })
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

const FARMER_CACHE_KEY = 'farmers'

export async function cacheFarmers(farmers) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CACHE_STORE, 'readwrite')
    const store = tx.objectStore(CACHE_STORE)
    store.put({ key: FARMER_CACHE_KEY, data: farmers, cached_at: new Date().toISOString() })
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getCachedFarmers() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CACHE_STORE, 'readonly')
    const store = tx.objectStore(CACHE_STORE)
    const request = store.get(FARMER_CACHE_KEY)
    request.onsuccess = () => {
      const entry = request.result
      if (entry && Date.now() - new Date(entry.cached_at).getTime() < 24 * 60 * 60 * 1000) {
        resolve(entry.data)
      } else {
        resolve(null)
      }
    }
    request.onerror = () => reject(request.error)
  })
}

export function searchCachedFarmers(farmers, q) {
  if (!farmers || !q || q.length < 2) return []
  const lower = q.toLowerCase()
  const isNumeric = /^[\d\+]+$/.test(q)
  return farmers.filter(f => {
    if (isNumeric) {
      return f.phone_number?.replace(/\D/g, '').includes(q.replace(/\D/g, ''))
    }
    return f.first_name?.toLowerCase().includes(lower)
      || f.last_name?.toLowerCase().includes(lower)
      || `${f.first_name} ${f.last_name}`.toLowerCase().includes(lower)
  })
}

export async function getCachedPendingDeliveries() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CACHE_STORE, 'readonly')
    const store = tx.objectStore(CACHE_STORE)
    const request = store.get('pending')
    request.onsuccess = () => {
      const entry = request.result
      if (entry && Date.now() - new Date(entry.cached_at).getTime() < 60 * 60 * 1000) {
        resolve(entry.data)
      } else {
        resolve(null)
      }
    }
    request.onerror = () => reject(request.error)
  })
}

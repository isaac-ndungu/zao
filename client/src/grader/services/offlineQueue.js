const DB_NAME = 'zao-grader-offline'
const DB_VERSION = 1
const STORE_NAME = 'pending-deliveries'

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'local_id' })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function saveDelivery(item) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
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
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
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
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
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
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
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
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
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
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const request = store.getAll()
    request.onsuccess = () => {
      const all = request.result || []
      resolve(all.filter(d => d.sync_status !== 'synced').length)
    }
    request.onerror = () => reject(request.error)
  })
}

import { useState, useEffect, useCallback, useRef } from 'react'
import { useOnlineStatus } from '../../shared/hooks/useOnlineStatus'
import * as offlineQueue from '../services/offlineQueue'
import syncManager from '../services/syncManager'

export function useOfflineSync() {
  const isOnline = useOnlineStatus()
  const [pendingCount, setPendingCount] = useState(0)
  const [pendingGradesCount, setPendingGradesCount] = useState(0)
  const [syncStatus, setSyncStatus] = useState('idle')
  const [lastSyncResult, setLastSyncResult] = useState(null)
  const isSyncing = useRef(false)
  const initialLoad = useRef(false)

  const loadPendingCount = useCallback(async () => {
    try {
      const [deliveryCount, gradeCount] = await Promise.all([
        offlineQueue.getCount(),
        offlineQueue.getGradeCount(),
      ])
      setPendingCount(deliveryCount)
      setPendingGradesCount(gradeCount)
    } catch { /* ignore */ }
  }, [])

  const triggerSync = useCallback(async () => {
    if (!isOnline || isSyncing.current) return
    isSyncing.current = true
    setSyncStatus('syncing')
    try {
      const result = await syncManager.syncAll()
      setLastSyncResult({ ...result, timestamp: new Date() })
      setSyncStatus(result.failed > 0 ? 'error' : 'done')
      await loadPendingCount()
    } catch {
      setSyncStatus('error')
    }
    isSyncing.current = false
  }, [isOnline, loadPendingCount])

  useEffect(() => {
    if (!initialLoad.current) {
      initialLoad.current = true
      loadPendingCount()
    }
  }, [loadPendingCount])

  useEffect(() => {
    if (isOnline && (pendingCount > 0 || pendingGradesCount > 0) && !isSyncing.current) {
      syncManager.syncAll().then(result => {
        setLastSyncResult({ ...result, timestamp: new Date() })
        if (result.failed > 0) setSyncStatus('error')
        else setSyncStatus('done')
        loadPendingCount()
      })
    }
  }, [isOnline, pendingCount, pendingGradesCount, loadPendingCount])

  useEffect(() => {
    syncManager.startAutoSync(30000)
    return () => syncManager.stopAutoSync()
  }, [])

  return { pendingCount, pendingGradesCount, syncStatus, lastSyncResult, triggerSync, loadPendingCount }
}

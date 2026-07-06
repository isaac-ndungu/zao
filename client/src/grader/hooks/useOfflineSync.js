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
  const [failedDetails, setFailedDetails] = useState([])
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

  const loadFailedDetails = useCallback(async () => {
    try {
      const [failedDeliveries, failedGrades] = await Promise.all([
        offlineQueue.getFailedDeliveries(),
        offlineQueue.getFailedGrades(),
      ])
      const details = [
        ...failedDeliveries.map(d => ({ type: 'delivery', batchId: d.batch_id || d.local_id, error: d.last_error, farmerName: d.farmer_name })),
        ...failedGrades.map(g => ({ type: 'grade', batchId: g.delivery_batch_id || g.local_id, error: g.last_error, farmerName: g.farmer_name })),
      ]
      setFailedDetails(details)
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
      await loadFailedDetails()
    } catch {
      setSyncStatus('error')
    }
    isSyncing.current = false
  }, [isOnline, loadPendingCount, loadFailedDetails])

  useEffect(() => {
    if (!initialLoad.current) {
      initialLoad.current = true
      loadPendingCount()
      loadFailedDetails()
    }
  }, [loadPendingCount, loadFailedDetails])

  useEffect(() => {
    if (isOnline && (pendingCount > 0 || pendingGradesCount > 0) && !isSyncing.current) {
      syncManager.syncAll().then(result => {
        setLastSyncResult({ ...result, timestamp: new Date() })
        if (result.failed > 0) setSyncStatus('error')
        else setSyncStatus('done')
        loadPendingCount()
        loadFailedDetails()
      })
    }
  }, [isOnline, pendingCount, pendingGradesCount, loadPendingCount, loadFailedDetails])

  useEffect(() => {
    syncManager.startAutoSync(30000)
    return () => syncManager.stopAutoSync()
  }, [])

  return { pendingCount, pendingGradesCount, syncStatus, lastSyncResult, failedDetails, triggerSync, loadPendingCount, loadFailedDetails }
}

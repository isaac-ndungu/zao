import { useState } from 'react'
import { useOnlineStatus } from '../../shared/hooks/useOnlineStatus'
import { useOfflineSync } from '../hooks/useOfflineSync'

function timeAgo(date) {
  if (!date) return 'Never'
  const diff = Date.now() - date.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.floor(mins / 60)
  return `${hours}h ago`
}

export default function Sync() {
  const isOnline = useOnlineStatus()
  const { pendingCount, syncStatus, lastSyncResult, triggerSync } = useOfflineSync()
  const [syncing, setSyncing] = useState(false)

  const handleSync = async () => {
    setSyncing(true)
    await triggerSync()
    setSyncing(false)
  }

  return (
    <div className="max-w-lg mx-auto">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Sync</h2>
        <p className="text-on-surface-variant font-body-md">Offline delivery synchronization</p>
      </header>

      <div className="flex items-center gap-3 mb-6 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-xl">
        <div className={`w-3 h-3 rounded-full ${isOnline ? 'bg-success' : 'bg-error'}`} />
        <span className="text-body-md text-on-surface font-medium">
          {isOnline ? 'Online' : 'Offline'}
        </span>
        {!isOnline && (
          <span className="text-label-md text-on-surface-variant ml-2">
            — Deliveries will be saved locally
          </span>
        )}
      </div>

      {!isOnline && (
        <div className="mb-6 px-4 py-3 bg-warning-container border border-warning rounded-xl text-body-md text-on-warning-container">
          You are offline. Deliveries will be saved locally and synced when you reconnect.
        </div>
      )}

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <div className="flex items-center gap-4 mb-6">
          <div className={`w-14 h-14 rounded-full flex items-center justify-center ${
            pendingCount > 0 ? 'bg-warning-container' : 'bg-primary-container'
          }`}>
            <span className={`material-symbols-outlined text-[28px] ${
              pendingCount > 0 ? 'text-warning' : 'text-primary'
            }`}>cloud_upload</span>
          </div>
          <div>
            <p className="text-headline-lg font-bold text-on-surface">{pendingCount}</p>
            <p className="text-label-md text-on-surface-variant">deliveries waiting to sync</p>
          </div>
        </div>

        <button
          onClick={handleSync}
          disabled={syncing || !isOnline || pendingCount === 0}
          className="w-full py-3 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <span className={`material-symbols-outlined text-[20px] ${syncing ? 'animate-spin' : ''}`}>
            {syncing ? 'sync' : 'sync'}
          </span>
          {syncing
            ? `Syncing... ${pendingCount} remaining`
            : pendingCount === 0
              ? 'All Synced'
              : `Sync Now (${pendingCount} pending)`}
        </button>
      </div>

      {syncStatus === 'syncing' && (
        <div className="mb-6 px-4 py-3 bg-primary-container text-on-primary-container rounded-xl text-body-md font-medium flex items-center gap-3">
          <span className="material-symbols-outlined animate-spin">sync</span>
          Syncing deliveries...
        </div>
      )}

      {syncStatus === 'done' && lastSyncResult && (
        <div className="mb-6 px-4 py-3 bg-success-container text-on-success-container rounded-xl text-body-md font-medium flex items-center gap-3">
          <span className="material-symbols-outlined">check_circle</span>
          {lastSyncResult.synced} deliveries synced successfully
        </div>
      )}

      {syncStatus === 'error' && lastSyncResult && lastSyncResult.failed > 0 && (
        <div className="mb-6 px-4 py-3 bg-error-container text-on-error-container rounded-xl text-body-md">
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined">error</span>
            <span className="font-medium">{lastSyncResult.failed} deliveries failed</span>
          </div>
          <button onClick={handleSync} className="text-label-md font-bold underline mt-1">
            Tap to retry
          </button>
        </div>
      )}

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-3">Sync History</h3>
        <div className="flex items-center gap-2 text-label-md text-on-surface-variant">
          <span className="material-symbols-outlined text-[16px]">history</span>
          {lastSyncResult?.timestamp
            ? `Last synced: ${timeAgo(lastSyncResult.timestamp)}`
            : 'No sync history'}
        </div>
      </div>
    </div>
  )
}

import { useOnlineStatus } from '../hooks/useOnlineStatus'

export default function OfflineBanner() {
  const isOnline = useOnlineStatus()

  if (isOnline) return null

  return (
    <div role="status" aria-live="polite" className="sticky top-16 z-30 bg-warning-container text-warning text-label-md text-center py-2 px-4 border-b border-warning">
      You are offline. Some features may be unavailable.
    </div>
  )
}

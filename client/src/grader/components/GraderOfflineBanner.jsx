import { useOnlineStatus } from '../../shared/hooks/useOnlineStatus'

export default function GraderOfflineBanner() {
  const isOnline = useOnlineStatus()

  if (isOnline) return null

  return (
    <div className="sticky top-0 z-30 bg-warning-container text-on-warning-container text-label-md text-center py-2.5 px-4 border-b border-warning flex items-center justify-center gap-2">
      <span className="material-symbols-outlined text-[16px]">wifi_off</span>
      You're offline — grades will sync when connection is restored.
    </div>
  )
}

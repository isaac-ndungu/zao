import { useState, useEffect } from 'react'

/**
 * Detects true online/offline status using two complementary strategies:
 *
 * 1. window online/offline events — fast detection, fires immediately
 * 2. Periodic HEAD ping to /api/health/ every 30s — catches the "connected
 *    but no internet" state common on congested Kenyan mobile networks and
 *    unreliable Android WebView environments.
 *
 * The event listener updates optimistically; the ping is the ground truth.
 */
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Health ping — supplements unreliable window events on Android WebView.
    const interval = setInterval(async () => {
      try {
        await fetch('/api/health/', { method: 'GET', cache: 'no-store' })
        setIsOnline(true)
      } catch {
        setIsOnline(false)
      }
    }, 30_000)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      clearInterval(interval)
    }
  }, [])

  return isOnline
}

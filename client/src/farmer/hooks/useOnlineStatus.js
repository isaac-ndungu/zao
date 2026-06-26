import { useState, useEffect } from 'react'

export default function useOnlineStatus() {
  const [online, setOnline] = useState(navigator.onLine)

  useEffect(() => {
    const go = () => setOnline(true)
    const goOff = () => setOnline(false)
    window.addEventListener('online', go)
    window.addEventListener('offline', goOff)
    return () => {
      window.removeEventListener('online', go)
      window.removeEventListener('offline', goOff)
    }
  }, [])

  return online
}

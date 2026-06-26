import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'

export default function NotificationBell() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let mounted = true
    async function fetchCount() {
      try {
        const res = await apiFetch('/api/notifications/?page=1&page_size=1')
        if (res.ok) {
          const data = await res.json()
          if (mounted) setCount(data.unread_count ?? data.count ?? 0)
        }
      } catch {/* ignore */}
    }
    fetchCount()
    const interval = setInterval(fetchCount, 30000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  return (
    <div className="relative inline-flex">
      <span className="material-symbols-outlined text-on-surface-variant">notifications</span>
      {count > 0 && (
        <span className="absolute -top-1 -right-1 bg-error text-white text-[10px] font-bold min-w-[16px] h-4 flex items-center justify-center rounded-full px-1">
          {count > 99 ? '99+' : count}
        </span>
      )}
    </div>
  )
}

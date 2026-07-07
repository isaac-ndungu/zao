import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api/client'

export default function NotificationBell({ viewAllPath }) {
  const [count, setCount] = useState(0)
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef(null)
  const navigate = useNavigate()

  // Fetch unread count (unchanged)
  useEffect(() => {
    let mounted = true
    async function fetchCount() {
      try {
        const res = await apiFetch('/api/notifications/?page=1&page_size=1')
        if (res.ok) {
          const data = await res.json()
          if (mounted) setCount(data.unread_count ?? data.count ?? 0)
        }
      } catch { /* ignore */ }
    }
    fetchCount()
    const interval = setInterval(fetchCount, 30000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/notifications/?page=1&page_size=5&ordering=-created_at')
      if (res.ok) {
        const data = await res.json()
        setNotifications(data.results || data || [])
      }
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  const toggleDropdown = () => {
    if (!open) fetchNotifications()
    setOpen(!open)
  }

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const timeSince = (dateStr) => {
    if (!dateStr) return ''
    const now = new Date()
    const then = new Date(dateStr)
    const diff = Math.floor((now - then) / 1000)
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return then.toLocaleDateString()
  }

  const handleViewAll = () => {
    if (viewAllPath) {
      setOpen(false)
      navigate(viewAllPath)
    }
  }

  return (
    <div className="relative inline-flex" ref={dropdownRef}>
      <button onClick={toggleDropdown} className="p-1 relative" aria-label="Notifications">
        <span className="material-symbols-outlined text-on-surface-variant" aria-hidden="true">notifications</span>
        {count > 0 && (
          <span className="absolute -top-1 -right-1 bg-error text-white text-[10px] font-bold min-w-[16px] h-4 flex items-center justify-center rounded-full px-1">
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-surface-container border border-outline-variant rounded-xl shadow-lg z-50 max-h-80 overflow-y-auto">
          <div className="p-3 border-b border-outline-variant">
            <p className="text-sm font-semibold text-on-surface">Notifications</p>
          </div>
          {loading ? (
            <div className="p-4 text-center text-sm text-on-surface-variant">Loading...</div>
          ) : notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-on-surface-variant">No notifications</div>
          ) : (
            <div>
              {notifications.map((n) => (
                <div key={n.id} className="p-3 border-b border-outline-variant/50 hover:bg-primary-container/10 transition-colors">
                  <p className="text-sm text-on-surface">{n.message || n.title || 'New notification'}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">{timeSince(n.created_at)}</p>
                </div>
              ))}
            </div>
          )}
          {viewAllPath && (
            <div className="p-2 text-center">
              <button onClick={handleViewAll} className="text-xs text-primary font-medium hover:underline">
                View all notifications
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
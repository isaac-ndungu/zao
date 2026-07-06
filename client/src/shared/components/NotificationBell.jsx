import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../../admin/api/client'

export default function NotificationBell({ endpoint = '/api/notifications/?page=1&page_size=5' }) {
  const { isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!open || !isAuthenticated) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    apiFetch(endpoint)
      .then((r) => r.json())
      .then((data) => setNotifications(data?.results || data || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [open, endpoint, isAuthenticated])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="p-2 text-on-surface-variant hover:bg-surface-container-high rounded-full transition-colors relative"
        aria-label={notifications.length > 0 ? `Notifications, ${notifications.length} unread` : 'Notifications'}
      >
        <span className="material-symbols-outlined" aria-hidden="true">notifications</span>
        {notifications.length > 0 && (
          <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full border-2 border-surface" aria-hidden="true" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-xl z-40 max-h-96 overflow-y-auto">
          <div className="px-4 py-3 border-b border-outline-variant">
            <p className="font-label-md font-bold text-on-surface">Notifications</p>
          </div>
          {loading ? (
            <div className="px-4 py-8 text-center text-on-surface-variant text-body-md">Loading...</div>
          ) : notifications.length === 0 ? (
            <div className="px-4 py-8 text-center text-on-surface-variant text-body-md">
              No notifications yet.
            </div>
          ) : (
            <div>
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className="px-4 py-3 hover:bg-surface-container transition-colors border-b border-outline-variant/50 last:border-0"
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={`material-symbols-outlined text-[18px] mt-0.5 ${
                        n.status === 'failed' ? 'text-error' : n.status === 'sent' ? 'text-primary' : 'text-on-surface-variant'
                      }`}
                      aria-hidden="true"
                    >
                      {n.channel === 'email' ? 'mail' : n.channel === 'sms' ? 'sms' : 'notifications'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-body-md text-on-surface truncate">{n.content}</p>
                      <p className="text-label-md text-on-surface-variant mt-0.5">
                        {n.notification_type} &middot; {n.created_at ? new Date(n.created_at).toLocaleDateString() : ''}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

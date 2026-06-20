import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAdminAuth } from '../../hooks/useAdminAuth'
import { useApi } from '../../hooks/useApi'
import PeriodPicker from './PeriodPicker'

const appBarTabs = [
  { label: 'Analytics', path: '/admin/dashboard' },
  { label: 'Reports', path: '/admin/financials' },
  { label: 'Audit Trail', path: '/admin/audit' },
]

export default function AppBar({ onMenuClick }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAdminAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [notifOpen, setNotifOpen] = useState(false)
  const notifRef = useRef(null)
  const { data: notifData } = useApi(notifOpen ? '/api/notifications/?page=1&page_size=5' : null)

  useEffect(() => {
    const handler = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase()
    : '??'

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/admin/farmers?search=${encodeURIComponent(searchQuery.trim())}`)
      setSearchQuery('')
    }
  }

  const notifications = notifData?.results || notifData || []

  return (
    <header className="fixed top-0 right-0 left-0 lg:left-64 h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-4 lg:px-6 z-30">
      <div className="flex items-center gap-3 lg:gap-8 flex-1 min-w-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 text-on-surface-variant hover:bg-surface-container-high rounded-lg transition-colors"
          aria-label="Toggle menu"
        >
          <span className="material-symbols-outlined">menu</span>
        </button>

        <form onSubmit={handleSearchSubmit} className="relative hidden sm:block sm:w-60 lg:w-72 flex-shrink-0">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
            search
          </span>
          <input
            className="w-full bg-surface-container border-none rounded-full py-2 pl-10 pr-4 text-body-md focus:ring-1 focus:ring-primary"
            placeholder="Search operations, records, or farmers..."
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </form>

        <div className="hidden md:block flex-shrink-0">
          <PeriodPicker />
        </div>

        <nav className="hidden xl:flex gap-6 ml-auto">
          {appBarTabs.map((tab) => {
            const isActive = pathname.startsWith(tab.path)
            return (
              <button
                key={tab.label}
                onClick={() => navigate(tab.path)}
                className={`font-label-md text-label-md transition-colors whitespace-nowrap ${
                  isActive
                    ? 'text-primary font-bold border-b-2 border-primary pb-1'
                    : 'text-on-surface-variant font-medium hover:text-primary'
                }`}
              >
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="flex items-center gap-2 lg:gap-4 flex-shrink-0">
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="p-2 text-on-surface-variant hover:bg-surface-container-high rounded-full transition-colors relative"
            aria-label="Notifications"
          >
            <span className="material-symbols-outlined">notifications</span>
            {notifications.length > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full border-2 border-surface" />
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-xl z-40 max-h-96 overflow-y-auto">
              <div className="px-4 py-3 border-b border-outline-variant">
                <p className="font-label-md font-bold text-on-surface">Notifications</p>
              </div>
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-on-surface-variant text-body-md">
                  No notifications yet.
                </div>
              ) : (
                <div>
                  {notifications.map((n) => (
                    <div key={n.id} className="px-4 py-3 hover:bg-surface-container transition-colors border-b border-outline-variant/50 last:border-0">
                      <div className="flex items-start gap-3">
                        <span className={`material-symbols-outlined text-[18px] mt-0.5 ${
                          n.status === 'failed' ? 'text-error' : n.status === 'sent' ? 'text-primary' : 'text-on-surface-variant'
                        }`}>
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

        <button className="p-2 text-on-surface-variant hover:bg-surface-container-high rounded-full transition-colors hidden sm:block">
          <span className="material-symbols-outlined">history_edu</span>
        </button>

        <div className="flex items-center gap-3 pl-2 lg:pl-4 border-l border-outline-variant">
          <div className="text-right hidden xl:block">
            <p className="font-label-md font-bold text-on-surface leading-tight truncate max-w-[120px]">
              {user ? `${user.first_name} ${user.last_name}` : 'Loading...'}
            </p>
            <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">
              Super Admin
            </p>
          </div>
          <div className="w-9 h-9 lg:w-10 lg:h-10 rounded-full bg-primary-fixed flex items-center justify-center border border-outline-variant text-primary font-bold text-sm overflow-hidden flex-shrink-0">
            {user?.avatar ? (
              <img src={user.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              initials
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

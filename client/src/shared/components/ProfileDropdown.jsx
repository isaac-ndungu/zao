import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProfileDropdown({ profilePath, roleLabel, onClose }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const ref = useRef(null)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose() }
    const esc = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', handler); document.removeEventListener('keydown', esc) }
  }, [onClose])

  const handleLogout = async () => {
    setLoggingOut(true)
    await logout()
    navigate('/admin/login')
  }

  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase()
    : '??'

  return (
    <div ref={ref} className="absolute right-0 top-full mt-2 w-56 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-xl z-[999] overflow-hidden">
      <div className="p-4 border-b border-outline-variant/50 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-sm overflow-hidden flex-shrink-0">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-bold text-on-surface truncate">{user ? `${user.first_name} ${user.last_name}` : ''}</p>
          <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">{roleLabel}</p>
        </div>
      </div>
      <button
        onClick={() => { navigate(profilePath); onClose() }}
        className="w-full flex items-center gap-3 px-4 py-3 text-sm text-on-surface hover:bg-surface-container transition-colors"
      >
        <span className="material-symbols-outlined text-[18px] text-on-surface-variant">person</span>
        Profile
      </button>
      {!showConfirm ? (
        <button
          onClick={() => setShowConfirm(true)}
          className="w-full flex items-center gap-3 px-4 py-3 text-sm text-error hover:bg-error-container/10 transition-colors border-t border-outline-variant/50"
        >
          <span className="material-symbols-outlined text-[18px]">logout</span>
          Logout
        </button>
      ) : (
        <div className="px-4 py-3 border-t border-outline-variant/50 space-y-2">
          <p className="text-xs text-on-surface-variant">Are you sure you want to log out?</p>
          <div className="flex gap-2">
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="flex-1 py-2 rounded-lg bg-error text-white text-xs font-bold hover:opacity-80 transition-opacity disabled:opacity-40"
            >
              {loggingOut ? <span className="inline-block animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" /> : 'Logout'}
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="flex-1 py-2 rounded-lg border border-outline-variant text-xs font-bold text-on-surface hover:bg-surface-container transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

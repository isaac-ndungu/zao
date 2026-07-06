import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import ConfirmModal from '../../admin/components/common/ConfirmModal'

const roleLabels = {
  admin: 'Super Admin',
  manager: 'Manager',
  accountant: 'Accountant',
  grader: 'Grader',
  auditor: 'Internal Auditor',
  external_auditor: 'External Auditor',
}

export default function Profile({ settingsPath }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

  const roleLabel = roleLabels[user?.role] || user?.role || 'Staff'
  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase()
    : '??'

  const handleLogout = async () => {
    setLoggingOut(true)
    try {
      await logout()
      navigate('/admin/login')
    } finally {
      setLoggingOut(false)
      setShowLogoutConfirm(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Profile</h2>
        <p className="text-on-surface-variant font-body-md">Your account information</p>
      </header>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <div className="flex items-center gap-4 pb-6 mb-6 border-b border-outline-variant/50">
          <div className="w-16 h-16 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-xl overflow-hidden flex-shrink-0">
            {initials}
          </div>
          <div>
            <h3 className="font-headline-sm text-headline-sm text-on-surface">{user?.first_name} {user?.last_name}</h3>
            <p className="text-label-md text-on-surface-variant">{roleLabel}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="text-label-md text-on-surface-variant mb-1">First Name</p>
            <p className="text-body-md font-medium text-on-surface">{user?.first_name || '-'}</p>
          </div>
          <div>
            <p className="text-label-md text-on-surface-variant mb-1">Last Name</p>
            <p className="text-body-md font-medium text-on-surface">{user?.last_name || '-'}</p>
          </div>
          <div>
            <p className="text-label-md text-on-surface-variant mb-1">Email</p>
            <p className="text-body-md font-medium text-on-surface">{user?.email || '-'}</p>
          </div>
          <div>
            <p className="text-label-md text-on-surface-variant mb-1">Phone</p>
            <p className="text-body-md font-medium text-on-surface">{user?.phone_number || '-'}</p>
          </div>
        </div>

        {settingsPath && (
          <div className="mt-6 pt-6 border-t border-outline-variant/50">
            <button
              onClick={() => navigate(settingsPath)}
              className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-primary hover:bg-surface-container-high transition-colors flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">settings</span>
              Go to Settings
            </button>
          </div>
        )}
      </div>

      <button
        onClick={() => setShowLogoutConfirm(true)}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-error hover:bg-error-container/10 rounded-lg transition-colors"
      >
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">logout</span>
        Logout
      </button>

      <ConfirmModal
        open={showLogoutConfirm}
        title="Logout"
        message="Are you sure you want to log out?"
        confirmLabel={loggingOut ? 'Logging out...' : 'Logout'}
        cancelLabel="Cancel"
        loading={loggingOut}
        onConfirm={handleLogout}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </div>
  )
}

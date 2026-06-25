import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'

export default function ForcePasswordChange({ onComplete }) {
  const { changePassword, logout } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setLoading(true)
    try {
      await changePassword(currentPassword, newPassword)
      onComplete?.()
    } catch (err) {
      setError(err.detail || err.message || 'Failed to change password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="font-display-lg text-display-lg text-primary">Zao</h1>
          <p className="text-on-surface-variant text-body-md mt-1">Change Your Password</p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl shadow-lg p-8 border border-outline-variant">
          <div className="bg-warning-container text-warning text-body-md px-3 py-2 rounded-lg mb-5">
            You must change your password before continuing.
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="currentPassword" className="block text-label-md text-on-surface-variant mb-1">
                Current Password
              </label>
              <input
                id="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoFocus
                autoComplete="current-password"
                className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label htmlFor="newPassword" className="block text-label-md text-on-surface-variant mb-1">
                New Password
              </label>
              <input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-label-md text-on-surface-variant mb-1">
                Confirm New Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {error && (
              <div className="bg-error-container text-error text-body-md px-3 py-2 rounded-lg">{error}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
              {loading ? 'Changing...' : 'Change Password'}
            </button>
          </form>

          <button
            onClick={logout}
            className="w-full text-center text-body-md text-error hover:underline mt-4"
          >
            Log out
          </button>
        </div>
      </div>
    </div>
  )
}

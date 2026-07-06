import { useAdminAuth } from '../hooks/useAdminAuth'
import { useState } from 'react'
import { apiFetch } from '../api/client'
import { useToast } from '../contexts/ToastContext'

export default function Settings() {
  const { user, refreshUser } = useAdminAuth()
  const { showToast } = useToast()
  const [form, setForm] = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '', email: user?.email || '', phone_number: user?.phone_number || '' })
  const [saving, setSaving] = useState(false)
  const [pwOpen, setPwOpen] = useState(false)
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [pwSaving, setPwSaving] = useState(false)
  const [twoFAOpen, setTwoFAOpen] = useState(false)
  const [twoFAPassword, setTwoFAPassword] = useState('')
  const [twoFALoading, setTwoFALoading] = useState(false)

  const twoFAEnabled = user?.two_fa_enabled || false

  const handleTwoFAToggle = async (e) => {
    e.preventDefault()
    setTwoFALoading(true)
    try {
      const endpoint = twoFAEnabled ? '/api/auth/2fa/disable/' : '/api/auth/2fa/enable/'
      const res = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ password: twoFAPassword }),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Two-factor authentication ${twoFAEnabled ? 'disabled' : 'enabled'}.` })
      setTwoFAOpen(false)
      setTwoFAPassword('')
      await refreshUser()
    } catch (e) {
      showToast({ type: 'error', message: `Failed: ${e.message}` })
    } finally {
      setTwoFALoading(false)
    }
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch(`/api/admin/users/${user.id}/`, {
        method: 'PATCH',
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Profile updated successfully.' })
    } catch (e) {
      showToast({ type: 'error', message: `Failed to save: ${e.message}` })
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (pwForm.new_password !== pwForm.confirm_password) {
      showToast({ type: 'error', message: 'Passwords do not match.' })
      return
    }
    setPwSaving(true)
    try {
      const res = await apiFetch('/api/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify({ current_password: pwForm.current_password, new_password: pwForm.new_password }),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Password changed successfully.' })
      setPwOpen(false)
      setPwForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (e) {
      showToast({ type: 'error', message: `Password change failed: ${e.message}` })
    } finally {
      setPwSaving(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Settings</h2>
        <p className="text-on-surface-variant font-body-md">Manage your admin profile and preferences.</p>
      </header>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-6">Profile</h4>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="id-first-name" className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label>
              <input id="id-first-name" type="text" value={form.first_name} onChange={(e) => setForm(f => ({ ...f, first_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
            </div>
            <div>
              <label htmlFor="id-last-name" className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
              <input id="id-last-name" type="text" value={form.last_name} onChange={(e) => setForm(f => ({ ...f, last_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
            </div>
          </div>
          <div>
            <label htmlFor="id-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
            <input id="id-email" type="email" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
          </div>
          <div>
            <label htmlFor="id-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
            <input id="id-phone" type="tel" value={form.phone_number} onChange={(e) => setForm(f => ({ ...f, phone_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
          </div>
          <div className="pt-2">
            <button type="submit" disabled={saving} className="px-6 py-2 bg-primary text-on-primary rounded-lg font-bold text-label-md hover:bg-primary/90 transition-colors disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Security</h4>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-outline-variant/50">
            <div>
              <p className="font-body-md font-medium text-on-surface">Password</p>
              <p className="text-label-md text-on-surface-variant">Change your account password</p>
            </div>
            <button onClick={() => setPwOpen(!pwOpen)} className="px-4 py-1.5 border border-primary text-primary rounded-lg text-label-md font-bold hover:bg-primary/5 transition-colors">
              {pwOpen ? 'Cancel' : 'Change'}
            </button>
          </div>
          {pwOpen && (
            <form onSubmit={handlePasswordChange} className="space-y-3 pt-2">
              <div><label htmlFor="id-current-password" className="block text-label-md font-bold text-on-surface-variant mb-1">Current Password</label><input id="id-current-password" type="password" required value={pwForm.current_password} onChange={(e) => setPwForm(f => ({ ...f, current_password: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="id-new-password" className="block text-label-md font-bold text-on-surface-variant mb-1">New Password</label><input id="id-new-password" type="password" required value={pwForm.new_password} onChange={(e) => setPwForm(f => ({ ...f, new_password: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label htmlFor="id-confirm-password" className="block text-label-md font-bold text-on-surface-variant mb-1">Confirm New Password</label><input id="id-confirm-password" type="password" required value={pwForm.confirm_password} onChange={(e) => setPwForm(f => ({ ...f, confirm_password: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <button type="submit" disabled={pwSaving} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 disabled:opacity-50">{pwSaving ? 'Saving...' : 'Update Password'}</button>
            </form>
          )}
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-body-md font-medium text-on-surface">Two-Factor Authentication</p>
              <p className="text-label-md text-on-surface-variant">Add an extra layer of security</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setTwoFAOpen(true)}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  twoFAEnabled ? 'bg-primary' : 'bg-surface-container-high'
                }`}
                aria-label="Toggle 2FA"
              >
                <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 shadow transition-transform ${
                  twoFAEnabled ? 'left-[22px]' : 'left-0.5'
                }`} />
              </button>
              <span className={`text-[10px] uppercase font-bold tracking-wider ${
                twoFAEnabled ? 'text-primary' : 'text-on-surface-variant'
              }`}>
                {twoFAEnabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>

          {twoFAOpen && (
            <div className="pt-2 pb-3">
              <form onSubmit={handleTwoFAToggle} className="space-y-3">
                <p className="text-body-md text-on-surface-variant">
                  {twoFAEnabled
                    ? 'Enter your password to disable two-factor authentication.'
                    : 'Enter your password to enable two-factor authentication.'}
                </p>
                <div className="flex gap-3">
                  <input
                    id="id-2fa-password"
                    type="password"
                    required
                    value={twoFAPassword}
                    onChange={(e) => setTwoFAPassword(e.target.value)}
                    placeholder="Confirm your password"
                    className="flex-1 bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  />
                  <button
                    type="submit"
                    disabled={twoFALoading || !twoFAPassword}
                    className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 disabled:opacity-50"
                  >
                    {twoFALoading ? 'Updating...' : 'Confirm'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setTwoFAOpen(false); setTwoFAPassword('') }}
                    className="px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Account</h4>
        <div className="flex items-center justify-between py-3">
          <div>
            <p className="font-body-md font-medium text-on-surface">Role</p>
            <p className="text-label-md text-on-surface-variant">{user?.role || 'Admin'}</p>
          </div>
          <span className="px-3 py-1 bg-primary-container text-on-primary-container rounded-full text-[11px] font-bold uppercase">Verified</span>
        </div>
      </div>
    </div>
  )
}

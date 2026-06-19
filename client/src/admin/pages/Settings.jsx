import { useAdminAuth } from '../hooks/useAdminAuth'
import { useState } from 'react'
import { apiFetch } from '../api/client'
import { useToast } from '../contexts/ToastContext'

export default function Settings() {
  const { user } = useAdminAuth()
  const { showToast } = useToast()
  const [form, setForm] = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '', email: user?.email || '', phone_number: user?.phone_number || '' })
  const [saving, setSaving] = useState(false)
  const [pwOpen, setPwOpen] = useState(false)
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [pwSaving, setPwSaving] = useState(false)

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
              <label className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label>
              <input type="text" value={form.first_name} onChange={(e) => setForm(f => ({ ...f, first_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
            </div>
            <div>
              <label className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
              <input type="text" value={form.last_name} onChange={(e) => setForm(f => ({ ...f, last_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
            </div>
          </div>
          <div>
            <label className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
          </div>
          <div>
            <label className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
            <input type="tel" value={form.phone_number} onChange={(e) => setForm(f => ({ ...f, phone_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
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
              <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Current Password</label><input type="password" required value={pwForm.current_password} onChange={(e) => setPwForm(f => ({ ...f, current_password: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">New Password</label><input type="password" required value={pwForm.new_password} onChange={(e) => setPwForm(f => ({ ...f, new_password: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <div><label className="block text-label-md font-bold text-on-surface-variant mb-1">Confirm New Password</label><input type="password" required value={pwForm.confirm_password} onChange={(e) => setPwForm(f => ({ ...f, confirm_password: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              <button type="submit" disabled={pwSaving} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 disabled:opacity-50">{pwSaving ? 'Saving...' : 'Update Password'}</button>
            </form>
          )}
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-body-md font-medium text-on-surface">Two-Factor Authentication</p>
              <p className="text-label-md text-on-surface-variant">Add an extra layer of security</p>
            </div>
            <span className="px-3 py-1 bg-surface-container-high text-on-surface-variant rounded-full text-[11px] font-bold uppercase">Coming Soon</span>
          </div>
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

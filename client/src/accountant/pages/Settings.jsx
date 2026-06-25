import { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'

export default function AccountantSettings() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [editing, setEditing] = useState(false)
  const [formData, setFormData] = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '', email: user?.email || '' })
  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', confirm_password: '' })
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)

  const handleProfileSave = async (e) => {
    e.preventDefault()
    setSavingProfile(true)
    try {
      const res = await apiFetch('/api/users/me/', { method: 'PATCH', body: JSON.stringify(formData) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to update') }
      showToast({ type: 'success', message: 'Profile updated.' })
      setEditing(false)
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSavingProfile(false) }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (pwForm.new_password !== pwForm.confirm_password) {
      showToast({ type: 'error', message: 'Passwords do not match.' })
      return
    }
    setSavingPassword(true)
    try {
      const res = await apiFetch('/api/auth/change-password/', { method: 'POST', body: JSON.stringify({ old_password: pwForm.old_password, new_password: pwForm.new_password }) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to change password') }
      showToast({ type: 'success', message: 'Password changed.' })
      setPwForm({ old_password: '', new_password: '', confirm_password: '' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSavingPassword(false) }
  }

  return (
    <div className="max-w-xl mx-auto">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Settings</h2>
        <p className="text-on-surface-variant font-body-md">Profile and account settings</p>
      </header>

      <section className="mb-8">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Profile</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          {!editing ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><p className="text-label-md text-on-surface-variant">First Name</p><p className="text-body-md text-on-surface font-medium">{user?.first_name || '-'}</p></div>
                <div><p className="text-label-md text-on-surface-variant">Last Name</p><p className="text-body-md text-on-surface font-medium">{user?.last_name || '-'}</p></div>
                <div><p className="text-label-md text-on-surface-variant">Email</p><p className="text-body-md text-on-surface font-medium">{user?.email || '-'}</p></div>
                <div><p className="text-label-md text-on-surface-variant">Phone</p><p className="text-body-md text-on-surface font-medium">{user?.phone_number || '-'}</p></div>
              </div>
              <button onClick={() => setEditing(true)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-primary hover:bg-surface-container-high transition-colors">Edit</button>
            </div>
          ) : (
            <form onSubmit={handleProfileSave} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-label-md text-on-surface-variant mb-1">First Name</label><input value={formData.first_name} onChange={(e) => setFormData(p => ({ ...p, first_name: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
                <div><label className="block text-label-md text-on-surface-variant mb-1">Last Name</label><input value={formData.last_name} onChange={(e) => setFormData(p => ({ ...p, last_name: e.target.value }))} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
              </div>
              <div><label className="block text-label-md text-on-surface-variant mb-1">Email</label><input value={formData.email} onChange={(e) => setFormData(p => ({ ...p, email: e.target.value }))} type="email" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
              <div className="flex gap-3">
                <button type="submit" disabled={savingProfile} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">{savingProfile ? 'Saving...' : 'Save'}</button>
                <button type="button" onClick={() => setEditing(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
              </div>
            </form>
          )}
        </div>
      </section>

      <section className="mb-8">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Two-Factor Authentication</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          <div className="flex items-center gap-3 mb-3">
            <span className="material-symbols-outlined text-success">verified</span>
            <span className="text-body-md text-on-surface font-medium">Two-factor authentication is enabled</span>
          </div>
          <p className="text-body-md text-on-surface-variant">2FA is mandatory for accountant accounts and cannot be disabled.</p>
        </div>
      </section>

      <section>
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Change Password</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div><label className="block text-label-md text-on-surface-variant mb-1">Current Password</label><input value={pwForm.old_password} onChange={(e) => setPwForm(p => ({ ...p, old_password: e.target.value }))} type="password" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
            <div><label className="block text-label-md text-on-surface-variant mb-1">New Password</label><input value={pwForm.new_password} onChange={(e) => setPwForm(p => ({ ...p, new_password: e.target.value }))} type="password" required minLength={8} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
            <div><label className="block text-label-md text-on-surface-variant mb-1">Confirm New Password</label><input value={pwForm.confirm_password} onChange={(e) => setPwForm(p => ({ ...p, confirm_password: e.target.value }))} type="password" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
            <button type="submit" disabled={savingPassword} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold disabled:opacity-50">{savingPassword ? 'Changing...' : 'Change Password'}</button>
          </form>
        </div>
      </section>
    </div>
  )
}

import { useAdminAuth } from '../hooks/useAdminAuth'
import { useState, useRef } from 'react'
import { apiFetch } from '../api/client'
import { useToast } from '../contexts/ToastContext'

export default function Settings() {
  const { user } = useAdminAuth()
  const { showToast } = useToast()
  const [saving, setSaving] = useState(false)
  const firstNameRef = useRef(null)
  const lastNameRef = useRef(null)
  const emailRef = useRef(null)
  const phoneRef = useRef(null)

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch(`/api/admin/users/${user.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          first_name: firstNameRef.current?.value || user.first_name,
          last_name: lastNameRef.current?.value || user.last_name,
          email: emailRef.current?.value || user.email,
          phone_number: phoneRef.current?.value || user.phone_number,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: 'Profile updated successfully.' })
    } catch (e) {
      showToast({ type: 'error', message: `Failed to save: ${e.message}` })
    } finally {
      setSaving(false)
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
              <input
                ref={firstNameRef}
                type="text"
                defaultValue={user?.first_name || ''}
                className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              />
            </div>
            <div>
              <label className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
              <input
                ref={lastNameRef}
                type="text"
                defaultValue={user?.last_name || ''}
                className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              />
            </div>
          </div>
          <div>
            <label className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
            <input
              ref={emailRef}
              type="email"
              defaultValue={user?.email || ''}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
            />
          </div>
          <div>
            <label className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
            <input
              ref={phoneRef}
              type="tel"
              defaultValue={user?.phone_number || ''}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
            />
          </div>
          <div className="pt-2">
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2 bg-primary text-on-primary rounded-lg font-bold text-label-md hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Account</h4>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-outline-variant/50">
            <div>
              <p className="font-body-md font-medium text-on-surface">Role</p>
              <p className="text-label-md text-on-surface-variant">{user?.role || 'Admin'}</p>
            </div>
            <span className="px-3 py-1 bg-primary-container text-on-primary-container rounded-full text-[11px] font-bold uppercase">Verified</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-body-md font-medium text-on-surface">Two-Factor Authentication</p>
              <p className="text-label-md text-on-surface-variant">Add an extra layer of security</p>
            </div>
            <button
              onClick={() => showToast({ type: 'info', message: '2FA management coming soon.' })}
              className="px-4 py-1.5 border border-primary text-primary rounded-lg text-label-md font-bold hover:bg-primary/5 transition-colors"
            >
              Enable
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useAdminAuth } from '../hooks/useAdminAuth'
import { useState } from 'react'
import { apiFetch } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import PasswordInput from '../../shared/components/PasswordInput'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

export default function Settings() {
  const { user, refreshUser } = useAdminAuth()
  const { showToast } = useToast()
  const [pwOpen, setPwOpen] = useState(false)
  const [twoFAOpen, setTwoFAOpen] = useState(false)

  const twoFAEnabled = user?.two_fa_enabled || false

  const [, profileAction] = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    const res = await apiFetch(`/api/admin/users/${user.id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(await res.text())
    showToast({ type: 'success', message: 'Profile updated successfully.' })
  }, {})

  const [, passwordAction] = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    if (data.new_password !== data.confirm_password) {
      throw new Error('Passwords do not match.')
    }
    const res = await apiFetch('/api/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify({ current_password: data.current_password, new_password: data.new_password }),
    })
    if (!res.ok) throw new Error(await res.text())
    showToast({ type: 'success', message: 'Password changed successfully.' })
    setPwOpen(false)
  }, {})

  const [, twoFAAction] = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    const endpoint = twoFAEnabled ? '/api/auth/2fa/disable/' : '/api/auth/2fa/enable/'
    const res = await apiFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify({ password: data.password }),
    })
    if (!res.ok) throw new Error(await res.text())
    showToast({ type: 'success', message: `Two-factor authentication ${twoFAEnabled ? 'disabled' : 'enabled'}.` })
    setTwoFAOpen(false)
    await refreshUser()
  }, {})

  return (
    <div className="max-w-2xl">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Settings</h2>
        <p className="text-on-surface-variant font-body-md">Manage your admin profile and preferences.</p>
      </header>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-6">Profile</h4>
        <form action={profileAction} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="id-first-name" className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label>
              <input id="id-first-name" type="text" name="first_name" defaultValue={user?.first_name || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
            </div>
            <div>
              <label htmlFor="id-last-name" className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
              <input id="id-last-name" type="text" name="last_name" defaultValue={user?.last_name || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
            </div>
          </div>
          <div>
            <label htmlFor="id-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
            <input id="id-email" type="email" name="email" defaultValue={user?.email || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
          </div>
          <div>
            <label htmlFor="id-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
            <input id="id-phone" type="tel" name="phone_number" defaultValue={user?.phone_number || ''} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
          </div>
          <div className="pt-2">
            <SubmitButton className="px-6 py-2 bg-primary text-on-primary rounded-lg font-bold text-label-md hover:bg-primary/90 transition-colors">Save Changes</SubmitButton>
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
            <form action={passwordAction} className="space-y-3 pt-2">
              <PasswordInput
                id="id-current-password"
                label="Current Password"
                name="current_password"
                required
              />
              <PasswordInput
                id="id-new-password"
                label="New Password"
                name="new_password"
                required
              />
              <PasswordInput
                id="id-confirm-password"
                label="Confirm New Password"
                name="confirm_password"
                required
              />
              <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90">Update Password</SubmitButton>
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
              <form action={twoFAAction} className="space-y-3">
                <p className="text-body-md text-on-surface-variant">
                  {twoFAEnabled
                    ? 'Enter your password to disable two-factor authentication.'
                    : 'Enter your password to enable two-factor authentication.'}
                </p>
                <div className="flex gap-3">
                  <input
                    id="id-2fa-password"
                    type="password"
                    name="password"
                    required
                    placeholder="Confirm your password"
                    className="flex-1 bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  />
                  <SubmitButton
                    className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90"
                  >
                    Confirm
                  </SubmitButton>
                  <button
                    type="button"
                    onClick={() => setTwoFAOpen(false)}
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

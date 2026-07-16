import { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import PasswordInput from '../../shared/components/PasswordInput'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

export default function AccountantSettings() {
  const { user, refreshUser } = useAuth()
  const { showToast } = useToast()
  const [editing, setEditing] = useState(false)
  const [showEnable2fa, setShowEnable2fa] = useState(false)

  const handleProfileSave = async (prev, formData) => {
    const data = formDataToObject(formData)
    try {
      const res = await apiFetch('/api/users/me/', { method: 'PATCH', body: JSON.stringify(data) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to update') }
      showToast({ type: 'success', message: 'Profile updated.' })
      setEditing(false)
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handlePasswordChange = async (prev, formData) => {
    const data = formDataToObject(formData)
    if (data.new_password !== data.confirm_password) {
      showToast({ type: 'error', message: 'Passwords do not match.' })
      return
    }
    try {
      const res = await apiFetch('/api/auth/change-password/', { method: 'POST', body: JSON.stringify({ old_password: data.old_password, new_password: data.new_password }) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to change password') }
      showToast({ type: 'success', message: 'Password changed.' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const handleEnable2fa = async (prev, formData) => {
    const data = formDataToObject(formData)
    try {
      const res = await apiFetch('/api/auth/2fa/enable/', {
        method: 'POST',
        body: JSON.stringify({ password: data.password }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to enable 2FA') }
      showToast({ type: 'success', message: 'Two-factor authentication enabled.' })
      setShowEnable2fa(false)
      refreshUser()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
  }

  const { formAction: profileAction } = useFormAction(handleProfileSave, {})
  const { formAction: enable2faAction } = useFormAction(handleEnable2fa, {})
  const { formAction: passwordAction } = useFormAction(handlePasswordChange, {})

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
            <form action={profileAction} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label htmlFor="id-first-name" className="block text-label-md text-on-surface-variant mb-1">First Name</label><input id="id-first-name" name="first_name" defaultValue={user?.first_name || ''} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
                <div><label htmlFor="id-last-name" className="block text-label-md text-on-surface-variant mb-1">Last Name</label><input id="id-last-name" name="last_name" defaultValue={user?.last_name || ''} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
              </div>
              <div><label htmlFor="id-email" className="block text-label-md text-on-surface-variant mb-1">Email</label><input id="id-email" name="email" defaultValue={user?.email || ''} type="email" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" /></div>
              <div className="flex gap-3">
                <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Save</SubmitButton>
                <button type="button" onClick={() => setEditing(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
              </div>
            </form>
          )}
        </div>
      </section>

      <section className="mb-8">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Two-Factor Authentication</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          {user?.two_fa_enabled ? (
            <>
              <div className="flex items-center gap-3 mb-3">
                <span className="material-symbols-outlined text-success" aria-hidden="true">verified</span>
                <span className="text-body-md text-on-surface font-medium">Two-factor authentication is enabled</span>
              </div>
              <p className="text-body-md text-on-surface-variant">2FA is mandatory for accountant accounts and cannot be disabled.</p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-3 mb-3">
                <span className="material-symbols-outlined text-on-surface-variant" aria-hidden="true">security</span>
                <span className="text-body-md text-on-surface font-medium">Two-factor authentication is not enabled</span>
              </div>
              <p className="text-body-md text-on-surface-variant mb-4">Enable 2FA to add an extra layer of security to your account.</p>
              {showEnable2fa ? (
                <form action={enable2faAction} className="space-y-3">
                  <div>
                    <label htmlFor="id-2fa-password" className="block text-label-md text-on-surface-variant mb-1">Confirm your password</label>
                    <input id="id-2fa-password" name="password" type="password" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" placeholder="Enter your password..." />
                  </div>
                  <div className="flex gap-3">
                    <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Enable 2FA</SubmitButton>
                    <button type="button" onClick={() => setShowEnable2fa(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
                  </div>
                </form>
              ) : (
                <button onClick={() => setShowEnable2fa(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">Enable 2FA</button>
              )}
            </>
          )}
        </div>
      </section>

      <section>
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Change Password</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          <form action={passwordAction} className="space-y-4">
            <PasswordInput
              id="id-current-password"
              label="Current Password"
              name="old_password"
              required
            />
            <PasswordInput
              id="id-new-password"
              label="New Password"
              name="new_password"
              required
              minLength={8}
            />
            <PasswordInput
              id="id-confirm-password"
              label="Confirm New Password"
              name="confirm_password"
              required
            />
            <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Change Password</SubmitButton>
          </form>
        </div>
      </section>
    </div>
  )
}

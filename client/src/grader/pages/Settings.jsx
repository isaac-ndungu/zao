import { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import PasswordInput from '../../shared/components/PasswordInput'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

export default function GraderSettings() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [editing, setEditing] = useState(false)

  const [, profileAction] = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    const res = await apiFetch('/api/users/me/', { method: 'PATCH', body: JSON.stringify(data) })
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to update') }
    showToast({ type: 'success', message: 'Profile updated.' })
    setEditing(false)
    return {}
  }, {})

  const [, passwordAction] = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    if (data.new_password !== data.confirm_password) {
      showToast({ type: 'error', message: 'Passwords do not match.' })
      return {}
    }
    const res = await apiFetch('/api/auth/change-password/', { method: 'POST', body: JSON.stringify({ old_password: data.old_password, new_password: data.new_password }) })
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to change password') }
    showToast({ type: 'success', message: 'Password changed.' })
    document.getElementById('grader-password-form')?.reset()
    return {}
  }, {})

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
                <div><label htmlFor="id-first-name" className="block text-label-md text-on-surface-variant mb-1">First Name</label><input id="id-first-name" name="first_name" defaultValue={user?.first_name || ''} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
                <div><label htmlFor="id-last-name" className="block text-label-md text-on-surface-variant mb-1">Last Name</label><input id="id-last-name" name="last_name" defaultValue={user?.last_name || ''} required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
              </div>
              <div><label htmlFor="id-email" className="block text-label-md text-on-surface-variant mb-1">Email</label><input id="id-email" name="email" defaultValue={user?.email || ''} type="email" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"/></div>
              <div className="flex gap-3">
                <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Save</SubmitButton>
                <button type="button" onClick={() => setEditing(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
              </div>
            </form>
          )}
        </div>
      </section>

      <section>
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Change Password</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          <form id="grader-password-form" action={passwordAction} className="space-y-4">
            <PasswordInput
              id="id-current-password"
              name="old_password"
              label="Current Password"
              required
            />
            <PasswordInput
              id="id-new-password"
              name="new_password"
              label="New Password"
              required
              minLength={8}
            />
            <PasswordInput
              id="id-confirm-password"
              name="confirm_password"
              label="Confirm New Password"
              required
            />
            <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Change Password</SubmitButton>
          </form>
        </div>
      </section>
    </div>
  )
}

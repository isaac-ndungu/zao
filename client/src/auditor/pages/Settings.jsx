import { useAuth } from '../../shared/hooks/useAuth'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import PasswordInput from '../../shared/components/PasswordInput'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

export default function AuditorSettings() {
  const { user } = useAuth()
  const { showToast } = useToast()

  const handleChangePassword = async (prev, formData) => {
    const data = formDataToObject(formData)
    if (data.new_password !== data.confirm_password) {
      showToast({ type: 'error', message: 'Passwords do not match.' })
      return
    }
    try {
      const res = await apiFetch('/api/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify({ current_password: data.current_password, new_password: data.new_password }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || Object.values(err).flat().join(', ')) }
      showToast({ type: 'success', message: 'Password changed successfully.' })
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
  }

  const { formAction: passwordAction } = useFormAction(handleChangePassword, {})

  return (
    <div>
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Settings</h2>
        <p className="text-on-surface-variant font-body-md">Profile & security</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Profile</h3>
          <div className="space-y-4">
            <div>
              <p className="text-label-md text-on-surface-variant">Name</p>
              <p className="text-body-md font-medium">{user ? `${user.first_name} ${user.last_name}` : '-'}</p>
            </div>
            <div>
              <p className="text-label-md text-on-surface-variant">Email</p>
              <p className="text-body-md">{user?.email || '-'}</p>
            </div>
            <div>
              <p className="text-label-md text-on-surface-variant">Role</p>
              <p className="text-body-md">Internal Auditor</p>
            </div>
            <div>
              <p className="text-label-md text-on-surface-variant">2FA</p>
              <p className="text-body-md text-success">Enabled (mandatory for auditors)</p>
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Change Password</h3>
          <form action={passwordAction} className="space-y-4">
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
              minLength={8}
            />
            <PasswordInput
              id="id-confirm-password"
              label="Confirm New Password"
              name="confirm_password"
              required
              minLength={8}
            />
            <SubmitButton className="px-6 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">Change Password</SubmitButton>
          </form>
        </div>
      </div>
    </div>
  )
}

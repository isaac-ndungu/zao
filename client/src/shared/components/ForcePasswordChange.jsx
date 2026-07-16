import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../hooks/useAuth'
import PasswordInput from './PasswordInput'
import { useFormAction, formDataToObject, SubmitButton } from '../hooks/useFormAction'

export default function ForcePasswordChange({ onComplete }) {
  const { changePassword, logout } = useAuth()

  const [, changeAction] = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    if (data.new_password !== data.confirm_password) {
      throw new Error('Passwords do not match.')
    }
    if (data.new_password.length < 8) {
      throw new Error('Password must be at least 8 characters.')
    }
    await changePassword(data.current_password, data.new_password)
    onComplete?.()
    return { success: true }
  }, {})

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

          <form action={changeAction} className="space-y-5">
            <PasswordInput
              id="currentPassword"
              name="current_password"
              label="Current Password"
              required
              autoFocus
              autoComplete="current-password"
            />

            <PasswordInput
              id="newPassword"
              name="new_password"
              label="New Password"
              required
              minLength={8}
              autoComplete="new-password"
            />

            <PasswordInput
              id="confirmPassword"
              name="confirm_password"
              label="Confirm New Password"
              required
              minLength={8}
              autoComplete="new-password"
            />

            <SubmitButton className="w-full bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors">
              Change Password
            </SubmitButton>
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

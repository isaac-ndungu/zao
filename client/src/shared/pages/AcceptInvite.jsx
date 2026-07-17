import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { apiFetch } from '../../admin/api/client'
import PasswordInput from '../components/PasswordInput'
import { useFormAction, formDataToObject, SubmitButton } from '../hooks/useFormAction'

const getErrMsg = (err) => {
  if (!err || typeof err === 'string') return err || ''
  if (typeof err.detail === 'string') return err.detail
  if (err.detail) return err.detail.join(', ')
  if (err.non_field_errors) return err.non_field_errors.join(', ')
  return Object.values(err).flat().join(', ')
}

export default function AcceptInvite() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [step, setStep] = useState('form')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [expired, setExpired] = useState(false)

  useEffect(() => {
    if (!token) {
      setError('Invalid invite link. No invite token found.')
    }
  }, [token])

  const handleResendOTP = async () => {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/auth/invite/request-otp/', {
        method: 'POST',
        body: JSON.stringify({ invite_token: token }),
        requireAuth: false,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        if (res.status === 400 && getErrMsg(err).includes('expired')) {
          setExpired(true)
          setError('This invite link has expired. Please contact your platform administrator to send a new invite.')
          return
        }
        throw new Error(getErrMsg(err) || 'Failed to resend code')
      }
      setStep('form')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const { formAction: inviteAction } = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    if (!token) {
      throw new Error('Invalid invite link.')
    }
    if (data.password.length < 8) {
      throw new Error('Password must be at least 8 characters.')
    }
    if (data.password !== data.confirm_password) {
      throw new Error('Passwords do not match.')
    }
    if (data.phone_number.length < 10) {
      throw new Error('Enter a valid phone number.')
    }
    if (data.otp_code.length !== 6) {
      throw new Error('Enter the 6-digit verification code from your email.')
    }

    const res = await apiFetch('/api/auth/invite/verify/', {
      method: 'POST',
      body: JSON.stringify({
        invite_token: token,
        otp_code: data.otp_code,
        password: data.password,
        phone_number: data.phone_number,
      }),
      requireAuth: false,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      if (res.status === 400 && getErrMsg(err).includes('expired')) {
        setExpired(true)
        throw new Error('This invite link has expired. Please contact your platform administrator to send a new invite.')
      }
      throw new Error(getErrMsg(err) || 'Verification failed')
    }
    navigate('/admin/login?invite=accepted', { replace: true })
    return { success: true }
  }, {})

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-container p-4">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-8 max-w-md w-full text-center">
          <span className="material-symbols-outlined text-5xl text-error mb-4" aria-hidden="true">link_off</span>
          <h1 className="text-xl font-bold text-on-surface mb-2">Invalid Invite Link</h1>
          <p className="text-on-surface-variant mb-4">No invite token found in the link. Please check the URL or contact your administrator.</p>
        </div>
      </div>
    )
  }

  if (expired) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-container p-4">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-8 max-w-md w-full text-center">
          <span className="material-symbols-outlined text-5xl text-warning mb-4" aria-hidden="true">timer_off</span>
          <h1 className="text-xl font-bold text-on-surface mb-2">Invite Expired</h1>
          <p className="text-on-surface-variant mb-6">This invite link has expired. Please contact your platform administrator to send a new invite.</p>
          <button onClick={handleResendOTP} disabled={loading} className="px-6 py-3 bg-primary text-on-primary rounded-xl font-bold disabled:opacity-50">
            {loading ? 'Sending...' : 'Request New Invite Code'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-container p-4">
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-8 max-w-md w-full">
        <div className="text-center mb-6">
          <span className="material-symbols-outlined text-5xl text-primary mb-2" aria-hidden="true">mail</span>
          <h1 className="text-xl font-bold text-on-surface">Accept Your Invite</h1>
          <p className="text-on-surface-variant text-sm mt-1">Check your email for the verification code</p>
        </div>

        <form action={inviteAction} className="space-y-4">
          <div>
            <label htmlFor="invite-otp" className="block text-label-md text-on-surface-variant mb-1">Verification Code *</label>
            <input
              id="invite-otp"
              name="otp_code"
              placeholder="000000"
              maxLength={6}
              required
              className="w-full px-3 py-3 border border-outline-variant rounded-xl text-body-md bg-surface text-center text-2xl tracking-[0.5em] font-mono"
            />
            <p className="text-xs text-on-surface-variant mt-1">Enter the 6-digit code sent to your email</p>
          </div>

          <div>
            <label htmlFor="invite-phone" className="block text-label-md text-on-surface-variant mb-1">Phone Number *</label>
            <input
              id="invite-phone"
              name="phone_number"
              placeholder="0712345678"
              required
              className="w-full px-3 py-3 border border-outline-variant rounded-xl text-body-md bg-surface"
            />
          </div>

          <div>
            <PasswordInput
              id="invite-password"
              name="password"
              label="Password *"
              placeholder="Min. 8 characters"
              minLength={8}
              required
            />
          </div>

          <div>
            <PasswordInput
              id="invite-confirm-password"
              name="confirm_password"
              label="Confirm Password *"
              placeholder="Repeat password"
              minLength={8}
              required
            />
          </div>

          {error && (
            <div className="bg-error-container text-error text-sm p-3 rounded-lg">
              {error}
              {error.includes('expired') && (
                <button type="button" onClick={handleResendOTP} className="block mt-2 underline font-bold">
                  Resend verification code
                </button>
              )}
            </div>
          )}

          <SubmitButton className="w-full bg-primary text-on-primary py-3 rounded-xl font-bold">
            Accept Invite & Set Password
          </SubmitButton>

          <p className="text-xs text-on-surface-variant text-center">
            Already have an account? <a href="/admin/login" className="text-primary underline">Sign in</a>
          </p>
        </form>
      </div>
    </div>
  )
}

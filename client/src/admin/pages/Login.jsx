import { useState, useEffect, useRef, useCallback, useTransition, useActionState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, getLoginRedirect } from '../../shared/hooks/useAuth'
import OTPInput from '../../shared/components/OTPInput'
import ForcePasswordChange from '../../shared/components/ForcePasswordChange'
import PasswordInput from '../../shared/components/PasswordInput'
import { apiFetch } from '../api/client'

function loadGisScript() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts) return resolve()
    const s = document.createElement('script')
    s.src = 'https://accounts.google.com/gsi/client'
    s.async = true
    s.defer = true
    s.onload = resolve
    s.onerror = () => reject(new Error('Failed to load Google Identity Services script.'))
    document.head.appendChild(s)
  })
}

export default function Login() {
  const auth = useAuth()
  const { login, requestOtp, verifyOtp, isAuthenticated } = auth
  const navigate = useNavigate()
  const googleBtnRef = useRef(null)
  const [gisReady, setGisReady] = useState(false)

  const [otpCode, setOtpCode] = useState('')
  const [step, setStep] = useState('credentials')
  const [loginToken, setLoginToken] = useState('')
  const [error, setError] = useState('')
  const [isPending, startTransition] = useTransition()
  const [googleLoading, setGoogleLoading] = useState(false)
  const [mustChangePassword, setMustChangePassword] = useState(false)
  const [otpSent, setOtpSent] = useState(false)

  const sessionExpired = new URLSearchParams(window.location.search).get('expired') === '1'

  useEffect(() => {
    if (isAuthenticated) {
      navigate(getLoginRedirect(auth.role), { replace: true })
    }
  }, [isAuthenticated, auth.role, navigate])

  useEffect(() => {
    loadGisScript()
      .then(() => setGisReady(true))
      .catch(() => {
        console.warn('Google Sign-In unavailable: failed to load Google Identity Services script.')
      })
  }, [])

  const handleGoogleCredential = useCallback(async (credential) => {
    setGoogleLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/auth/google/', {
        method: 'POST',
        body: JSON.stringify({ credential }),
        requireAuth: false,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw { ...data, status: res.status }

      const { setAccessToken } = await import('../api/client')
      setAccessToken(data.access)
      auth.refreshUser()
      navigate(getLoginRedirect(data.user.role), { replace: true })
    } catch (err) {
      setError(err.detail || err.message || 'Google sign-in failed.')
    } finally {
      setGoogleLoading(false)
    }
  }, [auth, navigate])

  useEffect(() => {
    if (!gisReady) return
    const container = googleBtnRef.current
    if (!container || container.hasChildNodes()) return
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) {
      console.warn('Google Sign-In disabled: VITE_GOOGLE_CLIENT_ID not configured.')
      return
    }

    google.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => handleGoogleCredential(response.credential),
    })
    google.accounts.id.renderButton(container, {
      theme: 'outline',
      size: 'large',
      text: 'signin_with',
      shape: 'rectangular',
      width: container.offsetWidth || 300,
    })
  }, [gisReady, handleGoogleCredential])

  const [, loginAction] = useActionState(async (_prev, formData) => {
    const email = formData.get('email')
    const password = formData.get('password')
    if (!email || !password) return
    setError('')

    startTransition(async () => {
      try {
        const result = await login(email, password)
        if (result.requires_2fa) {
          setLoginToken(result.loginToken)
          setStep('otp')
          setOtpCode('')
          setOtpSent(false)
          try {
            await requestOtp(result.loginToken)
            setOtpSent(true)
          } catch (otpErr) {
            setError(otpErr.detail || 'Failed to send verification code. Click "Resend code" to try again.')
          }
        } else {
          navigate(getLoginRedirect(result.user.role), { replace: true })
        }
      } catch (err) {
        if (err.must_change_password) {
          setMustChangePassword(true)
        } else {
          setError(err.detail || err.message || 'Invalid credentials.')
        }
      }
    })
  }, null)

  const handleSendOtp = async () => {
    setError('')
    startTransition(async () => {
      try {
        await requestOtp(loginToken)
        setOtpSent(true)
        setOtpCode('')
      } catch (err) {
        setError(err.detail || 'Failed to resend OTP.')
      }
    })
  }

  const handleOtpSubmit = async (e) => {
    e.preventDefault()
    if (otpCode.length !== 6) return
    setError('')

    startTransition(async () => {
      try {
        const result = await verifyOtp(loginToken, otpCode)
        if (result?.user) {
          navigate(getLoginRedirect(result.user.role), { replace: true })
        }
      } catch (err) {
        setError(err.detail || err.message || 'Invalid or expired OTP.')
      }
    })
  }

  if (mustChangePassword) {
    return (
      <ForcePasswordChange
        onComplete={() => {
          setMustChangePassword(false)
          navigate(getLoginRedirect(auth.role), { replace: true })
        }}
      />
    )
  }

  const backToCredentials = () => {
    setStep('credentials')
    setError('')
    setOtpCode('')
    setOtpSent(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="font-display-lg text-display-lg text-primary">Zao</h1>
          <p className="text-on-surface-variant text-body-md mt-1">Sign In</p>
        </div>

        {sessionExpired && (
          <div className="mb-4 px-4 py-3 bg-warning-container text-on-warning-container rounded-xl text-body-md text-center border border-warning">
            Your session has expired. Please sign in again.
          </div>
        )}

        <div className="bg-surface-container-lowest rounded-xl shadow-lg p-8 border border-outline-variant">
          {step === 'credentials' ? (
            <form action={loginAction} className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-label-md text-on-surface-variant mb-1">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="you@example.com"
                  required
                  autoFocus
                  autoComplete="email"
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent placeholder:text-on-surface-variant/60"
                />
              </div>

              <div>
                <PasswordInput
                  id="password"
                  name="password"
                  label="Password"
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <div className="bg-error-container text-error text-body-md px-3 py-2 rounded-lg">{error}</div>
              )}

              <button
                type="submit"
                disabled={isPending}
                className="w-full bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isPending && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
                {isPending ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleOtpSubmit} className="space-y-5">
              <div>
                <label htmlFor="otp" className="block text-label-md text-on-surface-variant mb-1">
                  Verification Code
                </label>
                <OTPInput
                  value={otpCode}
                  onChange={setOtpCode}
                  onSubmit={handleOtpSubmit}
                  error={error}
                  autoFocus
                />
                <p className="text-label-md text-on-surface-variant mt-2">
                  {otpSent
                    ? 'A 6‑digit code was sent to your email.'
                    : 'Click "Send Code" to receive a verification code.'}
                </p>
              </div>

              {error && (
                <div className="bg-error-container text-error text-body-md px-3 py-2 rounded-lg">{error}</div>
              )}

              <button
                type="submit"
                disabled={isPending || otpCode.length !== 6}
                className="w-full bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isPending && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
                {isPending ? 'Verifying...' : 'Verify'}
              </button>

              <button
                type="button"
                onClick={handleSendOtp}
                disabled={isPending}
                className="w-full text-center text-body-md text-primary hover:underline mt-1"
              >
                Resend code
              </button>

              <button
                type="button"
                onClick={backToCredentials}
                className="w-full text-center text-body-md text-primary hover:underline mt-1"
              >
                Back to login
              </button>
            </form>
          )}

          {step === 'credentials' && (
            <>
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-outline-variant" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-surface-container-lowest px-2 text-on-surface-variant">or</span>
                </div>
              </div>

              <div className="relative w-full min-h-[40px] flex justify-center items-center">
                <div ref={googleBtnRef} className={`w-full flex justify-center ${googleLoading ? 'invisible' : ''}`} />
                {googleLoading && (
                  <div className="absolute inset-0 flex items-center justify-center gap-2 text-on-surface-variant text-body-md">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
                    Signing in...
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <p className="text-center text-label-md text-on-surface-variant mt-6">
          <a href="/" className="hover:underline">Back to home</a>
        </p>
      </div>
    </div>
  )
}

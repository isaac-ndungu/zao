import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, getLoginRedirect } from '../../shared/hooks/useAuth'
import OTPInput from '../../shared/components/OTPInput'
import ForcePasswordChange from '../../shared/components/ForcePasswordChange'

export default function Login() {
  const auth = useAuth()
  const { login, requestOtp, verifyOtp, isAuthenticated } = auth
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [step, setStep] = useState('credentials')
  const [loginToken, setLoginToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mustChangePassword, setMustChangePassword] = useState(false)

  const sessionExpired = new URLSearchParams(window.location.search).get('expired') === '1'

  useEffect(() => {
    if (isAuthenticated) {
      navigate(getLoginRedirect(auth.role), { replace: true })
    }
  }, [isAuthenticated, auth.role, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await login(email, password)
      if (result.requires_2fa) {
        setLoginToken(result.loginToken)
        setStep('otp')
        setOtpSent(false)
      } else {
        navigate(getLoginRedirect(result.user.role), { replace: true })
      }
    } catch (err) {
      if (err.must_change_password) {
        setMustChangePassword(true)
      } else {
        setError(err.detail || err.message || 'Invalid credentials.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSendOtp = async () => {
    setError('')
    setLoading(true)
    try {
      await requestOtp(loginToken)
      setOtpSent(true)
    } catch (err) {
      setError(err.detail || 'Failed to send OTP.')
    } finally {
      setLoading(false)
    }
  }

  const handleOtpSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await verifyOtp(loginToken, otpCode)
      if (result?.user) {
        navigate(getLoginRedirect(result.user.role), { replace: true })
      }
    } catch (err) {
      setError(err.detail || err.message || 'Invalid or expired OTP.')
    } finally {
      setLoading(false)
    }
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
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-label-md text-on-surface-variant mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoFocus
                  autoComplete="email"
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent placeholder:text-on-surface-variant/60"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-label-md text-on-surface-variant mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent placeholder:text-on-surface-variant/60"
                />
              </div>

              {error && (
                <div className="bg-error-container text-error text-body-md px-3 py-2 rounded-lg">{error}</div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
                {loading ? 'Signing in...' : 'Sign In'}
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
                    ? 'A 6-digit code was sent to your email.'
                    : 'Click "Send Code" to receive a verification code.'}
                </p>
              </div>

              {error && !otpCode && (
                <div className="bg-error-container text-error text-body-md px-3 py-2 rounded-lg">{error}</div>
              )}

              <div className="flex gap-3">
                {!otpSent ? (
                  <button
                    type="button"
                    onClick={handleSendOtp}
                    disabled={loading}
                    className="flex-1 bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
                    {loading ? 'Sending...' : 'Send Code'}
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={loading || otpCode.length !== 6}
                    className="flex-1 bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
                    {loading ? 'Verifying...' : 'Verify'}
                  </button>
                )}
              </div>

              <button
                type="button"
                onClick={backToCredentials}
                className="w-full text-center text-body-md text-primary hover:underline mt-2"
              >
                Back to login
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-label-md text-on-surface-variant mt-6">
          Zao Farmer Management System
        </p>
      </div>
    </div>
  )
}

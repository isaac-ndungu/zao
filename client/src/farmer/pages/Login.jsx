import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../shared/hooks/useAuth'
import OTPInput from '../../shared/components/OTPInput'

export default function FarmerLogin() {
  const { farmerLogin, farmerVerify, isAuthenticated, isFarmer } = useAuth()
  const navigate = useNavigate()

  const [phoneNumber, setPhoneNumber] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [loginToken, setLoginToken] = useState('')
  const [step, setStep] = useState('phone')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated && isFarmer) {
      navigate('/farmer/dashboard', { replace: true })
    }
  }, [isAuthenticated, isFarmer, navigate])

  const handleSendOtp = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await farmerLogin(phoneNumber)
      setLoginToken(result.loginToken)
      setStep('otp')
    } catch (err) {
      setError(err.detail || err.message || 'Failed to send OTP.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOtp = async () => {
    setError('')
    setLoading(true)
    try {
      await farmerVerify(loginToken, otpCode)
      navigate('/farmer/dashboard', { replace: true })
    } catch (err) {
      setError(err.detail || err.message || 'Invalid or expired OTP.')
    } finally {
      setLoading(false)
    }
  }

  const handleOtpSubmit = (e) => {
    e.preventDefault()
    handleVerifyOtp()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="font-display-lg text-display-lg text-primary">Zao</h1>
          <p className="text-on-surface-variant text-body-md mt-1">Farmer Dashboard</p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl shadow-lg p-8 border border-outline-variant">
          {step === 'phone' ? (
            <form onSubmit={handleSendOtp} className="space-y-5">
              <div>
                <label htmlFor="phone" className="block text-label-md text-on-surface-variant mb-1">
                  Phone Number
                </label>
                <input
                  id="phone"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="0712 345 678"
                  required
                  autoFocus
                  autoComplete="tel"
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent placeholder:text-on-surface-variant/60"
                />
              </div>

              {error && (
                <div className="bg-error-container text-error text-body-md px-3 py-2 rounded-lg">{error}</div>
              )}

              <button
                type="submit"
                disabled={loading || !phoneNumber.trim()}
                className="w-full bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
                {loading ? 'Sending...' : 'Send OTP'}
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
                  onSubmit={handleVerifyOtp}
                  error={error}
                  autoFocus
                />
                <p className="text-label-md text-on-surface-variant mt-2">
                  A 6-digit code was sent to your phone.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading || otpCode.length !== 6}
                className="w-full bg-primary text-on-primary font-body-md text-body-md py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
                {loading ? 'Verifying...' : 'Verify'}
              </button>

              <button
                type="button"
                onClick={() => { setStep('phone'); setError(''); setOtpCode('') }}
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

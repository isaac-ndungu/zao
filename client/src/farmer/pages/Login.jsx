import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFarmerAuth } from '../context/FarmerAuthContext'
import { getToken } from '../api/client'

function OTPInput({ value, onChange, onSubmit, error, autoFocus }) {
  const handleChange = (val) => {
    const digits = val.replace(/\D/g, '').slice(0, 6)
    onChange(digits)
    if (digits.length === 6) setTimeout(() => onSubmit?.(), 100)
  }

  return (
    <div>
      <div className="flex gap-2 justify-center mb-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <input
            key={i}
            type="tel"
            maxLength={1}
            value={value[i] || ''}
            onChange={(e) => {
              const newVal = value.split('')
              newVal[i] = e.target.value.replace(/\D/g, '')
              handleChange(newVal.join(''))
              if (e.target.value && i < 5) {
                const next = document.querySelector(`[data-otp="${i + 1}"]`)
                next?.focus()
              }
            }}
            onKeyDown={(e) => {
              if (e.key === 'Backward' && !value[i] && i > 0) {
                const prev = document.querySelector(`[data-otp="${i - 1}"]`)
                prev?.focus()
              }
            }}
            data-otp={i}
            ref={(el) => { if (i === 0 && autoFocus) el?.focus() }}
            className="w-11 h-12 text-center text-xl font-bold border border-outline-variant rounded-lg bg-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
          />
        ))}
      </div>
      {error && <p className="text-error text-sm text-center mt-2">{error}</p>}
    </div>
  )
}

export default function FarmerLogin() {
  const { farmerLogin, farmerVerify, isAuthenticated } = useFarmerAuth()
  const navigate = useNavigate()

  const [phoneNumber, setPhoneNumber] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [loginToken, setLoginToken] = useState('')
  const [step, setStep] = useState('phone')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated || getToken()) navigate('/farmer/dashboard', { replace: true })
  }, [isAuthenticated, navigate])

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
    } finally { setLoading(false) }
  }

  const handleVerifyOtp = async () => {
    setError('')
    setLoading(true)
    try {
      await farmerVerify(loginToken, otpCode)
      navigate('/farmer/dashboard', { replace: true })
    } catch (err) {
      setError(err.detail || err.message || 'Invalid or expired OTP.')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="material-symbols-outlined text-on-primary text-3xl">agriculture</span>
          </div>
          <h1 className="text-2xl font-bold text-primary mb-1">Zao Farmer</h1>
          <p className="text-on-surface-variant text-sm">Sign in to your account</p>
        </div>

        <div className="bg-surface-container rounded-xl shadow-lg p-6 border border-outline-variant">
          {step === 'phone' ? (
            <form onSubmit={handleSendOtp} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">Phone Number</label>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="0712 345 678"
                  required
                  autoFocus
                  className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]"
                />
              </div>
              {error && <div className="bg-error-container text-error text-sm px-3 py-2 rounded-lg">{error}</div>}
              <button type="submit" disabled={loading || !phoneNumber.trim()} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed w-full">
                {loading ? <><span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full mr-2" /> Sending...</> : 'Send OTP'}
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); handleVerifyOtp() }} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1.5 text-center">Verification Code</label>
                <OTPInput value={otpCode} onChange={setOtpCode} onSubmit={handleVerifyOtp} error={error} autoFocus />
                <p className="text-xs text-on-surface-variant text-center mt-2">A 6-digit code was sent to your phone.</p>
              </div>
              <button type="submit" disabled={loading || otpCode.length !== 6} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed w-full">
                {loading ? <><span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full mr-2" /> Verifying...</> : 'Verify'}
              </button>
              <button type="button" onClick={() => { setStep('phone'); setError(''); setOtpCode('') }} className="w-full text-center text-sm text-primary font-medium hover:underline mt-2">
                Back to login
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-on-surface-variant mt-6">Zao Farmer Management System</p>
      </div>
    </div>
  )
}

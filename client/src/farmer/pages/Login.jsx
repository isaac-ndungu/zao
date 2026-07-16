import { useState, useEffect, useRef, useTransition, useActionState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFarmerAuth } from '../context/FarmerAuthContext'
import { getToken } from '../api/client'

function OTPInput({ value, onChange, onSubmit, error, autoFocus }) {
  const inputRefs = useRef([])

  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      inputRefs.current[0].focus()
    }
  }, [autoFocus])

  const handleChange = (newValue) => {
    const digits = newValue.replace(/\D/g, '').slice(0, 6)
    onChange(digits)
    if (digits.length === 6) {
      setTimeout(() => onSubmit?.(), 100)
    }
  }

  const focusNext = (index) => {
    if (index < 5) inputRefs.current[index + 1]?.focus()
  }

  const focusPrev = (index) => {
    if (index > 0) inputRefs.current[index - 1]?.focus()
  }

  const handleInputChange = (index, char) => {
    const digit = char.replace(/\D/g, '')
    if (!digit) return
    const newValue = value.split('')
    newValue[index] = digit
    handleChange(newValue.join(''))
    focusNext(index)
  }

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace') {
      if (value[index]) {
        const newValue = value.split('')
        newValue[index] = ''
        handleChange(newValue.join(''))
      } else {
        focusPrev(index)
      }
    } else if (e.key === 'ArrowLeft') {
      focusPrev(index)
    } else if (e.key === 'ArrowRight') {
      focusNext(index)
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const pastedData = e.clipboardData.getData('text/plain')
    const digits = pastedData.replace(/\D/g, '').slice(0, 6)
    handleChange(digits)
    const nextIndex = Math.min(digits.length, 5)
    inputRefs.current[nextIndex]?.focus()
  }

  return (
    <div>
      <div
        className="flex gap-2 justify-center mb-2"
        onPaste={handlePaste}
        role="group"
        aria-label="One-time password input, 6 digits"
      >
        {Array.from({ length: 6 }).map((_, i) => (
          <input
            key={i}
            ref={(el) => (inputRefs.current[i] = el)}
            type="tel"
            inputMode="numeric"
            maxLength={1}
            value={value[i] || ''}
            onChange={(e) => handleInputChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            className="w-11 h-12 text-center text-xl font-bold border border-outline-variant rounded-lg bg-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            aria-label={`Digit ${i + 1} of 6`}
          />
        ))}
      </div>
      {error && (
        <p role="alert" className="text-error text-sm text-center mt-2">
          {error}
        </p>
      )}
    </div>
  )
}

export default function FarmerLogin() {
  const { farmerLogin, farmerVerify, isAuthenticated } = useFarmerAuth()
  const navigate = useNavigate()

  const [otpCode, setOtpCode] = useState('')
  const [loginToken, setLoginToken] = useState('')
  const [step, setStep] = useState('phone')
  const [error, setError] = useState('')
  const [isPending, startTransition] = useTransition()
  const ignoreRef = useRef(false)

  const sessionExpired = new URLSearchParams(window.location.search).get('expired') === '1'

  useEffect(() => {
    if (isAuthenticated || getToken()) navigate('/farmer/dashboard', { replace: true })
  }, [isAuthenticated, navigate])

  const [, phoneAction] = useActionState(async (_prev, formData) => {
    const phone = formData.get('phone')?.trim()
    if (!phone) return
    setError('')

    startTransition(async () => {
      ignoreRef.current = false
      const safetyTimer = setTimeout(() => {
        if (!ignoreRef.current) {
          setError('Request timed out. Please try again.')
        }
      }, 30000)

      try {
        const result = await farmerLogin(phone)
        clearTimeout(safetyTimer)
        if (ignoreRef.current) return
        setLoginToken(result.loginToken)
        setStep('otp')
      } catch (err) {
        clearTimeout(safetyTimer)
        if (ignoreRef.current) return
        setError(err.detail || err.message || 'Failed to send OTP.')
      }
    })
  }, null)

  const handleVerifyOtp = async () => {
    if (otpCode.length !== 6) return
    setError('')

    startTransition(async () => {
      const safetyTimer = setTimeout(() => {
        if (!ignoreRef.current) {
          setError('Verification timed out. Please try again.')
        }
      }, 30000)

      try {
        await farmerVerify(loginToken, otpCode)
        clearTimeout(safetyTimer)
        navigate('/farmer/dashboard', { replace: true })
      } catch (err) {
        clearTimeout(safetyTimer)
        setError(err.detail || err.message || 'Invalid or expired OTP.')
      }
    })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
          <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="material-symbols-outlined text-on-primary text-3xl" aria-hidden="true">agriculture</span>
          </div>
          <h1 className="text-2xl font-bold text-primary mb-1">Zao Farmer</h1>
          <p className="text-on-surface-variant text-sm">Sign in to your account</p>
        </div>

        {sessionExpired && (
          <div role="alert" className="mb-4 px-4 py-3 bg-warning-container text-on-warning-container rounded-xl text-sm text-center border border-warning">
            Your session has expired. Please sign in again.
          </div>
        )}

        <div className="bg-surface-container rounded-xl shadow-lg p-6 border border-outline-variant">
          {step === 'phone' ? (
            <form action={phoneAction} className="space-y-5">
              <div>
                <label htmlFor="phone-input" className="block text-xs font-semibold text-on-surface-variant mb-1.5">Phone Number</label>
                <input
                  id="phone-input"
                  name="phone"
                  type="tel"
                  placeholder="0712 345 678"
                  required
                  autoFocus
                  className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]"
                />
              </div>
              {error && <div role="alert" className="bg-error-container text-error text-sm px-3 py-2 rounded-lg">{error}</div>}
              <button
                type="submit"
                disabled={isPending}
                className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed w-full"
                aria-label={isPending ? 'Sending one-time password' : 'Send one-time password'}
              >
                {isPending ? <><span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full mr-2" aria-hidden="true" /> Sending...</> : 'Send OTP'}
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); handleVerifyOtp() }} className="space-y-5">
              <div>
                <span id="otp-label" className="block text-xs font-semibold text-on-surface-variant mb-1.5 text-center">Verification Code</span>
                <OTPInput value={otpCode} onChange={setOtpCode} onSubmit={handleVerifyOtp} error={error} autoFocus />
                <p className="text-xs text-on-surface-variant text-center mt-2">A 6-digit code was sent to your phone.</p>
              </div>
              <button
                type="submit"
                disabled={isPending || otpCode.length !== 6}
                className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed w-full"
                aria-label={isPending ? 'Verifying one-time password' : 'Verify and sign in'}
              >
                {isPending ? <><span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full mr-2" aria-hidden="true" /> Verifying...</> : 'Verify'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep('phone')
                  setError('')
                  setOtpCode('')
                  ignoreRef.current = true
                }}
                className="w-full text-center text-sm text-primary font-medium hover:underline mt-2"
                aria-label="Back to login"
              >
                Back to login
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-on-surface-variant mt-6">
          <a href="/" className="hover:underline">Back to home</a>
        </p>
      </div>
    </div>
  )
}

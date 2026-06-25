import { useRef, useEffect } from 'react'

export default function OTPInput({ value, onChange, onSubmit, length = 6, disabled, error, autoFocus }) {
  const inputRef = useRef(null)

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
    }
  }, [autoFocus])

  const handleChange = (e) => {
    const cleaned = e.target.value.replace(/\D/g, '').slice(0, length)
    onChange(cleaned)
    if (onSubmit && cleaned.length === length) {
      onSubmit()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && value.length === length && onSubmit) {
      onSubmit()
    }
  }

  return (
    <div>
      <input
        ref={inputRef}
        id="otp"
        type="text"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={'0'.repeat(length)}
        required
        maxLength={length}
        inputMode="numeric"
        autoComplete="one-time-code"
        disabled={disabled}
        className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent placeholder:text-on-surface-variant/60 text-center tracking-[0.3em] disabled:opacity-50 disabled:cursor-not-allowed"
      />
      {error && (
        <p className="text-error text-body-md mt-1">{error}</p>
      )}
    </div>
  )
}

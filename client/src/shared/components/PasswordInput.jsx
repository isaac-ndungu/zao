import { useState } from 'react'

export default function PasswordInput({
  id,
  label,
  name,
  value,
  onChange,
  defaultValue,
  placeholder,
  required,
  autoComplete,
  autoFocus,
  minLength,
  error,
  className = '',
  ...props
}) {
  const [showPassword, setShowPassword] = useState(false)
  const isControlled = value !== undefined

  return (
    <div>
      {label && (
        <label htmlFor={id} className="block text-label-md text-on-surface-variant mb-1">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={id}
          name={name}
          type={showPassword ? 'text' : 'password'}
          {...isControlled ? { value, onChange } : { defaultValue }}
          placeholder={placeholder}
          required={required}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          minLength={minLength}
          className={`w-full px-3 py-2 pr-10 border border-outline-variant rounded-lg text-body-md text-on-surface bg-surface-container focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent placeholder:text-on-surface-variant/60 ${className}`}
          {...props}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-0 bottom-0 flex items-center text-[#5a6b5c] hover:text-primary transition-colors"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          <span className="material-symbols-outlined text-sm">
            {showPassword ? 'visibility_off' : 'visibility'}
          </span>
        </button>
      </div>
      {error && (
        <p className="text-error text-label-md mt-1">{error}</p>
      )}
    </div>
  )
}

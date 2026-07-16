/* eslint-disable react-refresh/only-export-components */
import { useActionState, useRef } from 'react'
import { useFormStatus } from 'react-dom'

export function formDataToObject(formData) {
  const obj = {}
  for (const [key, value] of formData) obj[key] = value
  return obj
}

export function useFormAction(action, initialState) {
  const onSuccessRef = useRef(null)
  onSuccessRef.current = action._onSuccess || null

  const [state, formAction, isPending] = useActionState(async (prev, formData) => {
    try {
      const result = await action(prev, formData)
      if (onSuccessRef.current) onSuccessRef.current(result)
      return { ...prev, ...result, error: null }
    } catch (err) {
      return { ...prev, error: err.message || 'Something went wrong' }
    }
  }, initialState)

  return { state, formAction, isPending }
}

export function SubmitButton({ children, className = '' }) {
  const { pending } = useFormStatus()

  return (
    <button
      type="submit"
      disabled={pending}
      className={`${className} disabled:opacity-40 disabled:cursor-not-allowed`}
    >
      {pending ? (
        <span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full" />
      ) : children}
    </button>
  )
}

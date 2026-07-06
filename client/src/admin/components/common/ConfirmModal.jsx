import { useEffect, useRef } from 'react'
import useFocusTrap from '../../../shared/hooks/useFocusTrap'

export default function ConfirmModal({ open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', onConfirm, onCancel, loading, destructive, impactSummary }) {
  const confirmRef = useRef(null)
  const focusRef = useRef(null)
  useFocusTrap(focusRef)

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') onCancel() }
    document.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    confirmRef.current?.focus()
    return () => {
      document.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [open, onCancel])

  if (!open) return null

  return (
    <div
      ref={focusRef}
      className="fixed inset-0 z-[60] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="fixed inset-0 bg-black/30 transition-opacity duration-200" onClick={onCancel} />
      <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl transform transition-all duration-200 scale-100">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">{title}</h3>
        <p className="text-body-md text-on-surface-variant mb-6">{message}</p>
        {impactSummary && (
          <div className="mb-6 px-4 py-3 bg-surface-container rounded-lg">
            <p className="text-label-md font-bold text-on-surface mb-1">This will also restore:</p>
            <ul className="space-y-0.5">
              {impactSummary.map((item, i) => (
                <li key={i} className="text-body-sm text-on-surface-variant flex items-center gap-2">
                  <span className="material-symbols-outlined text-[14px] text-primary" aria-hidden="true">{item.icon}</span>
                  {item.count} {item.label}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            onClick={onConfirm}
            disabled={loading}
            aria-describedby={loading ? 'confirm-loading' : undefined}
            className={`px-4 py-2 rounded-lg text-label-md font-bold text-white transition-colors disabled:opacity-50 ${
              destructive ? 'bg-error hover:bg-error/90' : 'bg-primary hover:bg-primary/90'
            }`}
          >
            {loading ? (
              <span className="flex items-center gap-2" id="confirm-loading">
                <div className="animate-spin rounded-full h-3 w-3 border-b border-white" aria-hidden="true" />
                <span>Processing...</span>
              </span>
            ) : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

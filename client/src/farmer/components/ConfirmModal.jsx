export default function ConfirmModal({ open, title, message, confirmLabel, cancelLabel, onConfirm, onCancel, loading }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" role="presentation" onClick={onCancel}>
      <div className="bg-surface rounded-2xl w-full max-w-sm p-6 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="confirm-modal-title" onClick={(e) => e.stopPropagation()}>
        <div className="w-12 h-12 rounded-full bg-error-container flex items-center justify-center mx-auto mb-4">
          <span className="material-symbols-outlined text-error" aria-hidden="true">logout</span>
        </div>
        <h3 id="confirm-modal-title" className="text-lg font-bold text-center mb-2">{title}</h3>
        <p className="text-sm text-on-surface-variant text-center mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 py-3 rounded-xl border border-outline-variant text-sm font-semibold min-h-[44px] hover:bg-surface-container-high transition-colors disabled:opacity-40"
          >
            {cancelLabel || 'Cancel'}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 py-3 rounded-xl bg-error text-white text-sm font-semibold min-h-[44px] hover:opacity-80 transition-colors disabled:opacity-40"
          >
            {loading ? <span className="inline-block animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" /> : (confirmLabel || 'Confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}

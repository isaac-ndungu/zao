import { createContext, useContext, useState, useCallback } from 'react'

const ToastContext = createContext(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

const typeStyles = {
  success: 'bg-primary text-on-primary',
  error: 'bg-error text-on-error',
  info: 'bg-surface-container-high text-on-surface border border-outline-variant',
  warning: 'bg-tertiary-fixed-dim text-on-tertiary-fixed',
}

const typeIcons = {
  success: 'check_circle',
  error: 'error',
  info: 'info',
  warning: 'warning',
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const showToast = useCallback(({ type = 'info', message, duration = 4000 }) => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, duration)
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg animate-slide-in ${typeStyles[toast.type] || typeStyles.info}`}
          >
            <span className="material-symbols-outlined text-[20px] flex-shrink-0">
              {typeIcons[toast.type] || 'info'}
            </span>
            <p className="text-body-md flex-1">{toast.message}</p>
            <button onClick={() => removeToast(toast.id)} className="p-0.5 hover:opacity-70 transition-opacity flex-shrink-0">
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

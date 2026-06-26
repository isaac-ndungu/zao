/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback } from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const showToast = useCallback(({ type = 'info', message, duration = 3000 }) => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, duration)
  }, [])

  const bgMap = { success: 'bg-success-container text-success', error: 'bg-error-container text-error', info: 'bg-info-container text-info', warning: 'bg-warning-container text-warning' }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed top-4 left-4 right-4 z-[60] flex flex-col gap-2 max-w-lg mx-auto pointer-events-none">
        {toasts.map(t => (
          <div key={t.id} className={`${bgMap[t.type] || bgMap.info} px-4 py-3 rounded-xl shadow-lg text-sm font-medium pointer-events-auto animate-[slideDown_0.3s_ease-out]`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

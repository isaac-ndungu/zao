import { createContext, useCallback, useContext, useRef, useState } from 'react'

const ToastContext = createContext(null)

let _id = 0
const nextId = () => ++_id

/**
 * Global toast notification system.
 *
 * Usage:
 *   const { toast } = useToast()
 *   toast.success('Farmer created')
 *   toast.error('Something went wrong')
 *   toast.info('Export queued')
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timersRef = useRef({})

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
    clearTimeout(timersRef.current[id])
    delete timersRef.current[id]
  }, [])

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = nextId()
    setToasts(prev => [...prev.slice(-4), { id, message, type }])
    timersRef.current[id] = setTimeout(() => dismiss(id), duration)
    return id
  }, [dismiss])

  const toast = {
    success: (msg, dur) => addToast(msg, 'success', dur),
    error: (msg, dur) => addToast(msg, 'error', dur ?? 8000),
    info: (msg, dur) => addToast(msg, 'info', dur),
    warning: (msg, dur) => addToast(msg, 'warning', dur),
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast container */}
      <div
        aria-live="polite"
        aria-atomic="false"
        style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
          pointerEvents: 'none',
          maxWidth: '22rem',
        }}
      >
        {toasts.map(t => (
          <Toast key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

const TYPE_STYLES = {
  success: { bg: '#166534', border: '#4ade80', icon: '✓' },
  error:   { bg: '#7f1d1d', border: '#f87171', icon: '✕' },
  warning: { bg: '#713f12', border: '#fbbf24', icon: '!' },
  info:    { bg: '#1e3a5f', border: '#60a5fa', icon: 'i' },
}

function Toast({ toast, onDismiss }) {
  const s = TYPE_STYLES[toast.type] || TYPE_STYLES.info
  const isError = toast.type === 'error'
  return (
    <div
      role={isError ? 'alert' : 'status'}
      aria-live={isError ? 'assertive' : 'polite'}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.75rem',
        padding: '0.875rem 1rem',
        borderRadius: '0.5rem',
        background: s.bg,
        borderLeft: `3px solid ${s.border}`,
        color: '#fff',
        fontSize: '0.875rem',
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        pointerEvents: 'all',
        animation: 'slideInRight 0.2s ease',
      }}
    >
      <span aria-hidden="true" style={{
        flexShrink: 0,
        width: '1.25rem',
        height: '1.25rem',
        borderRadius: '50%',
        border: `1.5px solid ${s.border}`,
        display: 'grid',
        placeItems: 'center',
        fontSize: '0.7rem',
        fontWeight: 700,
        color: s.border,
      }}>{s.icon}</span>
      <span style={{ flex: 1, lineHeight: 1.4 }}>{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss"
        style={{
          background: 'none',
          border: 'none',
          color: 'rgba(255,255,255,0.6)',
          cursor: 'pointer',
          fontSize: '1rem',
          lineHeight: 1,
          padding: 0,
          flexShrink: 0,
        }}
      >×</button>
    </div>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}

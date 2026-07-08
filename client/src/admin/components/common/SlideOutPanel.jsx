import { useEffect, useRef } from 'react'
import useFocusTrap from '../../../shared/hooks/useFocusTrap'

export default function SlideOutPanel({ open, onClose, title, subtitle, children, width = 'max-w-lg' }) {
  const focusRef = useRef(null)
  useFocusTrap(focusRef)

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  return (
    <>
      <div
        className={`fixed inset-0 z-[55] transition-opacity duration-300 ease-out ${
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        } bg-on-surface/40 backdrop-blur-[2px]`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={focusRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`fixed top-0 right-0 h-full bg-surface-container-lowest shadow-2xl z-[55] flex flex-col overflow-hidden
          rounded-l-2xl border-l border-outline-variant
          transition-transform duration-300 ease-out will-change-transform
          ${open ? 'translate-x-0' : 'translate-x-full'}
          ${width} w-full`}
      >
        <div className="relative flex items-start justify-between gap-4 px-6 pt-5 pb-4 border-b border-outline-variant bg-gradient-to-b from-surface-container-low to-surface-container-lowest">
          <div className="min-w-0 flex-1">
            <h3 className="font-headline-sm text-headline-sm text-on-surface truncate">{title}</h3>
            {subtitle && (
              <p className="mt-0.5 text-body-md text-on-surface-variant truncate">{subtitle}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="shrink-0 -mr-1 p-2 rounded-full text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface active:bg-surface-container-highest transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            aria-label="Close panel"
          >
            <span className="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto overscroll-contain px-6 py-5 scroll-smooth panel-scroll">
          {children}
        </div>
      </div>
    </>
  )
}

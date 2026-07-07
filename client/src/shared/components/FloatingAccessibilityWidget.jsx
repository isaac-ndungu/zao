import { useState, useEffect, useRef, createContext, useContext, useCallback } from 'react'
import { createPortal } from 'react-dom'

const STORAGE_KEY = 'zao_a11y_prefs'

const defaultPrefs = {
  fontSize: 'normal',
  contrast: 'standard',
  focusIndicators: 'normal',
  reduceMotion: false,
  language: 'en',
}

function loadPrefs() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return { ...defaultPrefs, ...JSON.parse(stored) }
  } catch {}
  return defaultPrefs
}

const A11yContext = createContext(null)

export function A11yProvider({ children }) {
  const [prefs, setPrefs] = useState(() => {
    if (typeof window === 'undefined') return defaultPrefs
    return loadPrefs()
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
    applyPrefs(prefs)
  }, [prefs])

  const updatePref = useCallback((key, value) => {
    setPrefs(p => ({ ...p, [key]: value }))
  }, [])

  return (
    <A11yContext.Provider value={{ prefs, updatePref }}>
      {children}
    </A11yContext.Provider>
  )
}

export function useA11yPrefs() {
  return useContext(A11yContext)
}

function applyPrefs(prefs) {
  const root = document.documentElement
  const body = document.body

  const fontScaleMap = { normal: 1, large: 1.15, 'extra-large': 1.3 }
  root.style.setProperty('--font-scale', fontScaleMap[prefs.fontSize] || 1)

  body.classList.toggle('high-contrast', prefs.contrast === 'high')
  body.classList.toggle('enhanced-focus', prefs.focusIndicators === 'enhanced')
  body.classList.toggle('reduce-motion', prefs.reduceMotion)

  if (prefs.language && typeof window !== 'undefined') {
    try {
      const farmerI18n = localStorage.getItem('zao_farmer_lang')
      if (farmerI18n !== prefs.language) {
        localStorage.setItem('zao_farmer_lang', prefs.language)
        window.dispatchEvent(new CustomEvent('zao-lang-change', { detail: { language: prefs.language } }))
      }
    } catch {}
  }
}

export default function FloatingAccessibilityWidget({ mode = 'staff' }) {
  const [isOpen, setIsOpen] = useState(false)
  const { prefs, updatePref } = useA11yPrefs()
  const panelRef = useRef(null)
  const triggerRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return
    const handler = (e) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen])

  useEffect(() => {
    if (isOpen && panelRef.current) {
      const focusable = panelRef.current.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
      if (focusable.length) focusable[0].focus()
    }
  }, [isOpen])

  const close = useCallback(() => {
    setIsOpen(false)
    triggerRef.current?.focus()
  }, [])

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768

  const widgetPosition = mode === 'farmer'
    ? 'bottom-20 right-4 sm:right-6'
    : 'bottom-6 right-20'

  const mobileTouchTarget = mode === 'farmer' ? 'min-h-[48px] min-w-[48px]' : ''

  const fontOptions = mode === 'farmer'
    ? [['normal', 'Normal'], ['large', 'Large']]
    : [['normal', 'Normal'], ['large', 'Large'], ['extra-large', 'Extra Large']]

  return (
    <>
      <style>{`
        :root { --font-scale: 1; }
        html { font-size: calc(16px * var(--font-scale)); }
        body.high-contrast {
          --primary: #004d00;
          --on-primary: #ffffff;
          --primary-container: #b8f5b8;
          --on-primary-container: #002200;
          --secondary: #8b4500;
          --on-secondary: #ffffff;
          --secondary-container: #ffd9a8;
          --on-secondary-container: #2d1600;
          --error: #ba1a1a;
          --on-error: #ffffff;
          --error-container: #ffdad6;
          --on-error-container: #410002;
          --background: #f8faf8;
          --on-background: #1a1c1a;
          --surface: #f8faf8;
          --on-surface: #1a1c1a;
          --surface-variant: #dde5db;
          --on-surface-variant: #414941;
          --outline: #717970;
          --outline-variant: #c1c9bf;
        }
        body.enhanced-focus *:focus {
          outline: 3px solid #0066cc !important;
          outline-offset: 2px !important;
          border-radius: 2px;
        }
        body.enhanced-focus *:focus-visible {
          outline: 3px solid #0066cc !important;
          outline-offset: 2px !important;
        }
        body.reduce-motion, body.reduce-motion * {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.01ms !important;
          scroll-behavior: auto !important;
        }
      `}</style>

      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Accessibility settings"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        className={`fixed ${widgetPosition} z-50 w-12 h-12 bg-primary-container text-on-primary-container rounded-full shadow-lg flex items-center justify-center hover:bg-primary/90 transition-colors ${mobileTouchTarget}`}
        style={{ marginBottom: 'env(safe-area-inset-bottom, 0)' }}
      >
        <span className="material-symbols-outlined text-2xl" aria-hidden="true">accessibility_new</span>
      </button>

      {isOpen && createPortal(
        <div
          className="fixed inset-0 z-[60]"
          onClick={close}
          role="presentation"
        >
          <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="a11y-panel-title"
            className="absolute bottom-6 right-4 sm:right-6 w-72 max-h-[70vh] overflow-y-auto bg-surface border border-outline-variant rounded-2xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            style={{ marginBottom: 'env(safe-area-inset-bottom, 0)' }}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant sticky top-0 bg-surface z-10">
              <h3 id="a11y-panel-title" className="font-headline-sm text-headline-sm text-on-surface">Accessibility</h3>
              <button
                onClick={close}
                aria-label="Close accessibility panel"
                className="p-1 hover:bg-surface-container-high rounded-lg"
              >
                <span className="material-symbols-outlined text-on-surface-variant" aria-hidden="true">close</span>
              </button>
            </div>

            <div className="p-4 space-y-5">
              <fieldset>
                <legend className="text-label-md font-bold text-on-surface mb-2">Font Size</legend>
                <div className="flex gap-2">
                  {fontOptions.map(([value, label]) => (
                    <button
                      key={value}
                      onClick={() => updatePref('fontSize', value)}
                      aria-pressed={prefs.fontSize === value}
                      className={`flex-1 py-2 px-3 rounded-lg text-label-md font-medium border transition-colors ${
                        prefs.fontSize === value
                          ? 'bg-primary text-on-primary border-primary'
                          : 'bg-surface-container border-outline-variant text-on-surface hover:bg-surface-container-high'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </fieldset>

              <fieldset>
                <legend className="text-label-md font-bold text-on-surface mb-2">Contrast</legend>
                <div className="flex gap-2">
                  {[['standard', 'Standard'], ['high', 'High']].map(([value, label]) => (
                    <button
                      key={value}
                      onClick={() => updatePref('contrast', value)}
                      aria-pressed={prefs.contrast === value}
                      className={`flex-1 py-2 px-3 rounded-lg text-label-md font-medium border transition-colors ${
                        prefs.contrast === value
                          ? 'bg-primary text-on-primary border-primary'
                          : 'bg-surface-container border-outline-variant text-on-surface hover:bg-surface-container-high'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </fieldset>

              <fieldset>
                <legend className="text-label-md font-bold text-on-surface mb-2">Focus Indicators</legend>
                <div className="flex gap-2">
                  {[['normal', 'Normal'], ['enhanced', 'Enhanced']].map(([value, label]) => (
                    <button
                      key={value}
                      onClick={() => updatePref('focusIndicators', value)}
                      aria-pressed={prefs.focusIndicators === value}
                      className={`flex-1 py-2 px-3 rounded-lg text-label-md font-medium border transition-colors ${
                        prefs.focusIndicators === value
                          ? 'bg-primary text-on-primary border-primary'
                          : 'bg-surface-container border-outline-variant text-on-surface hover:bg-surface-container-high'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </fieldset>

              <div className="flex items-center justify-between">
                <span id="reduce-motion-label" className="text-label-md font-bold text-on-surface">Reduce Motion</span>
                <button
                  role="switch"
                  aria-checked={prefs.reduceMotion}
                  aria-labelledby="reduce-motion-label"
                  onClick={() => updatePref('reduceMotion', !prefs.reduceMotion)}
                  className={`relative w-12 h-7 rounded-full transition-colors ${
                    prefs.reduceMotion ? 'bg-primary' : 'bg-surface-container-high'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-on-primary transition-transform ${
                      prefs.reduceMotion ? 'translate-x-5' : ''
                    }`}
                  />
                </button>
              </div>

              {mode === 'farmer' && (
                <fieldset>
                  <legend className="text-label-md font-bold text-on-surface mb-2">Language / Lugha</legend>
                  <div className="flex gap-2">
                    {[['en', 'English'], ['sw', 'Kiswahili']].map(([value, label]) => (
                      <button
                        key={value}
                        onClick={() => updatePref('language', value)}
                        aria-pressed={prefs.language === value}
                        className={`flex-1 py-2 px-3 rounded-lg text-label-md font-medium border transition-colors ${
                          prefs.language === value
                            ? 'bg-primary text-on-primary border-primary'
                            : 'bg-surface-container border-outline-variant text-on-surface hover:bg-surface-container-high'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </fieldset>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  )
}

import { useState, useEffect, useRef, createContext, useContext, useCallback } from 'react'
import { createPortal } from 'react-dom'

const STORAGE_KEY = 'zao_a11y_prefs'

const defaultPrefs = {
  fontSize: 'normal',
  contrast: 'standard',
  focusIndicators: 'normal',
  reduceMotion: false,
  darkMode: false,
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
  body.classList.toggle('dark-mode', prefs.darkMode)

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
    ? 'bottom-[88px] right-6'
    : 'bottom-[88px] right-6'

  const mobileTouchTarget = mode === 'farmer' ? 'min-h-[48px] min-w-[48px]' : ''

  const fontOptions = mode === 'farmer'
    ? [['normal', 'Normal'], ['large', 'Large']]
    : [['normal', 'Normal'], ['large', 'Large'], ['extra-large', 'Extra Large']]

  return (
    <>
      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Accessibility settings"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        className={`fixed ${widgetPosition} z-50 w-11 h-11 bg-surface border border-outline-variant text-[#8EA896] hover:bg-[#D8F3DC] hover:text-[#2D6A4F] rounded-full flex items-center justify-center transition-all duration-200 shadow-lg ${mobileTouchTarget}`}
        style={{ marginBottom: 'env(safe-area-inset-bottom, 0)' }}
      >
        <span className="material-symbols-outlined text-xl" aria-hidden="true">accessibility_new</span>
      </button>

      {isOpen && createPortal(
        <div
          className="fixed inset-0 z-[55]"
          onClick={close}
          role="presentation"
        >
          <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="a11y-panel-title"
            className="absolute bottom-6 right-4 sm:right-6 w-72 max-h-[70vh] overflow-y-auto bg-surface border border-outline-variant rounded-2xl shadow-2xl z-[56]"
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

              <div className="flex items-center justify-between">
                <span id="dark-mode-label" className="text-label-md font-bold text-on-surface">Dark Mode</span>
                <button
                  role="switch"
                  aria-checked={prefs.darkMode}
                  aria-labelledby="dark-mode-label"
                  onClick={() => updatePref('darkMode', !prefs.darkMode)}
                  className={`relative w-12 h-7 rounded-full transition-colors ${
                    prefs.darkMode ? 'bg-primary' : 'bg-surface-container-high'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-on-primary transition-transform ${
                      prefs.darkMode ? 'translate-x-5' : ''
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

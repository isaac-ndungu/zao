import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../../hooks/useApi'

function fmtDateTime(s) {
  if (!s) return '-'
  return new Date(s).toLocaleString()
}

export default function LegalHistoryDropdown() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const { data } = useApi('/api/admin/legal/recent-activity/')

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const pending = data?.pending_required_count ?? 0
  const recentAcceptances = data?.recent_acceptances ?? []
  const recentPublishes = data?.recent_publishes ?? []

  return (
    <div className="relative" ref={ref}>
      <button
        aria-label="Legal history"
        onClick={() => setOpen((o) => !o)}
        className="relative p-2 text-on-surface-variant hover:bg-surface-container-high rounded-full transition-colors hidden sm:block"
      >
        <span className="material-symbols-outlined">history_edu</span>
        {pending > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-error text-on-error text-[10px] font-bold flex items-center justify-center">
            {pending}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-[360px] max-h-[70vh] overflow-y-auto bg-surface-container-highest border border-outline-variant rounded-xl shadow-2xl z-50">
          <div className="px-4 py-3 border-b border-outline-variant">
            <p className="text-label-md font-bold text-on-surface">Legal history</p>
          </div>

          {recentPublishes.length > 0 && (
            <div className="px-4 py-3 border-b border-outline-variant">
              <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">Recent publishes</p>
              <ul className="space-y-2">
                {recentPublishes.map((d) => (
                  <li key={d.id} className="text-body-md">
                    <span className="font-mono text-body-sm text-on-surface-variant">{d.slug}</span>{' '}
                    <span className="text-on-surface">v{d.version}</span>{' '}
                    <span className="text-on-surface-variant">— {d.title}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recentAcceptances.length > 0 && (
            <div className="px-4 py-3">
              <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">Recent acceptances</p>
              <ul className="space-y-2">
                {recentAcceptances.map((a) => (
                  <li key={a.id} className="text-body-sm">
                    <span className="text-on-surface">{a.user_email}</span>{' '}
                    <span className="text-on-surface-variant">accepted</span>{' '}
                    <span className="font-mono text-body-sm">{a.document_slug}</span>{' '}
                    <span className="text-on-surface-variant">v{a.version}</span>
                    <div className="text-[11px] text-on-surface-variant">{fmtDateTime(a.accepted_at)}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="border-t border-outline-variant px-4 py-2 flex flex-col">
            <button
              onClick={() => { setOpen(false); navigate('/admin/legal') }}
              className="text-left text-primary text-body-md font-bold hover:underline py-1"
            >
              Manage legal documents →
            </button>
            <button
              onClick={() => { setOpen(false); navigate('/admin/legal/acceptances') }}
              className="text-left text-primary text-body-md font-bold hover:underline py-1"
            >
              View acceptance log →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

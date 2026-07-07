import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

function fmtDate(s) {
  if (!s) return '-'
  return new Date(s).toLocaleString()
}

export default function LegalAcceptances() {
  const { showToast } = useToast()
  const [slug, setSlug] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [query, setQuery] = useState({ slug: '', date_from: '', date_to: '' })

  const buildUrl = () => {
    const p = new URLSearchParams()
    if (query.slug) p.set('slug', query.slug)
    if (query.date_from) p.set('date_from', query.date_from)
    if (query.date_to) p.set('date_to', query.date_to)
    const qs = p.toString()
    return `/api/admin/legal/acceptances/${qs ? `?${qs}` : ''}`
  }
  const { data, loading, error, refetch } = useApi(buildUrl())

  const items = data?.results || []
  const count = data?.count ?? items.length

  const handleExport = () => {
    const p = new URLSearchParams()
    if (query.slug) p.set('slug', query.slug)
    if (query.date_from) p.set('date_from', query.date_from)
    if (query.date_to) p.set('date_to', query.date_to)
    p.set('format', 'csv')
    // Use the admin api client's baseURL; open in a new tab.
    // apiFetch normalizes to an absolute URL; we just need a stable href.
    const path = `/api/admin/legal/acceptances/?${p.toString()}`
    // For download, hit the path directly (browser handles the auth via cookies
    // for session auth; if the admin uses bearer tokens in localStorage, the
    // browser won't send them — this is fine for the current admin app which
    // uses cookie/session auth). Use the same origin.
    window.open(path, '_blank')
  }

  const apply = (e) => {
    e.preventDefault()
    setQuery({ slug, date_from: dateFrom, date_to: dateTo })
  }
  const clear = () => {
    setSlug(''); setDateFrom(''); setDateTo('')
    setQuery({ slug: '', date_from: '', date_to: '' })
  }

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Legal Acceptances</h2>
          <p className="text-sm text-on-surface-variant">Compliance log: who accepted which document version, when, and from where. Exportable for audits.</p>
        </div>
        <button
          onClick={handleExport}
          className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors flex items-center gap-2"
          aria-label="Export CSV"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">download</span>Export CSV
        </button>
      </header>

      <form onSubmit={apply} className="mb-4 flex flex-wrap gap-2 items-end">
        <div>
          <label htmlFor="slug" className="block text-label-md text-on-surface-variant mb-1">Document slug</label>
          <input
            id="slug"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="e.g. privacy-policy"
            className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          />
        </div>
        <div>
          <label htmlFor="dateFrom" className="block text-label-md text-on-surface-variant mb-1">From</label>
          <input
            id="dateFrom"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          />
        </div>
        <div>
          <label htmlFor="dateTo" className="block text-label-md text-on-surface-variant mb-1">To</label>
          <input
            id="dateTo"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          />
        </div>
        <button type="submit" className="px-3 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Apply</button>
        <button type="button" onClick={clear} className="px-3 py-2 text-on-surface-variant hover:text-on-surface text-label-md">Clear</button>
      </form>

      {loading ? (
        <div className="p-8 text-center text-on-surface-variant">Loading…</div>
      ) : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-surface-container-lowest border border-outline-variant rounded-xl">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant" aria-hidden="true">verified</span>
          <p className="text-on-surface-variant">No acceptances match the current filters.</p>
        </div>
      ) : (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-x-auto">
          <table className="w-full min-w-[800px]">
            <thead>
              <tr className="bg-surface-container border-b border-outline-variant">
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">User</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Document</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Version</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Accepted at</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">IP</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">User agent</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b border-outline-variant/50 hover:bg-surface-container">
                  <td className="px-4 py-2 text-body-md text-on-surface">{a.user_email}</td>
                  <td className="px-4 py-2 text-body-md text-on-surface">{a.document_slug} <span className="text-on-surface-variant text-body-sm">— {a.document_title}</span></td>
                  <td className="px-4 py-2 text-body-md text-on-surface font-mono">v{a.version}</td>
                  <td className="px-4 py-2 text-body-md text-on-surface">{fmtDate(a.accepted_at)}</td>
                  <td className="px-4 py-2 text-body-md text-on-surface-variant font-mono text-body-sm">{a.ip_address || '-'}</td>
                  <td className="px-4 py-2 text-body-md text-on-surface-variant text-body-sm truncate max-w-[260px]" title={a.user_agent}>{a.user_agent || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-2 text-label-md text-on-surface-variant border-t border-outline-variant">
            Showing {items.length} of {count}
          </div>
        </div>
      )}
    </div>
  )
}

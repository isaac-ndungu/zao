import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import DataTable from '../components/common/DataTable'
import StatusBadge from '../components/common/StatusBadge'
import { useToast } from '../contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

function fmtDate(s) {
  if (!s) return '-'
  return new Date(s).toLocaleDateString()
}

export default function LegalDocuments() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { data, loading, error, refetch } = useApi('/api/admin/legal/documents/')
  const docs = data?.results || []
  const [deletingId, setDeletingId] = useState(null)

  const handleDelete = async (id) => {
    if (!confirm('Delete this legal document version? This cannot be undone.')) return
    setDeletingId(id)
    try {
      const res = await apiFetch(`/api/admin/legal/documents/${id}/`, { method: 'DELETE' })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || 'Failed to delete.')
      }
      showToast({ type: 'success', message: 'Document deleted.' })
      refetch()
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    } finally {
      setDeletingId(null)
    }
  }

  const columns = [
    { key: 'slug', label: 'Slug', sortable: true, render: (r) => <code className="text-body-sm">{r.slug}</code> },
    { key: 'title', label: 'Title', sortable: true },
    {
      key: 'version', label: 'Version', sortable: true,
      render: (r) => <span className="font-mono text-body-sm">v{r.version}</span>,
    },
    {
      key: 'is_active', label: 'Status', sortable: true,
      render: (r) => <StatusBadge status={r.is_active ? 'success' : 'neutral'} label={r.is_active ? 'Active' : 'Draft'} />,
    },
    {
      key: 'requires_acceptance', label: 'Acceptance',
      render: (r) => r.requires_acceptance
        ? <StatusBadge status="warning" label="Required" />
        : <StatusBadge status="neutral" label="Not required" />,
    },
    { key: 'published_at', label: 'Published', sortable: true, render: (r) => fmtDate(r.published_at) },
    {
      key: 'actions', label: '', render: (r) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button
            onClick={() => navigate(`/admin/legal/documents/${r.id}`)}
            className="text-primary hover:text-primary/80"
            aria-label="Edit document"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">edit</span>
          </button>
          <button
            onClick={() => handleDelete(r.id)}
            disabled={deletingId === r.id}
            className="text-error hover:text-error/80 disabled:opacity-50"
            aria-label="Delete version"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span>
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Legal Documents</h2>
          <p className="text-sm text-on-surface-variant">Privacy policy, terms of service, and any document requiring user acceptance. Versioned; publishing creates a new version.</p>
        </div>
        <button
          onClick={() => navigate('/admin/legal/documents/new')}
          className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">add</span>New document
        </button>
      </header>

      {loading ? (
        <div className="p-8 text-center text-on-surface-variant">Loading…</div>
      ) : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : docs.length === 0 ? (
        <div className="text-center py-16 bg-surface-container-lowest border border-outline-variant rounded-xl">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant" aria-hidden="true">policy</span>
          <p className="text-on-surface-variant">No legal documents yet. The privacy policy and terms of service are seeded automatically on deploy.</p>
        </div>
      ) : (
        <>
          <DataTable
            columns={columns}
            data={docs}
            sortField="-published_at"
            sortOrder="desc"
            onSort={() => {}}
            emptyMessage="No documents."
          />
          <div className="mt-4">
            <button
              onClick={() => navigate('/admin/legal/acceptances')}
              className="text-primary text-body-md font-bold hover:underline"
            >
              View acceptance log →
            </button>
          </div>
        </>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

export default function LegalDocumentEdit() {
  const navigate = useNavigate()
  const { id } = useParams() // 'new' or a UUID
  const isNew = !id || id === 'new'
  const { showToast } = useToast()

  const { data: existing, loading } = useApi(isNew ? null : `/api/admin/legal/documents/${id}/`)
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState('')
  const [requiresAcceptance, setRequiresAcceptance] = useState(true)
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isNew && existing) {
      setTitle(existing.title || '')
      setSlug(existing.slug || '')
      setContent(existing.content || '')
      setRequiresAcceptance(!!existing.requires_acceptance)
    }
  }, [isNew, existing])

  const handleSave = async (e) => {
    e?.preventDefault?.()
    setError('')
    setSaving(true)
    try {
      const body = { title, slug, content, requires_acceptance: requiresAcceptance }
      const res = isNew
        ? await apiFetch('/api/admin/legal/documents/', { method: 'POST', body: JSON.stringify(body) })
        : await apiFetch(`/api/admin/legal/documents/${id}/`, { method: 'PATCH', body: JSON.stringify(body) })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(typeof d === 'string' ? d : JSON.stringify(d))
      }
      showToast({ type: 'success', message: 'Saved.' })
      navigate('/admin/legal')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    if (isNew) {
      showToast({ type: 'error', message: 'Save the document first, then publish a new version.' })
      return
    }
    if (!confirm('Publish a new version? This will create a v+1 row and mark it active.')) return
    setPublishing(true)
    try {
      const res = await apiFetch(`/api/admin/legal/documents/${id}/publish/`, { method: 'POST' })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(typeof d === 'string' ? d : JSON.stringify(d))
      }
      showToast({ type: 'success', message: 'New version published.' })
      navigate('/admin/legal')
    } catch (err) {
      setError(err.message)
    } finally {
      setPublishing(false)
    }
  }

  if (!isNew && loading) {
    return <div className="p-8 text-center text-on-surface-variant">Loading…</div>
  }
  if (!isNew && existing === null && !loading) {
    return <ErrorState message="Document not found." action={{ label: 'Back', onClick: () => navigate('/admin/legal') }} />
  }

  return (
    <div className="max-w-3xl mx-auto">
      <header className="mb-6">
        <button onClick={() => navigate('/admin/legal')} className="text-primary text-body-md hover:underline mb-2">← Back to Legal Documents</button>
        <h2 className="text-3xl font-bold text-on-surface">{isNew ? 'New legal document' : `Edit: ${existing?.title || slug}`}</h2>
        {!isNew && existing && (
          <p className="text-sm text-on-surface-variant mt-1">
            Editing v{existing.version}. Use <strong>Publish new version</strong> to make changes visible to users while preserving version history.
          </p>
        )}
      </header>

      <form onSubmit={handleSave} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 space-y-5">
        <div>
          <label className="block text-label-md text-on-surface-variant mb-1">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          />
        </div>
        <div>
          <label className="block text-label-md text-on-surface-variant mb-1">Slug</label>
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            required
            placeholder="e.g. privacy-policy, terms-of-service"
            className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container"
          />
        </div>
        <div>
          <label className="block text-label-md text-on-surface-variant mb-1">Content (Markdown)</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            required
            rows={16}
            className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container font-mono text-body-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id="req-acc"
            type="checkbox"
            checked={requiresAcceptance}
            onChange={(e) => setRequiresAcceptance(e.target.checked)}
            className="w-4 h-4 accent-primary"
          />
          <label htmlFor="req-acc" className="text-body-md text-on-surface">Requires user acceptance (gates the app until accepted)</label>
        </div>

        {error && (
          <div className="px-3 py-2 bg-error-container text-on-error-container rounded-lg text-body-md whitespace-pre-wrap">{error}</div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving…' : (isNew ? 'Create draft' : 'Save changes')}
          </button>
          {!isNew && (
            <button
              type="button"
              onClick={handlePublish}
              disabled={publishing}
              className="px-4 py-2 border border-primary text-primary rounded-lg text-label-md font-bold hover:bg-primary/5 transition-colors disabled:opacity-50"
            >
              {publishing ? 'Publishing…' : `Publish new version (v${(existing?.version || 0) + 1})`}
            </button>
          )}
          <button
            type="button"
            onClick={() => navigate('/admin/legal')}
            className="px-4 py-2 text-on-surface-variant hover:text-on-surface text-label-md"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../../admin/api/client'
import { useAuth } from '../hooks/useAuth'
import { emitLegalInvalidate } from '../utils/legalEvents'

export default function LegalAcceptanceGate({ children }) {
  const { loading: authLoading, isAuthenticated, logout } = useAuth()
  const [pendingDocs, setPendingDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState(null)
  const [error, setError] = useState('')

  const refetch = useCallback(async () => {
    if (!isAuthenticated) {
      setPendingDocs([])
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const res = await apiFetch('/api/legal/pending-acceptance/')
      if (res.ok) {
        const data = await res.json()
        setPendingDocs(data.pending_documents || [])
      }
    } catch {
      // If the endpoint fails, don't gate access
    } finally {
      setLoading(false)
    }
  }, [isAuthenticated])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refetch()
  }, [refetch])

  const handleAccept = async (slug) => {
    setAccepting(slug)
    setError('')
    try {
      const res = await apiFetch(`/api/legal/${slug}/accept/`, { method: 'POST' })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to accept.')
      }
      // Re-fetch from the server so the source of truth stays there; the
      // previous optimistic update could mask a stale-state failure.
      await refetch()
      emitLegalInvalidate()
    } catch (err) {
      setError(err.message)
    } finally {
      setAccepting(null)
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (pendingDocs.length > 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface px-4">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <h1 className="font-display-lg text-display-lg text-primary">Zao</h1>
            <p className="text-on-surface-variant text-body-md mt-1">Legal Documents</p>
          </div>

          <div className="bg-surface-container-lowest rounded-xl shadow-lg p-8 border border-outline-variant">
            <h2 className="font-headline-md text-headline-md text-on-surface mb-2">
              Please review and accept
            </h2>
            <p className="text-body-md text-on-surface-variant mb-6">
              You must accept the following documents before accessing the platform.
            </p>

            <div className="space-y-4">
              {pendingDocs.map((doc) => (
                <div key={doc.slug} className="border border-outline-variant rounded-lg p-4">
                  <h3 className="font-label-md font-bold text-on-surface mb-1">{doc.title}</h3>
                  {doc.summary && (
                    <p className="text-body-md text-on-surface-variant mb-3">{doc.summary}</p>
                  )}
                  <div className="flex gap-3">
                    <a
                      href={`/legal/${doc.slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary text-body-md hover:underline"
                    >
                      View document
                    </a>
                    <button
                      onClick={() => handleAccept(doc.slug)}
                      disabled={accepting === doc.slug}
                      className="ml-auto bg-primary text-on-primary font-body-md text-body-md py-1.5 px-4 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                      {accepting === doc.slug ? 'Accepting...' : 'Accept'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {error && (
              <div className="bg-error-container text-error text-body-md px-3 py-2 rounded-lg mt-4">{error}</div>
            )}

            <button
              onClick={logout}
              className="w-full text-center text-body-md text-error hover:underline mt-6"
            >
              Log out
            </button>
          </div>
        </div>
      </div>
    )
  }

  return children
}

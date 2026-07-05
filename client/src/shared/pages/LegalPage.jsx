import { useParams, Link } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useAuth } from '../hooks/useAuth'
import { markdownToHtml } from '../utils/markdown'
import { emitLegalInvalidate } from '../utils/legalEvents'
import ErrorState from '../components/ErrorState'

function fmtDate(s) {
  if (!s) return ''
  return new Date(s).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

export default function LegalPage() {
  const { slug } = useParams()
  const { isAuthenticated } = useAuth()
  const { data, loading, error, refetch } = useApi(`/api/legal/${slug}/`)

  // For authenticated users, also fetch their prior acceptance so we can
  // render the re-acceptance banner. Anon visitors (and 401s) render no banner.
  const { data: myAcceptance, refetch: refetchAcceptance } = useApi(
    isAuthenticated ? `/api/legal/${slug}/my-acceptance/` : null
  )

  const showReAcceptanceBanner = Boolean(
    myAcceptance
      && myAcceptance.accepted
      && myAcceptance.accepted_version != null
      && data
      && myAcceptance.accepted_version < data.version
  )

  const handleAcceptFromPage = async () => {
    if (!data) return
    try {
      const res = await apiFetch(`/api/legal/${slug}/accept/`, {
        method: 'POST',
        body: JSON.stringify({ version: data.version }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Failed to accept.')
      }
      refetchAcceptance()
      emitLegalInvalidate()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-surface-container border-b border-outline-variant">
        <div className="max-w-3xl mx-auto px-4 py-6 flex items-center justify-between">
          <Link to="/" className="text-on-surface-variant hover:text-on-surface text-body-md">← Home</Link>
          <Link to="/admin/legal" className="text-primary text-body-md font-bold hover:underline">Admin: Legal</Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10">
        {loading ? (
          <div className="p-8 text-center text-on-surface-variant">Loading…</div>
        ) : error ? (
          <ErrorState message={error === 'Not found.' ? 'This legal document is not available.' : error} action={{ label: 'Retry', onClick: refetch }} />
        ) : data ? (
          <article className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-8">
            <h1 className="text-3xl font-bold text-on-surface mb-2">{data.title}</h1>
            <p className="text-label-md text-on-surface-variant mb-6">
              Version {data.version} · Published {fmtDate(data.published_at)}
              {data.requires_acceptance && (
                <span className="ml-3 px-2 py-0.5 rounded-full bg-warning-container text-on-warning-container text-label-md font-bold">
                  Acceptance required
                </span>
              )}
            </p>

            {showReAcceptanceBanner && (
              <div className="mb-6 p-4 rounded-lg bg-warning-container text-on-warning-container border border-warning">
                <p className="font-bold text-label-lg mb-1">These terms have changed</p>
                <p className="text-body-md">
                  You accepted v{myAcceptance.accepted_version} on {fmtDate(myAcceptance.accepted_at)}.
                  The current version is v{data.version}. Please review the updated terms below
                  and accept the new terms to continue using the platform.
                </p>
                <button
                  onClick={handleAcceptFromPage}
                  className="mt-3 bg-primary text-on-primary font-bold text-label-md py-1.5 px-4 rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Accept new terms (v{data.version})
                </button>
              </div>
            )}

            <div
              className="prose prose-sm max-w-none text-on-surface [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mt-6 [&_h1]:mb-3 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:mt-5 [&_h2]:mb-2 [&_h3]:text-lg [&_h3]:font-bold [&_h3]:mt-4 [&_h3]:mb-2 [&_p]:mb-3 [&_p]:leading-relaxed [&_ul]:list-disc [&_ul]:ml-6 [&_ul]:mb-3 [&_strong]:font-bold [&_em]:italic"
              dangerouslySetInnerHTML={{ __html: markdownToHtml(data.content) }}
            />
          </article>
        ) : null}
      </main>
    </div>
  )
}

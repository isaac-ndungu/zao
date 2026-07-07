import { useState } from 'react'
import useFarmerApi from '../hooks/useFarmerApi'
import ErrorState from '../../shared/components/ErrorState'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import { ListSkeleton } from '../components/LoadingSkeleton'
import { t } from '../i18n'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

export default function FarmerGrades() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [disputeFor, setDisputeFor] = useState(null)
  const [disputeReason, setDisputeReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const { data, loading, error, refetch } = useFarmerApi(`/api/grades/?page=${page}&page_size=20&ordering=-created_at`)

  const grades = data?.results || data || []
  const total = data?.count || grades.length
  const pageSize = 20
  const totalPages = Math.ceil(total / pageSize)

  const acceptedGrades = grades.filter(g => g.grade_letter !== 'REJECTED')
  const rejectedCount = grades.length - acceptedGrades.length

  const handleDispute = async (gradeId) => {
    if (!disputeReason.trim()) return
    setSubmitting(true)
    try {
      const res = await apiFetch(`/api/grades/${gradeId}/dispute/`, {
        method: 'POST',
        body: JSON.stringify({ reason: disputeReason }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || t('disputeFailed')) }
      showToast({ type: 'success', message: t('disputeSubmitted') })
      setDisputeFor(null)
      setDisputeReason('')
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSubmitting(false) }
  }

  if (error) return <ErrorState message={error} action={{ label: t('retry'), onClick: refetch }} />
  if (loading) return <div><h2 className="text-lg font-bold mb-4">{t('grades')}</h2><ListSkeleton count={4} /></div>

  return (
    <div>
      <h2 className="text-lg font-bold mb-4">{t('grades')} {total > 0 && <span className="text-sm font-normal text-on-surface-variant">({total} {t('records')})</span>}</h2>

      {total > 0 && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-surface-container rounded-xl border border-outline-variant p-3 text-center">
            <p className="text-xs text-on-surface-variant">{t('acceptedGrades')}</p>
            <p className="text-lg font-bold text-success">{acceptedGrades.length}</p>
          </div>
          <div className="bg-surface-container rounded-xl border border-outline-variant p-3 text-center">
            <p className="text-xs text-on-surface-variant">{t('rejectedGrades')}</p>
            <p className="text-lg font-bold text-error">{rejectedCount}</p>
          </div>
        </div>
      )}

      {grades.length === 0 ? (
        <div className="text-center py-12">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-3" aria-hidden="true">grade</span>
          <p className="text-on-surface-variant">{t('noGrades')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {grades.map((g) => {
            const isRejected = g.grade_letter === 'REJECTED' || g.status === 'REJECTED'
            return (
              <div key={g.id} className="bg-surface-container rounded-xl border border-outline-variant p-4">
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-1 ${isRejected ? 'bg-error-container' : 'bg-success-container'}`}>
                    <span className={`material-symbols-outlined ${isRejected ? 'text-error' : 'text-success'}`} aria-hidden="true">
                      {isRejected ? 'close' : 'check_circle'}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-sm">{isRejected ? t('rejected') : `${t('gradeLetter')}: ${g.grade_letter}`}</p>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-on-surface-variant">
                      {g.price_per_unit && <span>{t('pricePerUnit')}: {formatKes(g.price_per_unit)}</span>}
                      <span className="ml-auto">{g.created_at ? new Date(g.created_at).toLocaleDateString() : '-'}</span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 mt-3">
                  {!isRejected && (
                    <button onClick={() => setDisputeFor(g)} className="bg-transparent border border-outline-variant px-4 py-2 rounded-xl text-xs font-semibold min-h-[36px] hover:bg-gray-50 flex-1 inline-flex items-center justify-center gap-1.5" title={t('disputeGrade')}>
                      <span className="material-symbols-outlined text-[16px]" aria-hidden="true">feedback</span> {t('disputeGrade')}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="bg-transparent border border-outline-variant px-4 py-2 rounded-xl text-xs font-semibold min-h-[36px] hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
            {t('previous')}
          </button>
          <span className="text-xs text-on-surface-variant">{t('of')} {page}/{totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="bg-transparent border border-outline-variant px-4 py-2 rounded-xl text-xs font-semibold min-h-[36px] hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
            {t('next')}
          </button>
        </div>
      )}

      {disputeFor && (
        <div className="fixed inset-0 bg-black/40 z-40 flex items-end" style={{ animation: 'fadeIn 0.2s' }} onClick={() => setDisputeFor(null)}>
          <div className="bg-surface-container rounded-t-2xl p-6 w-full max-h-[85vh] overflow-y-auto" style={{ animation: 'slideUp 0.3s ease-out' }} onClick={(e) => e.stopPropagation()}>
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto my-3" />
            <h3 className="font-bold text-lg mb-2">{t('disputeGrade')}</h3>
            <p className="text-sm text-on-surface-variant mb-4">
              {t('gradeLetter')}: {disputeFor.grade_letter} — {new Date(disputeFor.created_at).toLocaleDateString()}
            </p>
            <textarea
              value={disputeReason}
              onChange={(e) => setDisputeReason(e.target.value)}
              placeholder={t('reason')}
              rows={4}
              className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px] mb-4"
            />
            <div className="flex gap-3">
              <button onClick={() => handleDispute(disputeFor.id)} disabled={submitting || !disputeReason.trim()} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed flex-1">
                {submitting ? <span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full" aria-hidden="true" /> : t('submitDispute')}
              </button>
              <button onClick={() => setDisputeFor(null)} className="bg-transparent border border-outline-variant px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:bg-gray-50 flex-1">{t('cancel')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
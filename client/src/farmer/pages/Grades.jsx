import { useState } from 'react'
import useFarmerApi from '../hooks/useFarmerApi'
import ErrorState from '../../shared/components/ErrorState'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import { ListSkeleton } from '../components/LoadingSkeleton'
import { t } from '../i18n'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

const statusColors = {
  PENDING: 'bg-warning-container text-warning',
  RESOLVED: 'bg-success-container text-success',
  REJECTED: 'bg-error-container text-error',
}

export default function FarmerGrades() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [tab, setTab] = useState('grades')
  const [disputeFor, setDisputeFor] = useState(null)
  const [disputeReason, setDisputeReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const { data: gradesData, loading: gradesLoading, error: gradesError, refetch: refetchGrades } = useFarmerApi(`/api/grades/?page=${page}&page_size=20&ordering=-created_at`)
  const { data: disputesData, loading: disputesLoading, error: disputesError, refetch: refetchDisputes } = useFarmerApi('/api/disputes/?page=1&page_size=20&ordering=-created_at')

  const grades = gradesData?.results || gradesData || []
  const total = gradesData?.count || grades.length
  const pageSize = 20
  const totalPages = Math.ceil(total / pageSize)

  const disputes = disputesData?.results || disputesData || []
  const disputesTotal = disputesData?.count || disputes.length

  const acceptedGrades = grades.filter(g => g.grade_letter !== 'REJECTED')
  const rejectedCount = grades.length - acceptedGrades.length
  const pendingDisputes = disputes.filter(d => d.status === 'PENDING').length

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
      refetchGrades()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSubmitting(false) }
  }

  if (tab === 'grades') {
    if (gradesError) return <ErrorState message={gradesError} action={{ label: t('retry'), onClick: refetchGrades }} />
    if (gradesLoading) return <div><h2 className="text-lg font-bold mb-4">{t('grades')}</h2><ListSkeleton count={4} /></div>

    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">{t('grades')}</h2>
          <div className="flex gap-1 bg-surface-container rounded-lg p-1">
            <button
              onClick={() => setTab('grades')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors ${tab === 'grades' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container-high'}`}
            >
              {t('grades')}
            </button>
            <button
              onClick={() => setTab('disputes')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors flex items-center gap-1 ${tab === 'disputes' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container-high'}`}
            >
              {t('myDisputes')}
              {pendingDisputes > 0 && (
                <span className="bg-warning text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{pendingDisputes}</span>
              )}
            </button>
          </div>
        </div>

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
          <div className="fixed inset-0 bg-black/40 z-40 flex items-end cursor-pointer" style={{ animation: 'fadeIn 0.2s' }} onClick={() => setDisputeFor(null)}>
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

  if (tab === 'disputes') {
    if (disputesError) return <ErrorState message={disputesError} action={{ label: t('retry'), onClick: refetchDisputes }} />
    if (disputesLoading) return <div><h2 className="text-lg font-bold mb-4">{t('myDisputes')}</h2><ListSkeleton count={4} /></div>

    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">{t('myDisputes')}</h2>
          <div className="flex gap-1 bg-surface-container rounded-lg p-1">
            <button
              onClick={() => setTab('grades')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors ${tab === 'grades' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container-high'}`}
            >
              {t('grades')}
            </button>
            <button
              onClick={() => setTab('disputes')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors flex items-center gap-1 ${tab === 'disputes' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container-high'}`}
            >
              {t('myDisputes')}
              {pendingDisputes > 0 && (
                <span className="bg-warning text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{pendingDisputes}</span>
              )}
            </button>
          </div>
        </div>

        {disputes.length === 0 ? (
          <div className="text-center py-12">
            <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-3" aria-hidden="true">feedback</span>
            <p className="text-on-surface-variant">{t('noDisputes') || 'No disputes found.'}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {disputes.map((d) => (
              <div key={d.id} className="bg-surface-container rounded-xl border border-outline-variant p-4">
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-1 ${statusColors[d.status] || 'bg-surface-container'}`}>
                    <span className="material-symbols-outlined" aria-hidden="true">
                      {d.status === 'PENDING' ? 'hourglass_empty' : d.status === 'RESOLVED' ? 'check_circle' : 'cancel'}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-sm">{d.grade?.grade_letter || 'Grade'}</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${statusColors[d.status]}`}>
                        {d.status}
                      </span>
                    </div>
                    <p className="text-xs text-on-surface-variant mb-2 line-clamp-2">{d.reason || '-'}</p>
                    <div className="flex items-center gap-3 text-xs text-on-surface-variant">
                      <span>{d.created_at ? new Date(d.created_at).toLocaleDateString() : '-'}</span>
                      {d.resolved_at && <span>Resolved: {new Date(d.resolved_at).toLocaleDateString()}</span>}
                    </div>
                    {d.resolution_notes && (
                      <div className="mt-2 p-2 bg-surface rounded-lg">
                        <p className="text-xs text-on-surface-variant">{t('resolutionNotes') || 'Resolution'}: {d.resolution_notes}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return null
}
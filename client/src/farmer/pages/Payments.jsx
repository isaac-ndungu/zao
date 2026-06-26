import { useState } from 'react'
import useFarmerApi from '../hooks/useFarmerApi'
import ErrorState from '../../shared/components/ErrorState'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import { ListSkeleton } from '../components/LoadingSkeleton'
import { t } from '../i18n'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

const statusColors = { PENDING: 'bg-warning-container text-warning', PAID: 'bg-success-container text-success', FAILED: 'bg-error-container text-error', CANCELLED: 'bg-gray-200 text-gray-500' }

export default function FarmerPayments() {
  const { showToast } = useToast()
  const [downloadId, setDownloadId] = useState(null)
  const { data: profile, error: profileError, refetch: refetchProfile } = useFarmerApi('/api/farmers/me/')
  const { data, loading, error: dataError, refetch } = useFarmerApi(profile?.id ? `/api/statements/statement/history/?farmer_id=${profile.id}` : null)
  const apiError = profileError || dataError

  const payments = data?.payments || []
  const latestPayment = payments[0] || null

  const handleDownload = async (farmerPaymentId, e) => {
    e.stopPropagation()
    setDownloadId(farmerPaymentId)
    try {
      const res = await apiFetch(`/api/statements/statement/?farmer_payment_id=${farmerPaymentId}&download=true`)
      if (!res.ok) { showToast({ type: 'error', message: 'Statement not available.' }); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      URL.revokeObjectURL(url)
    } catch { showToast({ type: 'error', message: 'Failed to download.' }) }
    finally { setDownloadId(null) }
  }

  const handleLatest = async () => {
    setDownloadId('latest')
    try {
      const res = await apiFetch('/api/statements/statement/latest/?download=true')
      if (!res.ok) { showToast({ type: 'error', message: 'No statement available yet.' }); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      URL.revokeObjectURL(url)
    } catch { showToast({ type: 'error', message: 'Failed to download.' }) }
    finally { setDownloadId(null) }
  }

  if (apiError) return <ErrorState message={apiError} action={{ label: 'Retry', onClick: refetch || refetchProfile }} />
  if (loading) return <div><h2 className="text-lg font-bold mb-4">{t('payments')}</h2><ListSkeleton count={4} /></div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">{t('payments')} {payments.length > 0 && <span className="text-sm font-normal text-on-surface-variant">({payments.length})</span>}</h2>
        <button onClick={handleLatest} disabled={downloadId === 'latest'} className="bg-primary text-on-primary px-4 py-2 rounded-xl text-xs font-semibold min-h-[36px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed">
          {downloadId === 'latest' ? <span className="inline-block animate-spin h-4 w-4 border-2 border-outline-variant border-t-primary rounded-full" /> : t('latestStatement')}
        </button>
      </div>

      {latestPayment && (
        <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4 bg-primary-container/20 border-primary-container">
          <p className="text-xs text-on-surface-variant mb-1">{t('lastPayment')}</p>
          <div className="flex justify-between items-end">
            <div>
              <p className="text-xl font-bold text-primary">{formatKes(latestPayment.net_amount)}</p>
              <p className="text-xs text-on-surface-variant">{latestPayment.cycle_name} — {latestPayment.status}</p>
            </div>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${statusColors[latestPayment.status] || 'bg-gray-200 text-gray-500'}`}>{latestPayment.status}</span>
          </div>
        </div>
      )}

      {payments.length === 0 ? (
        <div className="text-center py-12">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-3">payments</span>
          <p className="text-on-surface-variant">{t('noPayments')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {payments.map((p, i) => (
            <div key={p.farmer_payment_id || i} className="bg-surface-container rounded-xl border border-outline-variant p-4">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="font-semibold text-sm">{p.cycle_name || `Payment #${i + 1}`}</p>
                  <p className="text-xs text-on-surface-variant">{p.period_start && p.period_end ? `${new Date(p.period_start).toLocaleDateString()} - ${new Date(p.period_end).toLocaleDateString()}` : '-'}</p>
                </div>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${statusColors[p.status] || 'bg-gray-200 text-gray-500'}`}>{p.status}</span>
              </div>
              <div className="flex justify-between items-center text-sm mb-3">
                <div>
                  <p className="text-xs text-on-surface-variant">{t('grossAmount')}</p>
                  <p className="font-medium">{formatKes(p.gross_amount)}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-on-surface-variant">{t('deductions')}</p>
                  <p className="font-medium text-error">-{formatKes(p.gross_amount - p.net_amount)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-on-surface-variant">{t('netAmount')}</p>
                  <p className="font-bold text-primary">{formatKes(p.net_amount)}</p>
                </div>
              </div>
              <button
                onClick={(e) => handleDownload(p.farmer_payment_id, e)}
                disabled={downloadId === p.farmer_payment_id}
                className="bg-primary text-on-primary px-4 py-2 rounded-xl text-xs font-semibold min-h-[36px] w-full hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {downloadId === p.farmer_payment_id ? <span className="inline-block animate-spin h-4 w-4 border-2 border-outline-variant border-t-primary rounded-full" /> : t('seeStatement')}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

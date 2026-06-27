import { useState } from 'react'
import useFarmerApi from '../hooks/useFarmerApi'
import ErrorState from '../../shared/components/ErrorState'
import { ListSkeleton } from '../components/LoadingSkeleton'
import { t } from '../i18n'

const statusColors = {
  PENDING: 'bg-warning-container text-warning',
  GRADED: 'bg-success-container text-success',
  ACCEPTED: 'bg-success-container text-success',
  REJECTED: 'bg-error-container text-error',
  PAID: 'bg-primary-container text-primary',
}

const productIcons = {
  MILK: 'local_drink',
  COFFEE_CHERRIES: 'coffee',
  HONEY: 'faucet',
  MACADAMIA: 'nutrition',
  AVOCADO: 'nutrition',
}

export default function FarmerDeliveries() {
  const [selected, setSelected] = useState(null)
  const [page, setPage] = useState(1)
  const { data, loading, error, refetch } = useFarmerApi(`/api/deliveries/?page=${page}&page_size=20&ordering=-date_delivered`)

  const deliveries = data?.results || data || []
  const total = data?.count || deliveries.length
  const pageSize = 20
  const totalPages = Math.ceil(total / pageSize)

  // Group by month for a seasonal view (optional, not shown, but can be added)
  // We'll add a "this month" counter at top
  const thisMonth = new Date().getMonth()
  const thisYear = new Date().getFullYear()
  const thisMonthDeliveries = deliveries.filter(d => {
    const date = new Date(d.date_delivered)
    return date.getMonth() === thisMonth && date.getFullYear() === thisYear
  })

  if (error) return <ErrorState message={error} action={{ label: t('retry'), onClick: refetch }} />
  if (loading) return <div><h2 className="text-lg font-bold mb-4">{t('deliveries')}</h2><ListSkeleton count={4} /></div>

  return (
    <div>
      <h2 className="text-lg font-bold mb-4">{t('deliveries')} {total > 0 && <span className="text-sm font-normal text-on-surface-variant">({total} {t('records')})</span>}</h2>

      {thisMonthDeliveries.length > 0 && (
        <div className="bg-primary-container/20 border border-primary-container rounded-xl p-3 mb-4">
          <p className="text-xs font-semibold text-primary">{t('thisMonth')}</p>
          <p className="text-sm">{thisMonthDeliveries.length} {t('deliveries')}</p>
        </div>
      )}

      {deliveries.length === 0 ? (
        <div className="text-center py-12">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-3">receipt_long</span>
          <p className="text-on-surface-variant">{t('noDeliveries')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {deliveries.map((d) => (
            <button key={d.id} onClick={() => setSelected(d)} className="bg-surface-container rounded-xl border border-outline-variant p-4 w-full text-left hover:bg-primary-container/10 transition-colors">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-container flex items-center justify-center shrink-0 mt-1">
                  <span className="material-symbols-outlined text-primary text-xl">
                    {productIcons[d.product_type] || 'inventory'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-semibold text-sm text-on-surface truncate capitalize">
                      {d.product_type?.replace(/_/g, ' ')}
                    </p>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${statusColors[d.status] || 'bg-gray-200 text-gray-500'}`}>
                      {d.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-on-surface-variant">
                    <span>{d.quantity_kg || d.volume_litres ? `${d.quantity_kg || d.volume_litres} ${d.quantity_kg ? 'kg' : 'L'}` : '-'}</span>
                    {d.batch_id && <span>{t('batch')}: {d.batch_id}</span>}
                    <span className="ml-auto">{d.date_delivered ? new Date(d.date_delivered).toLocaleDateString() : '-'}</span>
                  </div>
                  {d.grade && <p className="text-xs text-primary mt-1">{t('gradeLetter')}: {d.grade}</p>}
                </div>
                <span className="material-symbols-outlined text-on-surface-variant text-xl mt-2">chevron_right</span>
              </div>
            </button>
          ))}
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

      {/* Detail modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 z-40 flex items-end" style={{ animation: 'fadeIn 0.2s' }} onClick={() => setSelected(null)}>
          <div className="bg-surface-container rounded-t-2xl p-6 w-full max-h-[85vh] overflow-y-auto" style={{ animation: 'slideUp 0.3s ease-out' }} onClick={(e) => e.stopPropagation()}>
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto my-3" />
            <h3 className="font-bold text-lg mb-4">{t('deliveryDetails')}</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div><p className="text-xs text-on-surface-variant">{t('productType')}</p><p className="text-sm font-medium capitalize">{selected.product_type?.replace(/_/g, ' ')}</p></div>
                <div><p className="text-xs text-on-surface-variant">{t('status')}</p>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${statusColors[selected.status] || 'bg-gray-200 text-gray-500'}`}>
                    {selected.status}
                  </span>
                </div>
                <div><p className="text-xs text-on-surface-variant">{t('quantity')}</p><p className="text-sm font-medium">{selected.quantity_kg || selected.volume_litres || '-'} {selected.quantity_kg ? 'kg' : 'L'}</p></div>
                <div><p className="text-xs text-on-surface-variant">{t('shift')}</p><p className="text-sm font-medium">{selected.shift ? t(selected.shift.toLowerCase()) : '-'}</p></div>
                <div><p className="text-xs text-on-surface-variant">{t('date')}</p><p className="text-sm font-medium">{selected.date_delivered ? new Date(selected.date_delivered).toLocaleDateString() : '-'}</p></div>
                {selected.batch_id && <div><p className="text-xs text-on-surface-variant">{t('batch')}</p><p className="text-sm font-medium">{selected.batch_id}</p></div>}
              </div>
              {selected.grade && (
                <div className="border-t border-outline-variant pt-3 mt-3">
                  <p className="text-xs text-on-surface-variant mb-2">{t('gradeLetter')}</p>
                  <p className="text-sm font-bold text-primary">{selected.grade}</p>
                  {selected.quality_metrics && Object.keys(selected.quality_metrics).length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-on-surface-variant mb-1">{t('qualityMetrics')}</p>
                      {Object.entries(selected.quality_metrics).map(([k, v]) => (
                        <p key={k} className="text-xs text-on-surface-variant">{k}: {v}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {selected.rejection_reason && (
                <div className="bg-error-container rounded-xl p-4 mt-3">
                  <p className="text-xs font-bold text-error mb-1">{t('rejectionReason')}</p>
                  <p className="text-sm text-error">{selected.rejection_reason}</p>
                </div>
              )}
            </div>
            <button onClick={() => setSelected(null)} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 w-full mt-6">
              {t('close')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
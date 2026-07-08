import { useState } from 'react'
import useFarmerApi from '../hooks/useFarmerApi'
import { ListSkeleton } from '../components/LoadingSkeleton'
import { t } from '../i18n'

export default function FarmerNotifications() {
  const [page, setPage] = useState(1)
  const { data, loading, error, refetch } = useFarmerApi(`/api/notifications/?page=${page}&page_size=20&ordering=-created_at`)

  // Detect if the error is a 403
  const isForbidden = typeof error === 'string' && error.includes('403')   // adjust based on actual error format
  // or better: check status if your useFarmerApi exposes it; we'll assume error message contains "403"

  const notifications = data?.results || data || []
  const total = data?.count || notifications.length
  const pageSize = 20
  const totalPages = Math.ceil(total / pageSize)

  const timeSince = (dateStr) => {
    if (!dateStr) return ''
    const now = new Date()
    const then = new Date(dateStr)
    const diff = Math.floor((now - then) / 1000)
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return then.toLocaleDateString()
  }

  if (error) {
    // Check if it's a 403
    if (String(error).includes('403') || String(error).includes('permission')) {
      return (
        <div className="text-center py-12">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-3" aria-hidden="true">notifications_off</span>
          <p className="text-on-surface-variant">{t('notificationsUnavailable')}</p>
        </div>
      )
    }
    return <ErrorState message={error} action={{ label: t('retry'), onClick: refetch }} />
  }

  if (loading) return <div><h2 className="text-lg font-bold mb-4">{t('notifications')}</h2><ListSkeleton count={4} /></div>

  return (
    <div>
      <h2 className="text-lg font-bold mb-4">{t('notifications')} {total > 0 && <span className="text-sm font-normal text-on-surface-variant">({total})</span>}</h2>

      {notifications.length === 0 ? (
        <div className="text-center py-12">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-3" aria-hidden="true">notifications</span>
          <p className="text-on-surface-variant">{t('noNotifications')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <div key={n.id} className="bg-surface-container rounded-xl border border-outline-variant p-4">
              <p className="text-sm text-on-surface font-medium">{n.content || n.message || n.title || 'New notification'}</p>
              <p className="text-xs text-on-surface-variant mt-1">{timeSince(n.created_at)}</p>
            </div>
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
    </div>
  )
}
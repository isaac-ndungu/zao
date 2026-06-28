import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { KpiSkeleton } from '../../admin/components/common/Skeleton'
import ErrorState from '../../shared/components/ErrorState'

function timeSince(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export default function GraderDashboard() {
  const navigate = useNavigate()
  const { data: pendingData, loading, error, refetch } = useApi(`/api/deliveries/?status=PENDING&page_size=50&ordering=-date_delivered`)
  const { data: summary } = useApi(`/api/deliveries/summary/?date_from=${todayStr()}&date_to=${todayStr()}`)
  const { data: gradedToday } = useApi(`/api/grades/?created_at__date=${todayStr()}&page_size=1`)

  const pendingDeliveries = pendingData?.results || []
  const pendingCount = pendingData?.count || 0
  const gradedTodayCount = gradedToday?.count || 0

  if (loading) {
    return (
      <div>
        <header className="mb-8">
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Grader Dashboard</h2>
          <p className="text-on-surface-variant font-body-md">Pending deliveries queue</p>
        </header>
        <KpiSkeleton count={3} />
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <header className="mb-8">
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Grader Dashboard</h2>
          <p className="text-on-surface-variant font-body-md">Pending deliveries queue</p>
        </header>
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      </div>
    )
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Grader Dashboard</h2>
        <p className="text-on-surface-variant font-body-md">Pending deliveries queue</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <button onClick={() => navigate('/grader/grade')} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 flex items-center gap-4 cursor-pointer hover:shadow-md transition-shadow text-left w-full">
          <div className="w-12 h-12 rounded-full bg-primary-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-primary">pending</span>
          </div>
          <div>
            <p className="text-headline-lg font-bold text-on-surface">{pendingCount}</p>
            <p className="text-label-md text-on-surface-variant">Pending</p>
          </div>
        </button>
        <button onClick={() => navigate('/grader/grade')} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 flex items-center gap-4 cursor-pointer hover:shadow-md transition-shadow text-left w-full">
          <div className="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-secondary">grading</span>
          </div>
          <div>
            <p className="text-headline-lg font-bold text-on-surface">{gradedTodayCount}</p>
            <p className="text-label-md text-on-surface-variant">Graded Today</p>
          </div>
        </button>
        <button onClick={() => navigate('/grader/grade')} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 flex items-center gap-4 cursor-pointer hover:shadow-md transition-shadow text-left w-full">
          <div className="w-12 h-12 rounded-full bg-tertiary-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-tertiary">local_shipping</span>
          </div>
          <div>
            <p className="text-headline-lg font-bold text-on-surface">{summary?.total || 0}</p>
            <p className="text-label-md text-on-surface-variant">Total Today</p>
          </div>
        </button>
      </div>

      {pendingDeliveries.length === 0 ? (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
          <span className="material-symbols-outlined text-[48px] text-on-surface-variant">check_circle</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface mt-4">All caught up!</h3>
          <p className="text-body-md text-on-surface-variant mt-2">No pending deliveries to grade.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pendingDeliveries.map((delivery) => (
            <div
              key={delivery.id}
              className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-headline-sm text-title-md text-on-surface font-bold">{delivery.batch_id}</p>
                  <p className="text-label-md text-on-surface-variant">{delivery.farmer_name}</p>
                </div>
                <span className="text-label-sm text-on-surface-variant bg-surface-container-high px-2 py-1 rounded">
                  {timeSince(delivery.date_delivered)}
                </span>
              </div>

              <div className="flex items-center gap-4 mb-4">
                <div>
                  <p className="text-label-md text-on-surface-variant">Product</p>
                  <p className="text-body-md text-on-surface font-medium">{delivery.product_type || '-'}</p>
                </div>
                <div>
                  <p className="text-label-md text-on-surface-variant">Quantity</p>
                  <p className="text-body-md text-on-surface font-medium">
                    {delivery.quantity_kg ? `${delivery.quantity_kg} kg` : delivery.volume_litres ? `${delivery.volume_litres} L` : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-label-md text-on-surface-variant">Shift</p>
                  <p className="text-body-md text-on-surface font-medium">{delivery.shift || '-'}</p>
                </div>
              </div>

              <button
                onClick={() => navigate(`/grader/grade?delivery=${delivery.id}`)}
                className="w-full bg-primary text-on-primary py-2.5 rounded-lg font-bold text-label-md hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">grading</span>
                Grade Now
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

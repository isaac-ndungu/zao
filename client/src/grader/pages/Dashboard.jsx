import { useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { KpiSkeleton } from '../../admin/components/common/Skeleton'
import ErrorState from '../../shared/components/ErrorState'
import GraderOfflineBanner from '../components/GraderOfflineBanner'
import ProgressTracker from '../components/ProgressTracker'
import SevenDayChart from '../components/SevenDayChart'
import { cachePendingDeliveries } from '../services/offlineQueue'
import { useUrgencyThresholds, getUrgencyLevel } from '../hooks/useUrgencyThresholds'

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

function sevenDaysAgo() {
  const d = new Date()
  d.setDate(d.getDate() - 6)
  return d.toISOString().slice(0, 10)
}

const URGENCY_STYLES = {
  critical: {
    border: 'border-l-4 border-error',
    badge: 'bg-error/10 text-error',
  },
  warning: {
    border: 'border-l-4 border-warning',
    badge: 'bg-warning/10 text-warning',
  },
  fresh: {
    border: '',
    badge: 'bg-surface-container-high text-on-surface-variant',
  },
}

function DeliveryCard({ delivery, thresholds, onGrade }) {
  const urgency = getUrgencyLevel(delivery.date_delivered, thresholds)
  const styles = URGENCY_STYLES[urgency]

  return (
    <div
      className={`bg-surface-container-lowest rounded-xl p-4 hover:shadow-md transition-shadow ${styles.border}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="font-headline-sm text-title-md text-on-surface font-bold">{delivery.batch_id}</p>
          <p className="text-label-md text-on-surface-variant">{delivery.farmer_name}</p>
        </div>
        <span className={`text-label-sm px-2 py-1 rounded ${styles.badge}`}>
          {timeSince(delivery.date_delivered)}
        </span>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div>
          <p className="text-label-sm text-on-surface-variant">Product</p>
          <p className="text-body-sm text-on-surface font-medium">{delivery.product_type || '-'}</p>
        </div>
        <div>
          <p className="text-label-sm text-on-surface-variant">Quantity</p>
          <p className="text-body-sm text-on-surface font-medium">
            {delivery.quantity_kg
              ? `${delivery.quantity_kg} kg`
              : delivery.volume_litres
              ? `${delivery.volume_litres} L`
              : '-'}
          </p>
        </div>
        <div>
          <p className="text-label-sm text-on-surface-variant">Shift</p>
          <p className="text-body-sm text-on-surface font-medium">{delivery.shift || '-'}</p>
        </div>
      </div>

      <button
        onClick={() => onGrade(delivery.id)}
        className="w-full bg-primary text-on-primary py-2.5 rounded-lg font-bold text-label-md hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
      >
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">grading</span>
        Grade Now
      </button>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-10 text-center">
      <div className="w-16 h-16 rounded-full bg-primary-container/30 flex items-center justify-center mx-auto mb-4">
        <span className="material-symbols-outlined text-[32px] text-primary" aria-hidden="true">check_circle</span>
      </div>
      <h3 className="font-headline-sm text-on-surface mb-1">All caught up!</h3>
      <p className="text-body-sm text-on-surface-variant">No pending deliveries to grade right now.</p>
    </div>
  )
}

export default function GraderDashboard() {
  const navigate = useNavigate()
  const thresholds = useUrgencyThresholds()

  const { data: pendingData, loading, error, refetch } = useApi(
    `/api/deliveries/?status=PENDING&page_size=50&ordering=-date_delivered`
  )
  const { data: summary } = useApi(
    `/api/deliveries/summary/?date_from=${todayStr()}&date_to=${todayStr()}`
  )
  const { data: gradedToday } = useApi(
    `/api/grades/?created_at__date=${todayStr()}&page_size=1`
  )
  const { data: weekGrades } = useApi(
    `/api/grades/?created_at__date_from=${sevenDaysAgo()}&created_at__date_to=${todayStr()}&page_size=100`
  )

  useEffect(() => {
    if (pendingData?.results) {
      cachePendingDeliveries(pendingData.results)
    }
  }, [pendingData])

  const pendingDeliveries = pendingData?.results || []
  const pendingCount = pendingData?.count || 0
  const gradedTodayCount = gradedToday?.count || 0
  const totalToday = summary?.total || 0

  const weekResults = useMemo(
    () => weekGrades?.results || [],
    [weekGrades]
  )

  const handleGrade = (deliveryId) => {
    navigate(`/grader/grade?delivery=${deliveryId}`)
  }

  if (loading) {
    return (
      <div>
        <GraderOfflineBanner />
        <header className="mb-6">
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
        <GraderOfflineBanner />
        <header className="mb-6">
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Grader Dashboard</h2>
          <p className="text-on-surface-variant font-body-md">Pending deliveries queue</p>
        </header>
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      </div>
    )
  }

  const totalTodayDeliveries = gradedTodayCount + pendingCount

  return (
    <div>
      <GraderOfflineBanner />

      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Grader Dashboard</h2>
        <p className="text-on-surface-variant font-body-md">
          {pendingCount > 0
            ? `${pendingCount} pending delivery${pendingCount !== 1 ? 'ies' : ''} in queue`
            : 'Queue is clear'}
        </p>
      </header>

      <ProgressTracker graded={gradedTodayCount} total={totalTodayDeliveries} />

      <div className="grid grid-cols-3 gap-3 mb-6">
        <button
          onClick={() => navigate('/grader/grade')}
          className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 cursor-pointer hover:shadow-sm transition-shadow text-center"
        >
          <p className="text-headline-lg font-bold text-on-surface">{pendingCount}</p>
          <p className="text-label-sm text-on-surface-variant mt-0.5">Pending</p>
        </button>
        <button
          onClick={() => navigate('/grader/grade')}
          className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 cursor-pointer hover:shadow-sm transition-shadow text-center"
        >
          <p className="text-headline-lg font-bold text-primary">{gradedTodayCount}</p>
          <p className="text-label-sm text-on-surface-variant mt-0.5">Graded Today</p>
        </button>
        <button
          onClick={() => navigate('/grader/grade')}
          className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 cursor-pointer hover:shadow-sm transition-shadow text-center"
        >
          <p className="text-headline-lg font-bold text-on-surface">{totalToday}</p>
          <p className="text-label-sm text-on-surface-variant mt-0.5">Total Today</p>
        </button>
      </div>

      {weekResults.length > 0 && (
        <div className="mb-6">
          <SevenDayChart results={weekResults} />
        </div>
      )}

      {pendingDeliveries.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {pendingDeliveries.map((delivery) => (
            <DeliveryCard
              key={delivery.id}
              delivery={delivery}
              thresholds={thresholds}
              onGrade={handleGrade}
            />
          ))}
        </div>
      )}
    </div>
  )
}

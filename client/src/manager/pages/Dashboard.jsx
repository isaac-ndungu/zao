import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import KpiCard from '../../admin/components/common/KpiCard'
import { KpiSkeleton } from '../../admin/components/common/Skeleton'
import StatusBadge from '../../admin/components/common/StatusBadge'
import ErrorState from '../../shared/components/ErrorState'

function formatNumber(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n || 0)
}

export default function ManagerDashboard() {
  const navigate = useNavigate()
  const { data: analytics, loading: analyticsLoading, error: analyticsError, refetch: refetchAnalytics } = useApi('/api/analytics/dashboard/')
  const { data: deliveriesSummary } = useApi('/api/deliveries/summary/')
  const { data: farmersStats } = useApi('/api/farmers/stats/')
  const { data: coop } = useApi('/api/cooperatives/me/')
  const { data: recentDeliveries } = useApi('/api/deliveries/?page=1&page_size=5&ordering=-date_delivered')
  const { data: recentGrades } = useApi('/api/grades/?page=1&page_size=5&ordering=-created_at')
  const { data: recentCycles } = useApi('/api/payment-engine/?page=1&page_size=5&ordering=-created_at')
  const { data: pendingDisputes } = useApi('/api/disputes/?status=PENDING')
  const { data: pendingDisbursements } = useApi('/api/disbursements/?status=PENDING&page_size=1')

  const ad = analytics?.data || analytics
  const pendingGradings = deliveriesSummary?.pending_grading || 0
  const totalFarmers = farmersStats?.total || 0
  const activeFarmers = farmersStats?.active || 0
  const pendingDisputesCount = pendingDisputes?.count || pendingDisputes?.results?.length || 0
  const pendingDisbursementCount = pendingDisbursements?.count || pendingDisbursements?.results?.length || 0
  const todayDeliveries = deliveriesSummary?.by_status
    ? Object.values(deliveriesSummary.by_status).reduce((a, b) => a + b, 0)
    : 0

  const recentActivities = useMemo(() => {
    const items = []
    if (recentDeliveries?.results) {
      recentDeliveries.results.slice(0, 5).forEach((d) => {
        items.push({
          id: `del-${d.id}`,
          type: 'delivery',
          date: d.date_delivered,
          text: `${d.farmer_name || 'Farmer'} — ${d.quantity_kg || d.volume_litres}kg`,
          status: d.status,
        })
      })
    }
    if (recentGrades?.results) {
      recentGrades.results.slice(0, 5).forEach((g) => {
        items.push({
          id: `grade-${g.id}`,
          type: 'grade',
          date: g.created_at,
          text: `Grade ${g.grade_letter} — ${g.delivery?.batch_id || ''}`,
          status: g.grade_letter,
        })
      })
    }
    if (recentCycles?.results) {
      const cycle = recentCycles.results[0]
      if (cycle)
        items.push({
          id: `cycle-${cycle.id}`,
          type: 'cycle',
          date: cycle.updated_at,
          text: `Cycle: ${cycle.name}`,
          status: cycle.status,
        })
    }
    return items.sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 10)
  }, [recentDeliveries, recentGrades, recentCycles])

  if (analyticsLoading) {
    return (
      <div>
        <header className="mb-8">
          <h2 className="text-3xl font-bold text-on-surface mb-2">Dashboard</h2>
          {coop?.name && <p className="text-on-surface-variant">{coop.name}</p>}
        </header>
        <KpiSkeleton count={6} />
      </div>
    )
  }

  if (analyticsError)
    return <ErrorState message={analyticsError} action={{ label: 'Retry', onClick: refetchAnalytics }} />

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-8">
        <h2 className="text-3xl font-bold text-on-surface mb-1">
          {coop ? `Welcome, ${coop.name}` : 'Dashboard'}
        </h2>
        <p className="text-on-surface-variant text-sm">Cooperative management overview</p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <KpiCard icon="agriculture" label="Total Farmers" value={formatNumber(totalFarmers)} onClick={() => navigate('/manager/farmers')} />
        <KpiCard icon="person" label="Active Farmers" value={formatNumber(activeFarmers)} trend={activeFarmers > 0 ? 100 : 0} onClick={() => navigate('/manager/farmers')} />
        <KpiCard icon="grading" label="Pending Gradings" value={String(pendingGradings)} highlighted={pendingGradings > 0} onClick={() => navigate('/manager/grading')} />
        <KpiCard icon="local_shipping" label="Today's Deliveries" value={String(todayDeliveries)} onClick={() => navigate('/manager/deliveries')} />
        <KpiCard icon="warning" label="Pending Disputes" value={String(pendingDisputesCount)} highlighted={pendingDisputesCount > 0} onClick={() => navigate('/manager/grading')} />
        <KpiCard icon="account_balance" label="Pending Approvals" value={String(pendingDisbursementCount)} highlighted={pendingDisbursementCount > 0} onClick={() => navigate('/manager/disbursements')} />
      </div>

      {ad && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KpiCard icon="payments" label="Revenue" value={ad.financial?.total_revenue ? `KES ${formatNumber(ad.financial.total_revenue)}` : '-'} onClick={() => navigate('/manager/reports')} />
          <KpiCard icon="inventory_2" label="Production" value={ad.production?.total_kg ? `${formatNumber(ad.production.total_kg)} kg` : '-'} onClick={() => navigate('/manager/inventory')} />
          <KpiCard icon="account_balance" label="Gross Payout" value={ad.financial?.total_gross_payout ? `KES ${formatNumber(ad.financial.total_gross_payout)}` : '-'} onClick={() => navigate('/manager/cycles')} />
          <KpiCard icon="trending_up" label="Loan Portfolio" value={ad.loans?.total_outstanding ? `KES ${formatNumber(ad.loans.total_outstanding)}` : '-'} onClick={() => navigate('/manager/loans')} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-surface-container rounded-2xl border border-outline-variant/40 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-on-surface mb-4">Recent Activity</h3>
          {recentActivities.length === 0 ? (
            <p className="text-on-surface-variant text-sm">No recent activity.</p>
          ) : (
            <div className="space-y-3">
              {recentActivities.map((item) => (
                <div key={item.id} className="flex items-center gap-4 py-2 border-b border-outline-variant/20 last:border-0">
                  <span
                    className={`material-symbols-outlined text-xl ${
                      item.type === 'delivery' ? 'text-primary' : item.type === 'grade' ? 'text-secondary' : 'text-tertiary'
                    }`}
                  >
                    {item.type === 'delivery' ? 'local_shipping' : item.type === 'grade' ? 'grading' : 'payments'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-on-surface truncate">{item.text}</p>
                    <p className="text-xs text-on-surface-variant">
                      {item.date ? new Date(item.date).toLocaleDateString() : ''}
                    </p>
                  </div>
                  <StatusBadge status={item.status?.toLowerCase()} label={item.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-surface-container rounded-2xl border border-outline-variant/40 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-on-surface mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button
              onClick={() => navigate('/manager/farmers')}
              className="w-full flex items-center gap-3 px-4 py-3 bg-surface-container hover:bg-surface-container-high rounded-lg transition-colors text-left"
            >
              <span className="material-symbols-outlined text-primary">person_add</span>
              <span className="text-sm font-medium text-on-surface">Register Farmer</span>
            </button>
            <button
              onClick={() => navigate('/manager/deliveries')}
              className="w-full flex items-center gap-3 px-4 py-3 bg-surface-container hover:bg-surface-container-high rounded-lg transition-colors text-left"
            >
              <span className="material-symbols-outlined text-primary">add_circle</span>
              <span className="text-sm font-medium text-on-surface">Record Delivery</span>
            </button>
            <button
              onClick={() => navigate('/manager/loans')}
              className="w-full flex items-center gap-3 px-4 py-3 bg-surface-container hover:bg-surface-container-high rounded-lg transition-colors text-left"
            >
              <span className="material-symbols-outlined text-primary">account_balance_wallet</span>
              <span className="text-sm font-medium text-on-surface">Review Loans</span>
            </button>
            <button
              onClick={() => navigate('/manager/disbursements')}
              className="w-full flex items-center gap-3 px-4 py-3 bg-surface-container hover:bg-surface-container-high rounded-lg transition-colors text-left"
            >
              <span className="material-symbols-outlined text-primary">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Approve Disbursements</span>
              {pendingDisbursementCount > 0 && (
                <span className="ml-auto bg-error text-on-error text-[10px] font-bold px-2 py-0.5 rounded-full">
                  {pendingDisbursementCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
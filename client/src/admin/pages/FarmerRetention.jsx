import { useContext } from 'react'
import { useApi } from '../hooks/useApi'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import BarChartCard from '../components/charts/BarChartCard'
import LineChartCard from '../components/charts/LineChartCard'

const trendConfig = {
  STABLE: { icon: 'check_circle', color: 'text-primary', bg: 'bg-primary-container', label: 'Stable' },
  DECLINING: { icon: 'warning', color: 'text-orange-600', bg: 'bg-orange-100', label: 'Declining' },
  CRITICAL: { icon: 'error', color: 'text-error', bg: 'bg-error-container', label: 'Critical' },
}

export default function FarmerRetention() {
  const { period } = useContext(AdminFilterContext)
  const { data, loading, error } = useApi(`/api/admin/analytics/farmer-retention/?period=${period}`)

  const monthly = data?.data?.monthly || []
  const trend = data?.data?.trend
  const avgChurn = data?.data?.avg_monthly_churn_pct
  const netGrowth = data?.data?.net_growth

  if (loading) {
    return <div className="space-y-6"><div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-48 animate-pulse" /><div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-64 animate-pulse" /></div>
  }

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load retention data: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Farmer Retention</h2>
        <p className="text-on-surface-variant font-body-md">Track farmer churn, growth trends, and retention metrics.</p>
      </header>

      {trend && (
        <div className="mb-6">
          <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl ${trendConfig[trend]?.bg || 'bg-surface-container'}`}>
            <span className={`material-symbols-outlined ${trendConfig[trend]?.color || 'text-on-surface-variant'}`} aria-hidden="true">{trendConfig[trend]?.icon || 'help'}</span>
            <span className={`font-bold text-label-md ${trendConfig[trend]?.color || 'text-on-surface-variant'}`}>
              {trendConfig[trend]?.label || trend} — {trend === 'STABLE' ? 'Churn rate under 1%. Healthy cohort.' : trend === 'DECLINING' ? 'Churn rate between 1-3% requires attention.' : 'Churn rate above 3% requires immediate action.'}
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <KpiCard icon="trending_up" label="Net Growth" value={netGrowth !== undefined ? (netGrowth >= 0 ? `+${netGrowth}` : netGrowth) : '-'} highlighted={netGrowth > 0} />
        <KpiCard icon="percent" label="Avg Monthly Churn" value={avgChurn !== undefined ? `${avgChurn.toFixed(2)}%` : '-'} highlighted={avgChurn > 3} />
      </div>

      {monthly.length > 0 ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <BarChartCard
              title="New vs Deactivated Farmers"
              data={monthly.map(m => ({ month: m.month, new: m.new, deactivated: m.deactivated }))}
              categoryKey="month"
              dataKeys={['new', 'deactivated']}
              stacked
              height={300}
              emptyMessage="No retention data available."
            />
            <LineChartCard
              title="Monthly Churn Rate"
              data={monthly}
              xKey="month"
              lines={[
                { key: 'churn_pct', name: 'Churn %', color: '#dc2626' },
              ]}
              referenceLines={[
                { y: 1, label: '1%', color: '#d97706' },
                { y: 3, label: '3%', color: '#dc2626' },
              ]}
              yFormatter={(v) => `${v.toFixed(1)}%`}
              height={300}
              emptyMessage="No churn data available."
            />
          </div>
        </>
      ) : (
        <div className="text-center py-12 text-on-surface-variant bg-surface-container-lowest border border-outline-variant rounded-xl">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant" aria-hidden="true">group_off</span>
          <p>No retention data available for the selected period.</p>
        </div>
      )}
    </div>
  )
}

import { useContext, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import { CardSkeleton } from '../components/common/Skeleton'

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

  const maxCount = useMemo(() => Math.max(...monthly.map(m => m.start_count + m.new), 1), [monthly])

  if (loading) {
    return <div className="space-y-6"><CardSkeleton /><CardSkeleton /></div>
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
            <span className={`material-symbols-outlined ${trendConfig[trend]?.color || 'text-on-surface-variant'}`}>{trendConfig[trend]?.icon || 'help'}</span>
            <span className={`font-bold text-label-md ${trendConfig[trend]?.color || 'text-on-surface-variant'}`}>
              {trendConfig[trend]?.label || trend} — {trend === 'STABLE' ? 'Churn rate under 1%. Healthy cohort.' : trend === 'DECLINING' ? 'Churn rate between 1-3% requires attention.' : 'Churn rate above 3% requires immediate action.'}
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <KpiCard icon="trending_up" label="Net Growth" value={netGrowth !== undefined ? (netGrowth >= 0 ? `+${netGrowth}` : netGrowth) : '-'} highlighted={netGrowth > 0} />
        <KpiCard icon="percent" label="Avg Monthly Churn" value={avgChurn !== undefined ? `${avgChurn.toFixed(2)}%` : '-'} highlighted={avgChurn > 3} />
      </div>

      {monthly.length > 0 && (
        <>
          <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mb-6">
            <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">New vs Deactivated Farmers</h4>
            <div className="space-y-2">
              {monthly.map((m) => {
                const newPct = (m.new / maxCount) * 100
                const deactPct = (m.deactivated / maxCount) * 100
                return (
                  <div key={m.month}>
                    <div className="flex justify-between text-label-md font-medium mb-1">
                      <span className="text-on-surface-variant">{m.month}</span>
                      <span className="font-data-mono text-on-surface-variant">
                        <span className="text-primary">{m.new} new</span> · <span className="text-error">{m.deactivated} deactivated</span> · {m.end_count} total
                      </span>
                    </div>
                    <div className="h-6 w-full bg-surface-container rounded-lg overflow-hidden flex">
                      <div className="h-full bg-primary transition-all" style={{ width: `${newPct}%` }} title={`${m.new} new`} />
                      <div className="h-full bg-error transition-all" style={{ width: `${deactPct}%` }} title={`${m.deactivated} deactivated`} />
                    </div>
                  </div>
                )
              })}
            </div>
            <div className="flex gap-4 mt-3 pt-3 border-t border-outline-variant/50">
              <span className="flex items-center gap-1.5 text-label-md text-on-surface-variant"><span className="w-3 h-3 rounded-sm bg-primary" /> New</span>
              <span className="flex items-center gap-1.5 text-label-md text-on-surface-variant"><span className="w-3 h-3 rounded-sm bg-error" /> Deactivated</span>
            </div>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
            <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Monthly Churn Rate</h4>
            <div className="space-y-2">
              {monthly.map((m) => {
                const maxChurn = Math.max(...monthly.map(x => x.churn_pct), 0.1)
                const pct = (m.churn_pct / maxChurn) * 100
                return (
                  <div key={m.month} className="flex items-center gap-4">
                    <span className="text-label-md font-medium text-on-surface-variant w-16">{m.month}</span>
                    <div className="flex-1 h-5 bg-surface-container rounded-lg overflow-hidden">
                      <div
                        className={`h-full rounded-lg transition-all ${m.churn_pct > 3 ? 'bg-error' : m.churn_pct > 1 ? 'bg-orange-400' : 'bg-primary'}`}
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                    </div>
                    <span className="font-data-mono text-label-md text-on-surface-variant w-16 text-right">{m.churn_pct?.toFixed(2)}%</span>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}

      {monthly.length === 0 && (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">group_off</span>
          <p>No retention data available for the selected period.</p>
        </div>
      )}
    </div>
  )
}

import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import ErrorState from '../../shared/components/ErrorState'
import KpiCard from '../../admin/components/common/KpiCard'
import { KpiSkeleton } from '../../admin/components/common/Skeleton'
import LineChartCard from '../../admin/components/charts/LineChartCard'
import PieChartCard from '../../admin/components/charts/PieChartCard'

function formatKes(n) {
  if (!n || n === 0) return 'KES 0'
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(1)}K`
  return `KES ${Number(n).toLocaleString()}`
}

export default function AuditorFinancial() {
  const navigate = useNavigate()
  const { data: finData, loading, error, refetch } = useApi('/api/analytics/financial/')

  const fin = finData?.data || finData || {}
  const financial = fin

  const cyclesByStatus = financial.cycles_by_status || {}
  const activeCycles = Object.entries(cyclesByStatus)
    .filter(([k]) => k !== 'COMPLETED' && k !== 'CANCELLED')
    .reduce((s, [, v]) => s + v, 0)

  const deductionsBreakdown = financial.deductions_breakdown || {}
  const payoutTrend = financial.payout_trend || []
  const trendData = Array.isArray(payoutTrend)
    ? payoutTrend.map((p, i) => ({ month: p.month || p.label || `M${i + 1}`, payout: p.amount || p.value || 0 }))
    : []

  const pieData = Object.entries(deductionsBreakdown).map(([name, value]) => ({ name, value }))

  if (loading) {
    return (
      <div>
        <header className="mb-8"><h2 className="font-headline-lg text-display-md text-primary mb-1">Financial Overview</h2><p className="text-on-surface-variant font-body-md">Revenue, payouts & deductions</p></header>
        <KpiSkeleton count={6} />
      </div>
    )
  }

  if (error) {
    return <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
  }

  return (
    <div>
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Financial Overview</h2>
        <p className="text-on-surface-variant font-body-md">Revenue, payouts & deductions</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <KpiCard icon="payments" label="Total Revenue" value={formatKes(financial.total_revenue)} />
        <KpiCard icon="account_balance" label="Gross Payout" value={formatKes(financial.total_gross_payout)} />
        <KpiCard icon="money_off" label="Deductions" value={formatKes(financial.total_deductions)} />
        <KpiCard icon="receipt_long" label="WHT Held" value={formatKes(financial.total_withholding_tax)} />
        <KpiCard icon="payments" label="Active Cycles" value={String(activeCycles)} highlighted={activeCycles > 0} onClick={() => navigate('/auditor/reports')} />
        <KpiCard icon="account_balance" label="Avg Payout/Farmer" value={formatKes(financial.avg_payout_per_farmer)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {trendData.length > 0 && (
          <LineChartCard
            title="Gross Payout Trend"
            subtitle="Monthly gross payout over the period"
            data={trendData}
            lines={[{ dataKey: 'payout', name: 'Payout', color: '#4f46e5' }]}
            xKey="month"
            currency
          />
        )}
        {pieData.length > 0 && (
          <PieChartCard
            title="Deductions Breakdown"
            subtitle="By deduction type"
            data={pieData}
            dataKey="value"
            nameKey="name"
          />
        )}
      </div>
    </div>
  )
}

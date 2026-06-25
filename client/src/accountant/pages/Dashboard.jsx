import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
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

function formatNumber(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n || 0)
}

export default function AccountantDashboard() {
  const navigate = useNavigate()
  const { data: finData, loading: finLoading } = useApi('/api/analytics/financial/')
  const { data: dashData, loading: dashLoading } = useApi('/api/analytics/dashboard/')

  const loading = finLoading || dashLoading
  const fin = finData?.data || finData || {}
  const dash = dashData?.data || dashData || {}
  const financial = dash.financial || fin
  const production = dash.production || {}
  const loans = dash.loans || {}
  const disbursements = dash.disbursements || {}

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
        <header className="mb-8"><h2 className="font-headline-lg text-display-md text-primary mb-1">Financial Dashboard</h2><p className="text-on-surface-variant font-body-md">Period overview</p></header>
        <KpiSkeleton count={6} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6"><KpiSkeleton count={2} /></div>
      </div>
    )
  }

  return (
    <div>
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Financial Dashboard</h2>
        <p className="text-on-surface-variant font-body-md">
          {finData?.period ? `${finData.period.start} – ${finData.period.end}` : 'Period overview'}
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <KpiCard icon="payments" label="Total Revenue" value={formatKes(financial.total_revenue)} onClick={() => navigate('/accountant/reports')} />
        <KpiCard icon="account_balance" label="Gross Payout" value={formatKes(financial.total_gross_payout)} onClick={() => navigate('/accountant/cycles')} />
        <KpiCard icon="money_off" label="Deductions" value={formatKes(financial.total_deductions)} onClick={() => navigate('/accountant/deductions')} />
        <KpiCard icon="receipt_long" label="WHT Held" value={formatKes(financial.total_withholding_tax)} />
        <KpiCard icon="payments" label="Active Cycles" value={String(activeCycles)} highlighted={activeCycles > 0} onClick={() => navigate('/accountant/cycles')} />
        <KpiCard icon="local_shipping" label="Production" value={production.total_kg ? `${formatNumber(production.total_kg)} kg` : '-'} onClick={() => navigate('/accountant/reports')} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon="account_balance_wallet" label="Loan Portfolio" value={formatKes(loans.total_outstanding)} onClick={() => navigate('/accountant/loans')} />
        <KpiCard icon="trending_up" label="Repayment Rate" value={loans.repayment_rate_pct ? `${loans.repayment_rate_pct}%` : '-'} />
        <KpiCard icon="check_circle" label="Disbursed (period)" value={fin.total_disbursed_this_period ? formatKes(fin.total_disbursed_this_period) : formatKes(loans.total_disbursed_this_period)} />
        <KpiCard icon="account_balance" label="Disbursement Success" value={disbursements.success_rate_pct ? `${disbursements.success_rate_pct}%` : '-'} />
      </div>
    </div>
  )
}

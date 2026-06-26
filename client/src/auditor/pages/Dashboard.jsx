import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import ErrorState from '../../shared/components/ErrorState'
import KpiCard from '../../admin/components/common/KpiCard'
import { KpiSkeleton } from '../../admin/components/common/Skeleton'

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

export default function AuditorDashboard() {
  const navigate = useNavigate()
  const { data: dashData, loading, error, refetch } = useApi('/api/analytics/dashboard/')

  const dash = dashData?.data || dashData || {}
  const financial = dash.financial || {}
  const production = dash.production || {}
  const loans = dash.loans || {}

  if (loading) {
    return (
      <div>
        <header className="mb-8"><h2 className="font-headline-lg text-display-md text-primary mb-1">Auditor Dashboard</h2><p className="text-on-surface-variant font-body-md">Cooperative overview</p></header>
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
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Auditor Dashboard</h2>
        <p className="text-on-surface-variant font-body-md">Read-only cooperative overview</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <KpiCard icon="payments" label="Total Revenue" value={formatKes(financial.total_revenue)} onClick={() => navigate('/auditor/financial')} />
        <KpiCard icon="account_balance" label="Gross Payout" value={formatKes(financial.total_gross_payout)} onClick={() => navigate('/auditor/financial')} />
        <KpiCard icon="money_off" label="Deductions" value={formatKes(financial.total_deductions)} onClick={() => navigate('/auditor/financial')} />
        <KpiCard icon="receipt_long" label="WHT Held" value={formatKes(financial.total_withholding_tax)} />
        <KpiCard icon="local_shipping" label="Production" value={production.total_kg ? `${formatNumber(production.total_kg)} kg` : '-'} onClick={() => navigate('/auditor/production')} />
        <KpiCard icon="account_balance_wallet" label="Loan Portfolio" value={formatKes(loans.total_outstanding)} onClick={() => navigate('/auditor/loans')} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon="security" label="Audit Logs" value={dash.audit_log_count || '-'} onClick={() => navigate('/auditor/audit-log')} />
        <KpiCard icon="trending_up" label="Repayment Rate" value={loans.repayment_rate_pct ? `${loans.repayment_rate_pct}%` : '-'} />
        <KpiCard icon="description" label="Reports" value="View PDFs" onClick={() => navigate('/auditor/reports')} />
        <KpiCard icon="people" label="Active Farmers" value={formatNumber(production.active_farmers || dash.farmer_count || 0)} />
      </div>
    </div>
  )
}

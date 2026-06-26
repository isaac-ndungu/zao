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

export default function ExternalLoanPortfolio() {
  const { data: loanData, loading, error, refetch } = useApi('/api/analytics/loans/')

  const loans = loanData?.data || loanData || {}

  if (loading) {
    return (
      <div>
        <header className="mb-8"><h2 className="font-headline-lg text-display-md text-primary mb-1">Loan Portfolio</h2><p className="text-on-surface-variant font-body-md">Aggregate loan statistics</p></header>
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
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Loan Portfolio</h2>
        <p className="text-on-surface-variant font-body-md">Aggregate loan statistics (anonymous)</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard icon="account_balance_wallet" label="Total Portfolio" value={formatKes(loans.total_disbursed)} />
        <KpiCard icon="trending_up" label="Outstanding" value={formatKes(loans.total_outstanding)} />
        <KpiCard icon="check_circle" label="Repayment Rate" value={loans.repayment_rate_pct ? `${loans.repayment_rate_pct}%` : '-'} />
        <KpiCard icon="warning" label="Default Rate" value={loans.default_rate_pct ? `${loans.default_rate_pct}%` : '-'} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon="payments" label="Disbursed (period)" value={formatKes(loans.total_disbursed_this_period)} />
        <KpiCard icon="receipt" label="Total Repaid" value={formatKes(loans.total_repaid)} />
        <KpiCard icon="people" label="Active Borrowers" value={String(loans.active_borrowers || '-')} />
        <KpiCard icon="pending" label="Pending" value={String(loans.pending_count || '-')} />
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mt-6">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">Notes</h3>
        <ul className="text-body-md text-on-surface-variant space-y-2 list-disc list-inside">
          <li>All figures are aggregate and anonymous — no individual farmer data is displayed.</li>
          <li>Loan portfolio data is sourced from the analytics endpoint only.</li>
          <li>For detailed loan-level audit, contact the internal audit department.</li>
        </ul>
      </div>
    </div>
  )
}

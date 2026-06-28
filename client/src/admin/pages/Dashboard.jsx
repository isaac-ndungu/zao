import { useContext, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import { KpiSkeleton } from '../components/common/Skeleton'
import BarChartCard from '../components/charts/BarChartCard'
import PieChartCard from '../components/charts/PieChartCard'
import { CATEGORICAL_COLORS } from '../components/charts/chartTheme'

const roleColors = {
  farmer: 'bg-primary',
  manager: 'bg-secondary',
  accountant: 'bg-tertiary-fixed-dim',
  grader: 'bg-tertiary',
  admin: 'bg-outline',
  unknown: 'bg-outline-variant',
}

const roleLabels = {
  farmer: 'Farmers',
  manager: 'Managers',
  accountant: 'Accountants',
  grader: 'Graders',
  admin: 'Admins',
  unknown: 'Other',
}

const statusLabels = {
  PENDING: 'Pending',
  GRADED: 'Graded',
  ACCEPTED: 'Accepted',
  REJECTED: 'Rejected',
  PAID: 'Paid',
}

const pipelineStages = [
  { key: 'DRAFT', label: 'Draft', color: 'bg-surface-container-highest', textColor: 'text-on-surface-variant', valueColor: 'text-primary' },
  { key: 'COMPUTING', label: 'Computing', color: 'bg-primary-fixed', textColor: 'text-on-primary-fixed-variant', valueColor: 'text-primary' },
  { key: 'COMPUTED', label: 'Computed', color: 'bg-primary-container', textColor: 'text-on-primary-container', valueColor: 'text-white' },
  { key: 'LOCKED', label: 'Locked', color: 'bg-secondary', textColor: 'text-on-secondary', valueColor: 'text-white' },
  { key: 'DISBURSED', label: 'Disbursed', color: 'bg-tertiary', textColor: 'text-on-tertiary', valueColor: 'text-white' },
]

const cycleStatusColors = {
  DRAFT: CATEGORICAL_COLORS[5],
  COMPUTING: CATEGORICAL_COLORS[0],
  COMPUTED: CATEGORICAL_COLORS[1],
  LOCKED: CATEGORICAL_COLORS[2],
  DISBURSED: CATEGORICAL_COLORS[3],
}

function formatNumber(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { period } = useContext(AdminFilterContext)
  const { data, loading, error } = useApi(`/api/admin/dashboard/?period=${period}`)
  const { data: analytics, loading: analyticsLoading } = useApi(`/api/admin/analytics/dashboard/?period=${period}`)

  const totalUsers = data?.total_users ?? '—'
  const totalFarmers = data?.total_farmers ?? '—'
  const pendingDeliveries = data?.deliveries_by_status?.PENDING ?? '—'
  const totalDeliveries = data?.total_deliveries ?? '—'

  const totalDeleted = useMemo(() => {
    if (!data?.trash) return 0
    return Object.values(data.trash).reduce((s, v) => s + v, 0)
  }, [data?.trash])

  const usersByRole = useMemo(() => {
    const roles = data?.users_by_role
    if (!roles) return []
    return Object.entries(roles).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a)
  }, [data?.users_by_role])

  const deliveriesByStatus = useMemo(() => {
    const statuses = data?.deliveries_by_status
    if (!statuses) return []
    return Object.entries(statuses).filter(([, v]) => v > 0)
  }, [data?.deliveries_by_status])

  const cyclePipeline = useMemo(() => {
    const pipe = data?.cycles_by_status
    if (!pipe) return pipelineStages.map(s => ({ ...s, value: 0, percent: 0 }))
    const total = Object.values(pipe).reduce((s, v) => s + v, 0) || 1
    return pipelineStages.map((stage) => {
      const value = pipe[stage.key] || 0
      return { ...stage, value, percent: (value / total) * 100 }
    })
  }, [data?.cycles_by_status])

  const analyticsData = analytics?.data
  const gradeDist = useMemo(() => {
    if (!analyticsData?.production?.grade_distribution) return []
    return Object.entries(analyticsData.production.grade_distribution)
      .filter(([, v]) => v > 0)
      .sort(([, a], [, b]) => b - a)
  }, [analyticsData])

  if (loading) {
    return (
      <div>
        <header className="my-10">
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Executive Overview</h2>
          <p className="text-on-surface-variant font-body-md">Real-time cooperative performance & operational health metrics.</p>
        </header>
        <KpiSkeleton count={5} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-48 animate-pulse" />
          <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-48 animate-pulse" />
        </div>
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-48 animate-pulse" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-error-container text-error p-4 rounded-xl">
        Failed to load dashboard data: {error}
      </div>
    )
  }

  if (!data) return null

  return (
    <div>
      <header className="mb-8 mt-4">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Executive Overview</h2>
        <p className="text-on-surface-variant font-body-md">
          Real-time cooperative performance & operational health metrics.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
        <KpiCard icon="group" label="Total Users" value={formatNumber(totalUsers)} onClick={() => navigate('/admin/users')} />
        <KpiCard icon="agriculture" label="Total Farmers" value={formatNumber(totalFarmers)} onClick={() => navigate('/admin/users')} />
        <KpiCard icon="grading" label="Pending Deliveries" value={formatNumber(pendingDeliveries)} onClick={() => navigate('/admin/receipts')} />
        <KpiCard icon="inventory" label="Total Deliveries" value={formatNumber(totalDeliveries)} onClick={() => navigate('/admin/receipts')} />
        <KpiCard icon="delete" label="Soft Deleted" value={formatNumber(totalDeleted)} highlighted onClick={() => navigate('/admin/trash')} />
      </div>

      {analyticsData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <KpiCard icon="payments" label="Revenue" value={analyticsData.financial?.total_revenue ? `KES ${formatNumber(analyticsData.financial.total_revenue)}` : '—'} onClick={() => navigate('/admin/financials')} />
          <KpiCard icon="person" label="Active Farmers" value={analyticsData.farmers?.total_active ?? '—'} trend={analyticsData.farmers?.new_this_period ?? 0} onClick={() => navigate('/admin/farmer-payments')} />
          <KpiCard icon="inventory_2" label="Total Production" value={analyticsData.production?.total_kg ? `${formatNumber(analyticsData.production.total_kg)} kg` : '—'} onClick={() => navigate('/admin/inventory')} />
          <KpiCard icon="account_balance" label="Gross Payout" value={analyticsData.financial?.total_gross_payout ? `KES ${formatNumber(analyticsData.financial.total_gross_payout)}` : '—'} onClick={() => navigate('/admin/financials')} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <BarChartCard
          title="Users by Role"
          data={usersByRole.map(([name, value]) => ({ name: roleLabels[name] || name, value }))}
          categoryKey="name"
          dataKey="value"
          orientation="horizontal"
          height={220}
          emptyMessage="No user data available."
          colorMap={Object.fromEntries(
            Object.entries(roleColors).map(([k, v]) => [
              roleLabels[k] || k,
              v === 'bg-outline-variant' ? '#9ca3af'
                : v === 'bg-primary' ? CATEGORICAL_COLORS[0]
                : v === 'bg-secondary' ? CATEGORICAL_COLORS[2]
                : v === 'bg-tertiary-fixed-dim' ? CATEGORICAL_COLORS[3]
                : v === 'bg-tertiary' ? CATEGORICAL_COLORS[4]
                : CATEGORICAL_COLORS[5]
            ])
          )}
        />

        <PieChartCard
          title="Deliveries by Status"
          data={deliveriesByStatus.map(([name, value]) => ({ name: statusLabels[name] || name, value }))}
          dataKey="value"
          categoryKey="name"
          height={280}
          emptyMessage="No delivery data available."
          colorMap={Object.fromEntries(
            Object.entries(statusLabels).map(([k, v]) => [
              v,
              k === 'PENDING' ? CATEGORICAL_COLORS[0]
                : k === 'GRADED' ? CATEGORICAL_COLORS[1]
                : k === 'ACCEPTED' ? CATEGORICAL_COLORS[2]
                : k === 'REJECTED' ? '#dc2626'
                : CATEGORICAL_COLORS[5]
            ])
          )}
        />
      </div>

      {gradeDist.length > 0 && (
        <BarChartCard
          title="Grade Distribution"
          data={gradeDist.map(([name, value]) => ({ name: name.toLowerCase(), value }))}
          categoryKey="name"
          dataKey="value"
          orientation="horizontal"
          height={220}
          emptyMessage="No grade data available."
        />
      )}

      <BarChartCard
        title="Cycle Pipeline"
        subtitle="Flow of payment cycles through stages."
        data={cyclePipeline.map(s => ({ name: s.label, value: s.value }))}
        categoryKey="name"
        dataKey="value"
        orientation="horizontal"
        height={220}
        emptyMessage="No cycle data available."
      />
    </div>
  )
}

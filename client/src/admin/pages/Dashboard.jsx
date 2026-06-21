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

const statusColors = {
  pending: 'bg-tertiary-fixed-dim',
  in_progress: 'bg-primary',
  completed: 'bg-secondary',
  cancelled: 'bg-error',
}

const statusLabels = {
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

const pipelineStages = [
  { key: 'pending', label: 'Draft', color: 'bg-surface-container-highest', textColor: 'text-on-surface-variant', valueColor: 'text-primary' },
  { key: 'in_progress', label: 'Computing', color: 'bg-primary-fixed', textColor: 'text-on-primary-fixed-variant', valueColor: 'text-primary' },
  { key: 'completed', label: 'Completed', color: 'bg-primary-container', textColor: 'text-on-primary-container', valueColor: 'text-white' },
  { key: 'rejected', label: 'Rejected', color: 'bg-primary', textColor: 'text-on-primary', valueColor: 'text-white' },
]

const pipelineDetail = {
  pending: 'Awaiting system processing',
  in_progress: 'Analysis in progress',
  completed: 'Processed and finalized',
  rejected: 'Flagged or returned',
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
    const pipe = data?.cycle_pipeline
    if (!pipe) return pipelineStages.map(s => ({ ...s, value: 0, percent: 0 }))
    const total = Object.values(pipe).reduce((s, v) => s + v, 0) || 1
    return pipelineStages.map((stage) => {
      const value = pipe[stage.key] || 0
      return { ...stage, value, percent: (value / total) * 100 }
    })
  }, [data?.cycle_pipeline])

  const analyticsData = analytics?.data
  const gradeDist = useMemo(() => {
    if (!analyticsData?.production?.grade_distribution) return []
    return Object.entries(analyticsData.production.grade_distribution).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a)
  }, [analyticsData])

  if (loading) {
    return (
      <div>
        <header className="mb-8">
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
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Executive Overview</h2>
        <p className="text-on-surface-variant font-body-md">
          Real-time cooperative performance & operational health metrics.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
        <KpiCard icon="group" label="Total Users" value={formatNumber(data.total_users)} onClick={() => navigate('/admin/users')} />
        <KpiCard icon="agriculture" label="Active Users" value={formatNumber(data.active_users)} onClick={() => navigate('/admin/users')} />
        <KpiCard icon="grading" label="Pending Gradings" value={String(data.pending_gradings)} onClick={() => navigate('/admin/receipts')} />
        <KpiCard icon="inventory" label="Active Deliveries" value={String(data.active_deliveries)} onClick={() => navigate('/admin/receipts')} />
        <KpiCard icon="delete" label="Soft Deleted" value={formatNumber(data.trash_summary?.total_deleted || 0)} highlighted onClick={() => navigate('/admin/trash')} />
      </div>

      {/* Analytics KPIs */}
      {analyticsData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <KpiCard icon="payments" label="Revenue" value={analyticsData.financial?.total_revenue ? `KES ${formatNumber(analyticsData.financial.total_revenue)}` : '-'} onClick={() => navigate('/admin/financials')} />
          <KpiCard icon="person" label="Active Farmers" value={analyticsData.farmers?.total_active || 0} trend={analyticsData.farmers?.new_this_period || 0} onClick={() => navigate('/admin/farmer-payments')} />
          <KpiCard icon="inventory_2" label="Total Production" value={analyticsData.production?.total_kg ? `${formatNumber(analyticsData.production.total_kg)} kg` : '-'} onClick={() => navigate('/admin/inventory')} />
          <KpiCard icon="account_balance" label="Gross Payout" value={analyticsData.financial?.total_gross_payout ? `KES ${formatNumber(analyticsData.financial.total_gross_payout)}` : '-'} onClick={() => navigate('/admin/financials')} />
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
          colorMap={Object.fromEntries(Object.entries(roleColors).map(([k, v]) => [roleLabels[k] || k, v === 'bg-outline-variant' ? '#9ca3af' : v === 'bg-primary' ? CATEGORICAL_COLORS[0] : v === 'bg-secondary' ? CATEGORICAL_COLORS[2] : v === 'bg-tertiary-fixed-dim' ? CATEGORICAL_COLORS[3] : v === 'bg-tertiary' ? CATEGORICAL_COLORS[4] : CATEGORICAL_COLORS[5]]))}
        />

        <PieChartCard
          title="Deliveries by Status"
          data={deliveriesByStatus.map(([name, value]) => ({ name: statusLabels[name] || name, value }))}
          dataKey="value"
          categoryKey="name"
          height={280}
          emptyMessage="No delivery data available."
          colorMap={Object.fromEntries(Object.entries(statusColors).map(([k, v]) => [statusLabels[k] || k, v === 'bg-primary' ? CATEGORICAL_COLORS[0] : v === 'bg-secondary' ? '#059669' : v === 'bg-tertiary-fixed-dim' ? CATEGORICAL_COLORS[3] : v === 'bg-error' ? '#dc2626' : CATEGORICAL_COLORS[5]]))}
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
        subtitle="Flow of items through the current processing cycle."
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

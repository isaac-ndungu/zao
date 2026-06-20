import { useContext, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import { KpiSkeleton, CardSkeleton } from '../components/common/Skeleton'

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

  const maxRoleCount = useMemo(() => {
    if (!usersByRole.length) return 0
    return Math.max(...usersByRole.map(([, v]) => v))
  }, [usersByRole])

  const deliveriesByStatus = useMemo(() => {
    const statuses = data?.deliveries_by_status
    if (!statuses) return []
    return Object.entries(statuses).filter(([, v]) => v > 0)
  }, [data?.deliveries_by_status])

  const totalDeliveries = useMemo(() => {
    return deliveriesByStatus.reduce((s, [, v]) => s + v, 0)
  }, [deliveriesByStatus])

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

  const totalGrade = gradeDist.reduce((s, [, v]) => s + v, 0)

  if (loading) {
    return (
      <div>
        <header className="mb-8">
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Executive Overview</h2>
          <p className="text-on-surface-variant font-body-md">Real-time cooperative performance & operational health metrics.</p>
        </header>
        <KpiSkeleton count={5} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <CardSkeleton />
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
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
          <div className="flex justify-between items-center mb-6">
            <h4 className="font-headline-sm text-headline-sm">Users by Role</h4>
          </div>
          <div className="space-y-6">
            {usersByRole.length === 0 ? (
              <p className="text-on-surface-variant text-body-md">No user data available.</p>
            ) : usersByRole.map(([role, count]) => {
              const pct = maxRoleCount > 0 ? (count / maxRoleCount) * 100 : 0
              return (
                <div key={role} className="space-y-2">
                  <div className="flex justify-between text-label-md font-medium">
                    <span>{roleLabels[role] || role}</span>
                    <span className="font-data-mono">{formatNumber(count)}</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${roleColors[role] || 'bg-outline-variant'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
          <div className="flex justify-between items-center mb-6">
            <h4 className="font-headline-sm text-headline-sm">Deliveries by Status</h4>
            {totalDeliveries > 0 && (
              <div className="flex gap-2">
                {deliveriesByStatus.map(([status]) => (
                  <span key={status} className="flex items-center gap-1 text-[10px] uppercase font-bold text-on-surface-variant">
                    <span className={`w-2 h-2 rounded-full ${statusColors[status] || 'bg-outline'}`} />
                    {statusLabels[status] || status}
                  </span>
                ))}
              </div>
            )}
          </div>
          {deliveriesByStatus.length === 0 ? (
            <p className="text-on-surface-variant text-body-md">No delivery data available.</p>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="relative h-12 flex rounded-lg overflow-hidden border border-outline-variant/20">
                {deliveriesByStatus.map(([status, count]) => {
                  const pct = totalDeliveries > 0 ? (count / totalDeliveries) * 100 : 0
                  return (
                    <div
                      key={status}
                      className={`h-full ${statusColors[status] || 'bg-outline-variant'} flex items-center justify-center text-on-primary font-data-mono text-[11px]`}
                      style={{ width: `${pct}%` }}
                    >
                      {pct >= 15 ? `${Math.round(pct)}%` : ''}
                    </div>
                  )
                })}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="p-3 bg-surface border border-outline-variant rounded-lg">
                  <p className="text-[10px] uppercase font-bold text-on-surface-variant opacity-60">Total Deliveries</p>
                  <p className="font-data-mono text-lg text-primary">{totalDeliveries}</p>
                </div>
                <div className="p-3 bg-surface border border-outline-variant rounded-lg">
                  <p className="text-[10px] uppercase font-bold text-on-surface-variant opacity-60">Completed</p>
                  <p className="font-data-mono text-lg text-primary">
                    {data.deliveries_by_status?.completed || 0}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Grade Distribution from Analytics */}
      {gradeDist.length > 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mb-8">
          <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Grade Distribution</h4>
          <div className="space-y-3">
            {gradeDist.map(([grade, count]) => {
              const pct = totalGrade > 0 ? (count / totalGrade) * 100 : 0
              return (
                <div key={grade}>
                  <div className="flex justify-between text-label-md font-medium mb-1">
                    <span className="capitalize">{grade.toLowerCase()}</span>
                    <span className="font-data-mono text-on-surface-variant">{count?.toLocaleString()} kg</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mb-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h4 className="font-headline-sm text-headline-sm mb-1">Cycle Pipeline</h4>
            <p className="text-label-md text-on-surface-variant">
              Flow of items through the current processing cycle.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-0 relative overflow-hidden h-32 items-center px-4">
          {cyclePipeline.map((stage, i) => (
            <div
              key={stage.key}
              className={`funnel-stage ${stage.color} h-24 flex flex-col items-center justify-center ${i > 0 ? 'border-l border-white/20' : ''}`}
            >
              <span className={`text-[10px] font-bold uppercase ${stage.textColor}`}>
                {stage.label}
              </span>
              <span className={`font-data-mono text-headline-sm ${stage.valueColor}`}>
                {formatNumber(stage.value)}
              </span>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-4 gap-4 mt-6 text-center">
          {cyclePipeline.map((stage) => (
            <div key={stage.key} className="text-[11px] text-on-surface-variant">
              {pipelineDetail[stage.key]}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
